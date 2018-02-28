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

import cmd
import pprint

from . import passbolt_api


class PassboltShell(cmd.Cmd):
    intro = "Welcome to Passbolt shell. Type help or ? to list commands.\n"
    prompt = "(passbolt) "
    file = None

    def __init__(self, session):
        super().__init__()

        self.session = session

    def default(self, line):
        if line == 'EOF':
            return True
        else:
            return super().default(line)

    def do_get(self, path):
        response = passbolt_api.get_passbolt_response(self.session, path, {})
        pprint.pprint(response)
