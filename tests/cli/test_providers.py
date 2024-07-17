import os.path

from libterraform import TerraformCommand


class TestTerraformCommandProviders:
    def test_providers(self, cli: TerraformCommand):
        r = cli.providers()
        assert r.retcode == 0, r.error

    def test_providers_lock(self, cli: TerraformCommand):
        cli.apply()
        r = cli.providers_lock(
            fs_mirror=os.path.join(cli.cwd, ".terraform", "providers"),
            enable_plugin_cache=True,
        )
        assert r.retcode == 0, r.error

    def test_providers_schema(self, cli: TerraformCommand):
        r = cli.providers_schema()
        assert r.retcode == 0, r.error
        assert isinstance(r.value, dict)
