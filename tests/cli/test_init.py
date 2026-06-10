import inspect

from libterraform import TerraformCommand
from tests.consts import TF_SLEEP_DIR


class TestTerraformCommandInit:
    def test_init_declares_pluggable_state_storage_experiment_option(self):
        params = inspect.signature(TerraformCommand.init).parameters

        assert "enable_pluggable_state_storage_experiment" in params

    def test_init_declares_create_default_workspace_option(self):
        params = inspect.signature(TerraformCommand.init).parameters

        assert "create_default_workspace" in params

    def test_init_accepts_pluggable_state_storage_experiment_option(self, monkeypatch):
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
        r = cli.init(enable_pluggable_state_storage_experiment=True)

        assert r.retcode == 0
        assert call["cmd"] == "init"
        assert call["options"]["enable_pluggable_state_storage_experiment"] is ...
        assert call["chdir"] == "/work"

    def test_init_accepts_create_default_workspace_option(self, monkeypatch):
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
        r = cli.init(create_default_workspace=False)

        assert r.retcode == 0
        assert call["cmd"] == "init"
        assert call["options"]["create_default_workspace"] is False
        assert call["chdir"] == "/work"

    def test_init(self):
        r = TerraformCommand(TF_SLEEP_DIR).init()
        assert r.retcode == 0, r.error
