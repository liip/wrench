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

import configparser
from typing import Dict


def parse_config(path: str) -> Dict[str, Dict[str, str]]:
    """
    Parse the config file located in `path` and return a dict in the form {'section': {'key1': 'value1'}}.
    """
    config = configparser.ConfigParser()
    with open(path) as f:
        config.read_file(f)

    return {section: dict(values) for section, values in config.items()}


def create_config(path: str, config_dict: Dict[str, Dict[str, str]]) -> None:
    """
    Create a configuration file located in `path` with the values provided in `config_dict`. The created configuration
    file is an ini file, with sections being the keys of the given `config_dict`, and the options and their values
    being the keys and values of the associated dict.
    """
    config = configparser.ConfigParser()
    config.read_dict(config_dict)

    with open(path, 'w') as f:
        config.write(f)
