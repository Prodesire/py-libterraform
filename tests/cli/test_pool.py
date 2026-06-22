import inspect
import time
from concurrent.futures import Future

import pytest

from libterraform import TerraformCommand, TerraformPool
from libterraform.cli import CommandResult
from libterraform.exceptions import TerraformCommandError
from libterraform.pool import PoolCommand
from tests.cli.conftest import prepare_sleep_module


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
    from libterraform.cli import _STREAM_METHODS

    # Streaming methods cannot cross a process boundary, so the pool omits them.
    ignored = {"run"} | _STREAM_METHODS

    for name, value in vars(TerraformCommand).items():
        if name.startswith("_") or name in ignored or not callable(value):
            continue

        assert hasattr(PoolCommand, name)


def test_pool_command_proxy_omits_streaming_methods():
    from libterraform.cli import _STREAM_METHODS

    for name in _STREAM_METHODS:
        assert not hasattr(PoolCommand, name)


@pytest.mark.slow
def test_pool_runs_terraform_in_parallel(tmp_path):
    module_a = prepare_sleep_module(tmp_path / "parallel-a")
    module_b = prepare_sleep_module(tmp_path / "parallel-b")

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


@pytest.mark.slow
def test_pool_cancel_running_command_interrupts_terraform(tmp_path):
    module = prepare_sleep_module(tmp_path / "cancel-sync")

    with TerraformPool(max_workers=1) as pool:
        future = pool.command(module).apply(
            auto_approve=True, input=False, vars={"time1": "12s", "time2": "12s"}
        )
        # Let the apply reach the in-progress time_sleep resources.
        time.sleep(1.5)

        future.cancel()
        start = time.monotonic()
        result = future.result(timeout=8)
        elapsed = time.monotonic() - start

    # If cancellation did not interrupt Terraform, the ~12s apply would still be
    # running and result(timeout=8) would raise instead of returning here.
    assert isinstance(result, CommandResult)
    assert elapsed < 6


def test_pool_proxy_methods_are_not_coroutines():
    from libterraform.cli import _STREAM_METHODS

    # The proxy returns futures synchronously; methods must not be coroutines.
    for name, value in vars(TerraformCommand).items():
        if name.startswith("_") or name == "run" or name in _STREAM_METHODS:
            continue
        if not callable(value):
            continue

        assert not inspect.iscoroutinefunction(getattr(PoolCommand, name))
