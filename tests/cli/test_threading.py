import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from libterraform import TerraformCommand, TerraformConfig
from libterraform.exceptions import TerraformCommandError


def write_builtin_module(path: Path, name: str) -> None:
    path.mkdir()
    path.joinpath("main.tf").write_text(
        f'resource "terraform_data" "{name}" {{\n  input = "{name}"\n}}\n',
        encoding="utf-8",
    )


class TestThreading:
    def test_run_cli_keeps_chdir_and_stdout_isolated(self, tmp_path):
        module_names = [f"case_{index:02d}" for index in range(12)]
        module_dirs = []
        for name in module_names:
            module_dir = tmp_path / name
            write_builtin_module(module_dir, name)
            module_dirs.append(module_dir)

        original_cwd = os.getcwd()

        def graph_module(item):
            module_dir, name = item
            result = TerraformCommand(module_dir).graph()
            return name, result

        try:
            with ThreadPoolExecutor(max_workers=6) as executor:
                results = list(
                    executor.map(graph_module, zip(module_dirs, module_names))
                )
            observed_cwd = os.getcwd()
        finally:
            os.chdir(original_cwd)

        assert observed_cwd == original_cwd
        for name, result in results:
            assert result.retcode == 0, result.error
            assert f"terraform_data.{name}" in result.value
            other_names = set(module_names) - {name}
            assert not any(
                f"terraform_data.{other}" in result.value for other in other_names
            )

    def test_run_cli_keeps_mixed_stdout_and_stderr_isolated(self):
        def run_command(index):
            if index % 2 == 0:
                retcode, stdout, stderr = TerraformCommand.run("version")
                return "version", index, retcode, stdout, stderr

            command = f"missing-command-{index}"
            retcode, stdout, stderr = TerraformCommand.run(command)
            return "missing", index, retcode, stdout, stderr

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(run_command, range(24)))

        for kind, index, retcode, stdout, stderr in results:
            if kind == "version":
                assert retcode == 0
                assert "Terraform" in stdout
                assert stderr == ""
            else:
                assert retcode == 1
                assert stdout == ""
                assert (
                    f'Terraform has no command named "missing-command-{index}"'
                    in stderr
                )

    def test_run_cli_restores_cwd_after_threaded_check_errors(self, tmp_path):
        workdirs = [tmp_path / f"work-{index}" for index in range(12)]
        for workdir in workdirs:
            workdir.mkdir()

        original_cwd = os.getcwd()

        def run_invalid(item):
            index, workdir = item
            command = f"missing-command-{index}"
            try:
                TerraformCommand.run(command, chdir=str(workdir), check=True)
            except TerraformCommandError as exc:
                return command, exc
            raise AssertionError(f"{command} unexpectedly succeeded")

        try:
            with ThreadPoolExecutor(max_workers=6) as executor:
                results = list(executor.map(run_invalid, enumerate(workdirs)))
            observed_cwd = os.getcwd()
        finally:
            os.chdir(original_cwd)

        assert observed_cwd == original_cwd
        for command, exc in results:
            assert exc.retcode == 1
            assert exc.stdout == ""
            assert f'Terraform has no command named "{command}"' in exc.stderr

    def test_shared_terraform_command_instance_is_thread_safe(self, tmp_path):
        module_dir = tmp_path / "module"
        write_builtin_module(module_dir, "shared")
        cli = TerraformCommand(module_dir)

        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(lambda _: cli.validate(check=True), range(18)))

        assert all(result.retcode == 0 for result in results)
        assert all(result.value["valid"] is True for result in results)
        assert all(result.error == "" for result in results)

    def test_load_config_dir_is_thread_safe(self, tmp_path):
        module_names = [f"config_{index:02d}" for index in range(12)]
        module_dirs = []
        for name in module_names:
            module_dir = tmp_path / name
            write_builtin_module(module_dir, name)
            module_dirs.append(module_dir)

        def load_module(item):
            module_dir, name = item
            module, diagnostics = TerraformConfig.load_config_dir(str(module_dir))
            return name, module, diagnostics

        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(load_module, zip(module_dirs, module_names)))

        for name, module, diagnostics in results:
            assert not diagnostics
            assert f"terraform_data.{name}" in module["ManagedResources"]
