import os.path
import shutil

from libterraform import TerraformCommand


class TestTerraformCommandRefresh:
    def test_refresh(self, cli: TerraformCommand):
        r = cli.refresh()
        assert r.retcode == 0, r.error
        assert r.value

    def test_refresh_with_target(self, cli: TerraformCommand):
        r = cli.refresh(target='time_sleep.wait1')
        assert r.retcode == 0, r.error
        assert r.value
