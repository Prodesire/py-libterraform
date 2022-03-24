import os

import pytest

from libterraform import TerraformCommand
from tests.consts import TF_SLEEP_DIR


@pytest.fixture(scope='package')
def cli():
    cwd = TF_SLEEP_DIR
    tf = os.path.join(cwd, '.terraform')

    cli = TerraformCommand(cwd)
    if not os.path.exists(tf):
        cli.init()
    return cli
