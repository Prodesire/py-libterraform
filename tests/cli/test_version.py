from libterraform import TerraformCommand


class TestTerraformCommandVersion:
    def test_version(self, cli: TerraformCommand):
        r = cli.version()
        assert r.json is True
        for key in ('terraform_version', 'platform', 'provider_selections', 'terraform_outdated'):
            assert key in r.value

    def test_version_raw(self, cli: TerraformCommand):
        r = cli.version(json=False)
        assert r.json is False
        assert 'Terraform' in r.value
