import copy
import itertools
from unittest.mock import patch

import pytest

from ..assertions import assert_resource_added, assert_resource_shared, assert_tags_added
from ..conftest import default_config
from ..factories import EncryptedResourceFactory
from ..utils import to_foreign_resource_response

VALID_RESOURCES_FILE_CONTENTS = ("host	username	password	description	product\n"
                                 "https://www.example.com/	admin	1234	admin password	example site")
INVALID_RESOURCES_FILE_CONTENTS = ("host	username	password	description	product\n"
                                   "https://www.example.com/	admin	1234	admin password	example site\n"
                                   "https://www.example.com/	admin	1234 admin password	example site\n")


@pytest.fixture
def valid_resources_file(tmpdir):
    resources_file = tmpdir.join('resources.txt')
    resources_file.write(VALID_RESOURCES_FILE_CONTENTS)

    return resources_file


@pytest.fixture
def invalid_resources_file(tmpdir):
    resources_file = tmpdir.join('resources.txt')
    resources_file.write(INVALID_RESOURCES_FILE_CONTENTS)

    return resources_file


def run_import_resources_command(cli, path, owners='', readers='', tags=None, *args, **kwargs):
    params = [path]

    if tags:
        tags_params = [['-t', tag] for tag in tags]
        params += list(itertools.chain(*tags_params))

    with patch('wrench.io.input') as input_mock:
        input_mock.side_effect = [owners, readers]
        return cli('import-resources', params, *args, **kwargs)


def get_imported_resource(gpg, username):
    """
    Return a `Resource` object representing one of the imported resources.
    """
    return EncryptedResourceFactory(
        gpg=gpg, recipient=username, uri='https://www.example.com/', username='admin',
        description='admin password', name='example site', secret='1234'
    )


def test_import_imports_data(cli, tmpdir, api, users, gpg, valid_resources_file):
    resource = get_imported_resource(gpg, users[0].username)
    api.endpoints['add_resource'] = to_foreign_resource_response(resource)

    run_import_resources_command(cli, str(valid_resources_file))

    assert_resource_added(api, resource, users[0], gpg)


def test_import_with_invalid_record_doesnt_import_anything(cli, invalid_resources_file):
    result = run_import_resources_command(cli, str(invalid_resources_file))

    assert result.exit_code == 1
    assert "Could not split line 3" in result.output


def test_import_with_tags_creates_tags(cli, api, users, gpg, valid_resources_file):
    resource = EncryptedResourceFactory(gpg=gpg, recipient=users[0].username)
    api.endpoints['add_resource'] = to_foreign_resource_response(resource)

    run_import_resources_command(cli, str(valid_resources_file), tags=['#foo', '#bar'])

    assert_tags_added(api, resource, ['#foo', '#bar'])


def test_import_with_tags_creates_public_tags(cli, api, users, gpg, valid_resources_file):
    resource = EncryptedResourceFactory(gpg=gpg, recipient=users[0].username)
    api.endpoints['add_resource'] = to_foreign_resource_response(resource)

    run_import_resources_command(cli, str(valid_resources_file), tags=['foo', '#bar'])

    assert_tags_added(api, resource, ['#foo', '#bar'])


def test_import_inexistent_file_shows_error(cli):
    result = run_import_resources_command(cli, '/dev/null/inexistent.txt')
    assert "does not exist" in result.output


def test_import_shares_resources_with_recipients(cli, api, users, gpg, valid_resources_file):
    resource = get_imported_resource(gpg, users[0].username)
    api.endpoints['add_resource'] = to_foreign_resource_response(resource)

    run_import_resources_command(cli, str(valid_resources_file), owners=users[1].username)

    assert_resource_shared(api, resource, [users[1]], gpg)


def test_import_shares_resources_with_default_recipients(cli, api, users, gpg, valid_resources_file):
    config = copy.deepcopy(default_config)
    config['sharing']['default_owners'] = users[1].username
    resource = get_imported_resource(gpg, users[0].username)
    api.endpoints['add_resource'] = to_foreign_resource_response(resource)

    run_import_resources_command(cli, str(valid_resources_file), config=config)

    assert_resource_shared(api, resource, [users[1]], gpg)
