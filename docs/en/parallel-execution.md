# Parallel Execution

`TerraformCommand` is safe to call from multiple Python threads, but Terraform
CLI execution is serialized inside one Python process: Terraform reuses
process-wide state (working directory, stdio, plugin clients, signal handling),
so the shared library runs one command at a time. `AsyncTerraformCommand` keeps
an asyncio event loop responsive, but it does not make Terraform itself run in
parallel inside that process either.

`TerraformPool` is the built-in way to get true parallel Terraform operations. It
owns a `ProcessPoolExecutor` and runs each command in its own worker process, so
independent module operations run at the same time. Each worker imports
`libterraform`, builds its own `TerraformCommand`, and runs one command against
one module directory; command results and `check=True` errors come back to the
parent process unchanged.

## Before you start

The examples below need two things.

**Initialized module directories.** Each command runs against a module that has
already been initialized with `init`. The helper below creates minimal modules
that run anywhere — they use Terraform's built-in `terraform_data` resource, so
they need no cloud credentials and download no providers.

**A `__main__` guard.** A pool starts worker processes, and on macOS and Windows
those workers start a fresh Python interpreter that re-imports the program.
Without an `if __name__ == "__main__":` guard, that re-import would run the
top-level code again in every worker. So a program that uses `TerraformPool` must
put its work behind that guard (or inside a function the guard calls).

Putting both together, here is a complete program that validates three modules in
parallel:

```python
import os
import tempfile

from libterraform import TerraformCommand, TerraformPool


def make_module() -> str:
    """Create and initialize a minimal module; return its directory."""
    path = tempfile.mkdtemp()
    with open(os.path.join(path, "main.tf"), "w") as f:
        f.write('resource "terraform_data" "example" {\n  input = "ok"\n}\n')
    TerraformCommand(path).init(check=True)
    return path


def main() -> None:
    modules = [make_module() for _ in range(3)]

    with TerraformPool(max_workers=3) as pool:
        for module, result in zip(modules, pool.map("validate", modules, check=True)):
            print(os.path.basename(module), result.value["valid"])


if __name__ == "__main__":
    main()
```

Reuse a single pool to amortize the cost of starting workers and loading the
shared library, and use it as a context manager so it shuts down on exit. Keep
Terraform state, plugin cache, and working directories separated per operation
unless those operations are known to be safe to share. The remaining snippets
show the body that goes inside `main()` and reuse the `modules` list above.

## Synchronous: TerraformPool

### Fan one operation across modules

`map()` runs the same command against each directory in its own worker and yields
the results in order, mirroring `concurrent.futures.Executor.map`. The same
keyword arguments are passed to every command:

```python
with TerraformPool(max_workers=4) as pool:
    for module, result in zip(modules, pool.map("validate", modules, check=True)):
        print(os.path.basename(module), result.value["valid"])
```

Iterating re-raises the first command error encountered, so wrap a single module
in `try` / `except TerraformCommandError` to keep going after a failure.

### Submit different commands

`pool.command(cwd)` returns a `cwd`-bound proxy that mirrors `TerraformCommand`,
but every method returns a `concurrent.futures.Future` instead of blocking. This
lets different commands run against different modules and report their results as
they finish:

```python
from concurrent.futures import as_completed

with TerraformPool(max_workers=4) as pool:
    futures = {
        pool.command(modules[0]).apply(auto_approve=True, input=False): "first",
        pool.command(modules[1]).apply(auto_approve=True, input=False): "second",
    }
    for future in as_completed(futures):
        print(futures[future], future.result().retcode)
```

Two lower-level entry points help when a proxy does not fit:

```python
with TerraformPool(max_workers=4) as pool:
    # submit() takes the method name as a string (useful when it is dynamic).
    validated = pool.submit(modules[0], "validate", check=True)

    # run() mirrors TerraformCommand.run() and resolves to (retcode, stdout, stderr).
    version = pool.run("version")

    print(validated.result().retcode)
    print(version.result()[0])
```

### Cancel a running command

Each submission is tagged with a run id. A future that has not started running is
cancelled normally. For a command already executing in a worker process,
`future.cancel()` asks Terraform to stop through its normal interrupt handling,
delivered to the worker that owns the run. It returns `False` (mirroring the
standard library, which reports a running task as not cancelled), and the command
then returns whatever result Terraform produces as it winds down:

```python
with TerraformPool(max_workers=2) as pool:
    future = pool.command(modules[0]).apply(auto_approve=True, input=False)
    # ... later, to interrupt a long-running apply:
    future.cancel()
    result = future.result()
```

See [TerraformPool](api/terraform-pool.md) for the full API.

## Asynchronous: AsyncTerraformCommand

By default `AsyncTerraformCommand` runs the blocking call in a worker thread. That
keeps the event loop responsive, but Terraform CLI execution is still serialized
inside the process:

```python
from libterraform import AsyncTerraformCommand

cli = AsyncTerraformCommand(modules[0])
validation = await cli.validate(check=True)
```

To combine asyncio with true parallelism, pass a `TerraformPool` as the `pool`
backend. Awaited commands then run in the pool's worker processes, so awaiting
several of them concurrently gives genuine parallel Terraform execution. The same
`__main__` guard applies, and the async entry point is `asyncio.run(main())`:

```python
import asyncio

from libterraform import AsyncTerraformCommand, TerraformPool


async def main() -> None:
    modules = [make_module() for _ in range(2)]

    with TerraformPool(max_workers=2) as pool:
        first = AsyncTerraformCommand(modules[0], pool=pool)
        second = AsyncTerraformCommand(modules[1], pool=pool)

        results = await asyncio.gather(
            first.apply(auto_approve=True, input=False),
            second.apply(auto_approve=True, input=False),
        )
        print([result.retcode for result in results])


if __name__ == "__main__":
    asyncio.run(main())
```

`AsyncTerraformCommand.run()` accepts `pool` as well:

```python
with TerraformPool(max_workers=4) as pool:
    retcode, stdout, stderr = await AsyncTerraformCommand.run("version", pool=pool)
```

Cancelling the awaiting task requests cooperative cancellation for the run. With
the default thread backend the worker thread is not terminated directly; with a
`pool` backend the request is delivered to the worker process running the
command:

```python
task = asyncio.create_task(cli.apply(auto_approve=True))
# ... later:
task.cancel()
```
