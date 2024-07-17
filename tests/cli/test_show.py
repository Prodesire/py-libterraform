from libterraform import TerraformCommand


class TestTerraformCommandShow:
    def test_show(self, cli: TerraformCommand):
        r = cli.show()
        assert r.retcode == 0, r.error
        assert "format_version" in r.value

    def test_plan_and_show(self, cli: TerraformCommand):
        plan_path = "sleep.tfplan"
        cli.plan(out=plan_path)
        r = cli.show(plan_path)
        for key in (
            "format_version",
            "terraform_version",
            "variables",
            "planned_values",
            "resource_changes",
            "configuration",
        ):
            assert key in r.value
