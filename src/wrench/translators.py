from typing import Any, Dict, Iterable, Optional, Tuple

from . import utils
from .resources import Resource, SharedSecret
from .users import GpgKey, Group, User


def to_local_resource(data: Dict[str, Any]) -> Resource:
    """
    Return a :class:`Resource` object created from the values from the given `data`. which is expected to be a dict
    with the following keys (extra fields are ignored)::

        ('id', 'name', 'uri', 'description', 'username', 'secrets')

    The `secrets` key is expected to contain a list of dicts in the form `{'data': '...'}`.
    """
    # Make sure the exception is the same whether the secret or any other field is missing
    try:
        resource_data = dict(data, secret=data['secrets'][0]['data'])
    except (IndexError, KeyError):
        resource_data = data

    return utils.dict_to_namedtuple(Resource, resource_data)


def to_foreign_resource(resource: Resource) -> Dict[str, Any]:
    """
    Return a data dict representing a resource suitable to be used in Passbolt. Its structure is the following::

        {
            'Resource[id]': '...',
            'Resource[name]': '...',
            ...
            'Secret[0][data]': '...',
        }
    """
    secrets_dict = to_foreign_secret(0, None, resource.secret)

    return dict(
        {'Resource[{}]'.format(key): value for key, value in resource._asdict().items() if key != 'secret'},
        **secrets_dict
    )


def to_foreign_secret(index: int, user_id: Optional[str], secret: str) -> Dict[str, str]:
    """
    Return a data dict representing a secret suitable to be used in Passbolt. Its structure is the following::

        {
            'Secret[x][data]': '...',
            'Secret[x][user_id]': '...',
        }

    Where `x` is the given `index`. If `user_id` evaluates to False, the key is not included in the dict.
    """
    secret_dict = {'Secret[{}][data]'.format(index): secret}

    if user_id:
        secret_dict = dict(secret_dict, **{'Secret[{}][user_id]'.format(index): user_id})

    return secret_dict


def to_foreign_secrets(secrets: Iterable[Tuple[str, str]]) -> Dict[str, str]:
    """
    Return a data dict representing a series of secrets suitable to be used in Passbolt. See :func:`to_foreign_secret`
    for details on the structure.
    """
    secrets_dict = {}  # type: Dict[str, str]

    for i, (user_id, secret) in enumerate(secrets):
        secrets_dict.update(to_foreign_secret(i, user_id, secret))

    return secrets_dict


def to_foreign_shared_secret(index: int, shared_secret: SharedSecret) -> Dict[str, str]:
    """
    Return a data dict representing a secret to share suitable to be used in Passbolt. Its structure is the following::

        {
            'Permissions[x][Permission][isNew]': '1',
            'Permissions[x][Permission][aco]': 'Resource',
            'Permissions[x][Permission][aco_foreign_key]': '...',
            'Permissions[x][Permission][aro]': 'User',
            'Permissions[x][Permission][aro_foreign_key]': '...',
            'Permissions[x][Permission][type]': '1',
            'Secrets[x][Secret][user_id]': '...',
            'Secrets[x][Secret][resource_id]': '...',
            'Secrets[x][Secret][data]': '...'
        }

    Where `x` is the given `index`.
    """
    permission_key = 'Permissions[{}][Permission]'.format(index)
    secret_key = 'Secrets[{}][Secret]'.format(index)

    return {
        permission_key + '[isNew]': '1',
        permission_key + '[aco]': 'Resource',
        permission_key + '[aco_foreign_key]': shared_secret.resource.id,
        permission_key + '[aro]': 'User',
        permission_key + '[aro_foreign_key]': shared_secret.user.id,
        permission_key + '[type]': str(shared_secret.permission_type),
        secret_key + '[resource_id]': shared_secret.resource.id,
        secret_key + '[user_id]': shared_secret.user.id,
        secret_key + '[data]': shared_secret.secret,
    }


def to_foreign_shared_secrets(shared_secrets: Iterable[SharedSecret]) -> Dict[str, str]:
    """
    Return a data dict representing secrets to share suitable to be used in Passbolt. See
    :func:`to_foreign_shared_secret` for details on the structure.
    """
    shared_secrets_dict = {}  # type: Dict[str, str]

    for i, shared_secret in enumerate(shared_secrets):
        shared_secrets_dict.update(to_foreign_shared_secret(i, shared_secret))

    return shared_secrets_dict


def to_local_user(user_data: Dict[str, Any]) -> User:
    """
    Return a :class:`User` object created from the given `user_data` dict, which is expected to have the following
    structure::

        {
            'id': '...',
            'gpgkey': {'id': '...', 'fingerprint': '...', 'armored_key': '...'},
            'groups_users': [{'id': '...'}],
            'username': '...',
            'profile': {'first_name': '...', 'last_name': '...'}
        }
    """
    # Users might not have a gpgkey set if they've been invited but have not yet created their account
    gpg_key = utils.dict_to_namedtuple(GpgKey, user_data['gpgkey']) if user_data['gpgkey'] else None
    groups_ids = [group['id'] for group in user_data['groups_users']]
    user = User(id=user_data['id'], username=user_data['username'], first_name=user_data['profile']['first_name'],
                last_name=user_data['profile']['last_name'], groups_ids=groups_ids, gpg_key=gpg_key)

    return user


def to_local_group(group_data: Dict[str, Any]) -> Group:
    """
    Return a :class:`Group` object created from the given `group_data` dict, which is expected to have the following
    structure::

        {
            'groups_users': [{'user': {'id': '...'}}]
            'id': '...',
            'name': '...'
        }
    """
    members = [member['user']['id'] for member in group_data.get('groups_users', [])]
    group = utils.dict_to_namedtuple(Group, group_data, members_ids=members)

    return group
