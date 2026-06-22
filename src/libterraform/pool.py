"""Process-based parallel execution for Terraform commands.

Terraform reuses process-wide state (working directory, stdio, plugin clients,
signal handling), so CLI execution is serialized inside a single Python process
even when called from multiple threads. :class:`TerraformPool` runs each command
in its own worker process so independent module operations can truly run in
parallel.

Each worker process imports ``libterraform``, builds its own
:class:`~libterraform.cli.TerraformCommand`, and runs one command against one
module directory. Command results and ``check=True`` errors are returned to the
parent process unchanged.

Each submitted command is tagged with a run id. Calling ``future.cancel()`` on a
command that is already running asks Terraform to stop through its normal
interrupt handling (the same cooperative cancellation used by
:class:`~libterraform.async_cli.AsyncTerraformCommand`), delivered to the worker
process that owns the run.

Example::

    from libterraform import TerraformPool

    with TerraformPool(max_workers=4) as pool:
        # Fan one operation across many module directories.
        for result in pool.map("validate", ["modules/a", "modules/b"], check=True):
            print(result.value["valid"])

        # Or submit heterogeneous commands and collect their futures.
        plan = pool.command("modules/app").plan(check=True)
        version = pool.run("version")
        print(plan.result().retcode, version.result()[0])
"""

import multiprocessing
import threading
import uuid
from concurrent.futures import Future, ProcessPoolExecutor
from functools import wraps
from typing import Any, Dict, Iterator, Optional, Sequence

from libterraform.cli import TerraformCommand, _cancel_cli_run, _current_run_id
from libterraform.common import CmdType

__all__ = ["TerraformPool"]

# Time between polls of the shared cancellation registry inside a worker while a
# command is running. Cancellation is rare, so a short interval keeps response
# time low without measurable overhead.
_CANCEL_POLL_INTERVAL = 0.1

# Per-worker state, populated by ``_worker_initializer`` in each worker process.
# ``_worker_registry`` is a Manager().dict() proxy mapping run_id -> True once
# the parent has asked for that run to be cancelled.
_worker_registry: Optional[Any] = None
_worker_active: Dict[str, bool] = {}
_worker_lock = threading.Lock()
_worker_event = threading.Event()  # set while at least one run is active


def _worker_initializer(registry, user_initializer, user_initargs):
    """Initialize a worker process: wire up the cancel listener, then chain."""
    global _worker_registry
    _worker_registry = registry
    listener = threading.Thread(target=_cancel_listener, daemon=True)
    listener.start()
    if user_initializer is not None:
        user_initializer(*user_initargs)


def _cancel_listener():
    """Watch the shared registry and cancel active runs the parent flagged."""
    registry = _worker_registry
    if registry is None:
        return
    while True:
        _worker_event.wait()
        while True:
            with _worker_lock:
                active = list(_worker_active)
            if not active:
                _worker_event.clear()
                break
            try:
                for run_id in active:
                    if registry.get(run_id):
                        _cancel_cli_run(run_id)
            except (BrokenPipeError, EOFError, OSError):
                # The manager process is gone (pool shutting down). Nothing left
                # to watch, so the listener can exit.
                return
            _worker_event.wait(_CANCEL_POLL_INTERVAL)


def _run_with_cancel(run_id, func):
    """Run ``func`` in a worker while exposing its run id for cancellation."""
    if run_id is None or _worker_registry is None:
        return func()

    token = _current_run_id.set(run_id)
    with _worker_lock:
        _worker_active[run_id] = True
    _worker_event.set()
    try:
        return func()
    finally:
        _current_run_id.reset(token)
        with _worker_lock:
            _worker_active.pop(run_id, None)
        try:
            _worker_registry.pop(run_id, None)
        except (BrokenPipeError, EOFError, OSError, KeyError):
            pass


def _invoke_method(cwd, name, args, kwargs, run_id):
    """Run a TerraformCommand instance method inside a worker process."""

    def call():
        cli = TerraformCommand(cwd)
        return getattr(cli, name)(*args, **kwargs)

    return _run_with_cancel(run_id, call)


def _invoke_run(args, kwargs, run_id):
    """Run TerraformCommand.run inside a worker process."""
    return _run_with_cancel(run_id, lambda: TerraformCommand.run(*args, **kwargs))


def _install_cooperative_cancel(future, run_id, registry):
    """Make ``future.cancel()`` request cooperative cancellation when running.

    If the command has not started yet, the standard executor cancellation
    applies. If it is already running, the owning worker is asked to interrupt
    Terraform through its normal shutdown handling.
    """
    original_cancel = future.cancel

    def cancel():
        if original_cancel():
            return True
        if run_id is not None:
            try:
                registry[run_id] = True
            except (BrokenPipeError, EOFError, OSError):
                pass
        return False

    future.cancel = cancel


class PoolCommand:
    """A ``cwd``-bound proxy whose methods submit work to a :class:`TerraformPool`.

    It mirrors :class:`~libterraform.cli.TerraformCommand`, but every command
    method returns a :class:`concurrent.futures.Future` resolving to the usual
    :class:`~libterraform.cli.CommandResult` (or raising the usual error) instead
    of blocking until the command finishes.
    """

    def __init__(self, pool: "TerraformPool", cwd=None):
        self._pool = pool
        self.cwd = cwd

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)

        attr = getattr(TerraformCommand, name, None)
        if not callable(attr):
            raise AttributeError(name)

        def submit_method(*args, **kwargs) -> Future:
            return self._pool._submit_method(self.cwd, name, args, kwargs)

        return submit_method


def _make_pool_method(name):
    sync_method = getattr(TerraformCommand, name)

    @wraps(sync_method)
    def pool_method(self, *args, **kwargs) -> Future:
        return self._pool._submit_method(self.cwd, name, args, kwargs)

    return pool_method


for _name, _value in vars(TerraformCommand).items():
    if _name.startswith("_") or _name == "run" or not callable(_value):
        continue
    setattr(PoolCommand, _name, _make_pool_method(_name))


class TerraformPool:
    """Run Terraform commands in parallel across a pool of worker processes.

    The pool owns a :class:`concurrent.futures.ProcessPoolExecutor`; reuse a
    single pool to amortize the cost of starting workers and loading the shared
    library. Use it as a context manager, or call :meth:`shutdown` explicitly.

    Cancellation: a future that has not started running is cancelled normally.
    For a command already executing in a worker process, ``future.cancel()``
    asks Terraform to stop through its normal interrupt handling and returns
    ``False`` (mirroring the standard library, which reports a running task as
    not cancelled). The command then returns whatever result Terraform produces
    as it winds down.
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        mp_context=None,
        initializer=None,
        initargs: tuple = (),
    ):
        self._manager = (mp_context or multiprocessing).Manager()
        self._cancel_registry = self._manager.dict()
        self._executor = ProcessPoolExecutor(
            max_workers=max_workers,
            mp_context=mp_context,
            initializer=_worker_initializer,
            initargs=(self._cancel_registry, initializer, initargs),
        )

    def command(self, cwd=None) -> PoolCommand:
        """Return a ``cwd``-bound proxy whose command methods return futures."""
        return PoolCommand(self, cwd)

    def _submit_method(self, cwd, name, args, kwargs) -> Future:
        run_id = uuid.uuid4().hex
        future = self._executor.submit(_invoke_method, cwd, name, args, kwargs, run_id)
        _install_cooperative_cancel(future, run_id, self._cancel_registry)
        return future

    def submit(self, cwd, method, /, *args, **kwargs) -> Future:
        """Submit a single command method for ``cwd`` and return its future.

        :param cwd: Working directory for the command (passed to
            :class:`~libterraform.cli.TerraformCommand`).
        :param method: Name of the :class:`~libterraform.cli.TerraformCommand`
            method to call, e.g. ``"validate"`` or ``"apply"``.
        """
        return self._submit_method(cwd, method, args, kwargs)

    def run(
        self,
        cmd: CmdType,
        args: Optional[Sequence[str]] = None,
        options: Optional[dict] = None,
        chdir=None,
        check: bool = False,
        json=False,
    ) -> Future:
        """Mirror :meth:`TerraformCommand.run`, returning a future instead.

        The future resolves to the ``(retcode, stdout, stderr)`` tuple.
        """
        run_id = uuid.uuid4().hex
        future = self._executor.submit(
            _invoke_run,
            (cmd,),
            dict(args=args, options=options, chdir=chdir, check=check, json=json),
            run_id,
        )
        _install_cooperative_cancel(future, run_id, self._cancel_registry)
        return future

    def map(self, method, cwds, *args, **kwargs) -> Iterator:
        """Run ``method`` against each directory in ``cwds`` in parallel.

        Returns an iterator over the results in the order ``cwds`` were given,
        mirroring :meth:`concurrent.futures.Executor.map`. The same ``args`` and
        ``kwargs`` are passed to every command. Iterating re-raises the first
        command error encountered.
        """
        futures = [self._submit_method(cwd, method, args, kwargs) for cwd in cwds]

        def result_iterator():
            for future in futures:
                yield future.result()

        return result_iterator()

    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        """Shut down the underlying executor and worker manager."""
        self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)
        self._manager.shutdown()

    def __enter__(self) -> "TerraformPool":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.shutdown(wait=True)
        return False
