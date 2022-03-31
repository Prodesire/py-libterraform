from libterraform import TerraformCommand


class TestTerraformCommandOutput:
    def test_output(self, cli: TerraformCommand):
        cli.apply()
        r = cli.output()
        assert r.retcode == 0, r.error
        assert 'wait1_id' in r.value
        assert 'wait2_id' in r.value

    def test_output_with_name(self, cli: TerraformCommand):
        cli.apply()
        r = cli.output('wait1_id')
        assert r.retcode == 0, r.error
        assert isinstance(r.value, str)
