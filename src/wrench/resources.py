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
from typing import Iterable, Sequence

from gnupg import GPG

from . import utils

Resource = namedtuple('Resource', 'id name uri description username secret')
PermissionType = Enum('PermissionType', [('READ', 1), ('UPDATE', 7), ('OWNER', 15)])
SharedSecret = namedtuple('SharedSecret', 'resource user permission_type secret')


def resource_matches(resource: Resource, terms: str) -> bool:
    """
    Return `True` if terms are found in the given resource.
    """
    if not terms:
        return True

    terms = terms.casefold()
    values = (getattr(resource, attr) for attr in ('name', 'username', 'uri', 'description'))

    return any(terms in value.casefold() for value in filter(None, values))


def search_resources(resources: Iterable[Resource], terms: str) -> Sequence[Resource]:
    """
    Return a sequence of resources matching the given `terms`.
    """
    return [resource for resource in resources if resource_matches(resource, terms)]


def decrypt_resource(resource: Resource, gpg: GPG) -> Resource:
    """
    Return a new `Resource` object with its field `secret` decrypted.
    """
    return resource._replace(secret=utils.decrypt(resource.secret, gpg))
