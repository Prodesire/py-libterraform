from libterraform import TerraformCommand
from tests.consts import TF_SLEEP_DIR


class TestTerraformCommandInit:
    def test_init(self):
        r = TerraformCommand(TF_SLEEP_DIR).init()
        assert r.retcode == 0
