import inspect

from libterraform import TerraformCommand


class TestTerraformCommandGet:
    def test_get_declares_variable_options(self):
        params = inspect.signature(TerraformCommand.get).parameters

        assert "vars" in params
        assert "var_files" in params

    def test_get_accepts_variable_options(self, monkeypatch):
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
            return 0, "", ""

        monkeypatch.setattr(TerraformCommand, "run", staticmethod(fake_run))

        cli = TerraformCommand("/work")
        r = cli.get(vars={"name": "demo"}, var_files=["get.tfvars"])

        assert r.retcode == 0
        assert call["cmd"] == "get"
        assert call["options"]["var"] == {"name": "demo"}
        assert call["options"]["var_file"] == ["get.tfvars"]
        assert call["chdir"] == "/work"

    def test_get(self, cli: TerraformCommand):
        r = cli.get()
        assert r.retcode == 0, r.error
