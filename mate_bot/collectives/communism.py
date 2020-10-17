"""
MateBot communisms to divide costs on many different users
"""

import typing
import logging

import telegram

from mate_bot.collectives.base import BaseCollective, COLLECTIVE_ARGUMENTS
from mate_bot.state.transactions import Transaction


logger = logging.getLogger("collectives")


class Communism(BaseCollective):
    """
    Communism class to collect money from various other persons

    The constructor of this class accepts two different argument
    types. You can specify a single integer to get the Communism object
    that matches a remote record where the integer is the internal
    collectives ID. Alternatively, you can specify a tuple containing
    three objects: the creator of the new Communism as a MateBotUser
    object, the amount of the communism as integer measured in Cent
    and the description of the communism as string. While being optional
    in the database, you have to specify at least three chars as reason.

    :param arguments: either internal ID or tuple of arguments for creation or forwarding
    :raises ValueError: when a supplied argument has an invalid value
    :raises TypeError: when a supplied argument has the wrong type
    :raises RuntimeError: when the collective ID doesn't match the class definition
        or when the class did not properly define its collective type using the class
        attribute ``_communistic`` (which is ``None`` by default and should be set properly)
    """

    _communistic = True

    _ALLOWED_COLUMNS = ["externals", "active"]

    def __init__(self, arguments: COLLECTIVE_ARGUMENTS):
        self._price = 0
        self._fulfilled = None
        super().__init__(arguments)

        if isinstance(arguments, tuple):
            user = self._handle_tuple_constructor_argument(arguments, 0)
            if user is not None:
                self.add_user(user)

    def _get_basic_representation(self) -> str:
        """
        Retrieve the core information for the communism description message

        The returned string may be formatted using Markdown. The string
        should be suitable to be re-used inside :meth:`get_markdown`.

        :return: communism description message as pure text
        :rtype: str
        """

        usernames = ', '.join(self.get_users_names()) or "None"

        return (
            f"*Communism by {self.creator.name}*\n\n"
            f"Reason: {self.description}\n"
            f"Amount: {self.amount / 100 :.2f}€\n"
            f"Externals: {self.externals}\n"
            f"Joined users: {usernames}\n"
        )

    def get_markdown(self, status: typing.Optional[str] = None) -> str:
        """
        Generate the full message text as markdown string

        :param status: extended status information (ignored in this implementation)
        :type status: typing.Optional[str]
        :return: full message text as markdown string
        :rtype: str
        """

        markdown = self._get_basic_representation()

        if self.active:
            markdown += "\n_The communism is currently active._"
        elif not self.active:
            markdown += "\n_The communism has been closed._"
        elif self._fulfilled is not None:
            if self._fulfilled:
                markdown += "\n_The communism was closed. All transactions have been processed._"
                if self._externals > 0:
                    markdown += (
                        f"\n\n{self._price / 100:.2f}€ must be collected from each "
                        f"external user by {self.creator.name}."
                    )
                else:
                    markdown += f"\n\nEvery joined user paid {self._price / 100:.2f}€."
            else:
                markdown += "\n_The communism was aborted. No transactions have been processed._"

        return markdown

    def _get_inline_keyboard(self) -> telegram.InlineKeyboardMarkup:
        """
        Get the inline keyboard to control the communism

        :return: inline keyboard using callback data strings
        :rtype: telegram.InlineKeyboardMarkup
        """

        if not self.active:
            return telegram.InlineKeyboardMarkup([])

        def f(c):
            return f"communism {c} {self.get()}"

        return telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton("JOIN / LEAVE", callback_data = f("toggle")),
            ],
            [
                telegram.InlineKeyboardButton("FORWARD", switch_inline_query_current_chat = f"{self.get()} ")
            ],
            [
                telegram.InlineKeyboardButton("EXTERNALS +", callback_data = f("increase")),
                telegram.InlineKeyboardButton("EXTERNALS -", callback_data = f("decrease")),
            ],
            [
                telegram.InlineKeyboardButton("ACCEPT", callback_data = f("accept")),
                telegram.InlineKeyboardButton("CANCEL", callback_data = f("cancel")),
            ]
        ])

    def close(self, bot: typing.Optional[telegram.Bot] = None) -> bool:
        """
        Close the collective operation and perform all transactions

        :param bot: optional Telegram Bot object that sends transaction logs to some chat(s)
        :type bot: typing.Optional[telegram.Bot]
        :return: success of the operation
        :rtype: bool
        """

        users = self.get_users()
        participants = self.externals + len(users)
        if participants == 0:
            return False

        self._price = self.amount // participants

        # Avoiding too small amounts by letting everyone pay one Cent more
        if self.amount % participants:
            self._price += 1

        for member in users:
            if member == self.creator:
                continue

            Transaction(
                member,
                self.creator,
                self._price,
                f"communism: {self.description} ({self.get()})"
            ).commit(bot)

        self.active = False
        return True

    def accept(self, bot: telegram.Bot) -> bool:
        """
        Accept the collective operation, perform all transactions and update the message

        :param bot: Telegram Bot object
        :type bot: telegram.Bot
        :return: success of the operation
        :rtype: bool
        """

        if not self.close(bot):
            return False

        self._fulfilled = True
        self.edit_all_messages(self.get_markdown(), self._get_inline_keyboard(), bot)
        [self.unregister_message(c, m) for c, m in self.get_messages()]

        return True

    def cancel(self, bot: telegram.Bot) -> bool:
        """
        Cancel the current pending communism operation without fulfilling the transactions

        :param bot: Telegram Bot object
        :type bot: telegram.Bot
        :return: success of the operation
        :rtype: bool
        """

        if not self._abort():
            return False

        self._fulfilled = False
        self.edit_all_messages(self.get_markdown(), self._get_inline_keyboard(), bot)
        [self.unregister_message(c, m) for c, m in self.get_messages()]

        return True

    @property
    def externals(self) -> int:
        """
        Get and set the number of external users for the communism
        """

        return self._externals

    @externals.setter
    def externals(self, new: int) -> None:
        if not isinstance(new, int):
            raise TypeError("Expected integer")
        if new < 0:
            raise ValueError("External user count can't be negative")
        if abs(self._externals - new) > 1:
            raise ValueError("External count must be increased or decreased by 1")

        self._externals = new
        self._set_remote_value("externals", new)