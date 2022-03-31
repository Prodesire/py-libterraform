from libterraform import TerraformCommand


class TestTerraformCommandImport:
    def test_import(self, cli: TerraformCommand):
        cli.destroy()
        try:
            r = cli.import_resource('time_sleep.wait1', '1s,')
            assert r.retcode == 0, r.error
            assert 'Import successful!' in r.value
            assert 'Import does not generate resource configuration' not in r.value
        finally:
            cli.destroy()

    def test_import_missing(self, cli: TerraformCommand):
        cli.destroy()
        try:
            r = cli.import_resource('time_sleep.missing', '1s,')
            assert r.retcode == 1, r.value

            r = cli.import_resource('time_sleep.missing', '1s,', allow_missing_config=True)
            assert r.retcode == 0, r.error
            assert 'Import successful!' in r.value
            assert 'Import does not generate resource configuration' in r.value
        finally:
            cli.destroy()
