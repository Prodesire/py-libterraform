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

## 准备

下面的示例需要两样东西。

**已初始化的模块目录。** 每条命令都针对一个已经用 `init` 初始化过的模块运行。下面的
辅助函数会创建可随处运行的最小模块——它们使用 Terraform 内置的 `terraform_data`
资源，无需云凭证，也不会下载任何 provider。

**`__main__` 保护。** pool 会启动 worker 进程，而在 macOS 和 Windows 上，这些 worker
会启动全新的 Python 解释器并重新导入当前程序。如果没有 `if __name__ == "__main__":`
保护，这次重新导入会在每个 worker 里再次执行顶层代码。因此使用 `TerraformPool` 的
程序必须把工作放在该保护之下（或放在由它调用的函数里）。

把两者结合起来，下面是一段并行校验三个模块的完整程序：

```python
import os
import tempfile

from libterraform import TerraformCommand, TerraformPool


def make_module() -> str:
    """创建并初始化一个最小模块，返回其目录。"""
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

复用同一个 pool 可以摊薄启动 worker 与加载共享库的开销，并把它用作上下文管理器以便
退出时自动关闭。除非已确认多个操作可以安全共享，否则应为每个操作隔离 Terraform
state、plugin cache 和工作目录。后续片段展示放进 `main()` 的主体部分，并复用上面的
`modules` 列表。

## 同步：TerraformPool

### 将同一个操作分发到多个模块

`map()` 会在各自的 worker 中针对每个目录运行相同的命令，并按顺序产出结果，语义与
`concurrent.futures.Executor.map` 一致。相同的关键字参数会传给每条命令：

```python
with TerraformPool(max_workers=4) as pool:
    for module, result in zip(modules, pool.map("validate", modules, check=True)):
        print(os.path.basename(module), result.value["valid"])
```

迭代时遇到的第一个命令错误会被重新抛出；如果希望出错后继续，可针对单个模块用
`try` / `except TerraformCommandError` 包裹。

### 提交不同的命令

`pool.command(cwd)` 返回一个绑定到 `cwd` 的代理，它镜像 `TerraformCommand`，但每个
方法都返回 `concurrent.futures.Future` 而非阻塞等待。这样不同的命令可以针对不同的
模块运行，并在各自完成时报告结果：

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

当代理不适用时，还有两个更底层的入口：

```python
with TerraformPool(max_workers=4) as pool:
    # submit() 以字符串形式接收方法名（方法名是动态的时候很有用）。
    validated = pool.submit(modules[0], "validate", check=True)

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
    future = pool.command(modules[0]).apply(auto_approve=True, input=False)
    # ……稍后，要中断一个长时间运行的 apply：
    future.cancel()
    result = future.result()
```

完整 API 见 [TerraformPool](api/terraform-pool.md)。

## 异步：AsyncTerraformCommand

`AsyncTerraformCommand` 默认把阻塞调用放到 worker thread 中执行。这能让 event loop
保持响应，但 Terraform CLI 执行在进程内仍是串行的：

```python
from libterraform import AsyncTerraformCommand

cli = AsyncTerraformCommand(modules[0])
validation = await cli.validate(check=True)
```

要在 asyncio 中同时获得真正并行，可传入 `TerraformPool` 作为 `pool` 后端。此时被等待
的命令会在 pool 的 worker 进程中执行，因此并发等待多条命令即可获得真正并行的
Terraform 执行。同样需要 `__main__` 保护，异步入口为 `asyncio.run(main())`：

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
