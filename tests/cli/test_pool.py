import inspect
import shutil
import time
from concurrent.futures import Future
from pathlib import Path

import pytest

from libterraform import TerraformCommand, TerraformPool
from libterraform.cli import CommandResult
from libterraform.exceptions import TerraformCommandError
from libterraform.pool import PoolCommand
from tests.consts import TF_SLEEP_DIR


def _prepare_module(source_dir: Path, module_dir: Path) -> Path:
    module_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_dir / "main.tf", module_dir / "main.tf")
    if (source_dir / ".terraform.lock.hcl").exists():
        shutil.copyfile(
            source_dir / ".terraform.lock.hcl",
            module_dir / ".terraform.lock.hcl",
        )
    if (source_dir / ".terraform").exists():
        shutil.copytree(
            source_dir / ".terraform",
            module_dir / ".terraform",
            dirs_exist_ok=True,
        )
    if not (module_dir / ".terraform").exists():
        TerraformCommand(module_dir).init(check=True)
    return module_dir


def test_pool_run_returns_version():
    with TerraformPool(max_workers=2) as pool:
        future = pool.run("version", json=False)

        assert isinstance(future, Future)
        retcode, stdout, stderr = future.result()

    assert retcode == 0
    assert "Terraform" in stdout
    assert stderr == ""


def test_pool_command_proxy_returns_command_result(cli):
    with TerraformPool(max_workers=2) as pool:
        future = pool.command(cli.cwd).validate(check=True)

        assert isinstance(future, Future)
        result = future.result()

    assert isinstance(result, CommandResult)
    assert result.retcode == 0
    assert result.value["valid"] is True


def test_pool_map_fans_out_in_order(cli):
    with TerraformPool(max_workers=2) as pool:
        results = list(pool.map("validate", [cli.cwd, cli.cwd], check=True))

    assert len(results) == 2
    assert all(result.value["valid"] is True for result in results)


def test_pool_submit_low_level_api(cli):
    with TerraformPool(max_workers=2) as pool:
        future = pool.submit(cli.cwd, "validate", check=True)
        result = future.result()

    assert result.retcode == 0


def test_pool_propagates_check_errors():
    with TerraformPool(max_workers=2) as pool:
        future = pool.run("invalid", check=True)

        with pytest.raises(TerraformCommandError) as excinfo:
            future.result()

    assert excinfo.value.retcode != 0


def test_pool_shutdown_rejects_new_work():
    pool = TerraformPool(max_workers=1)
    pool.shutdown()

    with pytest.raises(RuntimeError):
        pool.run("version")


def test_pool_command_proxy_exposes_public_sync_methods():
    ignored = {"run"}

    for name, value in vars(TerraformCommand).items():
        if name.startswith("_") or name in ignored or not callable(value):
            continue

        assert hasattr(PoolCommand, name)


@pytest.mark.slow
def test_pool_runs_terraform_in_parallel(tmp_path):
    source_dir = Path(TF_SLEEP_DIR)
    module_a = _prepare_module(source_dir, tmp_path / "parallel-a")
    module_b = _prepare_module(source_dir, tmp_path / "parallel-b")

    apply_options = dict(
        auto_approve=True, input=False, vars={"time1": "3s", "time2": "3s"}
    )

    start = time.monotonic()
    with TerraformPool(max_workers=2) as pool:
        future_a = pool.command(module_a).apply(**apply_options)
        future_b = pool.command(module_b).apply(**apply_options)
        result_a = future_a.result()
        result_b = future_b.result()
    elapsed = time.monotonic() - start

    assert result_a.retcode == 0
    assert result_b.retcode == 0
    # Two ~3s applies would take ~6s sequentially; running them in separate
    # processes should finish well under that.
    assert elapsed < 5.5


def test_pool_proxy_methods_are_not_coroutines():
    # The proxy returns futures synchronously; methods must not be coroutines.
    for name, value in vars(TerraformCommand).items():
        if name.startswith("_") or name == "run" or not callable(value):
            continue

        assert not inspect.iscoroutinefunction(getattr(PoolCommand, name))
