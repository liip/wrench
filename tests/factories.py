import factory
from wrench.resources import PermissionType, Resource, SharedSecret
from wrench.users import GpgKey, Group, User


class ResourceFactory(factory.Factory):
    class Meta:
        model = Resource

    id = factory.Faker('uuid4')
    name = factory.Faker('word')
    uri = factory.Faker('url')
    description = factory.Faker('sentence')
    username = factory.Faker('user_name')
    secret = factory.Faker('password')


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


class SharedSecretFactory(factory.Factory):
    class Meta:
        model = SharedSecret

    resource = factory.SubFactory(ResourceFactory)
    user = factory.SubFactory(UserFactory)
    permission_type = PermissionType.READ.value
    secret = factory.Faker('password')
