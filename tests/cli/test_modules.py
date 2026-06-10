from libterraform import TerraformCommand


class TestTerraformCommandModules:
    def test_modules_defaults_to_json(self, monkeypatch):
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
            return 0, '{"format_version":"1.0","modules":[]}', ""

        monkeypatch.setattr(TerraformCommand, "run", staticmethod(fake_run))

        cli = TerraformCommand("/work")
        r = cli.modules()

        assert r.retcode == 0
        assert r.json is True
        assert r.value == {"format_version": "1.0", "modules": []}
        assert call == {
            "cmd": "modules",
            "args": None,
            "options": {"var": None, "var_file": None},
            "chdir": "/work",
            "check": False,
            "json": True,
        }

    def test_modules_accepts_variable_options(self, monkeypatch):
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
            return 0, '{"format_version":"1.0","modules":[]}', ""

        monkeypatch.setattr(TerraformCommand, "run", staticmethod(fake_run))

        cli = TerraformCommand("/work")
        r = cli.modules(vars={"name": "demo"}, var_files=["modules.tfvars"])

        assert r.retcode == 0
        assert call["cmd"] == "modules"
        assert call["options"]["var"] == {"name": "demo"}
        assert call["options"]["var_file"] == ["modules.tfvars"]
        assert call["chdir"] == "/work"

    def test_modules(self, cli: TerraformCommand):
        r = cli.modules()

        assert r.retcode == 0, r.error
        assert r.json is True
        assert r.value["format_version"] == "1.0"
        assert "modules" in r.value
        assert r.value["modules"] is None or isinstance(r.value["modules"], list)
