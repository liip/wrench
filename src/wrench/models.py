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

from collections import namedtuple
from enum import Enum


class IdEqualityMixin:
    """
    Mixin that implements the __eq__ and __hash__ methods for classes that have an `id` attribute that should be used
    for equality testing.
    """
    def __eq__(self, other):
        """
        Return `True` if the two objects are of the same type and have the same id.
        """
        return type(self) == type(other) and self.id == other.id

    def __hash__(self):
        return hash(self.id)


class Resource(IdEqualityMixin,
               namedtuple('Resource', 'id name uri description username secret encrypted_secret tags')):
    pass


class Group(IdEqualityMixin, namedtuple('Group', 'id name members_ids')):
    def __str__(self):
        return self.name


class User(IdEqualityMixin, namedtuple('User', 'id username first_name last_name groups_ids gpg_key')):
    def __str__(self):
        return self.username


class GpgKey(IdEqualityMixin, namedtuple('GpgKey', 'id fingerprint armored_key')):
    pass


PermissionType = Enum('PermissionType', [('READ', 1), ('UPDATE', 7), ('OWNER', 15)])
PermissionModificationType = Enum('PermissionModificationType', 'create update delete')
Secret = namedtuple('Secret', 'resource recipient secret')
Permission = namedtuple('Permission', 'id resource recipient permission_type')
