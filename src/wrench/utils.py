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

from typing import Any, Dict, Iterable, Sequence, Tuple, Type, TypeVar

from gnupg import GPG

T = TypeVar('T')


def subdict(d: Dict, keys: Iterable) -> Dict:
    """
    Return a new dict with only keys from `d` that are also in `keys`.
    """
    return {key: d[key] for key in keys if key in d}


def decrypt(data: str, gpg: GPG) -> str:
    """
    Decrypt `data` with `gpg` and return its value.
    """
    return str(gpg.decrypt(data, always_trust=True))


def dict_to_namedtuple(cls: Type[T], data_dict: Dict[str, Any], **kwargs) -> T:
    """
    Transform the given `data_dict` to an object of type `cls`, using the keys from `data_dict` that exist as
    attributes of `cls`. The given `kwargs` are passed as additional parameters when constructing the object.
    """
    # We can't typehint NamedTuple because of https://github.com/python/mypy/issues/3915
    fields = set(cls._fields) & set(data_dict.keys())  # type: ignore
    return cls(**dict(subdict(data_dict, fields), **kwargs))  # type: ignore


def obj_to_tuples(obj: T, fields: Iterable[str]) -> Sequence[Tuple[str, Any]]:
    """
    Return the given `obj` as a list of tuples `(attribute, value)`.
    """
    return list(zip(fields, (getattr(obj, field) for field in fields)))
