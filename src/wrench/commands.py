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
import re
import string
import sys
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Tuple, Union

import click
import requests
from requests_gpgauthlib import GPGAuthSession
from requests_gpgauthlib.exceptions import GPGAuthException, GPGAuthNoSecretKeyError
from requests_gpgauthlib.utils import create_gpg, get_workdir, import_user_private_key_from_file

from .config import create_config, parse_config
from .context import Context
from .exceptions import DecryptionError, FingerprintMismatchError, HttpRequestError, ImportParseError, ValidationError
from .io import ask_question, getch, input_recipients, split_csv
from .models import Group, PermissionType, Resource, User
from .passbolt_shell import PassboltShell
from .resources import add_resource, decrypt_resource, search_resources, share_resource, validate_resource
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


def get_session_from_ctx_obj(ctx_obj: Dict[str, Any], authenticate: bool = True) -> GPGAuthSession:
    """
    Return a `GPGAuthSession` from the given click context object. If `authenticate` is True, authentication will be
    made against the API.
    """
    session = GPGAuthSession(
        gpg=ctx_obj['gpg'], server_url=ctx_obj['config']['auth']['server_url']
    )

    if ctx_obj['config']['auth']['http_username'] or ctx_obj['config']['auth']['http_password']:
        session.auth = requests.auth.HTTPBasicAuth(
            ctx_obj['config']['auth']['http_username'], ctx_obj['config']['auth']['http_password']
        )

    if session.server_fingerprint != ctx_obj['config']['auth']['server_fingerprint']:
        raise FingerprintMismatchError("Server fingerprint {} doesn't match expected fingerprint {}".format(
            session.server_fingerprint, ctx_obj['config']['auth']['server_fingerprint']
        ))

    if authenticate:
        session.authenticate()

    return session


def get_context(ctx_obj: Dict[str, Any]) -> Context:
    """
    Create a session based on the given click context object and return a :class:`Context` object with this session.
    """
    return Context(session=get_session_from_ctx_obj(ctx_obj), get_users_func=get_users, get_groups_func=get_groups)


def config_values_wizard() -> Dict[str, Any]:
    auth_config = dict([
        ('server_url', ask_question(label="Passbolt server URL (eg. https://passbolt.example.com)",
                                          processors=[validate_non_empty, validate_http_url])),
        ('server_fingerprint', ask_question(label="Passbolt server fingerprint", processors=[validate_non_empty])),
        ('http_username', ask_question(label="Username for HTTP auth")),
        ('http_password', ask_question(label="Password for HTTP auth", secret=True)),
    ])
    sharing_config = dict([
        ('default_recipients', ask_question(
            label="Default recipients for resources (users e-mail addresses or group names, separated by commas)"))
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


def str_to_recipients(recipients_str: str, context: Context) -> List[Union[Group, User]]:
    """
    Take a string in the form "foo@bar.com, FooBar, bar@baz.com" and return the associated `User` and `Group` objects,
    in the same order. If any recipient doesn't exist, `KeyError` will be raised.
    """
    recipients = (recipient.strip() for recipient in recipients_str.split(','))
    recipient_objs = [get_recipient_by_name(recipient, context) for recipient in recipients]

    return recipient_objs


def get_sharing_recipients(config: Dict, recipients_key: str, context: Context) -> List[Union[Group, User]]:
    try:
        recipients = config['sharing'][recipients_key]
    except KeyError:
        recipients_list = []  # type: List[Union[Group, User]]
    else:
        try:
            recipients_list = str_to_recipients(recipients, context)
        except KeyError as e:
            raise click.ClickException(
                "Invalid recipient %s. Please fix the value of the `default_recipients` setting in the"
                " `[sharing]` section of your configuration file." % e
            )

    return recipients_list


def get_default_owners(config: Dict, context: Context) -> List[Union[Group, User]]:
    return get_sharing_recipients(config, 'default_owners', context)


def get_default_readers(config: Dict, context: Context) -> List[Union[Group, User]]:
    return get_sharing_recipients(config, 'default_readers', context)


def sharing_dialog(default_owners: List[Union[Group, User]], default_readers: List[Union[Group, User]],
                   context: Context):
    if default_owners:
        click.secho("The resource will be owned by the following recipients: ", fg="yellow", nl=False)
        click.echo(", ".join(str(recipient) for recipient in default_owners))
    click.secho("Enter any other owner: ", nl=False)
    new_owners = input_recipients(context.users, context.groups)
    owners = [(recipient, PermissionType.OWNER) for recipient in default_owners + new_owners]

    click.echo()

    if default_readers:
        click.secho("The resource will be readable by the following recipients: ", fg="yellow", nl=False)
        click.echo(", ".join(str(recipient) for recipient in default_readers))
    click.secho("Enter any other reader: ", nl=False)
    new_readers = input_recipients(context.users, context.groups)
    readers = [(recipient, PermissionType.READ) for recipient in default_readers + new_readers]

    return owners + readers


def _get_resource_field_for_display(field: str, value: str) -> str:
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


def _get_resource_fields_for_display(resource: Resource) -> Iterable[str]:
    resource_fields = obj_to_tuples(resource, ('name', 'id', 'uri', 'username', 'secret', 'description'))
    longest_field = max(len(field) for field, _ in resource_fields)

    return ("{}: {}".format(
        field.ljust(longest_field + 1), _get_resource_field_for_display(field, value)
    ) for field, value in resource_fields)


def _print_resource_short(id: str, resource: Resource) -> None:
    resource_title = click.style(resource.name or "<untitled>", bold=True) + (
        " ({})".format(resource.username) if resource.username else ""
    )
    fields_values = (resource_title,)  # type: Tuple[str, ...]
    if resource.description:
        fields_values += (resource.description.replace("\n", ", "),)

    fields_values_text = "\n    ".join(fields_values)
    click.echo("[{}] {}".format(click.style(id, fg='yellow'), fields_values_text))


def _select_resource(numbered_resources: Iterable[Tuple[str, Resource]]) -> Resource:
    numbered_resources_dict = dict(numbered_resources)

    while True:
        choice = getch()

        # \x03 is C-c
        if choice in ['q', '\x03']:
            raise KeyboardInterrupt()

        try:
            resource = numbered_resources_dict[choice]
        except KeyError:
            pass
        else:
            return resource


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
@click.option('--favourite', is_flag=True, help="Only search in resources marked as favourite in Passbolt.")
@click.option('--field', type=click.Choice(['name', 'username', 'uri', 'description']), multiple=True,
              help="Only search in specified fields.")
@click.pass_context
def search(ctx: Any, terms: Iterable[str], field: Iterable[str], favourite: bool) -> None:
    """
    Search for entries matching the given terms.

    You can restrict the fields to search in by using the `--field` option. Repeat it to include multiple fields. For
    example, the following will search all entries that contain "root" either in the uri or in the username fields:

    wrench search --field username --field uri root

    The default behaviour is to search in all fields.
    """

    context = get_context(ctx.obj)
    resources = get_resources(context.session, favourite_only=favourite)

    terms = ' '.join(terms)
    search_resources_partial = functools.partial(search_resources, resources=resources, terms=terms)
    matching_resources = search_resources_partial(fields=field) if field else search_resources_partial()

    choices = [
        letter for letter in (string.digits + string.ascii_letters) if letter.lower() != 'q'
    ]
    numbered_resources = list(zip(choices, matching_resources))

    if len(matching_resources) > 1:
        for number, resource in numbered_resources:
            _print_resource_short(number, resource)

    if len(matching_resources) > len(choices):
        click.secho("\nWarning: showing only {} choices out of {} results. Please refine your search.".format(
            len(choices), len(matching_resources)
        ), fg='yellow')

    if len(matching_resources) == 0:
        click.echo("Couldn't find any entry that matches your search.")
        return
    elif len(matching_resources) == 1:
        resource = matching_resources[0]
    else:
        click.echo("\nChoose an entry to display, or [q] to quit.", nl=False)

        try:
            resource = _select_resource(numbered_resources)
        except KeyboardInterrupt:
            return

        print("\n")

    click.echo("Decrypting...")
    try:
        resource = decrypt_resource(resource=resource, gpg=ctx.obj['gpg'], context=context)
    except DecryptionError:
        click.secho("Resource with id {} could not be decrypted.".format(resource.id), fg='red')

    click.echo("\n".join(_get_resource_fields_for_display(resource)))

    if resource.secret:
        try:
            import pyperclip
        except ImportError:
            click.echo(
                "\nHint: install pyperclip (see https://github.com/liip/wrench) to automatically copy the password to "
                "the clipboard."
            )
        else:
            pyperclip.copy(resource.secret)
            click.secho("\nPassword has been copied to the clipboard.", fg='green')


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
    get_default_owners(ctx.obj['config'], context)
    get_default_readers(ctx.obj['config'], context)

    resource_record = dict([
        ('name', ask_question(label="Name", processors=[validate_non_empty])),
        ('username', ask_question(label="Username")),
        ('secret', ask_question(label="Secret", secret=True, processors=[validate_non_empty])),
        ('uri', ask_question(label="URI")),
        ('description', ask_question(label="Description")),
        ('tags', ask_question(label="Tags (separated by commas, prefix with # sign for public tags)",
                              processors=[split_csv])),
    ])

    resource = Resource(**dict(resource_record, id=None, encrypted_secret=None))

    try:
        added_resource = add_resource(
            resource,
            encrypt_func=functools.partial(encrypt, fingerprint=session.user_fingerprint, gpg=ctx.obj['gpg']),
            context=context
        )
    except HttpRequestError as e:
        raise click.ClickException("Error while adding resource: %s." % e.response.text)

    print_success("\nResource '{}' successfully saved.\n".format(resource_record['name']))
    click.secho(
        "If you would like to share it, enter e-mail addresses or group names below, separated by commas."
        " Auto completion through Tab key is supported.\n", fg="yellow"
    )

    recipients = sharing_dialog(get_default_owners(ctx.obj['config'], context),
                                get_default_readers(ctx.obj['config'], context), context)

    if recipients:
        try:
            share_resource(
                added_resource, recipients, functools.partial(encrypt_for_user, gpg=ctx.obj['gpg']), context
            )
        except HttpRequestError as e:
            raise click.ClickException("Error while sharing resource: %s." % e.response.text)
        else:
            if recipients:
                nb_groups = len([recipient for recipient in (recipients) if isinstance(recipient[0], Group)])
                nb_users = len(recipients) - nb_groups
                print_success("\nResource successfully shared with {} users and {} groups.".format(nb_users, nb_groups))


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

    tag = [('#' + t if not t.startswith('#') else t) for t in tag]

    click.echo("Checking if file to import is valid... ")

    with open(path) as resource_file:
        resource_lines = resource_file.readlines()

    resources = []
    try:
        # Start counting at line 2 because of the header line
        for lineno, (host, username, password, description, product) in enumerate(get_resources(resource_lines), 2):
            resource = Resource(id=None, uri=host, name=product, description=description, username=username,
                                secret=password, encrypted_secret=None, tags=tag)

            try:
                validate_resource(resource)
            except ValidationError as e:
                raise click.ClickException("Error on line {}. {}".format(lineno, e))
            else:
                resources.append(resource)
    except ImportParseError as e:
        raise click.ClickException(
            "Could not split line {} of {} in 5 parts. Please check that it contains 4 tabs.".format(e.lineno, path)
        )

    context = get_context(ctx.obj)
    click.echo(
        "If you would like to share the resources after import, enter e-mail addresses or group names below, separated"
        " by commas. Auto completion through Tab key is supported.\n"
    )
    recipients = sharing_dialog(get_default_owners(ctx.obj['config'], context),
                                get_default_readers(ctx.obj['config'], context), context)

    for resource in resources:
        new_resource = add_resource(
            resource,
            functools.partial(encrypt, fingerprint=context.session.user_fingerprint, gpg=ctx.obj['gpg']),
            context
        )
        share_resource(new_resource, recipients, functools.partial(encrypt_for_user, gpg=ctx.obj['gpg']), context,
                       delete_existing_permissions=True)

    nb_imported_resources = len(resource_lines) - 1
    click.echo("{} resources successfully imported.".format(nb_imported_resources))


@cli.command()
@click.pass_context
def diagnose(ctx: Any):
    """
    Run various checks to test wrench installation status.
    """
    class DiagnoseError(Exception):
        pass

    def run_test(func: Callable, description: str) -> bool:
        """
        Run the given test function, show its description and the test result, and return True if the test run was
        successful, or False otherwise.
        """
        try:
            result = func()
        except AssertionError as e:
            result = str(e)
            success = False
        except Exception as e:
            result = "Unexpected failure {}".format(e)
            success = False
        else:
            success = True

        prefix = "[{}] ".format(
            click.style("OK", fg='green', bold=True) if success else click.style("KO", fg='red', bold=True)
        )

        result = (": " + result) if result else ""
        click.echo(prefix + description + result)

        return success

    def wrench_version():
        from . import __version__
        return __version__

    def python_gnupg_version():
        from gnupg import __version__
        return __version__

    def requests_gpgauthlib_version():
        from gpgauthlib import __version__
        return __version__

    def gnupg_version():
        import subprocess
        result = subprocess.run(['gpg', '--version'], stdout=subprocess.PIPE)
        stdout = result.stdout.decode()
        version_line = stdout.splitlines()[0]

        matches = re.search(r'\d+\.\d+(\.\d+)?', version_line)
        assert matches, "Unable to identify version number in " + version_line

        import itertools
        version_number = tuple(int(part) for part in matches.group(0).split('.'))
        version_number += tuple(itertools.repeat(0, 3 - len(version_number)))

        assert version_number >= (2, 1, 0), "gpg version should be >= 2.1.0"

        return '.'.join(str(v) for v in version_number)

    def test_secret_key():
        secret_keys = ctx.obj['gpg'].list_keys(True)
        assert len(secret_keys) == 1, "only one secret key should exist, found {}".format(len(secret_keys))
        return secret_keys[0]['fingerprint']

    def test_encryption():
        secret_keys = ctx.obj['gpg'].list_keys(True)
        # TODO check if no secret key
        secret_key = secret_keys[0]
        encrypted_data = ctx.obj['gpg'].encrypt('wrench', secret_key['fingerprint'], always_trust=True)
        assert encrypted_data.ok, "unable to encrypt data ({})".format(encrypted_data.status)
        decrypted_data = ctx.obj['gpg'].decrypt(str(encrypted_data))

        assert decrypted_data.ok, "unable to decrypt data ({})".format(decrypted_data.status)
        assert str(decrypted_data) == 'wrench', "decrypted data '{}' does not match original data 'wrench'".format(
            str(decrypted_data)
        )

    def test_server_connection():
        session = get_session_from_ctx_obj(ctx.obj, authenticate=False)

        try:
            server_fingerprint = session.server_fingerprint
        except GPGAuthException as e:
            raise AssertionError("could not verify server fingerprint ({})".format(e))
        else:
            expected_fingerprint = ctx.obj['config']['auth']['server_fingerprint']
            assert server_fingerprint == expected_fingerprint, ("server fingerprint {} does not match expected"
                                                                " fingerprint {}".format(server_fingerprint,
                                                                                         expected_fingerprint))

    def test_server_key():
        server_key_fingerprint = ctx.obj['config']['auth']['server_fingerprint']
        public_keys = ctx.obj['gpg'].list_keys()

        assert server_key_fingerprint in {key['fingerprint'] for key in public_keys}, "server key not found in keychain"

        return server_key_fingerprint

    def test_server_encryption():
        server_key_fingerprint = ctx.obj['config']['auth']['server_fingerprint']
        encrypted_data = ctx.obj['gpg'].encrypt('wrench', server_key_fingerprint, always_trust=True)

        assert encrypted_data.ok, "could not encrypt data with the server key {} ({})".format(
            server_key_fingerprint, encrypted_data.status
        )

    tests = (
        (wrench_version, "Wrench version"),
        (python_gnupg_version, "python-gnupg version"),
        (gnupg_version, "GnuPG version"),
        (test_secret_key, "User secret key exists"),
        (test_encryption, "Encryption/decryption using user key (passphrase dialog should open)"),
        (test_server_connection, "Server connection"),
        (test_server_key, "Server key exists"),
        (test_server_encryption, "Encryption using server key"),
    )
    for func, description in tests:
        run_test(func, description)


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
            "Error: no secret key available. Please export your key in Passbolt and run `wrench import-key "
            "<path_to_key>`.", err=True
        )
        sys.exit(ExitStatus.NO_SECRET_KEY.value)
    except FingerprintMismatchError as e:
        click.secho("Error: {}".format(e), err=True)


if __name__ == '__main__':
    main()
