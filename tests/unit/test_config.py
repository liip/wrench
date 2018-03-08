import os
import tempfile

from wrench.commands import create_config_file


def test_create_config_creates_directory():
    with tempfile.TemporaryDirectory() as directory:
        config_path = os.path.join(directory, 'subdir', 'config.ini')
        create_config_file(config_path, {'foo': 'bar'})

        assert os.path.exists(config_path)


def test_create_config_creates_file_if_directory_exists():
    with tempfile.TemporaryDirectory() as directory:
        config_path = os.path.join(directory, 'config.ini')
        create_config_file(config_path, {'foo': 'bar'})

        assert os.path.exists(config_path)
