# Parallel Execution

`TerraformCommand` is safe to call from multiple Python threads, but Terraform
CLI execution is serialized inside one Python process. `AsyncTerraformCommand`
keeps an asyncio event loop responsive; it does not make Terraform itself run in
parallel inside that process.

Use process isolation when you need true parallel Terraform operations. Each
worker process imports `libterraform`, creates its own `TerraformCommand`, and
runs against one module directory.

## TerraformPool

`TerraformPool` is the built-in way to run Terraform commands in parallel. It
owns a `ProcessPoolExecutor` and dispatches each command to a worker process, so
you do not have to wire up the executor and worker function yourself.

Use `map()` to fan one operation across many module directories:

```python
from pathlib import Path

from libterraform import TerraformPool

module_paths = [
    "modules/network",
    "modules/app",
    "modules/data",
]

with TerraformPool(max_workers=4) as pool:
    results = pool.map("validate", module_paths, check=True)
    for path, result in zip(module_paths, results):
        print(Path(path).name, result.value["valid"])
```

`pool.command(cwd)` returns a `cwd`-bound proxy that mirrors `TerraformCommand`,
but every method returns a `concurrent.futures.Future`. This lets you submit
different commands and collect their results when ready:

```python
with TerraformPool(max_workers=4) as pool:
    plan = pool.command("modules/app").plan(check=True)
    version = pool.run("version")

    print(plan.result().retcode)
    print(version.result()[0])
```

A future that has not started running can be cancelled, but a Terraform command
already executing in a worker process cannot be interrupted cooperatively.

See [TerraformPool](api/terraform-pool.md) for the full API.

## Rolling your own pool

If you need full control, drive a `ProcessPoolExecutor` directly. Each worker
imports `libterraform`, creates its own `TerraformCommand`, and runs against one
module directory:

```python
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from libterraform import TerraformCommand


def validate_module(module_path: str) -> dict:
    cli = TerraformCommand(module_path)
    return cli.validate(check=True).value


module_paths = [
    "modules/network",
    "modules/app",
    "modules/data",
]

with ProcessPoolExecutor() as executor:
    results = list(executor.map(validate_module, module_paths))

for path, result in zip(module_paths, results):
    print(Path(path).name, result["valid"])
```

Keep Terraform state, plugin cache, and working directories separated per
operation unless you already know those operations are safe to share. For
operations that can change infrastructure or state, prefer one module directory
per process and let Terraform backend locking protect shared remote state.

## Responsiveness with AsyncTerraformCommand

Use `AsyncTerraformCommand` for application responsiveness:

```python
from libterraform import AsyncTerraformCommand

cli = AsyncTerraformCommand("path/to/module")
result = await cli.validate(check=True)
```

Use `TerraformPool` (or another `ProcessPoolExecutor`-based supervisor) for
parallel Terraform execution.
