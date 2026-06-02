from libterraform import TerraformCommand
from tests.consts import EXPECTED_TERRAFORM_VERSION


class TestTerraformCommandVersion:
    def test_version(self, cli: TerraformCommand):
        r = cli.version()
        assert r.json is True
        for key in (
            "terraform_version",
            "platform",
            "provider_selections",
            "terraform_outdated",
        ):
            assert key in r.value
        assert r.value["terraform_version"] == EXPECTED_TERRAFORM_VERSION

    def test_version_raw(self, cli: TerraformCommand):
        r = cli.version(json=False)
        assert r.json is False
        assert f"Terraform v{EXPECTED_TERRAFORM_VERSION}" in r.value
