import asyncio
import time

import pytest

from libterraform import AsyncTerraformCommand, TerraformCommand, TerraformStream
from libterraform.exceptions import TerraformCommandError
from tests.cli.conftest import prepare_sleep_module

DATA_MODULE = 'resource "terraform_data" "a" {\n  input = "x"\n}\n'


@pytest.fixture
def data_cli(tmp_path):
    module = tmp_path / "data"
    module.mkdir()
    (module / "main.tf").write_text(DATA_MODULE)
    cli = TerraformCommand(str(module))
    cli.init(check=True)
    return cli


# --- synchronous streaming ---


def test_plan_stream_yields_json_events(data_cli):
    stream = data_cli.plan_stream()

    assert isinstance(stream, TerraformStream)
    types = [event.get("type") for event in stream]

    assert "planned_change" in types
    assert "change_summary" in types
    assert stream.retcode == 0
    assert stream.stderr == ""


def test_apply_stream_yields_text_lines_when_not_json(data_cli):
    lines = list(data_cli.apply_stream(json=False))

    assert lines  # got output
    assert all(isinstance(line, str) for line in lines)


def test_stream_check_raises_at_end_on_failure(data_cli):
    with pytest.raises(TerraformCommandError):
        for _ in data_cli.stream("invalid", check=True):
            pass


def test_stream_context_manager_sets_retcode(data_cli):
    with data_cli.plan_stream() as stream:
        events = list(stream)

    assert events
    assert stream.retcode == 0


@pytest.mark.slow
def test_apply_stream_is_live(tmp_path):
    module = prepare_sleep_module(tmp_path / "live")
    cli = TerraformCommand(module)

    start = time.monotonic()
    stamps = []
    for event in cli.apply_stream(vars={"time1": "4s", "time2": "4s"}):
        if event.get("type", "").startswith("apply_"):
            stamps.append(time.monotonic() - start)

    # An early apply event must arrive well before the ~4s run finishes, which is
    # only possible if output streams live rather than arriving all at once.
    assert min(stamps) < 2.0
    assert max(stamps) > 3.0


@pytest.mark.slow
def test_stream_close_cancels_running_command(tmp_path):
    module = prepare_sleep_module(tmp_path / "cancel-stream")
    cli = TerraformCommand(module)

    start = time.monotonic()
    with cli.apply_stream(vars={"time1": "12s", "time2": "12s"}) as stream:
        for event in stream:
            if event.get("type") == "apply_start":
                break  # leave early; __exit__ cancels and cleans up
    elapsed = time.monotonic() - start

    # Closing requested Terraform's shutdown, so we stop well before ~12s.
    assert elapsed < 8


# --- asynchronous streaming ---


@pytest.mark.asyncio
async def test_async_plan_stream_yields_events(data_cli):
    async_cli = AsyncTerraformCommand(data_cli.cwd)

    types = []
    async for event in async_cli.plan_stream():
        types.append(event.get("type"))

    assert "planned_change" in types


@pytest.mark.asyncio
async def test_async_stream_propagates_check_errors(data_cli):
    async_cli = AsyncTerraformCommand(data_cli.cwd)

    with pytest.raises(TerraformCommandError):
        async for _ in async_cli.stream("invalid", check=True):
            pass


@pytest.mark.asyncio
@pytest.mark.slow
async def test_async_apply_stream_cancel_releases_runtime(tmp_path):
    module = prepare_sleep_module(tmp_path / "async-stream-cancel")
    async_cli = AsyncTerraformCommand(module)

    async def consume():
        async for _ in async_cli.apply_stream(vars={"time1": "12s", "time2": "12s"}):
            pass

    task = asyncio.create_task(consume())
    await asyncio.sleep(2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Cancelling asked Terraform to stop, so the shared library frees up and a
    # follow-up command returns promptly instead of waiting out the ~12s apply.
    result = await asyncio.wait_for(
        AsyncTerraformCommand.run("version", json=False), timeout=8
    )
    assert result[0] == 0
