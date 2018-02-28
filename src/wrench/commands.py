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

import logging
import os
import sys
from enum import Enum
from typing import Any, Dict, Iterable

import click
import requests
from requests_gpgauthlib import GPGAuthSession
from requests_gpgauthlib.exceptions import GPGAuthException, GPGAuthNoSecretKeyError
from requests_gpgauthlib.utils import create_gpg, get_workdir, import_user_private_key_from_file

from . import passbolt_api
from .config import create_config, parse_config
from .passbolt_shell import PassboltShell
from .resources import Resource, decrypt_resource, resource_dicts_to_resources, search_resources
from .utils import obj_to_tuples

ExitStatus = Enum('ExitStatus', (('NO_SECRET_KEY', 1), ('SECRET_KEY_IMPORT_ERROR', 2)))


def get_config_path() -> str:
    """
    Return the path to the configuration file. The configuration file is stored in ~/.config/wrench/config.ini.
    """
    config_home = os.path.join(os.path.expanduser(os.environ.get('XDG_CONFIG_HOME', '~/.config')), 'wrench')
    config_file = os.path.join(config_home, 'config.ini')

    return config_file


def create_session_from_context(ctx_obj: Dict[str, Any]) -> GPGAuthSession:
    """
    Return a `GPGAuthSession` from the given click context object.
    """
    session = GPGAuthSession(
        gpg=ctx_obj['gpg'], server_url=ctx_obj['config']['auth']['server_url'], auth_uri='/auth/',
        server_fingerprint=ctx_obj['config']['auth']['server_fingerprint'],
    )
    session.auth = requests.auth.HTTPBasicAuth(
        ctx_obj['config']['auth']['http_username'], ctx_obj['config']['auth']['http_password']
    )
    session.authenticate()

    return session


def create_config_file(path: str) -> Dict[str, Dict[str, str]]:
    """
    Ask the user for configuration values, save them in the configuration file and then return them.
    """
    def get_response(question):
        print(question + ": ", end='')
        return input()

    questions = (
        ('server_url', "Passbolt server URL (eg. https://passbolt.example.com)"),
        ('server_fingerprint', "Passbolt server fingerprint"),
        ('http_username', "Username for HTTP auth"),
        ('http_password', "Password for HTTP auth"),
    )

    config_values = {'auth': {key: get_response(value) for key, value in questions}}
    create_config(path, config_values)

    return config_values


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.option('-v', '--verbose', count=True, help="Make it verbose. Repeat up to 3 times to increase verbosity.")
@click.pass_context
def cli(ctx: Any, verbose: bool) -> None:
    """
    Passbolt CLI.
    """
    if verbose:
        levels = {1: logging.WARNING, 2: logging.INFO, 3: logging.DEBUG}
        logging.basicConfig(level=levels.get(verbose, logging.ERROR))

    config_path = get_config_path()
    try:
        ctx.obj['config'] = parse_config(config_path)
    except FileNotFoundError:
        ctx.obj['config'] = create_config_file(config_path)

    ctx.obj['gpg'] = create_gpg(get_workdir())


@cli.command()
@click.argument('terms', nargs=-1)
@click.option('--favourite', is_flag=True)
@click.pass_context
def search(ctx: Any, terms: Iterable[str], favourite: bool):
    """
    Search for entries matching the given terms.
    """
    def get_field_for_display(field: str, value: str) -> str:
        colors = {
            'uri': 'yellow',
            'username': 'blue',
            'description': 'green',
            'name': 'red',
        }

        if field == 'secret':
            kwargs: Dict[str, Any] = {'fg': 'red', 'bg': 'red'}
        else:
            kwargs = {'fg': colors.get(field, 'white'), 'bold': True}

        return click.style(value, **kwargs)

    def get_fields_for_display(resource: Resource) -> Iterable[str]:
        resource_fields = obj_to_tuples(resource, ('name', 'id', 'uri', 'username', 'secret', 'description'))
        longest_field = max(len(field) for field, _ in resource_fields)

        return ("{}: {}".format(
            field.ljust(longest_field + 1), get_field_for_display(field, value)
        ) for field, value in resource_fields)

    terms = ' '.join(terms)
    session = create_session_from_context(ctx.obj)

    resource_records = passbolt_api.get_resources(session, favourite_only=favourite)
    resources = resource_dicts_to_resources(resource_records)

    output = (
        '\n'.join(get_fields_for_display(decrypt_resource(resource, ctx.obj['gpg'])))
        for resource in search_resources(resources, terms)
    )

    click.echo('\n\n'.join(output))


@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.pass_context
def import_key(ctx: Any, path: str) -> None:
    """
    Import the given Passbolt private key.
    """
    try:
        fingerprint = import_user_private_key_from_file(ctx.obj['gpg'], path)
    except GPGAuthException:
        click.echo("Error: unable to import key. Try again with -v to find out why.")
        sys.exit(ExitStatus.SECRET_KEY_IMPORT_ERROR.value)
    else:
        click.echo("Key {} successfully imported.".format(fingerprint))


@cli.command()
@click.pass_context
def passbolt_shell(ctx: Any) -> None:
    """
    Run a shell to execute Passbolt requests.

    Useful for debugging.
    """
    session = create_session_from_context(ctx.obj)

    shell = PassboltShell(session)
    shell.cmdloop()


def main() -> None:
    try:
        cli(obj={})
    except GPGAuthNoSecretKeyError:
        click.secho(
            "Error: no secret key available. Please export your key in Passbolt and run `wrench import_key "
            "<path_to_key>`.", err=True
        )
        sys.exit(ExitStatus.NO_SECRET_KEY.value)


if __name__ == '__main__':
    main()
