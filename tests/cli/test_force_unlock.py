from libterraform import TerraformCommand


class TestTerraformCommandForceUnlock:
    def test_force_unlock_invalid(self, cli: TerraformCommand):
        r = cli.force_unlock("invalid")
        assert r.retcode == 1
        assert r.error is not None
        assert "Failed to unlock state" in r.error
