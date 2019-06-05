from unittest.mock import patch

import pytest
from wrench.exceptions import FingerprintMismatchError

from ..conftest import default_config
from ..factories import EncryptedResourceFactory
from ..utils import to_foreign_resource_response


def run_search(cli, search, input_='q', *args, **kwargs):
    with patch('wrench.commands.getch') as getch_mock:
        getch_mock.return_value = input_

        return cli('search', [search], *args, **kwargs)


def test_search_doesnt_include_non_matching_resources(cli, gpg, users, api):
    resource = EncryptedResourceFactory(
        gpg=gpg, recipient=users[0].username, name='bank account', username='jane.doe', uri='example.com',
        description='my bank account'
    )
    api.endpoints['get_resources'] = [to_foreign_resource_response(resource)]

    result = run_search(cli, 'production')

    assert 'bank account' not in result.output


def test_search_includes_matching_resources(cli, gpg, users, api):
    resource = EncryptedResourceFactory(gpg=gpg, recipient=users[0].username, name='bank account')
    api.endpoints['get_resources'] = [to_foreign_resource_response(resource)]
    api.endpoints['get_resource_secret'] = {'data': resource.encrypted_secret}

    result = run_search(cli, 'bank')

    assert resource.description in result.output


def test_fingerprint_mismatch(cli):
    config = dict(default_config)
    config['auth']['server_fingerprint'] = 'A' * 40

    with pytest.raises(FingerprintMismatchError):
        cli('search', ['bank'], config=config)
