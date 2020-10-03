"""
MateBot command executor classes for /pay and its callback queries
"""

import typing

import telegram

from mate_bot.config import config
from mate_bot.commands.base import BaseCommand, BaseCallbackQuery
from mate_bot.parsing.types import amount as amount_type
from mate_bot.parsing.actions import JoinAction
from mate_bot.parsing.util import Namespace
from mate_bot.state.user import MateBotUser
from mate_bot.state.collectives import BaseCollective


PAYMENT_ARGUMENTS = typing.Union[
    int,
    typing.Tuple[int, MateBotUser, telegram.Bot],
    typing.Tuple[MateBotUser, int, str, telegram.Message]
]


class Pay(BaseCollective):
    """
    Payment class to get money from the community

    :param arguments: either internal ID or tuple of arguments for creation or forwarding
    :raises ValueError: when a supplied argument has an invalid value
    :raises TypeError: when a supplied argument has the wrong type
    :raises RuntimeError: when the internal collective ID points to a payment operation
    """

    _communistic = False

    _ALLOWED_COLUMNS = ["active"]

    def __init__(self, arguments: PAYMENT_ARGUMENTS):

        if isinstance(arguments, int):
            self._id = arguments
            self.update()
            if self._communistic:
                raise RuntimeError("Remote record is no payment request")

        elif isinstance(arguments, tuple):
            if len(arguments) == 3:

                payment_id, user, bot = arguments

            elif len(arguments) == 4:

                user, amount, reason, message = arguments
                if not isinstance(user, MateBotUser):
                    raise TypeError("Expected MateBotUser object as first element")
                if not isinstance(amount, int):
                    raise TypeError("Expected int object as second element")
                if not isinstance(reason, str):
                    raise TypeError("Expected str object as third element")
                if not isinstance(message, telegram.Message):
                    raise TypeError("Expected telegram.Message as fourth element")

                self._creator = user.uid
                self._amount = amount
                self._description = reason
                self._externals = None
                self._active = True

                self._create_new_record()

                reply = message.reply_markdown(self.get_markdown(), reply_markup=self._gen_inline_keyboard())
                self.register_message(reply.chat_id, reply.message_id)

            else:
                raise TypeError("Expected three or four arguments for the tuple")

        else:
            raise TypeError("Expected int or tuple of arguments")

    def get_votes(self) -> typing.Tuple[typing.List[MateBotUser], typing.List[MateBotUser]]:
        """
        Get the approving and disapproving voters as lists of MateBotUsers

        :return: the returned tuple contains a list of approving voters and disapproving voters each
        :rtype: typing.Tuple[typing.List[MateBotUser], typing.List[MateBotUser]]
        """

        approved = []
        disapproved = []

        for entry in self._get_remote_joined_record()[1]:
            if entry["collectives_users.id"] is None or entry["vote"] is None:
                continue
            user = MateBotUser(entry["users_id"])
            if entry["vote"]:
                approved.append(user)
            else:
                disapproved.append(user)

        return approved, disapproved

    def get_markdown(self, status: typing.Optional[str] = None) -> str:
        """
        Generate the full message text as markdown string

        :param status: extended status information about the payment request (Markdown supported)
        :type status: typing.Optional[str]
        :return: full message text as markdown string
        :rtype: str
        """

        approved, disapproved = self.get_votes()
        approved = ", ".join(map(lambda u: u.name, approved)) or "None"
        disapproved = ", ".join(map(lambda u: u.name, disapproved)) or "None"

        markdown = f"*Payment request by {self.creator.name}*\n"
        markdown += f"\nAmount: {self.amount / 100:.2f}€\nReason: {self.description}\n"
        markdown += f"\nApproved: {approved}\nDisapproved: {disapproved}\n\n"

        if status is not None:
            markdown += status
        elif self.active:
            markdown += "_The payment request is currently active._"
        else:
            markdown += "_The payment request has been closed._"

        return markdown

    def _gen_inline_keyboard(self) -> telegram.InlineKeyboardMarkup:
        """
        Generate the inline keyboard to control the payment operation

        :return: inline keyboard using callback data strings
        :rtype: telegram.InlineKeyboardMarkup
        """

        if not self.active:
            return telegram.InlineKeyboardMarkup([])

        def f(c):
            return f"pay {c} {self.get()}"

        return telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton("APPROVE", callback_data=f("approve")),
                telegram.InlineKeyboardButton("DISAPPROVE", callback_data=f("disapprove")),
            ],
            [
                telegram.InlineKeyboardButton("FORWARD", switch_inline_query_current_chat=f"{self.get()} ")
            ]
        ])

    def close(self) -> bool:
        """
        Check if the payment is fulfilled, then close it and perform the transactions

        The returned value determines whether the payment request is still
        valid and open for further votes (``True``) or closed due to enough
        approving / disapproving votes (``False``). Use it to easily
        determine the status for the returned message to the user(s).

        :return: whether the payment request is still open for further votes
        :rtype: bool
        """

        approved, disapproved = self.get_votes()

        if len(approved) - len(disapproved) >= config["community"]["payment-consent"]:
            return False

        elif len(disapproved) - len(approved) >= config["community"]["payment-denial"]:
            return False

        else:
            return True


class PayCommand(BaseCommand):
    """
    Command executor for /pay

    Note that the majority of the functionality is located in the query handler.
    """

    def __init__(self):
        super().__init__("pay", "")
        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("reason", action=JoinAction, nargs="*")

        self.parser.new_usage().add_argument(
            "subcommand",
            choices=("stop", "show"),
            type=lambda x: str(x).lower()
        )

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = MateBotUser(update.effective_message.from_user)

        if args.subcommand is None:
            if Pay.has_user_active_collective(user):
                update.effective_message.reply_text("You already have a collective in progress.")
                return

            Pay((user, args.amount, args.reason, update.effective_message))
            return

        update.effective_message.reply_text("Subcommands are not yet supported.")


class PayCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /pay
    """

    def __init__(self):
        super().__init__("pay")

    def _get_payment(self, query: telegram.CallbackQuery) -> typing.Optional[Pay]:
        """
        Retrieve the Pay object based on the callback data

        :param query: incoming Telegram callback query with its attached data
        :type query: telegram.CallbackQuery
        :return: Pay object that handles the current collective
        :rtype: typing.Optional[Pay]
        """

        if self.data is None or self.data.strip() == "":
            query.answer("Empty stripped callback data!", show_alert=True)
            return

        try:
            vote, payment_id = self.data.split(" ")
        except IndexError:
            query.answer("Invalid callback data format!", show_alert=True)
            raise

        try:
            payment_id = int(payment_id)
        except ValueError:
            query.answer("Wrong payment ID format!", show_alert=True)
            raise

        try:
            pay = Pay(payment_id)
            if pay.active:
                return pay
            query.answer("The pay is not active anymore!")
        except IndexError:
            query.answer("The payment does not exist in the database!", show_alert=True)
            raise

    def run(self, update: telegram.Update) -> None:
        """
        Check and process the incoming callback query

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        payment = self._get_payment(update.callback_query)
        if payment is not None:
            user = MateBotUser(update.callback_query.from_user)
            if payment.creator == user:
                update.callback_query.answer(
                    "You can't vote on your own payment request.",
                    show_alert=True
                )
                return

            if self.data.startswith("approve"):
                vote = True
            elif self.data.startswith("disapprove"):
                vote = False
            else:
                update.callback_query.answer("Invalid callback query data!", show_alert=True)
                raise ValueError(f"Invalid callback query data: '{self.data}'")

            success = payment.add_user(user, vote)
            if not success:
                update.callback_query.answer("You already voted on this payment request.")
                return

            update.callback_query.answer("You successfully voted on this payment request.")
            active = payment.close()
            if not active:
                payment.edit_all_messages(
                    payment.get_markdown(),
                    payment._gen_inline_keyboard(),
                    update.callback_query.bot
                )


"""
def pay_query(_, update):
    sender, selected_pay, cmd, sender_id, action = get_data_from_query(update, pays)

    approved = selected_pay.approved
    disapproved = selected_pay.disapproved
    changed = False

    if sender == selected_pay.creator:
        if action == "disapprove":
            del pays[sender_id]
            selected_pay.message.edit_text("Pay canceled (the creator disapproves himself).")
            return
    elif action == "approve":
        if sender not in approved:
            approved.append(sender)
            changed = True
        if sender in disapproved:
            disapproved.remove(sender)
    elif action == "disapprove":
        if sender in approved:
            approved.remove(sender)
        if sender not in disapproved:
            disapproved.append(sender)
            changed = True

    def check_list(users):
        if len(users) < config['pay-min-users']:
            return False

        has_member = False
        for user in users:
            if user['id'] in config['members']:
                has_member = True
                break

        return has_member

    if check_list(selected_pay.disapproved):
        del pays[sender_id]
        selected_pay.message.edit_text("DISAPPROVED\n" + str(selected_pay))
    elif check_list(selected_pay.approved):
        del pays[sender_id]
        #create_transaction(selected_pay.creator, selected_pay.amount,
        # "pay for {}, approved by {}".format(selected_pay.reason, user_list_to_string(selected_pay.approved)))
        selected_pay.message.edit_text("APPROVED\n" + str(selected_pay))
    elif changed:
        selected_pay.message.edit_text(str(selected_pay), reply_markup=selected_pay.message_markup)
    else:
        update.callback_query.answer()
"""
