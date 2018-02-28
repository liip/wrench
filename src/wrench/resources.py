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
from typing import Any, Dict, Iterable, Sequence

from gnupg import GPG

from . import utils

Resource = namedtuple('Resource', 'id name uri description username secret')


def resource_matches(resource: Resource, terms: str) -> bool:
    """
    Return `True` if terms are found in the given resource.
    """
    return any(terms in getattr(resource, attr) for attr in ('name', 'username', 'uri', 'description'))


def to_resource(resource_record: Dict[str, Any]) -> Resource:
    """
    Create a `Resource` object with values from the given `resource_dict` common with the attributes from the
    `Resource` type.
    """
    return utils.dict_to_namedtuple(Resource, resource_record, secret=resource_record['secrets'][0]['data'])


def resource_dicts_to_resources(resource_records: Iterable[Dict[str, Any]]) -> Sequence[Resource]:
    """
    Return a sequence of `Resource` objects from the given resource dicts list. The resource dicts list is expected to
    be in the following format: [{'Resource': {'name': ...}, 'Secret': [{'data': 'encrypted secret'}]}]
    """
    return [to_resource(record) for record in resource_records]


def search_resources(resources: Iterable[Resource], terms: str) -> Sequence[Resource]:
    """
    Return a sequence of resources matching the given `terms`.
    """
    return [resource for resource in resources if resource_matches(resource, terms)]


def decrypt_resource(resource: Resource, gpg: GPG) -> Resource:
    """
    Return a new `Resource` object with its field `secret` decrypted.
    """
    return Resource(**dict(resource._asdict(), secret=utils.decrypt(resource.secret, gpg)))
