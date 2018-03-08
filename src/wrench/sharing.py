from typing import Callable, Iterable, Sequence

from requests_gpgauthlib import GPGAuthSession

from .io import input_recipients
from .resources import PermissionType, Resource, SharedSecret
from .services import get_current_user, get_users, share_resource
from .users import User


def share_resource_interactive(session: GPGAuthSession, resource: Resource,
                               encrypt_func: Callable[[str, User], str]) -> Sequence[User]:
    """
    Invite the user to enter a list of recipients to share this resource with. The attribute `resource.secret` *must*
    be the cleartext secret, so that it can be re-encrypted for each recipient.
    """
    recipients = input_recipients(get_users(session))

    if not recipients:
        return []

    current_user = get_current_user(session)

    # Make sure the resource is not shared with current user (or this would result in an error from Passbolt) and that
    # each user id only is used only once
    share_to_users = list({
        recipient.id: recipient for recipient in recipients if recipient.id != current_user.id
    }.values())
    shared_secrets = get_shared_secrets(resource, share_to_users, encrypt_func)

    if shared_secrets:
        share_resource(session, shared_secrets)

    return share_to_users


def get_shared_secrets(resource: Resource, users: Iterable[User],
                       encrypt_func: Callable[[str, User], str]) -> Iterable[SharedSecret]:
    """
    Return a list of :class:`SharedSecret` objects generated from the given `resource` for all the given :class:`User`
    objects. The `resource.secret` attribute *must* be the cleartext secret.
    """
    secrets = [SharedSecret(user=user, resource=resource, permission_type=PermissionType.READ.value,
                            secret=encrypt_func(resource.secret, user)) for user in users]

    return secrets
