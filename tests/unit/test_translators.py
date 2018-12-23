from uuid import uuid4

import pytest
from wrench.models import Permission, PermissionType
from wrench.translators import foreign as foreign_translators
from wrench.translators import local as local_translators

from ..factories import (EncryptedResourceFactory, GroupFactory, PermissionFactory, ResourceFactory, SecretFactory,
                         UserFactory)


def test_to_local_resource():
    resource = ResourceFactory()
    generated_resource = local_translators.to_local_resource({
        'id': resource.id, 'name': resource.name, 'uri': resource.uri, 'description': resource.description,
        'username': resource.username, 'secrets': [{'data': resource.secret}]
    })

    assert generated_resource == resource


@pytest.mark.parametrize('field', ('id', 'name', 'uri', 'username', 'secrets'))
def test_to_local_resource_with_missing_field_raises_error(field):
    values = {
        'id': uuid4(), 'name': 'bank', 'uri': 'example.com', 'username': 'jane.doe', 'secrets': [{'data': '1234'}]
    }
    del values[field]

    with pytest.raises(TypeError):
        local_translators.to_local_resource(values)


def test_to_local_resource_with_extra_field_ignores_it():
    resource = ResourceFactory()
    generated_resource = local_translators.to_local_resource({
        'id': resource.id, 'name': resource.name, 'uri': resource.uri, 'description': resource.description,
        'username': resource.username, 'secrets': [{'data': resource.secret}], 'extra': 'foo'
    })

    assert generated_resource == resource


def test_to_foreign_resource(gpg, users):
    user = UserFactory()
    resource = EncryptedResourceFactory(gpg=gpg, recipient=users[0].username)

    assert foreign_translators.to_foreign_resource(resource, user) == {
        'id': resource.id, 'name': resource.name, 'uri': resource.uri, 'description': resource.description,
        'username': resource.username, 'secrets': [{
            'data': resource.encrypted_secret,
            'resource_id': resource.id,
            'user_id': user.id,
        }]
    }


def test_to_foreign_secret():
    secret = SecretFactory()
    foreign_secret = foreign_translators.to_foreign_secret(secret)

    assert foreign_secret == {
        'data': secret.secret,
        'user_id': secret.recipient.id,
        'resource_id': secret.resource.id
    }


def test_to_foreign_secret_without_user_id_skips_key():
    secret = SecretFactory(recipient=None)
    foreign_secret = foreign_translators.to_foreign_secret(secret)

    assert foreign_secret == {
        'data': secret.secret,
        'resource_id': secret.resource.id
    }


def test_to_foreign_permission():
    permission = PermissionFactory()

    assert foreign_translators.to_foreign_permission(permission) == {
        'isNew': 'true',
        'aco': 'Resource',
        'aco_foreign_key': permission.resource.id,
        'aro': 'User',
        'aro_foreign_key': permission.recipient.id,
        'type': '15',
    }


def test_to_local_user():
    user = UserFactory(groups_ids=['42', '43'])
    user_dict = {
        'id': user.id,
        'gpgkey': {
            'id': user.gpg_key.id,
            'fingerprint': user.gpg_key.fingerprint,
            'armored_key': user.gpg_key.armored_key
        },
        'groups_users': [{'id': user.groups_ids[0]}, {'id': user.groups_ids[1]}],
        'username': user.username,
        'profile': {'first_name': user.first_name, 'last_name': user.last_name}
    }

    assert local_translators.to_local_user(user_dict) == user


def test_to_local_group():
    group = GroupFactory(members_ids=['42'])
    group_dict = {
        'groups_users': [{'user': {'id': '42'}}],
        'id': group.id,
        'name': group.name,
    }

    assert local_translators.to_local_group(group_dict) == group


def test_to_local_permission(users):
    group = GroupFactory(name='All', members_ids=[user.id for user in users])
    resource = ResourceFactory()
    permission = Permission(id='42', resource=resource, recipient=users[0], permission_type=PermissionType(15))
    permission_data = {
        'id': '42', 'aco_foreign_key': resource.id, 'aro': 'User', 'type': '15', 'aro_foreign_key': users[0].id
    }
    users_cache = {user.id: user for user in users}
    groups_cache = {group.id: group}

    assert local_translators.to_local_permission(permission_data, groups_cache, users_cache) == permission
