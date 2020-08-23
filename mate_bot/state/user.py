#!/usr/bin/env python3

import typing
import datetime
import telegram

from .dbhelper import execute as _execute


class MateBotUser:
    """
    MateBotUser convenience class storing all information about a user

    Specify a Telegram User object to initialize this object. It will
    fetch all available data from the database in the background.
    Do not cache these values for consistency reasons.
    """

    def __init__(self, user: telegram.User):
        """
        :param user: the Telegram user to create a MateBot user for
        :type user: telegram.User
        """

        self._user = user

        state, values = _execute("SELECT * FROM users WHERE tid=%s", (self._user.id,))

        if state == 0 and len(values) == 0:
            _execute(
                "INSERT INTO users (tid, username, name) VALUES (%s, %s, %s)",
                (self._user.id, self._user.name, self._user.full_name)
            )

            state, values = _execute("SELECT * FROM users WHERE tid=%s", (self._user.id,))

        if state == 1 and len(values) == 1:
            record = values[0]
            self._id = record["id"]
            self._name = record["name"]
            self._username = record["username"]
            self._balance = record["balance"]
            self._permission = record["permission"]
            self._created = record["tscreated"]
            self._accessed = record["tsaccessed"]

            if self._name != self._user.full_name:
                self._name = self._update_record("name", self._user.full_name)

            if self._username != self._user.name:
                self._username = self._update_record("username", self._user.name)

    def __eq__(self, other) -> bool:
        if isinstance(other, type(self)):
            return self.uid == other.uid and self.tid == other.tid
        return False

    def _update_record(self, column: str, value: typing.Union[str, int, bool]) -> typing.Union[str, int]:
        """
        Update a value in the column of the current user record in the database

        :param column: name of the database column
        :type column: str
        :param value: value to be set for the current user in the specified column
        :type value: str, int or bool
        :return: str or int
        """

        if isinstance(value, str):
            value = "'{}'".format(value)
        if isinstance(value, float):
            if value.is_integer():
                value = int(value)
            else:
                raise TypeError("No floats allowed")
        if not isinstance(value, (bool, int)):
            raise TypeError("Unsupported type")

        if column not in ["username", "name", "balance", "permission"]:
            raise RuntimeError("Operation not allowed")

        _execute(
            "UPDATE users SET %s=%s WHERE tid=%s",
            (column, value, self._user.id)
        )

        state, result = _execute(
            "SELECT %s, tsaccessed FROM users WHERE tid=%s",
            (column, self._user.id)
        )
        self._accessed = result[0]["tsaccessed"]
        return result[0][column]

    @property
    def user(self) -> telegram.User:
        return self._user

    @property
    def uid(self) -> int:
        return self._id

    @property
    def tid(self) -> int:
        return self._user.id

    @property
    def username(self) -> str:
        return self._username

    @property
    def name(self) -> str:
        return self._name

    @property
    def balance(self) -> int:
        return self._balance

    @property
    def permission(self) -> bool:
        return bool(self._permission)

    @property
    def created(self) -> datetime.datetime:
        return self._created

    @property
    def accessed(self) -> datetime.datetime:
        return self._accessed

    @permission.setter
    def permission(self, new: bool):
        self._permission = self._update_record("permission", bool(new))