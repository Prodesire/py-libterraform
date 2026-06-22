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

Reuse a single pool to amortize the cost of starting workers and loading the
shared library. Use it as a context manager (which shuts the pool down on exit),
or call `shutdown()` explicitly.

Keep Terraform state, plugin cache, and working directories separated per
operation unless you already know those operations are safe to share. For
operations that can change infrastructure or state, prefer one module directory
per worker and let Terraform backend locking protect shared remote state.

## Synchronous: TerraformPool

### Fan one operation across modules

`map()` runs the same command against each directory in its own worker and yields
the results in order, mirroring `concurrent.futures.Executor.map`. The same
keyword arguments are passed to every command:

```python
from pathlib import Path

from libterraform import TerraformPool

module_paths = ["modules/network", "modules/app", "modules/data"]

with TerraformPool(max_workers=4) as pool:
    for path, result in zip(module_paths, pool.map("validate", module_paths, check=True)):
        print(Path(path).name, result.value["valid"])
```

Iterating re-raises the first command error encountered, so wrap a single module
in `try`/`except TerraformCommandError` if you want to keep going.

### Submit different commands

`pool.command(cwd)` returns a `cwd`-bound proxy that mirrors `TerraformCommand`,
but every method returns a `concurrent.futures.Future` instead of blocking. This
lets you submit different commands to different modules and collect their results
when they are ready:

```python
from concurrent.futures import as_completed

with TerraformPool(max_workers=4) as pool:
    futures = {
        pool.command("modules/network").apply(auto_approve=True): "network",
        pool.command("modules/app").apply(auto_approve=True): "app",
    }
    for future in as_completed(futures):
        print(futures[future], future.result().retcode)
```

Two lower-level entry points are available when a proxy does not fit:

```python
with TerraformPool(max_workers=4) as pool:
    # submit() takes the method name as a string (useful when it is dynamic).
    validated = pool.submit("modules/app", "validate", check=True)

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
    future = pool.command("modules/app").apply(auto_approve=True)
    # ... later, to interrupt the running apply:
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

cli = AsyncTerraformCommand("path/to/module")
result = await cli.validate(check=True)
```

To combine asyncio with true parallelism, pass a `TerraformPool` as the `pool`
backend. Awaited commands then run in the pool's worker processes, so awaiting
several of them concurrently gives genuine parallel Terraform execution:

```python
import asyncio

from libterraform import AsyncTerraformCommand, TerraformPool

with TerraformPool(max_workers=4) as pool:
    network = AsyncTerraformCommand("modules/network", pool=pool)
    app = AsyncTerraformCommand("modules/app", pool=pool)

    results = await asyncio.gather(
        network.apply(auto_approve=True),
        app.apply(auto_approve=True),
    )
    print([r.retcode for r in results])
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
