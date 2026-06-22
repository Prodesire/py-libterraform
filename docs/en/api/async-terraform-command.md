# AsyncTerraformCommand

Import `AsyncTerraformCommand` from the package root:

```python
from libterraform import AsyncTerraformCommand
```

`AsyncTerraformCommand` provides asyncio-compatible access to
`TerraformCommand`. It mirrors the synchronous command methods and runs the
blocking Terraform call in a worker thread, so callers can `await` Terraform
operations without blocking the event loop.

## Execution Model

By default `AsyncTerraformCommand` runs the blocking call in a worker thread, so
it does not make Terraform CLI execution parallel inside one Python process.
Terraform still uses process-wide state, so the shared library serializes CLI
execution. Pass a [`TerraformPool`](terraform-pool.md) as `pool` to run commands
in worker processes when you need true parallel Terraform operations.

If a coroutine is cancelled, the awaiting task is cancelled, but the underlying
worker thread is not terminated directly by this API. `AsyncTerraformCommand` sends a
cooperative cancellation request to Terraform's shutdown channel and then
re-raises `asyncio.CancelledError`. Terraform or a provider may still take some
time to return from its own shutdown path.

## Usage

```python
from libterraform import AsyncTerraformCommand

cli = AsyncTerraformCommand("path/to/terraform/module")

await cli.init(check=True)
plan = await cli.plan(check=True)
```

`AsyncTerraformCommand.run()` accepts the same command arguments as
`TerraformCommand.run()`:

```python
retcode, stdout, stderr = await AsyncTerraformCommand.run("version")
```

Pass an executor when you need to integrate with an application-owned thread
pool:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=1) as executor:
    cli = AsyncTerraformCommand("path/to/terraform/module", executor=executor)
    validation = await cli.validate(check=True)
```

Pass a `TerraformPool` as `pool` to await commands that run in worker processes,
giving true parallel Terraform execution. `AsyncTerraformCommand.run()` accepts
`pool` as well:

```python
from libterraform import AsyncTerraformCommand, TerraformPool

with TerraformPool(max_workers=4) as pool:
    network = AsyncTerraformCommand("modules/network", pool=pool)
    app = AsyncTerraformCommand("modules/app", pool=pool)
    results = await asyncio.gather(
        network.apply(auto_approve=True),
        app.apply(auto_approve=True),
    )
```

Cancellation requests are scoped to the Terraform run started by the coroutine:

```python
task = asyncio.create_task(cli.apply(auto_approve=True))
task.cancel()
```

This asks Terraform to stop through its normal interrupt handling. With the
default thread backend it is not a direct termination of the worker thread; with
a `pool` backend the request is delivered to the worker process running the
command.

::: libterraform.async_cli.AsyncTerraformCommand
