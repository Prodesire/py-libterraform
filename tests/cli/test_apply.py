import os

from libterraform import TerraformCommand


class TestTerraformCommandApply:
    def test_apply(self, cli: TerraformCommand):
        r = cli.apply()
        assert r.retcode == 0, r.error
        assert isinstance(r.value, list)

    def test_plan_and_apply(self, cli: TerraformCommand):
        tfstate_path = "terraform.tfstate"
        if os.path.exists(tfstate_path):
            os.remove(tfstate_path)

        tfplan_path = "sleep.tfplan"
        cli.plan(out=tfplan_path)
        r = cli.apply(tfplan_path)
        assert r.retcode == 0, r.error
        assert isinstance(r.value, list)

    def test_apply_maps_apply_time_variable_options(self, monkeypatch):
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
            return 0, "[]", ""

        monkeypatch.setattr(TerraformCommand, "run", staticmethod(fake_run))

        cli = TerraformCommand("/work")
        r = cli.apply(
            "saved.tfplan",
            vars={"ephemeral_input": "secret"},
            var_files=["ephemeral.tfvars"],
        )

        assert r.retcode == 0
        assert call["cmd"] == "apply"
        assert call["args"] == ["saved.tfplan"]
        assert call["chdir"] == "/work"
        assert call["json"] is True
        assert call["options"]["var"] == {"ephemeral_input": "secret"}
        assert call["options"]["var_file"] == ["ephemeral.tfvars"]
