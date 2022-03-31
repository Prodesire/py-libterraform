import os

from libterraform import TerraformCommand


class TestTerraformCommandApply:
    def test_apply(self, cli: TerraformCommand):
        r = cli.apply()
        assert r.retcode == 0, r.error
        assert isinstance(r.value, list)

    def test_plan_and_apply(self, cli: TerraformCommand):
        tfstate_path = 'terraform.tfstate'
        if os.path.exists(tfstate_path):
            os.remove(tfstate_path)

        tfplan_path = 'sleep.tfplan'
        cli.plan(out=tfplan_path)
        r = cli.apply(tfplan_path)
        assert r.retcode == 0, r.error
        assert isinstance(r.value, list)
