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

import logging
from typing import Any, Dict, Iterable, Mapping

from requests_gpgauthlib import GPGAuthSession

from .exceptions import HttpRequestError

base_params = {'api-version': 'v2'}
logger = logging.getLogger(__name__)


def get_cookie_by_name(session: GPGAuthSession, cookie_name: str):
    """
    Return the the cookie named `cookie_name`. If `cookie_name` is not found in `session`, raise `KeyError`.
    """
    try:
        cookie = [cookie for cookie in session.cookies if cookie.name == cookie_name][0]
    except IndexError:
        raise KeyError("Cookie %s doesn't exist in given session" % cookie_name)
    else:
        return cookie


def get_passbolt_response(session: GPGAuthSession, path: str, params: Mapping[str, Any] = None,
                          method: str = 'get', **kwargs) -> Any:
    """
    Execute a request on the given `path` on the passbolt server and returns the response body.
    """
    if not params:
        params = {}

    params = dict(base_params, **params)
    full_path = session.build_absolute_uri(path)
    logger.info("Sending Passbolt request to %s with params %s, kwargs %s", full_path, params, kwargs)
    # Passbolt 2.2 added CSRF protection. The CSRF token cookie should be set in the x-csrf-token header. If the cookie
    # doesn't exit, do not fail for Passbolt < 2.2 compatibility
    try:
        csrf_token = get_cookie_by_name(session, 'csrfToken').value
    except KeyError:
        headers = {}  # type: Dict[str, str]
    else:
        headers = {'x-csrf-token': csrf_token}

    response = getattr(session, method)(full_path, params=params, headers=headers, **kwargs)

    if not response.ok:
        logger.error("Got non-ok response from server (status code %s). Contents: %s. Sent data: %s",
                     response.status_code, response.text, params)
        raise HttpRequestError(response)

    return response.json()['body']


def get_resources(session: GPGAuthSession, favourite_only: bool) -> Iterable[Dict[str, Any]]:
    """
    Return a list of resource dicts from Passbolt.
    """
    params = {'contain[tag]': 1}
    if favourite_only:
        params['filter[is-favorite]'] = 1

    return get_passbolt_response(session, '/resources.json', params)


def get_resource_secret(session: GPGAuthSession, resource_id: str) -> Dict[str, Any]:
    """
    Return a resource secret dict from Passbolt.
    """
    return get_passbolt_response(session, '/secrets/resource/{}.json'.format(resource_id))


def share_resource(session: GPGAuthSession, resource_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Share the resource identified by `resource_id` and with the given data. Check
    `translators.foreign.to_foreign_secret` and `translators.foreign.to_shared_permission` for the expected data
    structure.
    """
    return get_passbolt_response(session, '/share/resource/{}.json'.format(resource_id), method='put', json=data)


def get_users(session: GPGAuthSession, terms: str = None) -> Iterable[Dict[str, Any]]:
    """
    Return a list of user dicts from Passbolt, optionally filtered with the given `terms`.
    """
    params = {'keywords': terms} if terms else {}

    return get_passbolt_response(session, '/users.json', params)


def get_user(session: GPGAuthSession, id: str) -> Dict[str, Any]:
    """
    Return the given user from Passbolt. According to the Passbolt code, `id` can be 'me', in which case the current
    logged in user info is returned.
    """
    return get_passbolt_response(session, '/users/{}.json'.format(id))


def get_groups(session: GPGAuthSession, include_users: bool = True) -> Iterable[Dict[str, Any]]:
    """
    Return a list of group dicts from Passbolt. If `include_users` is `True`, user information is returned along with
    the groups.
    """
    endpoint = '/groups.json'

    if include_users:
        endpoint += '?contain[user]=1'

    return get_passbolt_response(session, endpoint)


def get_group(session: GPGAuthSession, id: str) -> Dict[str, Any]:
    """
    Return a group dict from Passbolt.
    """
    return get_passbolt_response(session, '/groups/{}.json'.format(id))


def add_resource(session: GPGAuthSession, resource_data: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Add the given resource to Passbolt. See `translators.foreign.to_foreign_resource` for the expected data structure.
    """
    return get_passbolt_response(session, '/resources.json', method='post', json=resource_data)


def get_resource_permissions(session: GPGAuthSession, resource_id: str) -> Iterable[Mapping[str, Any]]:
    """
    Return the existing permissions of the given resource id.
    """
    return get_passbolt_response(session, '/permissions/resource/{}.json'.format(resource_id))


def add_tags(session: GPGAuthSession, resource_id: str, tag_data: Dict[str, Any]) -> None:
    """
    Add the given `tag_data` to the resource identified by `resource_id`. `tag_data` should be a dict in the form
    `{'Tags': ['tag1', 'tag2', '#public_tag_1']}`.
    """
    return get_passbolt_response(session, '/tags/{}.json'.format(resource_id), json=tag_data, method='post')
