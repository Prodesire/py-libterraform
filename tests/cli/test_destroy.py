from libterraform import TerraformCommand


class TestTerraformCommandApply:
    def test_destroy(self, cli: TerraformCommand):
        cli.apply()
        r = cli.destroy()
        assert r.retcode == 0, r.error
