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


def test_search_without_result_shows_message(cli, gpg, users, api):
    resource = EncryptedResourceFactory(
        gpg=gpg, recipient=users[0].username, name='bank account', username='jane.doe', uri='example.com',
        description='my bank account'
    )
    api.endpoints['get_resources'] = [to_foreign_resource_response(resource)]

    result = run_search(cli, 'production')

    assert "Couldn't find any entry that matches your search." in result.output


def test_search_includes_matching_resources(cli, gpg, users, api):
    resources = [
        EncryptedResourceFactory(gpg=gpg, recipient=users[0].username, name='bank account'),
        EncryptedResourceFactory(gpg=gpg, recipient=users[0].username, name='second bank account'),
    ]
    api.endpoints['get_resources'] = [to_foreign_resource_response(resource) for resource in resources]
    api.endpoints['get_resource_secret'] = [{'data': resource.encrypted_secret} for resource in resources]

    result = run_search(cli, 'bank')

    assert all(resource.description in result.output for resource in resources)


def test_search_skips_resource_selection_if_one_result(cli, gpg, users, api):
    resource = EncryptedResourceFactory(
        gpg=gpg, recipient=users[0].username, name='bank account', username='jane.doe', uri='example.com',
        description='my bank account'
    )
    api.endpoints['get_resources'] = [to_foreign_resource_response(resource)]
    api.endpoints['get_resource_secret'] = {'data': resource.encrypted_secret}

    result = run_search(cli, 'bank', input_='')

    assert resource.secret in result.output


def test_fingerprint_mismatch(cli):
    config = dict(default_config)
    config['auth']['server_fingerprint'] = 'A' * 40

    with pytest.raises(FingerprintMismatchError):
        cli('search', ['bank'], config=config)
