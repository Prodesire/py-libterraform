import asyncio
import uuid
from concurrent.futures import Executor
from functools import wraps
from typing import Any, Optional, Sequence, Tuple

from libterraform.cli import TerraformCommand, _cancel_cli_run, _current_run_id
from libterraform.common import CmdType


class AsyncTerraformCommand:
    """Async-compatible Terraform command line API.

    This class mirrors :class:`libterraform.cli.TerraformCommand` and runs the
    synchronous Terraform call in a worker thread so callers can await it without
    blocking the event loop. Terraform CLI execution is still serialized inside
    the shared library because Terraform uses process-wide state.

    Cancelling the awaiting coroutine requests cooperative cancellation for the
    corresponding Terraform run. The worker thread is not terminated directly.
    """

    def __init__(self, cwd=None, executor: Optional[Executor] = None):
        self.cwd = cwd
        self.executor = executor
        self._sync_cli = TerraformCommand(cwd)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)

        attr = getattr(self._sync_cli, name)
        if not callable(attr):
            return attr

        async def async_method(*args, **kwargs):
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
    ) -> Tuple[int, str, str]:
        """Run command with args without blocking the event loop."""

        return await cls._call(
            TerraformCommand.run,
            cmd,
            args=args,
            options=options,
            chdir=chdir,
            check=check,
            json=json,
            executor=executor,
        )


def _make_async_method(name):
    sync_method = getattr(TerraformCommand, name)

    @wraps(sync_method)
    async def async_method(self, *args, **kwargs):
        return await self._call(
            getattr(self._sync_cli, name),
            *args,
            executor=self.executor,
            **kwargs,
        )

    return async_method


for _name, _value in vars(TerraformCommand).items():
    if _name.startswith("_") or _name == "run" or not callable(_value):
        continue
    setattr(AsyncTerraformCommand, _name, _make_async_method(_name))
