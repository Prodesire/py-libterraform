import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from libterraform import TerraformCommand
from libterraform.exceptions import TerraformCommandError


class TestTerraformCommandRun:
    def test_run_version(self):
        retcode, stdout, stderr = TerraformCommand.run("version")
        assert retcode == 0
        assert "Terraform" in stdout

    def test_run_version_is_thread_safe(self, tmp_path):
        workdirs = [tmp_path / f"work-{index}" for index in range(12)]
        for workdir in workdirs:
            workdir.mkdir()

        original_cwd = os.getcwd()

        def run_version(workdir):
            return TerraformCommand.run("version", chdir=str(workdir))

        try:
            with ThreadPoolExecutor(max_workers=6) as executor:
                results = list(executor.map(run_version, workdirs))
            observed_cwd = os.getcwd()
        finally:
            os.chdir(original_cwd)

        assert observed_cwd == original_cwd
        assert all(retcode == 0 for retcode, _, _ in results)
        assert all("Terraform" in stdout for _, stdout, _ in results)
        assert all(stderr == "" for _, _, stderr in results)

    def test_run_invalid(self):
        retcode, stdout, stderr = TerraformCommand.run("invalid")
        assert retcode == 1
        assert 'Terraform has no command named "invalid"' in stderr

        with pytest.raises(TerraformCommandError):
            TerraformCommand.run("invalid", check=True)
