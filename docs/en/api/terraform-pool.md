# TerraformPool

Import `TerraformPool` from the package root:

```python
from libterraform import TerraformPool
```

`TerraformPool` runs Terraform commands in parallel across a pool of worker
processes. Terraform reuses process-wide state (working directory, stdio, plugin
clients, signal handling), so CLI execution is serialized inside a single Python
process even when called from multiple threads. `TerraformPool` gives each
command its own worker process, so independent module operations can achieve
true parallel Terraform operations.

## Execution Model

Each worker process imports `libterraform`, builds its own `TerraformCommand`,
and runs one command against one module directory. Command results and
`check=True` errors are returned to the parent process unchanged.

Reuse a single pool to amortize the cost of starting workers and loading the
shared library. Use it as a context manager, or call `shutdown()` explicitly.

The examples below use illustrative paths like `modules/app`; replace them with
your own initialized module directories. A program that uses `TerraformPool` must
also run under an `if __name__ == "__main__":` guard, because the pool starts
worker processes. See [Parallel Execution](../parallel-execution.md) for a
complete, runnable setup.

## Cancellation

Each submitted command is tagged with a run id. A future that has not started
running is cancelled normally. For a command already executing in a worker
process, `future.cancel()` asks Terraform to stop through its normal interrupt
handling — the same cooperative cancellation used by `AsyncTerraformCommand` —
delivered to the worker process that owns the run. It returns `False` (mirroring
the standard library, which reports a running task as not cancelled), and the
command then returns whatever result Terraform produces as it winds down.

```python
future = pool.command("modules/app").apply(auto_approve=True)
# ... later, to interrupt a long-running apply:
future.cancel()
result = future.result()
```

## Usage

Fan one operation across many module directories with `map()`:

```python
from libterraform import TerraformPool

with TerraformPool(max_workers=4) as pool:
    for result in pool.map("validate", ["modules/a", "modules/b"], check=True):
        print(result.value["valid"])
```

Submit heterogeneous commands and collect their futures. `pool.command(cwd)`
returns a `cwd`-bound proxy that mirrors `TerraformCommand`, but each method
returns a `concurrent.futures.Future`:

```python
with TerraformPool(max_workers=4) as pool:
    plan = pool.command("modules/app").plan(check=True)
    version = pool.run("version")

    print(plan.result().retcode)
    print(version.result()[0])
```

Use the low-level `submit()` when you want to name the method dynamically:

```python
future = pool.submit("modules/network", "apply", auto_approve=True)
result = future.result()
```

`pool.run()` mirrors `TerraformCommand.run()` and resolves to the
`(retcode, stdout, stderr)` tuple.

::: libterraform.pool.TerraformPool
