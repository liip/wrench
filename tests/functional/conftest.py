import glob
import os
import stat
from typing import Any, Dict, Iterable, List, Mapping, Tuple
from unittest.mock import patch

import pytest
import wrench.commands
from click.testing import CliRunner
from gnupg import GPG


default_config = {
    'auth': {
        'server_url': 'http://localhost',
        'server_fingerprint': 'F' * 40,
        'http_username': 'john.doe',
        'http_password': 'password',
    }
}


class GpgSandbox:
    """
    The GPG sandbox wraps a :class:`gnupg.GPG` instance that uses a temporary directory as its home directory. This
    allows to import keys without messing with the user's system. It automatically imports files named `*.key` placed
    in `keys_dir` (`data/keys`) by default. The keys can then be referenced by their filename minus the `.key`
    extension, for example `john.doe.key` can then be used with `gpg.get_key('john.doe').
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
        return glob.glob(os.path.join(os.path.dirname(__file__), '..', keys_dir, '*.key'))

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
        return str(self.gpg.decrypt(data, always_trust=True))

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


@pytest.fixture
def gpg(tmpdir):
    return GpgSandbox(str(tmpdir))


@pytest.fixture
def cli(gpg):
    """
    Fixture for a callable that executes the given wrench command with a sandboxed GPG instance. Use it like this::

        cli('search', ['foobar'])

    This will execute `wrench search foobar`. You can also use the `config` keyword to pass a config dict (if not
    provided, the value of `default_config` will be used).

    Additional kwargs are passed to the `click.CliRunner.invoke` method.
    """
    def inner(cmd: str, args: List[str] = None, config: Mapping[str, Any] = None, **kwargs) -> Any:
        if not args:
            args = []

        if not config:
            config = dict(default_config)

        with patch('wrench.commands.GPGAuthSession') as GPGAuthSession:
            GPGAuthSession.return_value.server_fingerprint = 'F' * 40

            return CliRunner(echo_stdin=True).invoke(wrench.commands.cli, [cmd] + args, catch_exceptions=False, obj={
                'gpg': gpg.gpg,
                'config': config,
            }, **kwargs)

    return inner
