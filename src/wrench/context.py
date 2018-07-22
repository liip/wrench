# wrench -- A CLI for Passbolt
# Copyright (C) 2018 Liip SA <wrench@liip.ch>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

import functools
from typing import Callable, Dict, Iterable, Optional  # noqa

from requests_gpgauthlib import GPGAuthSession

from .models import Group, User


def cached(func):
    """
    Store the result of the function call in the object `__cache` attribute so that subsequent calls to the function
    with the same parameters just return the cached value.
    """
    @functools.wraps(func)
    def inner(*args, **kwargs):
        obj = args[0]

        if not hasattr(obj, '__cache'):
            obj.__cache = {}

        cache_key = (func, args[1:], frozenset(kwargs.items()))
        if cache_key not in obj.__cache:
            obj.__cache[cache_key] = func(*args, **kwargs)

        return obj.__cache[cache_key]

    return inner


class Context:
    """
    Container for data that comes from Passbolt and that we don't want to retrieve over and over again in all methods
    that use them.
    """
    def __init__(self, session: GPGAuthSession, get_users_func: Callable[[GPGAuthSession], Iterable[User]],
                 get_groups_func: Callable[[GPGAuthSession], Iterable[Group]]) -> None:
        """
        The `get_users_func` and `get_groups_func` are callables that should take a `session` parameter and return an
        iterable of users and groups.
        """
        self.session = session
        self.get_users_func = get_users_func
        self.get_groups_func = get_groups_func
        self._users = None  # type: Optional[Iterable[User]]
        self._groups = None  # type: Optional[Iterable[Group]]
        self._users_by_id = None  # type: Optional[Dict[str, User]]
        self._groups_by_id = None  # type: Optional[Dict[str, Group]]

    @property  # type: ignore
    @cached
    def users(self) -> Iterable[User]:
        """
        Return an iterable of :class:`User` objects from Passbolt. The result is cached so calling this method multiple
        times will trigger only one request to Passbolt.
        """
        return self.get_users_func(self.session)

    def get_users_by(self, attr):
        return {getattr(user, attr): user for user in self.users}

    @property  # type: ignore
    @cached
    def users_by_id(self) -> Dict[str, User]:
        """
        Return a dict in the form `{id: user}` of the Passbolt users.
        """
        return {user.id: user for user in self.users}

    @property  # type: ignore
    @cached
    def users_by_name(self) -> Dict[str, User]:
        """
        Return a dict in the form `{username: user}` of the Passbolt users.
        """
        return {user.username: user for user in self.users}

    @property  # type: ignore
    @cached
    def groups(self) -> Iterable[Group]:
        """
        Return an iterable of :class:`Group` objects from Passbolt. The result is cached so calling this method multiple
        times will trigger only one request to Passbolt.
        """
        return self.get_groups_func(self.session)

    @property  # type: ignore
    @cached
    def groups_by_id(self) -> Dict[str, Group]:
        """
        Return a dict in the form `{id: group}` of the Passbolt groups.
        """
        return {group.id: group for group in self.groups}

    @property  # type: ignore
    @cached
    def groups_by_name(self) -> Dict[str, Group]:
        """
        Return a dict in the form `{group_name: group}` of the Passbolt groups.
        """
        return {group.name: group for group in self.groups}
