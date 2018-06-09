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

from typing import Callable, Iterable, Sequence, Union

from .context import Context
from .io import input_recipients
from .models import Group, Permission, PermissionType, Secret, User
from .resources import Resource
from .services import get_permissions
from .services import share_resource as share_resource_service
from .users import unfold_groups


def share_resource_interactive(resource: Resource, encrypt_func: Callable[[str, User], str],
                               context: Context) -> Sequence[Union[Group, User]]:
    """
    Invite the user to enter a list of recipients to share this resource with. The attribute `resource.secret` *must*
    be the cleartext secret, so that it can be re-encrypted for each recipient.
    """
    recipients = input_recipients(context.users, context.groups)

    if not recipients:
        return []

    return share_resource(resource, recipients, encrypt_func, context)


def share_resource(resource: Resource, recipients: Iterable[Union[User, Group]],
                   encrypt_func: Callable[[str, User], str], context: Context) -> Sequence[Union[Group, User]]:
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

    new_recipients = set(recipients) - set(existing_recipients)
    unfolded_recipients = unfold_groups(new_recipients, context.users_by_id)
    new_user_recipients = set(unfolded_recipients) - set(existing_user_recipients)

    secrets = [
        Secret(resource=resource, recipient=recipient, secret=encrypt_func(resource.secret, recipient))
        for recipient in new_user_recipients
    ]
    permissions = [
        Permission(resource=resource, recipient=recipient, permission_type=PermissionType.READ.value)
        for recipient in new_recipients
    ]

    share_resource_service(context.session, resource.id, secrets, permissions)

    return list(new_recipients)
