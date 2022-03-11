import os.path

import pytest

from libterraform import TerraformConfig
from libterraform.exceptions import LibTerraformError

cur_dirname = os.path.dirname(os.path.abspath(__file__))
sleep_dirname = os.path.join(cur_dirname, 'sleep')


class TestTerraformConfig:
    def test_load_config_dir(self):
        mod, diags = TerraformConfig.load_config_dir(sleep_dirname)
        assert 'time_sleep.wait' in mod['ManagedResources']

    def test_load_config_dir_no_exits(self):
        with pytest.raises(LibTerraformError):
            TerraformConfig.load_config_dir('not-exits')
