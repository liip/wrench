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

import readline
from getpass import getpass
from typing import Any, Callable, Dict, Iterable, Optional, List, Union  # noqa

import click

from .exceptions import ValidationError
from .users import Group, User
from .validators import validate_recipients


def ask_question(label: str, secret: bool = False, processors: Optional[Iterable[Callable[[str], Any]]] = None) -> Any:
    """
    Display the given `label`, wait for user input, call the given `processors` on the entered value until no processor
    raises :exc:`ValidationError`, and return the transformed value.
    """
    func = getpass if secret else input
    valid_input = False

    while not valid_input:
        value = func(label + ": ") if label else func()  # type: ignore

        try:
            if processors:
                for processor in processors:
                    value = processor(value)
        except ValidationError as e:
            click.echo(str(e))
        else:
            valid_input = True

    return value


def init_autocomplete(choices: Iterable[str]) -> None:
    """
    Initialize readline's autocomplete with the given `choices`.
    """
    def complete(text, state):
        text = text.strip().casefold()
        matches = [choice for choice in choices if text in choice.casefold()]
        return matches[state]

    readline.set_completer_delims(', ')
    readline.parse_and_bind('tab: complete')
    readline.set_completer(complete)


def input_recipients(users: Iterable[User], groups: Iterable[Group]) -> List[Union[Group, User]]:
    """
    Ask the user to select users out of the given `users` or groups out of the given `groups`, and return an iterable
    with the selected users and groups.
    """
    users_dict = {user.username: user for user in users}
    groups_dict = {group.name: group for group in groups}
    recipients_dict = dict(users_dict, **groups_dict)  # type: Dict[str, Union[Group, User]]

    init_autocomplete(recipients_dict.keys())

    return ask_question(label="", processors=[
        lambda value: validate_recipients(value, recipients_dict),
    ])


def split_csv(input_str: str) -> List[str]:
    """
    Split the given `input_str` on the comma character and return the resulting list. If `input_str` is empty, return
    an empty list.
    """
    if not input_str:
        return []

    return [value.strip() for value in input_str.split(",")]


def _find_getch():
    """
    Read a single character from stdin and return it.
    """
    try:
        import termios
    except ImportError:
        # Non-POSIX. Return msvcrt's (Windows') getch.
        import msvcrt
        return msvcrt.getch

    # POSIX system. Create and return a getch that manipulates the tty.
    import sys
    import tty

    def _getch():
        fd = sys.stdin.fileno()

        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    return _getch


getch = _find_getch()
