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

from typing import Dict  # noqa
from typing import Iterable, Mapping

from requests_gpgauthlib import GPGAuthSession

from . import passbolt_api
from .models import Group, Permission, PermissionModificationType, Resource, Secret, User
from .translators import to_foreign, to_local


def add_resource(session: GPGAuthSession, resource: Resource) -> Resource:
    """
    Add the given `resource` to Passbolt and return the added :class:`Resource` object with its id and original secret
    set.
    """
    tags = resource.tags
    resource = to_local(
        passbolt_api.add_resource(session, to_foreign(resource, user=get_current_user(session))), Resource
    )._replace(tags=tags, secret=resource.secret)

    if tags:
        passbolt_api.add_tags(session, resource.id, {'Tags': tags})

    return resource


def get_resources(session: GPGAuthSession, favourite_only: bool = False) -> Iterable[Resource]:
    """
    Return :class:`Resource` objects from Passbolt.
    """
    return [to_local(resource, Resource) for resource in passbolt_api.get_resources(session, favourite_only)]


def get_resource_secret(session: GPGAuthSession, resource_id: str) -> str:
    """
    Return the encrypted secret of the given `resource_id`.
    """
    return passbolt_api.get_resource_secret(session, resource_id)['data']


def get_users(session: GPGAuthSession) -> Iterable[User]:
    """
    Return :class:`User` objects from Passbolt.
    """
    return [to_local(user, User) for user in passbolt_api.get_users(session)]


def get_groups(session: GPGAuthSession) -> Iterable[Group]:
    """
    Return :class:`Group` objects from Passbolt.
    """
    return [to_local(group, Group) for group in passbolt_api.get_groups(session)]


def get_users_from_group(session: GPGAuthSession) -> Iterable[Group]:
    """
    Return :class:`Group` objects from Passbolt.
    """
    return [to_local(group, Group) for group in passbolt_api.get_groups(session)]


def get_current_user(session: GPGAuthSession) -> User:
    """
    Return a :class:`User` object from Passbolt representing the currently logged in user.
    """
    return to_local(passbolt_api.get_user(session, 'me'), User)


def get_permissions(session: GPGAuthSession, resource_id: str, users_cache: Mapping[str, User],
                    groups_cache: Mapping[str, Group]) -> Iterable[Permission]:
    """
    Return the current permissions of the resource identified by the given `resource_id`. `users_cache` and
    `groups_cache` must contain all the possible groups and users to build the relationship between permissions and
    recipients.
    """
    permissions = [
        to_local(permission, Permission, users_cache=users_cache, groups_cache=groups_cache)
        for permission in passbolt_api.get_resource_permissions(session, resource_id)
    ]

    return permissions


def share_resource(session: GPGAuthSession, resource_id: str, secrets: Iterable[Secret],
                   new_permissions: Iterable[Permission], deleted_permissions: Iterable[Permission] = None) -> None:
    """
    Share the resource identified by the given `resource_id`. `secrets` must contain the resource secret encrypted to
    every recipient. It is very important that `secrets` does not contain ids of recipients the resource is already
    shared with, or the operation will fail. Use `get_permissions` to get the recipients the resource is already shared
    with.
    """
    new_permissions_dicts = [to_foreign(permission) for permission in new_permissions] if new_permissions else []
    deleted_permissions_dicts = [
        to_foreign(permission, modification_type=PermissionModificationType.delete)
        for permission in deleted_permissions
    ] if deleted_permissions else []
    permissions = new_permissions_dicts + deleted_permissions_dicts

    if permissions:
        data = {
            'secrets': [to_foreign(secret) for secret in secrets],
            'permissions': permissions,
        }

        passbolt_api.share_resource(session, resource_id=resource_id, data=data)
