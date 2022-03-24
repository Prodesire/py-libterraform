import pytest

from libterraform import TerraformCommand
from tests.consts import TF_SLEEP_DIR


@pytest.fixture(scope='package')
def cli():
    return TerraformCommand(TF_SLEEP_DIR)
