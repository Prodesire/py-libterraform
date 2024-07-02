from libterraform import TerraformCommand


class TestTerraformCommandGet:
    def test_get(self, cli: TerraformCommand):
        r = cli.get()
        assert r.retcode == 0, r.error
