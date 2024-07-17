import pytest

from libterraform import TerraformCommand
from libterraform.exceptions import TerraformCommandError


class TestTerraformCommandRun:
    def test_run_version(self):
        retcode, stdout, stderr = TerraformCommand.run("version")
        assert retcode == 0
        assert "Terraform" in stdout

    def test_run_invalid(self):
        retcode, stdout, stderr = TerraformCommand.run("invalid")
        assert retcode == 1
        assert 'Terraform has no command named "invalid"' in stderr

        with pytest.raises(TerraformCommandError):
            TerraformCommand.run("invalid", check=True)
