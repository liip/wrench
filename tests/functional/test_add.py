from unittest.mock import patch

from ..factories import ResourceFactory, UserFactory
from ..utils import to_foreign_resource_response, to_foreign_user_response


@patch('wrench.io.getpass')
@patch('wrench.io.input')
@patch('wrench.services.passbolt_api.get_user')
@patch('wrench.services.passbolt_api.get_users')
@patch('wrench.services.passbolt_api.add_resource')
@patch('wrench.commands.get_session_from_ctx_obj')
def test_add_sends_encrypted_secret(get_session_from_ctx_obj, add_resource, get_users, get_user, input, getpass,
                                    cli, gpg):
    resource = ResourceFactory(id=None)
    encrypted_resource = resource._replace(secret=gpg.encrypt(resource.secret, 'john.doe'), id='42')
    users = UserFactory.build_batch(2)

    input.side_effect = (resource.name, resource.uri, resource.description, resource.username, '')
    getpass.return_value = resource.secret
    get_session_from_ctx_obj.return_value.user_fingerprint = gpg.get_fingerprint('john.doe')
    add_resource.return_value = to_foreign_resource_response(encrypted_resource)
    get_users.return_value = [to_foreign_user_response(user) for user in users]
    get_user.return_value = to_foreign_user_response(users[0])

    cli('add')

    assert add_resource.called
    assert gpg.decrypt(add_resource.call_args[0][-1]['Secret[0][data]']) == resource.secret


@patch('wrench.io.getpass')
@patch('wrench.io.input')
@patch('wrench.services.passbolt_api.share_resource')
@patch('wrench.services.passbolt_api.get_user')
@patch('wrench.services.passbolt_api.get_users')
@patch('wrench.services.passbolt_api.add_resource')
@patch('wrench.commands.get_session_from_ctx_obj')
def test_add_with_sharing_encrypts_data_for_recipient(get_session_from_ctx_obj, add_resource, get_users, get_user,
                                                      share_resource, input, getpass, cli, gpg):
    def user_factory_key_args(email):
        return dict(username=email, gpg_key__fingerprint=gpg.get_fingerprint(email),
                    gpg_key__armored_key=gpg.get_key(email))

    resource = ResourceFactory(id=None)
    encrypted_resource = resource._replace(secret=gpg.encrypt(resource.secret, 'john.doe'), id='42')
    users = (UserFactory(**user_factory_key_args('john.doe')),
             UserFactory(**user_factory_key_args('alicia.doe')))

    input.side_effect = (resource.name, resource.uri, resource.description, resource.username, users[1].username)
    getpass.return_value = resource.secret
    get_session_from_ctx_obj.return_value.user_fingerprint = gpg.get_fingerprint('john.doe')
    add_resource.return_value = to_foreign_resource_response(encrypted_resource)
    get_users.return_value = [to_foreign_user_response(user) for user in users]
    get_user.return_value = to_foreign_user_response(users[0])

    cli('add')

    assert share_resource.called
    assert share_resource.call_args[1]['resource_id'] == '42'
    assert gpg.decrypt(share_resource.call_args[1]['data']['Secrets[0][Secret][data]']) == resource.secret
