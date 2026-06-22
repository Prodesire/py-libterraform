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

from concurrent.futures import Future, ProcessPoolExecutor
from functools import wraps
from typing import Iterator, Optional, Sequence

from libterraform.cli import TerraformCommand
from libterraform.common import CmdType

__all__ = ["TerraformPool"]


def _invoke_method(cwd, name, args, kwargs):
    """Run a TerraformCommand instance method inside a worker process."""
    cli = TerraformCommand(cwd)
    return getattr(cli, name)(*args, **kwargs)


def _invoke_run(args, kwargs):
    """Run TerraformCommand.run inside a worker process."""
    return TerraformCommand.run(*args, **kwargs)


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

    Note on cancellation: a future that has not started running can be cancelled,
    but a Terraform command already executing in a worker process cannot be
    interrupted cooperatively.
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        mp_context=None,
        initializer=None,
        initargs: tuple = (),
    ):
        self._executor = ProcessPoolExecutor(
            max_workers=max_workers,
            mp_context=mp_context,
            initializer=initializer,
            initargs=initargs,
        )

    def command(self, cwd=None) -> PoolCommand:
        """Return a ``cwd``-bound proxy whose command methods return futures."""
        return PoolCommand(self, cwd)

    def _submit_method(self, cwd, name, args, kwargs) -> Future:
        return self._executor.submit(_invoke_method, cwd, name, args, kwargs)

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
        return self._executor.submit(
            _invoke_run,
            (cmd,),
            dict(args=args, options=options, chdir=chdir, check=check, json=json),
        )

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
        """Shut down the underlying executor."""
        self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)

    def __enter__(self) -> "TerraformPool":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.shutdown(wait=True)
        return False
