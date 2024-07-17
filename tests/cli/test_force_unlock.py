from libterraform import TerraformCommand


class TestTerraformCommandForceUnlock:
    def test_force_unlock_invalid(self, cli: TerraformCommand):
        r = cli.force_unlock("invalid")
        assert r.retcode == 1
        assert "Failed to unlock state" in r.error
