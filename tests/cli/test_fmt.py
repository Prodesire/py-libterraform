import re

from libterraform import TerraformCommand
from tests.consts import TF_SLEEP_DIR


class TestTerraformCommandFmt:
    def test_fmt(self, cli: TerraformCommand):
        r = cli.fmt(list=False, write=False, diff=True, recursive=True)
        assert r.retcode == 0, r.error
        assert 'old/main.tf' in r.value
        assert 'new/main.tf' in r.value

    def test_fmt_dir(self):
        old_pattern = re.compile(r'old\S+main.tf')
        new_pattern = re.compile(r'new\S+main.tf')
        cli = TerraformCommand()
        r = cli.fmt(TF_SLEEP_DIR, list=False, write=False, diff=True, recursive=True)
        assert r.retcode == 0, r.error
        assert old_pattern.search(r.value)
        assert new_pattern.search(r.value)
