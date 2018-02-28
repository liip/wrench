import uuid

import factory
from wrench.resources import Resource


class ResourceFactory(factory.Factory):
    class Meta:
        model = Resource

    id = factory.Faker('uuid4')
    name = factory.Faker('words')
    uri = factory.Faker('url')
    description = factory.Faker('sentence')
    username = factory.Faker('user_name')
    secret = factory.Faker('password')
