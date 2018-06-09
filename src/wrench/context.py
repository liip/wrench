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

from typing import Callable, Dict, Iterable

from requests_gpgauthlib import GPGAuthSession

from .models import Group, User


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
        self._users = None  # type: Iterable[User]
        self._groups = None  # type: Iterable[Group]
        self._users_by_id = None  # type: Dict[str, User]
        self._groups_by_id = None  # type: Dict[str, Group]

    @property  # type: ignore
    def users(self) -> Iterable[User]:
        """
        Return an iterable of :class:`User` objects from Passbolt. The result is cached so calling this method multiple
        times will trigger only one request to Passbolt.
        """
        if self._users is None:
            self._users = self.get_users_func(self.session)

        return self._users

    @property  # type: ignore
    def users_by_id(self) -> Dict[str, User]:
        """
        Return a dict in the form `{id: user}` of the Passbolt users.
        """
        if self._users_by_id is None:
            self._users_by_id = {user.id: user for user in self.users}

        return self._users_by_id

    @property  # type: ignore
    def groups(self) -> Iterable[Group]:
        """
        Return an iterable of :class:`Group` objects from Passbolt. The result is cached so calling this method multiple
        times will trigger only one request to Passbolt.
        """
        if self._groups is None:
            self._groups = self.get_groups_func(self.session)

        return self._groups

    @property  # type: ignore
    def groups_by_id(self) -> Dict[str, Group]:
        """
        Return a dict in the form `{id: group}` of the Passbolt groups.
        """
        if self._groups_by_id is None:
            self._groups_by_id = {group.id: group for group in self.groups}

        return self._groups_by_id
