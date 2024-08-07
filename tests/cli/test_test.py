import os.path

from libterraform import TerraformCommand
from tests.consts import TF_SLEEP2_DIR


class TestTerraformCommandTest:
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

    def test_test_assertion_error(self):
        cwd = TF_SLEEP2_DIR
        tf = os.path.join(cwd, ".terraform")

        cli = TerraformCommand(cwd)
        if not os.path.exists(tf):
            cli.init()
        r = cli.test(vars={"sleep2_time1": "2s"})
        assert r.retcode == 1
        assert r.value[-1]["test_summary"]["status"] == "fail"
