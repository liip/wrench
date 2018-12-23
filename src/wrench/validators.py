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

from typing import Any, Dict, Iterable

from .exceptions import ValidationError
from .users import User


def validate_non_empty(value: str) -> str:
    """
    Return the given value or raise :exc:`ValidationError` if the given value is empty.
    """
    if not value:
        raise ValidationError("This field is mandatory.")

    return value


def validate_http_url(value: str) -> str:
    """
    Return the given value or raise :exc:`ValidationError` if the given URL doesn't start with http:// or
    https://.
    """
    if not value.startswith('http://') and not value.startswith('https://'):
        raise ValidationError("The value must be a valid HTTP URL.")

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
        raise ValidationError("Recipient {} is invalid.".format(e.args[0]))

    return selected_users
