from libterraform import TerraformCommand


class TestTerraformCommandPlan:
    def test_plan(self, cli: TerraformCommand):
        r = cli.plan()
        assert r.retcode == 0
        assert isinstance(r.value, list)

    def test_plan_with_vars(self, cli: TerraformCommand):
        r = cli.plan(vars={'time1': '1s', 'time2': '2s'})
        assert r.retcode == 0
        assert isinstance(r.value, list)
