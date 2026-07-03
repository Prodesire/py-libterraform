import asyncio
import uuid
from concurrent.futures import Executor
from functools import wraps
from threading import Thread
from typing import Any, Optional, Sequence, Tuple

from libterraform.cli import (
    _STREAM_METHODS,
    TerraformCommand,
    TerraformStream,
    _cancel_cli_run,
    _current_run_id,
)
from libterraform.common import CmdType
from libterraform.pool import TerraformPool


class AsyncTerraformCommand:
    """Async-compatible Terraform command line API.

    This class mirrors `TerraformCommand` and awaits the
    Terraform call without blocking the event loop.

    By default the synchronous call uses process-isolated execution so Terraform's
    process-wide state does not leak into the caller process. Use
    ``backend="thread"`` to run through the current process, or pass a
    `TerraformPool` as ``pool`` to reuse worker processes for true parallel
    Terraform execution.

    Cancelling the awaiting coroutine requests cancellation for the corresponding
    Terraform run. With the process backend the worker process is interrupted;
    with a thread backend the worker thread is not terminated directly; with a
    process pool the owning worker is asked to interrupt Terraform through its
    normal shutdown handling.
    """

    def __init__(
        self,
        cwd=None,
        executor: Optional[Executor] = None,
        pool: Optional[TerraformPool] = None,
        backend: str = "process",
    ):
        self.cwd = cwd
        self.executor = executor
        self._pool = pool
        self.backend = backend
        self._sync_cli = TerraformCommand(cwd, backend=backend)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)

        attr = getattr(self._sync_cli, name)
        if not callable(attr):
            return attr

        async def async_method(*args, **kwargs):
            if self._pool is not None:
                return await _await_pool_future(
                    self._pool._submit_method(self.cwd, name, args, kwargs)
                )
            return await self._call(
                attr,
                *args,
                executor=self.executor,
                **kwargs,
            )

        return async_method

    @staticmethod
    async def _call(func, *args, executor: Optional[Executor] = None, **kwargs):
        run_id = uuid.uuid4().hex

        def call_with_run_id():
            token = _current_run_id.set(run_id)
            try:
                return func(*args, **kwargs)
            finally:
                _current_run_id.reset(token)

        if executor is None:
            try:
                return await asyncio.to_thread(call_with_run_id)
            except asyncio.CancelledError:
                _cancel_cli_run(run_id)
                raise

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(executor, call_with_run_id)
        except asyncio.CancelledError:
            _cancel_cli_run(run_id)
            raise

    @classmethod
    async def run(
        cls,
        cmd: CmdType,
        args: Optional[Sequence[str]] = None,
        options: Optional[dict] = None,
        chdir=None,
        check: bool = False,
        json=False,
        executor: Optional[Executor] = None,
        pool: Optional[TerraformPool] = None,
        backend: str = "process",
    ) -> Tuple[int, str, str]:
        """Run command with args without blocking the event loop."""

        if pool is not None:
            return await _await_pool_future(
                pool.run(
                    cmd,
                    args=args,
                    options=options,
                    chdir=chdir,
                    check=check,
                    json=json,
                )
            )

        return await cls._call(
            TerraformCommand.run,
            cmd,
            args=args,
            options=options,
            chdir=chdir,
            check=check,
            json=json,
            backend=backend,
            executor=executor,
        )

    async def stream(
        self,
        cmd: CmdType,
        args: Optional[Sequence[str]] = None,
        options: Optional[dict] = None,
        chdir=None,
        json: bool = True,
        check: bool = False,
    ):
        """Async iterator over a streaming command. See ``TerraformCommand.stream``.

        Usage: ``async for event in async_cli.stream("plan"): ...``. Cancelling
        the consuming task requests cooperative cancellation of the command.
        """
        sync_stream = self._sync_cli.stream(cmd, args, options, chdir, json, check)
        async for event in _aiter_stream(sync_stream):
            yield event

    async def plan_stream(self, json: bool = True, check: bool = False, **options):
        """Async iterator over ``terraform plan`` output."""
        sync_stream = self._sync_cli.plan_stream(json=json, check=check, **options)
        async for event in _aiter_stream(sync_stream):
            yield event

    async def apply_stream(
        self,
        json: bool = True,
        check: bool = False,
        auto_approve: bool = True,
        input: bool = False,
        **options,
    ):
        """Async iterator over ``terraform apply`` output."""
        sync_stream = self._sync_cli.apply_stream(
            json=json,
            check=check,
            auto_approve=auto_approve,
            input=input,
            **options,
        )
        async for event in _aiter_stream(sync_stream):
            yield event


async def _aiter_stream(stream: TerraformStream):
    """Bridge a synchronous TerraformStream to an async iterator.

    A daemon thread drives the blocking stream and forwards each event to the
    event loop through a queue. Cancelling the consumer requests cooperative
    cancellation; the driver thread then reaches EOF and finishes on its own.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    done = object()

    def pump():
        try:
            for event in stream:
                loop.call_soon_threadsafe(queue.put_nowait, (event, None))
        except BaseException as exc:  # forward check/parse errors to the consumer
            loop.call_soon_threadsafe(queue.put_nowait, (None, exc))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, done)

    Thread(target=pump, daemon=True).start()
    try:
        while True:
            item = await queue.get()
            if item is done:
                break
            event, exc = item
            if exc is not None:
                raise exc
            yield event
    except (asyncio.CancelledError, GeneratorExit):
        stream.cancel()
        raise


async def _await_pool_future(future):
    """Await a pool future, requesting cooperative cancellation on cancel."""
    try:
        return await asyncio.wrap_future(future)
    except asyncio.CancelledError:
        future.cancel()
        raise


def _make_async_method(name):
    sync_method = getattr(TerraformCommand, name)

    @wraps(sync_method)
    async def async_method(self, *args, **kwargs):
        if self._pool is not None:
            return await _await_pool_future(
                self._pool._submit_method(self.cwd, name, args, kwargs)
            )
        return await self._call(
            getattr(self._sync_cli, name),
            *args,
            executor=self.executor,
            **kwargs,
        )

    return async_method


for _name, _value in vars(TerraformCommand).items():
    if _name.startswith("_") or _name == "run" or _name in _STREAM_METHODS:
        continue
    if not callable(_value):
        continue
    setattr(AsyncTerraformCommand, _name, _make_async_method(_name))
