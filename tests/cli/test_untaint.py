from libterraform import TerraformCommand


class TestTerraformCommandUnTaint:
    def test_untaint(self, cli: TerraformCommand):
        cli.apply()
        addr = 'time_sleep.wait1'
        cli.taint(addr)
        r = cli.taint(addr)
        assert r.retcode == 0, r.error
        assert 'time_sleep.wait1' in r.value

    def test_untaint_allow_missing(self, cli: TerraformCommand):
        r = cli.untaint('time_sleep.invalid', allow_missing=True)
        assert r.retcode == 0, r.error
        assert 'No such resource instance' in r.value
