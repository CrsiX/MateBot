#!/usr/bin/env python3

import typing
import logging
import argparse

from telegram.ext import (
    Updater, Dispatcher, CommandHandler,
    CallbackQueryHandler, InlineQueryHandler
)

from mate_bot import err
from mate_bot import log
from mate_bot import registry
from mate_bot.config import config
from mate_bot.commands.handler import FilteredChosenInlineResultHandler
from mate_bot.state.dbhelper import BackendHelper


class _SubcommandHelper:
    def __init__(self, args: argparse.Namespace, logger: logging.Logger):
        self.args = args
        self.logger = logger

    def __call__(self) -> int:
        raise NotImplementedError


class _Runner(_SubcommandHelper):
    handler_types = typing.Union[
        typing.Type[CommandHandler],
        typing.Type[CallbackQueryHandler],
        typing.Type[InlineQueryHandler],
        typing.Type[FilteredChosenInlineResultHandler]
    ]

    def __call__(self) -> int:
        BackendHelper._query_logger = logging.getLogger("database")

        updater = Updater(config["token"], use_context = True)

        self.logger.info("Adding error handler...")
        updater.dispatcher.add_error_handler(err.log_error)

        self.add_handler(updater.dispatcher, CommandHandler, registry.commands, False)
        self.add_handler(updater.dispatcher, CallbackQueryHandler, registry.callback_queries, True)
        self.add_handler(updater.dispatcher, InlineQueryHandler, registry.inline_queries, True)
        self.add_handler(updater.dispatcher, FilteredChosenInlineResultHandler, registry.inline_results, True)

        self.logger.info("Starting bot...")
        updater.start_polling()
        updater.idle()

        return 0

    def add_handler(self, dispatcher: Dispatcher, handler: handler_types, pool: dict, pattern: bool = True) -> None:
        """
        Add the executors from the given pool to the dispatcher using the given handler type

        :param dispatcher: Telegram's dispatcher to add the executor to
        :type dispatcher: telegram.ext.Dispatcher
        :param handler: type of the handler (subclass of ``telegram.ext.Handler``)
        :type handler: handler_types
        :param pool: collection of all executors for one handler type
        :type pool: dict
        :param pattern: switch whether the keys of the pool are patterns or names
        :type pattern: bool
        :return: None
        """

        self.logger.info(f"Adding {handler.__name__} executors...")
        for name in pool:
            if pattern:
                dispatcher.add_handler(handler(pool[name], pattern = name))
            else:
                dispatcher.add_handler(handler(name, pool[name]))

class MateBot:
    """
    MateBot application executor

    :param args: parsed program arguments as returned by ``parse_args``
    :type args: argparse.Namespace
    """

    _args: argparse.Namespace

    def __init__(self, args: argparse.Namespace):
        self._args = args
        log.setup()
        self.logger = logging.getLogger("runner")

        self.run = _Runner(args, self.logger)
        self.install = _Installer(args, self.logger)
        self.extract = _Extractor(args, self.logger)

        self.logger.debug(f"Created MateBotRunner object {self}")

    @staticmethod
    def setup() -> argparse.ArgumentParser:
        """
        Setup the ArgumentParser to provide the command-line interface

        :return: ArgumentParser
        :rtype: argparse.ArgumentParser
        """

        parser = argparse.ArgumentParser(
            description = "MateBot maintaining command-line interface"
        )

        parser.add_argument(
            "-v", "--verbose",
            help = "print out verbose information",
            dest = "verbose",
            action = "store_true"
        )

        subcommands = parser.add_subparsers(
            title = "available subcommands",
            dest = "command",
            required = True
        )

        run = subcommands.add_parser(
            "run",
            help = "run the MateBot program"
        )

        install = subcommands.add_parser(
            "install",
            help = "install the MateBot database and systemd service files"
        )

        database.add_argument(
            "-s", "--show",
            help = "show all data stored in the specified table",
            dest = "data",
            metavar = "table"
        )

        extract = subcommands.add_parser(
            "extract",
            help = "extract the raw data from the MateBot database"
        )

        return parser


if __name__ == "__main__":
    arguments = MateBot.setup().parse_args()
    exit(MateBot(arguments).start())
