import os
import tempfile

from wrench.commands import create_config_file


def test_create_config_creates_directory():
    def get_response(question: str) -> str:
        return 'hello'

    with tempfile.TemporaryDirectory() as directory:
        config_path = os.path.join(directory, 'subdir', 'config.ini')
        create_config_file(config_path, get_response)

        assert os.path.exists(config_path)
