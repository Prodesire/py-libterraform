# Parallel Execution

`TerraformCommand` is safe to call from multiple Python threads, but Terraform
CLI execution is serialized inside one Python process. `AsyncTerraformCommand`
keeps an asyncio event loop responsive; it does not make Terraform itself run in
parallel inside that process.

Use process isolation when you need true parallel Terraform operations. Each
worker process imports `libterraform`, creates its own `TerraformCommand`, and
runs against one module directory.

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

Use `AsyncTerraformCommand` for application responsiveness:

```python
from libterraform import AsyncTerraformCommand

cli = AsyncTerraformCommand("path/to/module")
result = await cli.validate(check=True)
```

Use `ProcessPoolExecutor` or another process supervisor for parallel Terraform
execution.
