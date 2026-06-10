import inspect

from libterraform import TerraformCommand


class TestTerraformCommandValidate:
    def test_validate_declares_query_option(self):
        params = inspect.signature(TerraformCommand.validate).parameters

        assert "query" in params

    def test_validate_declares_variable_options(self):
        params = inspect.signature(TerraformCommand.validate).parameters

        assert "vars" in params
        assert "var_files" in params

    def test_validate_accepts_query_option(self, monkeypatch):
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
            return 0, '{"valid":true}', ""

        monkeypatch.setattr(TerraformCommand, "run", staticmethod(fake_run))

        cli = TerraformCommand("/work")
        r = cli.validate(query=True)

        assert r.retcode == 0
        assert r.value == {"valid": True}
        assert call["cmd"] == "validate"
        assert call["options"]["query"] is ...
        assert call["chdir"] == "/work"

    def test_validate_accepts_variable_options(self, monkeypatch):
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
            return 0, '{"valid":true}', ""

        monkeypatch.setattr(TerraformCommand, "run", staticmethod(fake_run))

        cli = TerraformCommand("/work")
        r = cli.validate(vars={"name": "demo"}, var_files=["validate.tfvars"])

        assert r.retcode == 0
        assert r.value == {"valid": True}
        assert call["cmd"] == "validate"
        assert call["options"]["var"] == {"name": "demo"}
        assert call["options"]["var_file"] == ["validate.tfvars"]
        assert call["chdir"] == "/work"

    def test_validate(self, cli: TerraformCommand):
        r = cli.validate()
        assert r.retcode == 0, r.error
        assert r.value == {
            "format_version": "1.0",
            "valid": True,
            "error_count": 0,
            "warning_count": 0,
            "diagnostics": [],
        }
