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
import logging
import os
import sys
from enum import Enum
from typing import Any, Dict, Iterable, List, Union

import click
import requests
from requests_gpgauthlib import GPGAuthSession
from requests_gpgauthlib.exceptions import GPGAuthException, GPGAuthNoSecretKeyError
from requests_gpgauthlib.utils import create_gpg, get_workdir, import_user_private_key_from_file

from .config import create_config, parse_config
from .context import Context
from .exceptions import FingerprintMismatchError, HttpRequestError, ImportParseError
from .io import ask_question, input_recipients, split_csv
from .models import Group, Resource, User
from .passbolt_shell import PassboltShell
from .resources import add_resource, decrypt_resource, search_resources, share_resource
from .services import get_groups, get_resources, get_users
from .utils import encrypt, encrypt_for_user, obj_to_tuples
from .validators import validate_http_url, validate_non_empty

ExitStatus = Enum('ExitStatus', (('NO_SECRET_KEY', 1), ('SECRET_KEY_IMPORT_ERROR', 2)))

logger = logging.getLogger(__name__)


def get_config_path() -> str:
    """
    Return the path to the configuration file. The configuration file is stored in ~/.config/wrench/config.ini.
    """
    config_home = os.path.join(os.path.expanduser(os.environ.get('XDG_CONFIG_HOME', '~/.config')), 'wrench')
    config_file = os.path.join(config_home, 'config.ini')

    return config_file


def get_session_from_ctx_obj(ctx_obj: Dict[str, Any]) -> GPGAuthSession:
    """
    Return a `GPGAuthSession` from the given click context object.
    """
    session = GPGAuthSession(
        gpg=ctx_obj['gpg'], server_url=ctx_obj['config']['auth']['server_url']
    )
    session.auth = requests.auth.HTTPBasicAuth(
        ctx_obj['config']['auth']['http_username'], ctx_obj['config']['auth']['http_password']
    )

    if session.server_fingerprint != ctx_obj['config']['auth']['server_fingerprint']:
        raise FingerprintMismatchError("Server fingerprint {} doesn't match expected fingerprint {}".format(
            session.server_fingerprint, ctx_obj['config']['auth']['server_fingerprint']
        ))

    session.authenticate()

    return session


def get_context(ctx_obj: Dict[str, Any]) -> Context:
    """
    Create a session based on the given click context object and return a :class:`Context` object with this session.
    """
    return Context(session=get_session_from_ctx_obj(ctx_obj), get_users_func=get_users, get_groups_func=get_groups)


def config_values_wizard() -> Dict[str, str]:
    mandatory_question = functools.partial(ask_question, processors=[validate_non_empty])
    auth_config = dict([
        ('server_url', mandatory_question(label="Passbolt server URL (eg. https://passbolt.example.com)",
                                          processors=[validate_non_empty, validate_http_url])),
        ('server_fingerprint', mandatory_question(label="Passbolt server fingerprint")),
        ('http_username', mandatory_question(label="Username for HTTP auth")),
        ('http_password', mandatory_question(label="Password for HTTP auth", secret=True)),
    ])
    sharing_config = dict([
        ('default_recipients', ask_question(
            label="Default recipients for resources (users e-mail addresses or group names, separated by commas)"
            ))
        ])

    return {'auth': auth_config, 'sharing': sharing_config}


def create_config_file(path: str, config_values: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    Save the given `config_values` in the configuration file and return a dict representing the config file.
    """
    config = config_values

    os.makedirs(os.path.dirname(path), exist_ok=True)
    create_config(path, config)

    return config


print_success = functools.partial(click.secho, fg='green')


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return

    from wrench import __version__
    click.echo("Wrench version {}".format(__version__))
    ctx.exit()


def get_recipient_by_name(name: str, context: Context) -> Union[Group, User]:
    """
    Given a recipient name (e-mail address or group name), return the corresponding `User` or `Group` object. The group
    matching is only checked if no user e-mail address matches the given `name`.
    """
    try:
        recipient = context.users_by_name[name]
    except KeyError:
        recipient = context.groups_by_name[name]

    return recipient


def get_default_recipients(config: Dict[str, Any], context: Context) -> List[Union[Group, User]]:
    """
    Return the config value `[sharing] default_recipients` as an iterable of `Group` and/or `User` objects. If any
    recipient cannot be found in the list, a `KeyError` will be raised.
    """
    try:
        recipients = (
            recipient.strip() for recipient in config['sharing']['default_recipients'].split(',')
        )
    except KeyError:
        recipient_objs = []  # type: List[Union[Group, User]]
    else:
        try:
            recipient_objs = [get_recipient_by_name(recipient, context) for recipient in recipients]
        except KeyError as e:
            raise click.ClickException(
                "Invalid default recipient %s. Please fix the value of the `default_recipients` setting in the"
                " `[sharing]` section of your configuration file." % e
            )

    return recipient_objs


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.option('-v', '--verbose', count=True, help="Make it verbose. Repeat up to 3 times to increase verbosity.")
@click.option('--version', is_flag=True, expose_value=False, callback=print_version, is_eager=True,
              help="Print version number and exit.")
@click.pass_context
def cli(ctx: Any, verbose: bool) -> None:
    """
    Passbolt CLI.
    """
    if verbose:
        levels = {1: logging.WARNING, 2: logging.INFO, 3: logging.DEBUG}
        logging.basicConfig(level=levels.get(verbose, logging.ERROR))

    if 'config' not in ctx.obj:
        config_path = get_config_path()
        try:
            ctx.obj['config'] = parse_config(config_path)
        except FileNotFoundError:
            ctx.obj['config'] = create_config_file(config_path, config_values_wizard())

    if 'gpg' not in ctx.obj:
        ctx.obj['gpg'] = create_gpg(get_workdir())


@cli.command()
@click.argument('terms', nargs=-1)
@click.option('--favourite', is_flag=True)
@click.pass_context
def search(ctx: Any, terms: Iterable[str], favourite: bool) -> None:
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
            kwargs = {'fg': 'red', 'bg': 'red'}  # type: Dict[str, Any]
        else:
            kwargs = {'fg': colors.get(field, 'white'), 'bold': True}

        # Prevent None values from making the call raise an exception
        return click.style(value if value else '', **kwargs)

    def get_fields_for_display(resource: Resource) -> Iterable[str]:
        resource_fields = obj_to_tuples(resource, ('name', 'id', 'uri', 'username', 'secret', 'description'))
        longest_field = max(len(field) for field, _ in resource_fields)

        return ("{}: {}".format(
            field.ljust(longest_field + 1), get_field_for_display(field, value)
        ) for field, value in resource_fields)

    terms = ' '.join(terms)
    context = get_context(ctx.obj)
    resources = get_resources(context.session, favourite_only=favourite)

    output = (
        '\n'.join(get_fields_for_display(decrypt_resource(resource, ctx.obj['gpg'])))
        for resource in search_resources(resources, terms)
    )

    click.echo('\n\n'.join(output))


@cli.command()
@click.pass_context
def add(ctx: Any) -> None:
    """
    Add a new resource.

    The command prompts for a name, URL, username, description and secret and then allows to share it with other users.
    """
    context = get_context(ctx.obj)
    session = context.session
    # Get the list of recipients as soon as possible so that we can show an early error if it contains invalid
    # recipients
    default_recipients = get_default_recipients(ctx.obj['config'], context)

    resource_record = dict([
        ('name', ask_question(label="Name", processors=[validate_non_empty])), ('uri', ask_question(label="URI")),
        ('description', ask_question(label="Description")), ('username', ask_question(label="Username")),
        ('tags', ask_question(label="Tags (separated by commas, use # sign for public tags)", processors=[split_csv])),
    ])
    secret = ask_question(label="Secret", secret=True, processors=[validate_non_empty])

    resource = Resource(**dict(resource_record, id=None, secret=secret, encrypted_secret=None))

    try:
        added_resource = add_resource(
            resource,
            encrypt_func=functools.partial(encrypt, fingerprint=session.user_fingerprint, gpg=ctx.obj['gpg']),
            context=context
        )
    except HttpRequestError as e:
        raise click.ClickException("Error while adding resource: %s." % e.response.text)

    print_success("\nResource '{}' successfully saved.\n".format(resource_record['name']))
    click.echo(
        "If you would like to share it, enter e-mail addresses or group names below, separated by commas."
        " Auto completion through Tab key is supported."
    )

    if default_recipients:
        click.echo("The resource will also be shared with the following recipients: %s" % click.style(", ".join(
            str(recipient) for recipient in default_recipients
        ), fg='yellow'))

    recipients = default_recipients + input_recipients(context.users, context.groups)

    if recipients:
        try:
            share_resource(
                added_resource, recipients, functools.partial(encrypt_for_user, gpg=ctx.obj['gpg']), context
            )
        except HttpRequestError as e:
            raise click.ClickException("Error while sharing resource: %s." % e.response.text)
        else:
            if recipients:
                nb_groups = len([recipient for recipient in recipients if isinstance(recipient, Group)])
                nb_users = len(recipients) - nb_groups
                print_success("Resource successfully shared with {} users and {} groups.".format(nb_users, nb_groups))


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
@click.argument('path', type=click.Path(exists=True))
@click.option('--tag', '-t', multiple=True, help="Public tag to assign to the imported resources. Can be repeated"
                                                 " multiple times.")
@click.pass_context
def import_resources(ctx: Any, path: str, tag: List[str]) -> None:
    """
    Import the given resources file into Passbolt.

    The file should be in CSV format, using tabs as separators, and contain 5 fields:

        host<TAB>username<TAB>password<TAB>description<TAB>product

    The first line is considered as the header and will be ignored.
    """
    def get_resources(lines):
        nb_header_lines = 1
        for lineno, line in enumerate(lines[nb_header_lines:], 1):
            try:
                host, username, password, description, product = line.split('\t')
            except ValueError:
                raise ImportParseError(lineno + nb_header_lines)
            else:
                yield host, username, password, description, product

    with open(path) as resource_file:
        resource_lines = resource_file.readlines()

    try:
        for resource in get_resources(resource_lines):
            pass
    except ImportParseError as e:
        raise click.ClickException(
            "Could not split line {} of {} in 5 parts. Please check that it contains 4 tabs.".format(e.lineno, path)
        )

    context = get_context(ctx.obj)
    click.echo(
        "If you would like to share the resources after import, enter e-mail addresses or group names below, separated"
        " by commas. Auto completion through Tab key is supported."
    )
    default_recipients = get_default_recipients(ctx.obj['config'], context)
    if default_recipients:
        click.echo("The imported resources will also be shared with the following recipients: %s" %
                   click.style(", ".join(str(recipient) for recipient in default_recipients), fg='yellow'))

    recipients = default_recipients + input_recipients(context.users, context.groups)
    tag = [('#' + t if not t.startswith('#') else t) for t in tag]

    for host, username, password, description, product in get_resources(resource_lines):
        resource = Resource(id=None, uri=host, name=product, description=description, username=username,
                            secret=password, encrypted_secret=None, tags=tag)
        new_resource = add_resource(
            resource,
            functools.partial(encrypt, fingerprint=context.session.user_fingerprint, gpg=ctx.obj['gpg']),
            context
        )
        share_resource(new_resource, recipients, functools.partial(encrypt_for_user, gpg=ctx.obj['gpg']), context)

    nb_imported_resources = len(resource_lines) - 1
    click.echo("{} resources successfully imported.".format(nb_imported_resources))


@cli.command()
@click.pass_context
def passbolt_shell(ctx: Any) -> None:
    """
    Run a shell to execute Passbolt requests.

    Useful for debugging.
    """
    context = get_context(ctx.obj)

    shell = PassboltShell(context.session)
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
    except FingerprintMismatchError as e:
        click.secho("Error: {}".format(e), err=True)


if __name__ == '__main__':
    main()
