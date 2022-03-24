import pytest

from libterraform import TerraformConfig
from libterraform.exceptions import LibTerraformError
from tests.consts import TF_SLEEP_DIR


class TestTerraformConfig:
    def test_load_config_dir(self):
        mod, diags = TerraformConfig.load_config_dir(TF_SLEEP_DIR)
        assert 'time_sleep.wait' in mod['ManagedResources']

    def test_load_config_dir_no_exits(self):
        with pytest.raises(LibTerraformError):
            TerraformConfig.load_config_dir('not-exits')
