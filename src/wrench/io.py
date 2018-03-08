import readline
from getpass import getpass
from typing import Any, Callable, Iterable, Optional

import click

from .exceptions import InputValidationError
from .users import User
from .validators import validate_recipients


def ask_question(label: str, secret: bool = False, processors: Optional[Iterable[Callable[[str], Any]]] = None) -> Any:
    """
    Display the given `label`, wait for user input, call the given `processors` on the entered value until no processor
    raises :exc:`InputValidationError`, and return the transformed value.
    """
    func = getpass if secret else input
    valid_input = False

    while not valid_input:
        value = func(label + ": ")  # type: ignore

        try:
            if processors:
                for processor in processors:
                    value = processor(value)
        except InputValidationError as e:
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


def input_recipients(users: Iterable[User]) -> Iterable[User]:
    """
    Ask the user to select users out of the given `users` and return the selected users.
    """
    users_dict = {user.username: user for user in users}
    init_autocomplete(users_dict.keys())

    return ask_question(label="Recipients", processors=[lambda value: validate_recipients(value, users_dict)])
