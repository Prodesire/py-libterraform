import asyncio
import inspect
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from libterraform import AsyncTerraformCommand, TerraformCommand, TerraformPool
import libterraform.async_cli as async_cli_module
import libterraform.cli as terraform_cli
from libterraform.exceptions import TerraformCommandError
from tests.cli.conftest import prepare_sleep_module
from tests.consts import TF_SLEEP_DIR


@pytest.mark.asyncio
async def test_async_run_returns_version():
    retcode, stdout, stderr = await AsyncTerraformCommand.run("version")

    assert retcode == 0
    assert "Terraform" in stdout
    assert stderr == ""


@pytest.mark.asyncio
async def test_async_method_returns_command_result(cli):
    async_cli = AsyncTerraformCommand(cli.cwd)

    result = await async_cli.validate(check=True)

    assert result.retcode == 0
    assert result.value["valid"] is True


@pytest.mark.asyncio
async def test_async_run_propagates_check_errors():
    with pytest.raises(TerraformCommandError):
        await AsyncTerraformCommand.run("invalid", check=True)


@pytest.mark.asyncio
async def test_async_call_does_not_block_event_loop(monkeypatch):
    def slow_version(self, **options):
        time.sleep(0.2)
        return "done"

    monkeypatch.setattr(TerraformCommand, "version", slow_version)
    async_cli = AsyncTerraformCommand()

    task = asyncio.create_task(async_cli.version())
    await asyncio.sleep(0.01)

    assert not task.done()
    assert await task == "done"


@pytest.mark.asyncio
async def test_custom_executor_is_used(monkeypatch):
    thread_names = []

    def fake_version(self, **options):
        thread_names.append(threading.current_thread().name)
        return "ok"

    monkeypatch.setattr(TerraformCommand, "version", fake_version)

    with ThreadPoolExecutor(
        max_workers=1, thread_name_prefix="terraform-async"
    ) as executor:
        async_cli = AsyncTerraformCommand(executor=executor)
        assert await async_cli.version() == "ok"

    assert len(thread_names) == 1
    assert thread_names[0].startswith("terraform-async")


@pytest.mark.asyncio
async def test_cancelling_running_async_method_requests_terraform_cancel(monkeypatch):
    entered = asyncio.Event()
    release = threading.Event()
    run_ids = []

    def fake_cancel(run_id):
        run_ids.append(run_id)
        release.set()
        return 1

    def slow_version(self, **options):
        run_id = terraform_cli._current_run_id.get()
        assert run_id
        loop.call_soon_threadsafe(entered.set)
        release.wait(timeout=2)
        return "late"

    loop = asyncio.get_running_loop()
    monkeypatch.setattr(async_cli_module, "_cancel_cli_run", fake_cancel)
    monkeypatch.setattr(TerraformCommand, "version", slow_version)

    async_cli = AsyncTerraformCommand()
    task = asyncio.create_task(async_cli.version())
    await asyncio.wait_for(entered.wait(), timeout=1)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert len(run_ids) == 1
    assert run_ids[0]


@pytest.mark.asyncio
async def test_cancelling_queued_async_method_requests_cancel_without_starting(
    monkeypatch,
):
    started = []
    cancel_calls = []
    release_worker = threading.Event()

    def fake_cancel(run_id):
        cancel_calls.append(run_id)
        return 0

    def fake_version(self, **options):
        started.append("version")
        return "unexpected"

    monkeypatch.setattr(async_cli_module, "_cancel_cli_run", fake_cancel)
    monkeypatch.setattr(TerraformCommand, "version", fake_version)

    with ThreadPoolExecutor(max_workers=1) as executor:
        blocker = executor.submit(release_worker.wait)
        async_cli = AsyncTerraformCommand(executor=executor)
        task = asyncio.create_task(async_cli.version())
        await asyncio.sleep(0.01)

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        release_worker.set()
        blocker.result(timeout=1)

    assert started == []
    assert len(cancel_calls) == 1
    assert cancel_calls[0]


@pytest.mark.asyncio
async def test_cancelling_running_terraform_call_releases_next_command(tmp_path):
    source_dir = Path(TF_SLEEP_DIR)
    module_dir = tmp_path / "cancel-apply"
    module_dir.mkdir()
    shutil.copyfile(source_dir / "main.tf", module_dir / "main.tf")
    if (source_dir / ".terraform.lock.hcl").exists():
        shutil.copyfile(
            source_dir / ".terraform.lock.hcl",
            module_dir / ".terraform.lock.hcl",
        )
    if (source_dir / ".terraform").exists():
        shutil.copytree(source_dir / ".terraform", module_dir / ".terraform")

    if not (module_dir / ".terraform").exists():
        TerraformCommand(module_dir).init(check=True)
    async_cli = AsyncTerraformCommand(module_dir)
    task = asyncio.create_task(
        async_cli.apply(
            auto_approve=True,
            input=False,
            vars={"time1": "10s", "time2": "10s"},
        )
    )

    await asyncio.sleep(0.5)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    result = await asyncio.wait_for(async_cli.version(json=False), timeout=5)
    assert result.retcode == 0
    assert "Terraform" in result.value


@pytest.mark.asyncio
async def test_async_pool_method_runs_in_process(cli):
    with TerraformPool(max_workers=2) as pool:
        async_cli = AsyncTerraformCommand(cli.cwd, pool=pool)
        result = await async_cli.validate(check=True)

    assert result.retcode == 0
    assert result.value["valid"] is True


@pytest.mark.asyncio
async def test_async_pool_run_classmethod():
    with TerraformPool(max_workers=2) as pool:
        retcode, stdout, stderr = await AsyncTerraformCommand.run("version", pool=pool)

    assert retcode == 0
    assert "Terraform" in stdout


@pytest.mark.asyncio
async def test_async_pool_propagates_check_errors():
    with TerraformPool(max_workers=2) as pool:
        with pytest.raises(TerraformCommandError):
            await AsyncTerraformCommand.run("invalid", check=True, pool=pool)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_async_pool_cancel_releases_worker(tmp_path):
    module_dir = prepare_sleep_module(tmp_path / "async-pool-cancel")

    with TerraformPool(max_workers=1) as pool:
        async_cli = AsyncTerraformCommand(module_dir, pool=pool)
        task = asyncio.create_task(
            async_cli.apply(
                auto_approve=True,
                input=False,
                vars={"time1": "12s", "time2": "12s"},
            )
        )

        await asyncio.sleep(1.5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        # Cancelling interrupts the in-flight apply, so the single worker frees
        # up and the next command returns promptly instead of waiting ~12s.
        result = await asyncio.wait_for(
            AsyncTerraformCommand.run("version", json=False, pool=pool),
            timeout=8,
        )

    assert result[0] == 0
    assert "Terraform" in result[1]


def test_async_command_exposes_public_sync_methods():
    from libterraform.cli import _STREAM_METHODS

    ignored = {"run"} | _STREAM_METHODS

    for name, value in vars(TerraformCommand).items():
        if name.startswith("_") or name in ignored or not callable(value):
            continue

        assert hasattr(AsyncTerraformCommand, name)
        assert inspect.iscoroutinefunction(getattr(AsyncTerraformCommand, name))


def test_async_command_exposes_streaming_methods():
    from libterraform.cli import _STREAM_METHODS

    for name in _STREAM_METHODS:
        method = getattr(AsyncTerraformCommand, name)
        # Streaming methods are async generators (async for ...), not coroutines.
        assert inspect.isasyncgenfunction(method)
        assert not inspect.iscoroutinefunction(method)
