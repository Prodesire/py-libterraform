from libterraform import TerraformCommand


class TestTerraformCommandTest:
    def test_test(self, cli: TerraformCommand):
        r = cli.test()
        assert r.retcode == 0, r.error
        assert 'The "terraform test" command is experimental' in r.value
        assert 'No tests defined' in r.error
