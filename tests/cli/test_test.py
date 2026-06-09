import inspect
import os.path

from libterraform import TerraformCommand
from tests.consts import TF_SLEEP2_DIR


class TestTerraformCommandTest:
    def test_test_declares_junit_xml_option(self):
        params = inspect.signature(TerraformCommand.test).parameters

        assert "junit_xml" in params

    def test_test_declares_run_parallelism_option(self):
        params = inspect.signature(TerraformCommand.test).parameters

        assert "run_parallelism" in params

    def test_test_declares_allow_deferral_option(self):
        params = inspect.signature(TerraformCommand.test).parameters

        assert "allow_deferral" in params

    def test_test_cleanup_is_not_exposed_for_final_terraform_releases(self):
        assert not hasattr(TerraformCommand, "test_cleanup")

    def test_test_accepts_junit_xml_option(self, monkeypatch):
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
            return 0, '{"type":"test_summary","test_summary":{"status":"pass"}}', ""

        monkeypatch.setattr(TerraformCommand, "run", staticmethod(fake_run))

        cli = TerraformCommand("/work")
        r = cli.test(junit_xml="report.xml", json=True)

        assert r.retcode == 0
        assert r.json is True
        assert call["cmd"] == "test"
        assert call["options"]["junit_xml"] == "report.xml"
        assert call["chdir"] == "/work"

    def test_test_accepts_run_parallelism_option(self, monkeypatch):
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
            return 0, '{"type":"test_summary","test_summary":{"status":"pass"}}', ""

        monkeypatch.setattr(TerraformCommand, "run", staticmethod(fake_run))

        cli = TerraformCommand("/work")
        r = cli.test(run_parallelism=4, json=True)

        assert r.retcode == 0
        assert r.json is True
        assert call["cmd"] == "test"
        assert call["options"]["run_parallelism"] == 4
        assert call["chdir"] == "/work"

    def test_test_accepts_allow_deferral_option(self, monkeypatch):
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
            return 0, '{"type":"test_summary","test_summary":{"status":"pass"}}', ""

        monkeypatch.setattr(TerraformCommand, "run", staticmethod(fake_run))

        cli = TerraformCommand("/work")
        r = cli.test(allow_deferral=True, json=True)

        assert r.retcode == 0
        assert r.json is True
        assert call["cmd"] == "test"
        assert call["options"]["allow_deferral"] is ...
        assert call["chdir"] == "/work"

    def test_test(self, cli: TerraformCommand):
        r = cli.test(json=False)
        assert r.retcode == 0, r.error
        assert "Success! 0 passed, 0 failed." in r.value
        assert not r.error

    def test_test_run(self):
        cwd = TF_SLEEP2_DIR
        tf = os.path.join(cwd, ".terraform")

        cli = TerraformCommand(cwd)
        if not os.path.exists(tf):
            cli.init()
        r = cli.test()
        assert r.retcode == 0, r.error
        assert r.value[-1]["test_summary"]["status"] == "pass"

    def test_test_writes_junit_xml_report(self, tmp_path):
        cwd = TF_SLEEP2_DIR
        tf = os.path.join(cwd, ".terraform")
        report = tmp_path / "report.xml"

        cli = TerraformCommand(cwd)
        if not os.path.exists(tf):
            cli.init()
        r = cli.test(junit_xml=str(report), json=False)

        assert r.retcode == 0, r.error
        assert report.exists()
        assert report.read_text(encoding="utf-8").startswith(
            '<?xml version="1.0" encoding="UTF-8"?><testsuites>'
        )

    def test_test_assertion_error(self):
        cwd = TF_SLEEP2_DIR
        tf = os.path.join(cwd, ".terraform")

        cli = TerraformCommand(cwd)
        if not os.path.exists(tf):
            cli.init()
        r = cli.test(vars={"sleep2_time1": "2s"})
        assert r.retcode == 1
        assert r.value[-1]["test_summary"]["status"] == "fail"
