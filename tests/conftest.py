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

import glob
import os
import stat
from typing import Any, Dict, Generator, Iterable, List, Mapping, Tuple
from unittest.mock import patch, Mock  # noqa

import pytest
import wrench.commands
from click.testing import CliRunner
from gnupg import GPG
from wrench.models import User
from wrench.utils import decrypt

from .factories import GpgUserFactory, GroupFactory
from .utils import to_foreign_group_response, to_foreign_user_response

default_config = {
    'auth': {
        'server_url': 'http://localhost',
        'server_fingerprint': 'F' * 40,
        'http_username': 'john.doe',
        'http_password': 'password',
    },
    'sharing': {}
}

pytest.register_assert_rewrite("tests.assertions")


class GpgSandbox:
    """
    Wrapper for a :class:`gnupg.GPG` instance that uses a temporary directory as its home directory. This allows to
    import keys without messing with the user's file system. It automatically imports files named `*.key` placed in
    `keys_dir` (`data/keys` by default). The keys can then be referenced by their filename minus the `.key` extension,
    for example `john.doe.key` can then be used with `gpg.get_key('john.doe').
    """
    def __init__(self, tmpdir: str, keys_dir: str = 'data/keys') -> None:
        # GPG needs the homedir to have limited permissions
        os.chmod(tmpdir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        self.homedir = tmpdir
        self.gpg = GPG(gnupghome=tmpdir)
        self.keys = self.import_keys(keys_dir)

    def get_key_files(self, keys_dir: str) -> Iterable[str]:
        """
        Return the list of key files in the keys directory.
        """
        return glob.glob(os.path.join(os.path.dirname(__file__), keys_dir, '*.key'))

    def import_key(self, key: str) -> str:
        """
        Import the given armored key and return its fingerprint.
        """
        import_result = self.gpg.import_keys(key)

        return import_result.fingerprints[0]

    def import_keys(self, keys_dir: str) -> Dict[str, Tuple[str, str]]:
        """
        Iterate over the `.key` files in `keys_dir` and import then into GPG.
        """
        keys = {}

        for key_path in self.get_key_files(keys_dir):
            username = os.path.basename(key_path)[:-len('.key')]

            with open(key_path) as key_file:
                key = key_file.read()

            keys[username] = (self.import_key(key), key)

        return keys

    def encrypt(self, data: str, username: str) -> str:
        """
        Return `data` encrypted for `username`, which should match a key in the keys directory.
        """
        return str(self.gpg.encrypt(data, self.keys[username][0], always_trust=True))

    def decrypt(self, data: str) -> str:
        """
        Return `data` decrypted. A corresponding private key must be available so this data can be decrypted.
        """
        return decrypt(data, self.gpg)

    def get_fingerprint(self, username: str) -> str:
        """
        Return the key fingerprint of the given username.
        """
        return self.keys[username][0]

    def get_key(self, username: str) -> str:
        """
        Return the armored key of the given username.
        """
        return self.keys[username][1]


class ApiStub:
    """
    Patch the Passbolt API upon object creation, so that any call to a Passbolt API endpoint will return the value of
    the corresponding attribute. For example the function `wrench.passbolt_api.get_users` will be mocked to return the
    value of the `api_stub_instance.get_users` attribute.

    Note that only calls to the Passbolt API from the `wrench.services` module are patched.
    """
    patches = {
        'get_resources': [],
        'get_users': [],
        'share_resource': {},
        'get_user': {},
        'get_groups': [],
        'get_group': {},
        'add_resource': {},
        'get_resource_permissions': [],
        'add_tags': {},
    }  # type: Dict[str, Any]

    def __init__(self):
        self.endpoints = {}  # type: Dict[str, Any]
        self.start()

    def start(self) -> None:
        def get_mock_value(func: str) -> Any:
            def inner(*args, **kwargs):
                return self.endpoints[func]

            return inner

        self.mocks = {}  # type: Dict[str, Mock]
        self.patchers = []  # type: ignore

        for func, default_value in ApiStub.patches.items():
            self.endpoints[func] = default_value
            patcher = patch('wrench.services.passbolt_api.' + func)

            self.patchers.append(patcher)
            self.mocks[func] = patcher.start()
            self.mocks[func].side_effect = get_mock_value(func)

    def stop(self) -> None:
        for patcher in self.patchers:
            patcher.stop()

        self.mocks = {}


@pytest.fixture
def api(users: List[User]) -> Generator[ApiStub, None, None]:
    """
    Create an :class:`ApiStub` object and return it. This will mock all the calls to the Passbolt API. Check the
    documentation from the :class:`ApiStub` class for more information on how to override the calls to the API.

    This fixture will also by default set the return values of the following API endpoints:

        * get_users: return the users from the `users` fixture
        * get_user: return the first user from the `users` fixture
        * get_groups: return a group named 'All' that contains all users from the `users` fixture
    """
    api_stub = ApiStub()
    api_stub.endpoints['get_users'] = [to_foreign_user_response(user) for user in users]
    api_stub.endpoints['get_user'] = to_foreign_user_response(users[0])
    api_stub.endpoints['get_groups'] = [
        to_foreign_group_response(GroupFactory(name='All', members_ids=[user.id for user in users]))
    ]

    yield api_stub

    api_stub.stop()


@pytest.fixture
def users(gpg):
    """
    Return two :class:`wrench.models.User` objects that have valid GPG keys.
    """
    return GpgUserFactory.create_batch(2, gpg=gpg)


@pytest.fixture
def gpg(tmpdir):
    """
    Return a :class:`GpgSandbox` instance that will act on a temporary directory.
    """
    return GpgSandbox(str(tmpdir))


@pytest.fixture
def cli(gpg):
    """
    Provide a callable that executes the given wrench command with a sandboxed GPG instance. The first parameter should
    be the wrench command to execute, and the second parameter a list of arguments to pass. Use it like this::

        cli('search', ['foobar'])

    This will execute `wrench search foobar`. You can also use the `config` keyword to pass a config dict (if not
    provided, the value of `default_config` will be used).

    Additional kwargs are passed to the `click.CliRunner.invoke` method.
    """
    def inner(cmd: str, cmd_args: List[str] = None, config: Mapping[str, Any] = None, **kwargs) -> Any:
        if not cmd_args:
            cmd_args = []

        if not config:
            config = dict(default_config)

        with patch('wrench.commands.GPGAuthSession') as GPGAuthSession:
            GPGAuthSession.return_value.server_fingerprint = 'F' * 40
            GPGAuthSession.return_value.user_fingerprint = gpg.get_fingerprint('john.doe')

            return CliRunner(echo_stdin=True).invoke(
                wrench.commands.cli, [cmd] + cmd_args, catch_exceptions=False, obj={
                    'gpg': gpg.gpg,
                    'config': config,
                }, **kwargs
            )

    return inner
