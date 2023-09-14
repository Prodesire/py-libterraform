import re

from libterraform import TerraformCommand
from tests.consts import TF_SLEEP_DIR, TF_SLEEP2_DIR


class TestTerraformCommandFmt:
    def test_fmt(self, cli: TerraformCommand):
        r = cli.fmt(list=False, write=False, diff=False, recursive=True)
        assert r.retcode == 0, r.error
        assert r.value

    def test_fmt_dir(self):
        cli = TerraformCommand()
        r = cli.fmt(TF_SLEEP_DIR, list=False, write=False, diff=False, recursive=True)
        assert r.retcode == 0, r.error
        assert r.value

    def test_fmt_dirs(self):
        cli = TerraformCommand()
        r = cli.fmt([TF_SLEEP_DIR, TF_SLEEP2_DIR], list=False, write=False, diff=False, recursive=True)
        assert r.retcode == 0, r.error
        assert r.value
