from libterraform import TerraformCommand


class TestTerraformCommandShow:
    def test_show_accepts_variable_options(self, monkeypatch):
        call = {}

        def fake_run(cmd, args=None, options=None, chdir=None, check=False, json=False):
            call.update(
                cmd=cmd,
                args=args,
                options=options,
                chdir=chdir,
                check=check,
                json=json,
            )
            return 0, '{"format_version":"1.0"}', ""

        monkeypatch.setattr(TerraformCommand, "run", staticmethod(fake_run))

        cli = TerraformCommand("/work")
        r = cli.show(vars={"name": "demo"}, var_files=["show.tfvars"])

        assert r.retcode == 0
        assert call["cmd"] == "show"
        assert call["options"]["var"] == {"name": "demo"}
        assert call["options"]["var_file"] == ["show.tfvars"]
        assert call["chdir"] == "/work"

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
