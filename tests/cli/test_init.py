from libterraform import TerraformCommand


class TestTerraformCommandInit:
    def test_init(self, cli: TerraformCommand):
        r = cli.init()
        assert r.retcode == 0
