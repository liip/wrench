from typing import Any, Dict, Iterable

from requests_gpgauthlib import GPGAuthSession

from . import passbolt_api
from .resources import Resource, SharedSecret
from .translators import to_foreign_resource, to_foreign_shared_secrets, to_local_resource, to_local_user
from .users import User


def add_resource(session: GPGAuthSession, resource: Resource) -> Resource:
    """
    Add the given `resource` to Passbolt and return the added :class:`Resource` object with its id set.
    """
    return to_local_resource(passbolt_api.add_resource(session, to_foreign_resource(resource)))


def get_resources(session: GPGAuthSession, favourite_only: bool = False) -> Iterable[Resource]:
    """
    Return :class:`Resource` objects from Passbolt.
    """
    return [to_local_resource(resource) for resource in passbolt_api.get_resources(session, favourite_only)]


def get_users(session: GPGAuthSession) -> Iterable[User]:
    """
    Return :class:`User` objects from Passbolt.
    """
    return [to_local_user(user) for user in passbolt_api.get_users(session)]


def get_current_user(session: GPGAuthSession) -> User:
    """
    Return a :class:`User` object from Passbolt representing the currently logged in user.
    """
    return to_local_user(passbolt_api.get_user(session, 'me'))


def share_resource(session: GPGAuthSession, secrets: Iterable[SharedSecret]) -> Dict[str, Any]:
    """
    Share the given secrets and return the Passbolt API HTTP response.
    """
    if not secrets:
        raise ValueError("No secrets to share.")

    resource_id = next(iter(secrets)).resource.id
    return passbolt_api.share_resource(session, resource_id=resource_id, data=to_foreign_shared_secrets(secrets))
