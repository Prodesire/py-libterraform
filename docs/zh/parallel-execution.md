# 并行执行

`TerraformCommand` 可以被多个 Python 线程安全调用，但在单个 Python 进程内，
Terraform CLI 执行会被串行化：Terraform 复用进程级全局状态（工作目录、stdio、plugin
客户端、信号处理），因此共享库一次只能执行一条命令。`AsyncTerraformCommand` 能让
asyncio event loop 保持响应，但同样不会让 Terraform 在该进程内真正并行执行。

`TerraformPool` 是内置的、用于获得真正并行 Terraform 操作的方式。它持有一个
`ProcessPoolExecutor`，让每条命令运行在独立的 worker 进程中，从而让相互独立的模块
操作同时执行。每个 worker 都会导入 `libterraform`，构建自己的 `TerraformCommand`，并
针对单个模块目录运行一条命令；命令结果以及 `check=True` 抛出的错误会原样返回给
父进程。

复用同一个 pool 可以摊薄启动 worker 与加载共享库的开销。可将其用作上下文管理器
（退出时自动关闭进程池），或显式调用 `shutdown()`。

除非你已经确认多个操作可以安全共享，否则应为每个操作隔离 Terraform state、plugin
cache 和工作目录。对于可能修改基础设施或 state 的操作，优先使用每个 worker 一个模块
目录，并让 Terraform backend locking 保护共享的远端 state。

## 同步：TerraformPool

### 将同一个操作分发到多个模块

`map()` 会在各自的 worker 中针对每个目录运行相同的命令，并按顺序产出结果，语义与
`concurrent.futures.Executor.map` 一致。相同的关键字参数会传给每条命令：

```python
from pathlib import Path

from libterraform import TerraformPool

module_paths = ["modules/network", "modules/app", "modules/data"]

with TerraformPool(max_workers=4) as pool:
    for path, result in zip(module_paths, pool.map("validate", module_paths, check=True)):
        print(Path(path).name, result.value["valid"])
```

迭代时遇到的第一个命令错误会被重新抛出；如果希望出错后继续，可针对单个模块用
`try` / `except TerraformCommandError` 包裹。

### 提交不同的命令

`pool.command(cwd)` 返回一个绑定到 `cwd` 的代理，它镜像 `TerraformCommand`，但每个
方法都返回 `concurrent.futures.Future` 而非阻塞等待。这样你可以把不同的命令提交到
不同的模块，并在结果就绪时收集：

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

当代理不适用时，还有两个更底层的入口：

```python
with TerraformPool(max_workers=4) as pool:
    # submit() 以字符串形式接收方法名（方法名是动态的时候很有用）。
    validated = pool.submit("modules/app", "validate", check=True)

    # run() 镜像 TerraformCommand.run()，结果为 (retcode, stdout, stderr)。
    version = pool.run("version")

    print(validated.result().retcode)
    print(version.result()[0])
```

### 取消运行中的命令

每条提交的命令都会被打上一个 run id。尚未开始执行的 future 会被正常取消。对于已经
在 worker 进程中运行的命令，`future.cancel()` 会请求 Terraform 通过其正常的 interrupt
处理停止，并投递到持有该 run 的 worker 进程。它返回 `False`（与标准库一致，运行中的
任务被视为未取消），命令随后会在退出过程中返回 Terraform 产生的结果：

```python
with TerraformPool(max_workers=2) as pool:
    future = pool.command("modules/app").apply(auto_approve=True)
    # ……稍后，要中断正在运行的 apply：
    future.cancel()
    result = future.result()
```

完整 API 见 [TerraformPool](api/terraform-pool.md)。

## 异步：AsyncTerraformCommand

`AsyncTerraformCommand` 默认把阻塞调用放到 worker thread 中执行。这能让 event loop
保持响应，但 Terraform CLI 执行在进程内仍是串行的：

```python
from libterraform import AsyncTerraformCommand

cli = AsyncTerraformCommand("path/to/module")
result = await cli.validate(check=True)
```

要在 asyncio 中同时获得真正并行，可传入 `TerraformPool` 作为 `pool` 后端。此时被等待
的命令会在 pool 的 worker 进程中执行，因此并发等待多条命令即可获得真正并行的
Terraform 执行：

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

`AsyncTerraformCommand.run()` 同样接受 `pool` 参数：

```python
with TerraformPool(max_workers=4) as pool:
    retcode, stdout, stderr = await AsyncTerraformCommand.run("version", pool=pool)
```

取消等待中的 task 会为该 run 请求协作式取消。使用默认线程后端时，不会直接终止
worker thread；使用 `pool` 后端时，该请求会投递到运行该命令的 worker 进程：

```python
task = asyncio.create_task(cli.apply(auto_approve=True))
# ……稍后：
task.cancel()
```
