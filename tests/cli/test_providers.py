import os.path
import shutil

from libterraform import TerraformCommand


class TestTerraformCommandProviders:
    def test_providers(self, cli: TerraformCommand):
        r = cli.providers()
        assert r.retcode == 0, r.error

    def test_providers_lock(self, cli: TerraformCommand):
        r = cli.providers_lock()
        assert r.retcode == 0, r.error

    def test_providers_mirror(self, cli: TerraformCommand):
        tmp_path = os.path.join(cli.cwd, 'tmp')
        r = cli.providers_mirror(tmp_path)
        assert r.retcode == 0, r.error
        assert os.path.exists(tmp_path)
        shutil.rmtree(tmp_path)

    def test_providers_schema(self, cli: TerraformCommand):
        r = cli.providers_schema()
        assert r.retcode == 0, r.error
        assert isinstance(r.value, dict)
