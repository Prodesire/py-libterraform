from libterraform import TerraformCommand


class TestTerraformCommandTaint:
    def test_taint(self, cli: TerraformCommand):
        cli.apply()
        r = cli.taint("time_sleep.wait1")
        assert r.retcode == 0, r.error
        assert "time_sleep.wait1" in r.value

    def test_taint_allow_missing(self, cli: TerraformCommand):
        r = cli.taint("time_sleep.invalid", allow_missing=True)
        assert r.retcode == 0, r.error
        assert "No such resource instance" in r.value
