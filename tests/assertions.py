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

from typing import Iterable

from wrench.exceptions import DecryptionError
from wrench.models import Resource, User
from wrench.utils import subdict

from .conftest import ApiStub, GpgSandbox


def assert_resource_added(api: ApiStub, resource: Resource, recipient: User, gpg: GpgSandbox) -> None:
    try:
        sent_secret = gpg.decrypt(api.mocks['add_resource'].call_args[0][1]['secrets'][0]['data'])
    except DecryptionError as e:
        raise AssertionError("Could not decrypt sent secret, error was: {}".format(e))

    assert api.mocks['add_resource'].called, "API endpoint add_resource not called"
    assert resource.secret == sent_secret, "Sent secret doesn't match resource secret"
    assert subdict(api.mocks['add_resource'].call_args[0][1], {'id', 'name', 'uri', 'description', 'username'}) == {
        'id': None,
        'name': resource.name,
        'uri': resource.uri,
        'description': resource.description,
        'username': resource.username,
    }


def assert_resource_shared(api: ApiStub, resource: Resource, recipients: Iterable[User], gpg: GpgSandbox) -> None:
    assert api.mocks['share_resource'].called, "API endpoint share_resource not called"

    actual_user_ids = {secret['user_id'] for secret in api.mocks['share_resource'].call_args[1]['data']['secrets']}
    expected_user_ids = {user.id for user in recipients}
    assert actual_user_ids == expected_user_ids, "Resource not shared with expected user ids"

    secrets = {secret['data'] for secret in api.mocks['share_resource'].call_args[1]['data']['secrets']}
    for secret in secrets:
        decrypted_secret = gpg.decrypt(secret)
        assert decrypted_secret == resource.secret, "Decrypted secret doesn't match original secret"


def assert_tags_added(api: ApiStub, resource: Resource, tags: Iterable[str]) -> None:
    assert api.mocks['add_tags'].called
    assert api.mocks['add_tags'].call_args[0][1:] == (resource.id, {'Tags': list(tags)})
