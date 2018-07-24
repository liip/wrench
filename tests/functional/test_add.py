import copy
from unittest.mock import patch

from ..assertions import assert_resource_shared, assert_tags_added
from ..conftest import default_config
from ..factories import EncryptedResourceFactory
from ..utils import to_foreign_resource_response


def run_add_command(cli, inputs, secret_input, cmd_args=None, **kwargs):
    with patch('wrench.io.getpass') as getpass_mock, patch('wrench.io.input') as input_mock:
        input_mock.side_effect = inputs
        getpass_mock.return_value = secret_input

        return cli('add', cmd_args, **kwargs)


def get_add_resource_inputs(resource):
    """
    Return a tuple of strings that can be used as a side-effect to the `input` function to simulate the entry of a
    resource in the `add` command.
    """
    return resource.name, resource.uri, resource.description, resource.username, ', '.join(resource.tags)


def test_add_sends_encrypted_secret(cli, gpg, api, users):
    resource = EncryptedResourceFactory(gpg=gpg, recipient=users[0].username)
    api.endpoints['add_resource'] = to_foreign_resource_response(resource)

    run_add_command(cli, get_add_resource_inputs(resource) + ('',), resource.secret)

    assert api.mocks['add_resource'].called
    assert gpg.decrypt(api.mocks['add_resource'].call_args[0][-1]['secrets'][0]['data']) == resource.secret


def test_tags_are_set(cli, gpg, api, users):
    resource = EncryptedResourceFactory(gpg=gpg, recipient=users[0].username, tags=('foo', 'bar', '#pub'))
    api.endpoints['add_resource'] = to_foreign_resource_response(resource)

    run_add_command(cli, get_add_resource_inputs(resource) + ('',), resource.secret)

    assert_tags_added(api, resource, resource.tags)


def test_empty_tags_does_not_call_add_tags(cli, gpg, api, users):
    resource = EncryptedResourceFactory(gpg=gpg, recipient=users[0].username, tags=[])
    api.endpoints['add_resource'] = to_foreign_resource_response(resource)

    run_add_command(cli, get_add_resource_inputs(resource) + ('',), resource.secret)

    assert not api.mocks['add_tags'].called


def test_add_with_sharing_encrypts_data_for_recipient(cli, gpg, api, users):
    resource = EncryptedResourceFactory(gpg=gpg, recipient=users[0].username)
    api.endpoints['add_resource'] = to_foreign_resource_response(resource)

    run_add_command(cli, get_add_resource_inputs(resource) + (users[1].username,), resource.secret)

    assert_resource_shared(api, resource, [users[1]], gpg)


def test_added_resource_is_shared_with_default_recipients(cli, gpg, api, users):
    config = copy.deepcopy(default_config)
    config['sharing']['default_recipients'] = 'All, {}'.format(users[1].username)
    resource = EncryptedResourceFactory(gpg=gpg, recipient=users[0].username)
    api.endpoints['add_resource'] = to_foreign_resource_response(resource)

    run_add_command(cli, get_add_resource_inputs(resource) + (users[1].username,), resource.secret, config=config)

    assert_resource_shared(api, resource, users, gpg)


def test_invalid_default_recipient_shows_error(cli, gpg, api, users):
    config = copy.deepcopy(default_config)
    config['sharing']['default_recipients'] = 'inexistent@localhost'
    resource = EncryptedResourceFactory(gpg=gpg, recipient=users[0].username)
    api.add_resource = to_foreign_resource_response(resource)

    result = run_add_command(cli, get_add_resource_inputs(resource) + (users[1].username,), resource.secret,
                             config=config)

    assert 'Invalid default recipient' in result.output
    assert not api.mocks['share_resource'].called


def test_group_recipient_shares_with_all_group_members(cli, gpg, api, users):
    resource = EncryptedResourceFactory(gpg=gpg, recipient=users[0].username)
    api.endpoints['add_resource'] = to_foreign_resource_response(resource)

    run_add_command(cli, get_add_resource_inputs(resource) + ('All',), resource.secret)

    assert_resource_shared(api, resource, users, gpg)


def test_share_with_invalid_recipient_shows_error(cli, gpg, api, users):
    resource = EncryptedResourceFactory(gpg=gpg, recipient=users[0].username)
    api.endpoints['add_resource'] = to_foreign_resource_response(resource)

    result = run_add_command(cli, get_add_resource_inputs(resource) + ('foobar', users[1].username), resource.secret)

    assert 'Recipient foobar is invalid' in result.output
