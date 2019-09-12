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

from typing import Any, Dict, Mapping, Union  # noqa

from .. import utils
from ..models import GpgKey, Group, Permission, PermissionType, Resource, User


def to_local_resource(data: Dict[str, Any]) -> Resource:
    """
    Return a :class:`Resource` object created from the values from the given `data`. which is expected to be a dict
    with the following keys (extra fields are ignored)::

        ('id', 'name', 'uri', 'description', 'username', 'tags')

    """
    tags = [tag['slug'] for tag in data.pop('tags', [])]

    # Make sure the exception is the same whether the secret or any other field is missing
    try:
        encrypted_secret = data['secrets'][0]['data']
    except (IndexError, KeyError):
        encrypted_secret = None

    resource_data = dict(data, secret=None, encrypted_secret=encrypted_secret, tags=tags)

    # Passbolt sometimes adds \n characters at the end of some fields, make sure we strip them
    for field in ('name', 'description'):
        try:
            resource_data[field] = resource_data[field].strip() if resource_data[field] is not None else None
        except KeyError:
            pass

    return utils.dict_to_namedtuple(Resource, resource_data)


def to_local_user(user_data: Dict[str, Any]) -> User:
    """
    Return a :class:`User` object created from the given `user_data` dict, which is expected to have the following
    structure::

        {
            'id': '...',
            'gpgkey': {'id': '...', 'fingerprint': '...', 'armored_key': '...'},
            'groups_users': [{'id': '...'}],
            'username': '...',
            'profile': {'first_name': '...', 'last_name': '...'}
        }
    """
    # Users might not have a gpgkey set if they've been invited but have not yet created their account
    gpg_key = utils.dict_to_namedtuple(GpgKey, user_data['gpgkey']) if user_data['gpgkey'] else None
    groups_ids = [group['id'] for group in user_data['groups_users']]
    user = User(id=user_data['id'], username=user_data['username'], first_name=user_data['profile']['first_name'],
                last_name=user_data['profile']['last_name'], groups_ids=groups_ids, gpg_key=gpg_key)

    return user


def to_local_group(group_data: Dict[str, Any]) -> Group:
    """
    Return a :class:`Group` object created from the given `group_data` dict, which is expected to have the following
    structure::

        {
            'users': [{'id': '...'}]
            'id': '...',
            'name': '...'
        }
    """
    members = [member['id'] for member in group_data.get('users', [])]
    group = utils.dict_to_namedtuple(Group, group_data, members_ids=members)

    return group


def to_local_permission(permission_data: Mapping[str, Any], groups_cache: Mapping[str, Group],
                        users_cache: Mapping[str, User]) -> Permission:
    """
    Return a :class:`Permission` object created from the given `permission_data` dict, and populated with the
    `groups_cache` and `users_cache` to match ids to real objects. The `resource` attribute of the returned
    `Permission` object will only have its id populated.
    """
    resource_id = permission_data['aco_foreign_key']
    resource = Resource(id=resource_id, name=None, uri=None, description=None, username=None, encrypted_secret=None,
                        secret=None, tags=[])
    permission_type = PermissionType(int(permission_data['type']))

    if permission_data['aro'] == 'User':
        cache = users_cache  # type: Union[Mapping[str, User], Mapping[str, Group]]
    else:
        cache = groups_cache

    recipient = cache[permission_data['aro_foreign_key']]

    return Permission(id=permission_data['id'], resource=resource, recipient=recipient, permission_type=permission_type)
