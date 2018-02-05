#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# wrench -- A Passbolt Client in Python
# Copyright (C) 2018 Didier Raboud <odyx@liip.ch>
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

import argparse
import logging

import requests
from termcolor import colored

from requests_gpgauthlib import GPGAuthSession

parser = argparse.ArgumentParser()
parser.add_argument(
    '-d', '--debug',
    help="Print lots of debugging statements",
    action="store_const", dest="loglevel", const=logging.DEBUG,
    default=logging.WARNING,
)
parser.add_argument(
    '-v', '--verbose',
    help="Be verbose",
    action="store_const", dest="loglevel", const=logging.INFO,
)
parser.add_argument(
    'search', metavar='search term', type=str, nargs='+', help="The search term",
)
args = parser.parse_args()

SERVER_URL = 'https://beta.vault.liip.ch'
SERVER_FINGERPRINT = '60FB552D26EEBBCA9CF4E5D9CEEDBEB87DCDB9A7'
SERVER_AUTH_USERNAME = 'http-auth-user'
SERVER_AUTH_PASSWORD = 'http-auth-pass'

logging.basicConfig(level=args.loglevel)

ga = GPGAuthSession(
  auth_url=SERVER_URL + '/auth/',
  server_fingerprint=SERVER_FINGERPRINT,
)
ga.auth = requests.auth.HTTPBasicAuth(SERVER_AUTH_USERNAME, SERVER_AUTH_PASSWORD)
ga.authenticate()

all_resources = ga.get(SERVER_URL + '/resources.json', params={'contain[secret]': 1}).json()['body']

for resource in all_resources:
    # Concatenate all our text fields
    research_searchtext = (
        ' '.join(
            [
                v.lower() for (k, v) in
                resource['Resource'].items()
                if k in ['name', 'username', 'uri', 'description']
            ]
        )
    )
    output = True
    for word in args.search:
        if word.lower() not in research_searchtext:
            output = False
    if output:
        output_dict = {
            k: v
            for (k, v) in resource['Resource'].items()
            if k in ['id', 'name', 'uri', 'description', 'username']
        }
        output_dict['secret'] = str(ga.gpg.decrypt(resource['Secret'][0]['data'], always_trust=True))

        output = "\n"
        for k in ['id', 'name', 'uri', 'username', 'secret', 'description']:
            v = output_dict[k]
            output += '%s: ' % k.title().ljust(25)
            if k == 'name':
                output += colored(v, 'blue')
            elif k == 'uri':
                output += colored(v, 'white')
            elif k == 'description':
                output += colored(v, 'green')
            elif k == 'username':
                output += colored(v, 'white')
            elif k == 'secret':
                output += colored(v, 'red', 'on_red')
            else:
                output += v
            output += '\n'
        print(output)
