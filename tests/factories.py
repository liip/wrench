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
    tags = []


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
    username = factory.Faker('user_name')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    groups_ids = ()
    gpg_key = factory.SubFactory(GpgKeyFactory)


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
