from typing import Any, Dict, Iterable

from .exceptions import InputValidationError
from .users import User


def validate_non_empty(value: str) -> str:
    """
    Return the given value or raise :exc:`InputValidationError` if the given value is empty.
    """
    if not value:
        raise InputValidationError("This field is mandatory.")

    return value


def validate_http_url(value: str) -> str:
    """
    Return the given value or raise :exc:`InputValidationError` if the given URL doesn't start with http:// or
    https://.
    """
    if not value.startswith('http://') or value.startswith('https://'):
        raise InputValidationError("The value must be a valid HTTP URL.")

    return value


def validate_recipients(value: str, recipients_dict: Dict[str, Any]) -> Iterable[User]:
    """
    Split the given `value` on commas and return users as a list of :class:`User` objects. If a user is not in
    `recipients_dict`, raise :exc:`InputValidatiorError`.
    """
    value = value.strip()

    if not value:
        return []

    try:
        selected_users = [recipients_dict[recipient.strip()] for recipient in value.split(',')]
    except KeyError as e:
        raise InputValidationError("Recipient {} is invalid.".format(e.args[0]))

    return selected_users
