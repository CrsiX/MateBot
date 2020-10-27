"""
MateBot testing suite
"""

import sys
import typing
import unittest
import functools


DEFAULT_WEIGHT = 0


def significance(
        weight_or_fn: typing.Union[typing.Callable, int],
        optional_weight: typing.Optional[int] = None
) -> typing.Callable:
    """
    Wrap around a callable to add a property ``significance`` to it

    This property can be used to sort and compare different functions or methods
    based on their "weight". A higher weight should be executed earlier, a lower
    weight later. This feature is used to sort different test cases.

        >>> from test import significance, DEFAULT_WEIGHT
        >>> @significance
        ... def f():
        ...     pass
        ...
        >>> @significance(42)
        ... def g():
        ...     pass
        ...
        >>> f.significance == DEFAULT_WEIGHT
        True
        >>> g.significance
        42
        >>>

    :param weight_or_fn: either function that should be wrapped or integer that reflects the
        significance / importance of the function that should be wrapped up
    :type weight_or_fn: typing.Union[typing.Callable, int]
    :param optional_weight: optional weight of the function or feature that has been wrapped up
    :type optional_weight: typing.Optional[int]
    :return: wrapped function that provides a property ``significance`` now
    :rtype: typing.Callable
    :raises TypeError: when the first argument is not integer nor callable
    :raises ValueError: when the first argument is an integer and the second not ``None``
    """


class EnvironmentTests(unittest.TestCase):
    """
    Testing suite for the environment the MateBot is running in
    """

    def test_os(self):
        self.assertEqual(sys.platform, "linux")

    def test_py_version(self):
        self.assertEqual(sys.version_info.major, 3)
        self.assertGreaterEqual(sys.version_info.minor, 7)

    @staticmethod
    def test_imports():
        import pytz
        import tzlocal
        import telegram
        import pymysql
        del pytz, tzlocal, telegram, pymysql

    def test_config(self):
        from mate_bot.config import config

        mandatory_keys = [
            ("general", dict),
            ("token", str),
            ("chats", dict),
            ("community", dict),
            ("database", dict),
            ("consumables", list)
        ]

        for k in mandatory_keys:
            self.assertIn(k[0], config)
            self.assertIsInstance(config[k[0]], k[1])

        mandatory_subkeys = [
            ("general:max-amount", int),
            ("general:max-consume", int),
            ("chats:internal", int),
            ("community:payment-consent", int),
            ("community:payment-denial", int),
            ("database:host", str),
            ("database:db", str),
            ("database:user", str),
            ("database:password", str)
        ]

        for k in mandatory_subkeys:
            first, second = k[0].split(":")
            self.assertIn(second, config[first])
            self.assertIsInstance(config[first][second], k[1])

        mandatory_consumable_keys = [
            ("name", str),
            ("description", str),
            ("price", int),
            ("messages", list),
            ("symbol", str)
        ]

        for consumable in config["consumables"]:
            for k in mandatory_consumable_keys:
                self.assertIn(k[0], consumable)
                self.assertIsInstance(consumable[k[0]], k[1])

    def test_significance(self):
        @significance
        def f():
            pass

        @significance(42)
        def g():
            pass

        self.assertEqual(f.significance, DEFAULT_WEIGHT)
        self.assertEqual(g.significance, 42)


class CollectivesTests(unittest.TestCase):
    """
    Testing suite for the package :mod:`mate_bot.collectives`
    """

    pass


class CommandsTests(unittest.TestCase):
    """
    Testing suite for the package :mod:`mate_bot.commands`
    """

    pass


class ParsingTests(unittest.TestCase):
    """
    Testing suite for the package :mod:`mate_bot.parsing`
    """

    pass


class StateTests(unittest.TestCase):
    """
    Testing suite for the package :mod:`mate_bot.state`
    """

    pass

    def test_db_schema_conversion(self):
        pass

    def test_db_execute(self):
        pass

    def test_db_checking(self):
        pass

    def test_db_rebuild_database(self):
        pass

    def test_db_get_values_by_key_manually(self):
        pass

    def test_db_get_values_by_key(self):
        pass

    def test_db_get_value_manually(self):
        pass

    def test_db_get_value(self):
        pass

    def test_db_set_value_manually(self):
        pass

    def test_db_set_value(self):
        pass

    def test_db_set_all_manually(self):
        pass

    def test_db_set_all(self):
        pass

    def test_db_insert_manually(self):
        pass

    def test_db_insert(self):
        pass

    def test_db_extract_all(self):
        pass


if __name__ == "__main__":
    unittest.main()
