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

from typing import Any, Dict

from ..models import Group, Permission, Resource, Secret, User


def to_foreign_resource(resource: Resource, user: User) -> Dict[str, Any]:
    """
    Return a data dict representing a resource suitable to be used in Passbolt. Its structure is the following::

        {
            'id': '...',
            'name': '...',
            'secrets': [{'data': '...'}],
        }
    """
    secret = Secret(resource=resource, recipient=user, secret=resource.secret)
    secrets_dict = to_foreign_secret(secret)
    non_resource_fields = {'secret', 'tags'}

    return dict(
        {key: value for key, value in resource._asdict().items() if key not in non_resource_fields},
        **{'secrets': [secrets_dict]}
    )


def to_foreign_secret(shared_secret: Secret) -> Dict[str, str]:
    """
    Return a data dict representing a secret to share suitable to be used in Passbolt. Its structure is the following::

        {
            'user_id': '...',
            'resource_id': '...',
            'data': '...'
        }

    Where `x` is the given `index`. If `add_resource_syntax`, the syntax specific to the "add resource" action will be
    used, which is `Secret[x][user_id]` for example.
    """
    secret_dict = {
        'data': shared_secret.secret,
    }

    if shared_secret.recipient and shared_secret.recipient.id:
        secret_dict['user_id'] = shared_secret.recipient.id

    if shared_secret.resource and shared_secret.resource.id:
        secret_dict['resource_id'] = shared_secret.resource.id

    return secret_dict


def to_foreign_permission(permission: Permission) -> Dict[str, str]:
    """
    Return a data dict representing a permission, suitable to be used in Passbolt. Its structure is the following::

        {
            'isNew': 'true',
            'aco': 'Resource',
            'aco_foreign_key': '...',
            'aro': 'User',
            'aro_foreign_key': '...',
            'type': '...',
        }
    """
    return {
        'isNew': 'true',
        'aco': 'Resource',
        'aco_foreign_key': permission.resource.id,
        'aro': 'User' if isinstance(permission.recipient, User) else 'Group',
        'aro_foreign_key': permission.recipient.id,
        'type': str(permission.permission_type),
    }


def to_foreign_user(user: User) -> Dict[str, Any]:
    return {
        'gpgkey': {
            'id': user.gpg_key.id,
            'armored_key': user.gpg_key.armored_key,
            'fingerprint': user.gpg_key.fingerprint
        },
        'groups_users': [{'group_id': group.id, 'user_id': user.id} for group in user.groups_ids],
        'id': user.id,
        'username': user.username,
        'profile': {'first_name': user.first_name, 'last_name': user.last_name, 'user_id': user.id}
    }


def to_foreign_group(group: Group) -> Dict[str, Any]:
    return {
        'id': group.id,
        'name': group.name,
        'users': [{'id': member_id} for member_id in group.members_ids]
    }
