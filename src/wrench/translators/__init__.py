from typing import Any, Callable, Mapping, Optional, Tuple, Type, TypeVar, Union  # noqa

from . import foreign, local
from ..models import Group, Permission, Resource, Secret, User

TRANSLATORS = {
    Resource: (local.to_local_resource, foreign.to_foreign_resource),
    Group: (local.to_local_group, foreign.to_foreign_group),
    User: (local.to_local_user, foreign.to_foreign_user),
    Secret: (None, foreign.to_foreign_secret),
    Permission: (local.to_local_permission, foreign.to_foreign_permission),
}  # type: Mapping[Any, Tuple[Optional[Callable], Optional[Callable]]]
T = TypeVar('T')


class TranslatorNotFound(Exception):
    ...


def get_translator(entity_type: Any, local: bool) -> Optional[Callable]:
    try:
        return TRANSLATORS[entity_type][0 if local else 1]
    except KeyError:
        raise TranslatorNotFound("Entity type {} doesn't have any associated translator".format(entity_type))


def to_local(obj: Mapping[str, Any], local_type: Type[T], *args, **kwargs) -> T:
    translator = get_translator(local_type, local=True)

    if not translator:
        raise TranslatorNotFound("Entity type {} doesn't have any local translator".format(local_type))

    return translator(obj, *args, **kwargs)


def to_foreign(obj: Union[Group, Permission, Resource, Secret, User], *args, **kwargs) -> Mapping[str, Any]:
    translator = get_translator(type(obj), local=False)

    if not translator:
        raise TranslatorNotFound("Entity type {} doesn't have any foreign translator".format(type(obj)))

    return translator(obj, *args, **kwargs)
