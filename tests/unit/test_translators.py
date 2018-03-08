from uuid import uuid4

import pytest
from wrench import translators

from ..factories import GroupFactory, ResourceFactory, SharedSecretFactory, UserFactory


def test_to_local_resource():
    resource = ResourceFactory()
    generated_resource = translators.to_local_resource({
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
        translators.to_local_resource(values)


def test_to_local_resource_with_extra_field_ignores_it():
    resource = ResourceFactory()
    generated_resource = translators.to_local_resource({
        'id': resource.id, 'name': resource.name, 'uri': resource.uri, 'description': resource.description,
        'username': resource.username, 'secrets': [{'data': resource.secret}], 'extra': 'foo'
    })

    assert generated_resource == resource


def test_to_foreign_resource():
    resource = ResourceFactory()

    assert translators.to_foreign_resource(resource) == {
        'Resource[id]': resource.id, 'Resource[name]': resource.name, 'Resource[uri]': resource.uri,
        'Resource[username]': resource.username, 'Secret[0][data]': resource.secret,
        'Resource[description]': resource.description
    }


def test_to_foreign_secret():
    user_id = str(uuid4())
    secret = translators.to_foreign_secret(0, user_id, 'secret')

    assert secret == {'Secret[0][data]': 'secret', 'Secret[0][user_id]': user_id}


def test_to_foreign_secret_without_user_id_skips_key():
    secret = translators.to_foreign_secret(0, None, 'secret')

    assert secret == {'Secret[0][data]': 'secret'}


def test_to_foreign_secrets():
    secrets = (
        ('42', "secret 0"),
        ('43', "secret 1"),
        (None, "secret 2"),
    )

    assert translators.to_foreign_secrets(secrets) == {
        'Secret[0][data]': 'secret 0',
        'Secret[0][user_id]': '42',
        'Secret[1][data]': 'secret 1',
        'Secret[1][user_id]': '43',
        'Secret[2][data]': 'secret 2',
    }


def test_to_foreign_shared_secrets():
    shared_secrets = SharedSecretFactory.build_batch(2)

    assert translators.to_foreign_shared_secrets(shared_secrets) == {
        'Permissions[0][Permission][isNew]': '1',
        'Permissions[0][Permission][aco]': 'Resource',
        'Permissions[0][Permission][aco_foreign_key]': shared_secrets[0].resource.id,
        'Permissions[0][Permission][aro]': 'User',
        'Permissions[0][Permission][aro_foreign_key]': shared_secrets[0].user.id,
        'Permissions[0][Permission][type]': '1',
        'Secrets[0][Secret][user_id]': shared_secrets[0].user.id,
        'Secrets[0][Secret][resource_id]': shared_secrets[0].resource.id,
        'Secrets[0][Secret][data]': shared_secrets[0].secret,
        'Permissions[1][Permission][isNew]': '1',
        'Permissions[1][Permission][aco]': 'Resource',
        'Permissions[1][Permission][aco_foreign_key]': shared_secrets[1].resource.id,
        'Permissions[1][Permission][aro]': 'User',
        'Permissions[1][Permission][aro_foreign_key]': shared_secrets[1].user.id,
        'Permissions[1][Permission][type]': '1',
        'Secrets[1][Secret][user_id]': shared_secrets[1].user.id,
        'Secrets[1][Secret][resource_id]': shared_secrets[1].resource.id,
        'Secrets[1][Secret][data]': shared_secrets[1].secret,
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

    assert translators.to_local_user(user_dict) == user


def test_to_local_group():
    group = GroupFactory(members_ids=['42'])
    group_dict = {
        'groups_users': [{'user': {'id': '42'}}],
        'id': group.id,
        'name': group.name,
    }

    assert translators.to_local_group(group_dict) == group
