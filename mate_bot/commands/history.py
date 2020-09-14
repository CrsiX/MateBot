import argparse

import telegram

from mate_bot import state
from mate_bot.args.types import natural as natural_type
from mate_bot.args.actions import MutExAction
from mate_bot.commands.base import BaseCommand


class HistoryCommand(BaseCommand):
    """
    Command executor for /history
    """

    @staticmethod
    def _handle_export(args: argparse.Namespace, update: telegram.Update) -> None:
        """
        Handle the request to export the full transaction log of a user

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        update.effective_message.reply_text("Exporting is not supported yet.")

    @staticmethod
    def _handle_report(args: argparse.Namespace, update: telegram.Update) -> None:
        """
        Handle the request to report the most current transaction entries of a user

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = state.MateBotUser(update.effective_message.from_user)
        logs = state.TransactionLog(user, args.length).to_string()
        log = "\n".join(logs)
        heading = f"Transaction history for {user.name}:\n```"
        if len(logs) == 0:
            update.effective_message.reply_text("You don't have any registered transactions yet.")
            return

        if update.effective_message.chat.type != "private":

            text = f"{heading}\n{log}```"
            if len(text) > 4096:
                update.effective_message.reply_text(
                    "Your requested transaction logs are too long. Try a smaller "
                    "number of entries or execute this command in private chat again."
                )
            else:
                update.effective_message.reply_markdown_v2(text)

        else:

            text = f"{heading}\n{log}```"
            if len(text) < 4096:
                update.effective_message.reply_markdown_v2(text)
                return

            results = [heading]
            for entry in logs:
                if len("\n".join(results + [entry])) > 4096:
                    results.append("```")
                    update.effective_message.reply_markdown_v2("\n".join(results))
                    results = ["```"]
                results.append(entry)

            if len(results) > 0:
                update.effective_message.reply_markdown_v2("\n".join(results + ["```"]))

    def __init__(self):
        super().__init__("history", "")
        mut = self.parser.add_argument("length_export", action=MutExAction, nargs="?")
        mut.add_action(self.parser.add_argument("length", nargs="?", default=10, type=natural_type))
        mut.add_action(self.parser.add_argument("export", nargs="?", type=str, choices=("json", "csv")))

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if args.export is None:
            self._handle_report(args, update)
        else:
            self._handle_export(args, update)
