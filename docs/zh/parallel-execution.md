# 并行执行

`TerraformCommand` 可以被多个 Python 线程安全调用，但在单个 Python 进程内，
Terraform CLI 执行会被共享库串行化。`AsyncTerraformCommand` 让 asyncio event
loop 保持响应；它不会让 Terraform 在该进程内真正并行执行。

需要真正并行的 Terraform 操作时，使用进程隔离。每个 worker process 都单独导入
`libterraform`，创建自己的 `TerraformCommand`，并针对一个模块目录执行命令。

## TerraformPool

`TerraformPool` 是内置的 Terraform 命令并行执行方式。它持有一个
`ProcessPoolExecutor`，并把每条命令分发到 worker 进程，因此你无需自己编写 executor
和 worker 函数。

用 `map()` 将同一个操作分发到多个模块目录：

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

`pool.command(cwd)` 返回一个绑定到 `cwd` 的代理，它镜像 `TerraformCommand`，但每个
方法都返回 `concurrent.futures.Future`。这样你可以提交不同的命令，并在就绪时收集
各自的结果：

```python
with TerraformPool(max_workers=4) as pool:
    plan = pool.command("modules/app").plan(check=True)
    version = pool.run("version")

    print(plan.result().retcode)
    print(version.result()[0])
```

尚未开始执行的 future 可以被取消，但已经在 worker 进程中运行的 Terraform 命令无法
被协作式中断。

完整 API 见 [TerraformPool](api/terraform-pool.md)。

## 自行管理进程池

如果需要完全控制，可直接驱动 `ProcessPoolExecutor`。每个 worker 都导入
`libterraform`，创建自己的 `TerraformCommand`，并针对一个模块目录执行命令：

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

## 用 AsyncTerraformCommand 保持响应性

使用 `AsyncTerraformCommand` 解决应用响应性：

```python
from libterraform import AsyncTerraformCommand

cli = AsyncTerraformCommand("path/to/module")
result = await cli.validate(check=True)
```

使用 `TerraformPool`（或其他基于 `ProcessPoolExecutor` 的进程管理器）来实现真正
并行的 Terraform 执行。
