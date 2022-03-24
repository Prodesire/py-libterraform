import os

from libterraform import TerraformCommand


class TestTerraformCommandValidate:
    def test_validate(self, cli: TerraformCommand):
        r = cli.validate()
        assert r.retcode == 0
        assert r.value == {
            'format_version': '1.0',
            'valid': True,
            'error_count': 0,
            'warning_count': 0,
            'diagnostics': []
        }
