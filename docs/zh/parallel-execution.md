# 并行执行

`TerraformCommand` 可以被多个 Python 线程安全调用，但在单个 Python 进程内，
Terraform CLI 执行会被共享库串行化。`AsyncTerraformCommand` 让 asyncio event
loop 保持响应；它不会让 Terraform 在该进程内真正并行执行。

需要真正并行的 Terraform 操作时，使用进程隔离。每个 worker process 都单独导入
`libterraform`，创建自己的 `TerraformCommand`，并针对一个模块目录执行命令。

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

除非你已经确认多个操作可以安全共享，否则应为每个操作隔离 Terraform state、
plugin cache 和工作目录。对于可能修改基础设施或 state 的操作，优先使用每个进程
一个模块目录，并让 Terraform backend locking 保护共享的远端 state。

使用 `AsyncTerraformCommand` 解决应用响应性：

```python
from libterraform import AsyncTerraformCommand

cli = AsyncTerraformCommand("path/to/module")
result = await cli.validate(check=True)
```

使用 `ProcessPoolExecutor` 或其他进程管理器来实现真正并行的 Terraform 执行。
