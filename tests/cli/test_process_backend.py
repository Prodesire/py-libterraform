import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from libterraform import (
    AsyncTerraformCommand,
    ProcessTerraformCommand,
    TerraformCommand,
    ThreadTerraformCommand,
)
from tests.cli.conftest import prepare_sleep_module


def _changed_cwd_samples(original_cwd, future):
    changed = []
    while not future.done():
        current = os.getcwd()
        if current != original_cwd:
            changed.append(current)
        time.sleep(0.05)
    return changed


def test_terraform_command_defaults_to_process_backend_for_cwd_isolation(tmp_path):
    module = prepare_sleep_module(tmp_path / "sync-process-default")
    original_cwd = os.getcwd()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            lambda: TerraformCommand(module).apply(
                check=True,
                json=False,
                vars={"time1": "2s", "time2": "2s"},
            )
        )
        changed = _changed_cwd_samples(original_cwd, future)
        result = future.result(timeout=10)

    assert result.retcode == 0
    assert os.getcwd() == original_cwd
    assert changed == []


def test_explicit_command_classes_select_their_backend():
    assert ProcessTerraformCommand().backend == "process"
    assert ThreadTerraformCommand().backend == "thread"


def test_terraform_command_thread_backend_remains_available(tmp_path):
    module = prepare_sleep_module(tmp_path / "sync-thread-backend")
    original_cwd = os.getcwd()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            lambda: TerraformCommand(module, backend="thread").apply(
                check=True,
                json=False,
                vars={"time1": "2s", "time2": "2s"},
            )
        )
        changed = _changed_cwd_samples(original_cwd, future)
        result = future.result(timeout=10)

    assert result.retcode == 0
    assert os.getcwd() == original_cwd
    assert changed


@pytest.mark.asyncio
async def test_async_terraform_command_defaults_to_process_backend_for_cwd_isolation(
    tmp_path,
):
    module = prepare_sleep_module(tmp_path / "async-process-default")
    original_cwd = os.getcwd()

    async_cli = AsyncTerraformCommand(module)
    task = asyncio.create_task(
        async_cli.apply(
            check=True,
            json=False,
            vars={"time1": "2s", "time2": "2s"},
        )
    )
    changed = []
    while not task.done():
        current = os.getcwd()
        if current != original_cwd:
            changed.append(current)
        await asyncio.sleep(0.05)
    result = await task

    assert result.retcode == 0
    assert os.getcwd() == original_cwd
    assert changed == []
