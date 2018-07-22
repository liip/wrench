from typing import List  # noqa

import factory
from wrench.models import GpgKey, Group, Permission, PermissionType, Resource, Secret, User


class ResourceFactory(factory.Factory):
    class Meta:
        model = Resource

    id = factory.Faker('uuid4')
    name = factory.Faker('word')
    uri = factory.Faker('url')
    description = factory.Faker('sentence')
    username = factory.Faker('user_name')
    secret = factory.Faker('password')
    encrypted_secret = None
    tags = []  # type: List[str]


class EncryptedResourceFactory(ResourceFactory):
    encrypted_secret = factory.LazyAttribute(lambda o: o.gpg.encrypt(o.secret, o.recipient))

    class Params:
        gpg = None
        recipient = None


class GpgKeyFactory(factory.Factory):
    class Meta:
        model = GpgKey

    id = factory.Faker('uuid4')
    fingerprint = 'fingerprint'
    armored_key = 'armored key'


class GroupFactory(factory.Factory):
    class Meta:
        model = Group

    id = factory.Faker('uuid4')
    name = factory.Faker('word')
    members_ids = ()


class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.Faker('uuid4')
    username = factory.Faker('email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    groups_ids = ()
    gpg_key = factory.SubFactory(GpgKeyFactory)


class GpgUserFactory(UserFactory):
    username = factory.Iterator(['john.doe', 'alicia.doe'])
    gpg_key = factory.SubFactory(
        GpgKeyFactory, fingerprint=factory.LazyAttribute(
            lambda o: o.factory_parent.gpg.get_fingerprint(o.factory_parent.username)
        ), armored_key=factory.LazyAttribute(lambda o: o.factory_parent.gpg.get_key(o.factory_parent.username))
    )

    class Params:
        gpg = None


class SecretFactory(factory.Factory):
    class Meta:
        model = Secret

    resource = factory.SubFactory(ResourceFactory)
    recipient = factory.SubFactory(UserFactory)
    secret = factory.Faker('password')


class PermissionFactory(factory.Factory):
    class Meta:
        model = Permission

    resource = factory.SubFactory(ResourceFactory)
    recipient = factory.SubFactory(UserFactory)
    permission_type = PermissionType.OWNER.value
