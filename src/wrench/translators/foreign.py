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


def to_foreign_resource(resource: Resource) -> Dict[str, Any]:
    """
    Return a data dict representing a resource suitable to be used in Passbolt. Its structure is the following::

        {
            'Resource[id]': '...',
            'Resource[name]': '...',
            'Secret[0][data]': '...',
        }
    """
    secret = Secret(resource=resource, recipient=None, secret=resource.secret)
    secrets_dict = to_foreign_secret(secret, 0, add_resource_syntax=True)

    return dict(
        {'Resource[{}]'.format(key): value for key, value in resource._asdict().items() if key != 'secret'},
        **secrets_dict
    )


def to_foreign_secret(shared_secret: Secret, index: int, add_resource_syntax: bool = False) -> Dict[str, str]:
    """
    Return a data dict representing a secret to share suitable to be used in Passbolt. Its structure is the following::

        {
            'Secrets[x][Secret][user_id]': '...',
            'Secrets[x][Secret][resource_id]': '...',
            'Secrets[x][Secret][data]': '...'
        }

    Where `x` is the given `index`. If `add_resource_syntax`, the syntax specific to the "add resource" action will be
    used, which is `Secret[x][user_id]` for example.
    """
    secret_key_syntax = 'Secret[{}]' if add_resource_syntax else 'Secrets[{}][Secret]'
    secret_key = secret_key_syntax.format(index)
    secret_dict = {
        secret_key + '[data]': shared_secret.secret,
    }

    if shared_secret.recipient and shared_secret.recipient.id:
        secret_dict[secret_key + '[user_id]'] = shared_secret.recipient.id

    if shared_secret.resource and shared_secret.resource.id:
        secret_dict[secret_key + '[resource_id]'] = shared_secret.resource.id

    return secret_dict


def to_foreign_permission(permission: Permission, index: int) -> Dict[str, str]:
    """
    Return a data dict representing a permission, suitable to be used in Passbolt. Its structure is the following::

        {
            'Permissions[x][Permission][isNew]': 'true',
            'Permissions[x][Permission][aco]': 'Resource',
            'Permissions[x][Permission][aco_foreign_key]': '...',
            'Permissions[x][Permission][aro]': 'User',
            'Permissions[x][Permission][aro_foreign_key]': '...',
            'Permissions[x][Permission][type]': '...',
        }
    """
    permission_key = 'Permissions[{}][Permission]'.format(index)

    return {
        permission_key + '[isNew]': 'true',
        permission_key + '[aco]': 'Resource',
        permission_key + '[aco_foreign_key]': permission.resource.id,
        permission_key + '[aro]': 'User' if isinstance(permission.recipient, User) else 'Group',
        permission_key + '[aro_foreign_key]': permission.recipient.id,
        permission_key + '[type]': str(permission.permission_type),
    }


def to_foreign_user(user: User) -> Dict[str, str]:
    return {
        'gpgkey': {'id': user.gpg_key.id, 'armored_key': user.gpg_key.armored_key, 'fingerprint': user.gpg_key.fingerprint},
        'groups_users': [{'group_id': group.id, 'user_id': user.id} for group in user.groups_ids],
        'id': user.id,
        'username': user.username,
        'profile': {'first_name': user.first_name, 'last_name': user.last_name, 'user_id': user.id}
    }


def to_foreign_group(group: Group) -> Dict[str, str]:
    return {
        'id': group.id,
        'name': group.name,
        'users': [{'id': member_id} for member_id in group.members_ids]
    }
