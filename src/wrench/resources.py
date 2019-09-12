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
from typing import Callable, Iterable, Optional, Sequence, Tuple, Union

from gnupg import GPG

from . import utils
from .context import Context
from .exceptions import ValidationError
from .models import Group, Permission, PermissionType, Resource, Secret, User
from .services import add_resource as add_resource_service
from .services import get_permissions, get_resource_secret
from .services import share_resource as share_resource_service
from .users import unfold_groups


def resource_matches(resource: Resource, terms: str,
                     fields: Tuple[str, ...] = ('name', 'username', 'uri', 'description')) -> bool:
    """
    Return `True` if terms are found in the given resource. Search is case insensitive, and terms are split at the
    space character. The resource matches only if all given terms are found in the combination of all the given
    `fields`.
    """
    if not terms:
        return True

    terms_list = terms.casefold().split(' ')
    resource_str = ' '.join(
        value.casefold() for value in (
            getattr(resource, attr) for attr in fields
        )
        if value
    )

    return all(term in resource_str for term in terms_list)


def search_resources(resources: Iterable[Resource], terms: str,
                     fields: Optional[Tuple[str, ...]] = None) -> Sequence[Resource]:
    """
    Return a sequence of resources matching the given `terms`.
    """
    resource_matches_partial = functools.partial(resource_matches, terms=terms)

    if fields:
        resource_matches_partial = functools.partial(resource_matches_partial, fields=fields)

    return [resource for resource in resources if resource_matches_partial(resource=resource)]


def decrypt_resource(resource: Resource, gpg: GPG, context: Context) -> Resource:
    """
    Decrypt the secret of the given `resource` and set it in clear text in the `secret` field. If the `secret` field is
    already populated, no decryption is done and the resource is returned unchanged.
    """
    if resource.secret is not None:
        return resource

    return resource._replace(
        secret=utils.decrypt(data=get_resource_secret(session=context.session, resource_id=resource.id), gpg=gpg)
    )


def share_resource(resource: Resource, recipients: Iterable[Tuple[Union[User, Group], PermissionType]],
                   encrypt_func: Callable[[str, User], str], context: Context,
                   delete_existing_permissions: bool = False) -> Sequence[Union[Group, User]]:
    """
    Share the given resource with the given recipients.
    """
    if not recipients:
        return []

    # Sending an existing Secret or Permission to the Passbolt API returns an error so we need to make sure to strip
    # any recipients that already have the resource shared with them
    existing_permissions = get_permissions(session=context.session, resource_id=resource.id,
                                           users_cache=context.users_by_id, groups_cache=context.groups_by_id)
    existing_recipients = [permission.recipient for permission in existing_permissions]
    existing_user_recipients = unfold_groups(existing_recipients, context.users_by_id)

    new_users = [recipient[0] for recipient in recipients]
    new_recipients = set(new_users) - set(existing_recipients)
    unfolded_recipients = unfold_groups(new_recipients, context.users_by_id)
    new_user_recipients = set(unfolded_recipients) - set(existing_user_recipients)

    secrets = [
        Secret(resource=resource, recipient=recipient, secret=encrypt_func(resource.secret, recipient))
        for recipient in new_user_recipients
    ]
    permissions = [
        Permission(id=None, resource=resource, recipient=recipient, permission_type=permission.value)
        for recipient, permission in recipients
    ]
    new_permissions = set(permissions) - set(existing_permissions)

    if delete_existing_permissions:
        deleted_permissions = [
            Permission(id=permission.id, resource=None, recipient=None, permission_type=None)
            for permission in existing_permissions
        ]
    else:
        deleted_permissions = []

    share_resource_service(session=context.session, resource_id=resource.id, secrets=secrets,
                           new_permissions=new_permissions, deleted_permissions=deleted_permissions)

    return list(new_recipients)


def add_resource(resource: Resource, encrypt_func: Callable[[str], str], context: Context) -> Resource:
    resource = resource._replace(encrypted_secret=encrypt_func(resource.secret))
    return add_resource_service(context.session, resource)


def validate_resource(resource: Resource):
    max_len = {
        'name': 64,
        'username': 64,
    }

    for attr, length in max_len.items():
        if len(getattr(resource, attr)) > length:
            raise ValidationError("Length of field {} exceeds max length of {} characters".format(attr, length))
