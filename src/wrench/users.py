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

import itertools
from typing import Iterable, Mapping, Union

from .models import Group, User


def unfold_group(group: Group, users_by_id: Mapping[str, User]) -> Iterable[User]:
    """
    Return all :class:`User` objects from the given `group`. `users_by_id` must be the cache containing all users in
    the system.
    """
    return [users_by_id[user_id] for user_id in group.members_ids]


def unfold_groups(recipients: Iterable[Union[User, Group]], users_by_id: Mapping[str, User]) -> Iterable[User]:
    """
    Return a sequence of :class:`User` objects with:

        * All :class:`User` objects from the given `recipients`
        * All :class:`User` objects members of the :class:`Group` objects present in the `recipients`

    `users_by_id` must be the cache containing all users in the system.
    """
    groups = (recipient for recipient in recipients if isinstance(recipient, Group))
    user_recipients = (recipient for recipient in recipients if isinstance(recipient, User))
    unfolded_groups = (unfold_group(group, users_by_id) for group in groups)
    users_in_groups = itertools.chain(*unfolded_groups)

    return list(user_recipients) + list(users_in_groups)
