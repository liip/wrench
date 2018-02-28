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

from typing import Any, Dict, Iterable, Mapping

from requests_gpgauthlib import GPGAuthSession

base_params = {'api-version': 'v2'}


def get_passbolt_response(session: GPGAuthSession, path: str, params: Mapping[str, Any]) -> Iterable[Dict[str, Any]]:
    """
    Executes a request on the given `path` on the passbolt server and returns the response as a list of dicts.
    """
    params = dict(base_params, **params)

    return session.get(session.build_absolute_uri(path), params=params).json()['body']


def get_resources(session: GPGAuthSession, favourite_only: bool = False) -> Iterable[Dict[str, Any]]:
    """
    Return a list of resource dicts from Passbolt.
    """
    params = {'contain[secret]': 1}
    if favourite_only:
        params['filter[is-favorite]'] = 1

    return get_passbolt_response(session, '/resources.json', params)


def get_users(session: GPGAuthSession, terms: str) -> Iterable[Dict[str, Any]]:
    """
    Return a list of user dicts from Passbolt.
    """
    params = {'keywords': terms} if terms else {}

    return get_passbolt_response(session, '/users.json', params)
