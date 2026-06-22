# TerraformPool

从包根路径导入 `TerraformPool`：

```python
from libterraform import TerraformPool
```

`TerraformPool` 通过一组 worker 进程并行执行 Terraform 命令。Terraform 使用进程级
全局状态（工作目录、stdio、plugin 客户端、信号处理），因此即便从多个线程调用，CLI
执行在单个 Python 进程内仍会串行。`TerraformPool` 让每条命令运行在独立的 worker
进程中，从而让相互独立的模块操作实现真正并行的 Terraform 操作。

## 执行模型

每个 worker 进程都会导入 `libterraform`，构建自己的 `TerraformCommand`，并针对单个
模块目录运行一条命令。命令结果以及 `check=True` 抛出的错误会原样返回给父进程。

复用同一个 pool 可以摊薄启动 worker 与加载共享库的开销。可将其用作上下文管理器，
或显式调用 `shutdown()`。

下面的示例使用 `modules/app` 等示意路径，请替换为自己已初始化的模块目录。此外，
使用 `TerraformPool` 的程序必须运行在 `if __name__ == "__main__":` 保护之下，因为
pool 会启动 worker 进程。完整可运行的搭建方式见[并行执行](../parallel-execution.md)。

## 取消

每条提交的命令都会被打上一个 run id。尚未开始执行的 future 会被正常取消。对于已经
在 worker 进程中运行的命令，`future.cancel()` 会请求 Terraform 通过其正常的 interrupt
处理停止——与 `AsyncTerraformCommand` 使用的协作式取消相同——并投递到持有该 run 的
worker 进程。它返回 `False`（与标准库一致，运行中的任务被视为未取消），命令随后会在
退出过程中返回 Terraform 产生的结果。

```python
future = pool.command("modules/app").apply(auto_approve=True)
# ……稍后，要中断一个长时间运行的 apply：
future.cancel()
result = future.result()
```

## 使用

用 `map()` 将同一个操作分发到多个模块目录：

```python
from libterraform import TerraformPool

with TerraformPool(max_workers=4) as pool:
    for result in pool.map("validate", ["modules/a", "modules/b"], check=True):
        print(result.value["valid"])
```

提交不同的命令并收集各自的 future。`pool.command(cwd)` 返回一个绑定到 `cwd` 的代理，
它镜像 `TerraformCommand`，但每个方法都返回 `concurrent.futures.Future`：

```python
with TerraformPool(max_workers=4) as pool:
    plan = pool.command("modules/app").plan(check=True)
    version = pool.run("version")

    print(plan.result().retcode)
    print(version.result()[0])
```

当需要动态指定方法名时，可使用底层的 `submit()`：

```python
future = pool.submit("modules/network", "apply", auto_approve=True)
result = future.result()
```

`pool.run()` 镜像 `TerraformCommand.run()`，其结果为 `(retcode, stdout, stderr)` 元组。

## 接口

### `TerraformPool(max_workers=None, mp_context=None, initializer=None, initargs=())`

创建进程池。内部持有一个 `concurrent.futures.ProcessPoolExecutor`，以及用于跨进程
传递取消请求的 worker 管理器。

参数：

| 参数 | 类型 | 说明 |
|---|---|---|
| `max_workers` | `int \| None` | worker 进程数量。为 `None` 时使用默认值（CPU 核数）。 |
| `mp_context` | `multiprocessing` 上下文 \| `None` | 用于创建进程的 multiprocessing 上下文。 |
| `initializer` | `callable \| None` | 每个 worker 启动时调用的可选初始化函数。 |
| `initargs` | `tuple` | 传给 `initializer` 的参数。 |

### `command(cwd=None)`

返回一个绑定到 `cwd` 的代理（`PoolCommand`）。该代理镜像 `TerraformCommand` 的命令
方法，但每个方法都把命令提交到进程池，并返回 `concurrent.futures.Future`，其结果为
通常的 `CommandResult`（或抛出通常的错误）。

参数：

| 参数 | 类型 | 说明 |
|---|---|---|
| `cwd` | `str \| None` | 命令的工作目录，传给 `TerraformCommand`。 |

返回值：`PoolCommand` —— 绑定 `cwd` 的代理，其方法返回 `Future`。

### `submit(cwd, method, *args, **kwargs)`

底层接口：为 `cwd` 提交单条命令方法并返回其 `Future`。当需要动态指定方法名时使用。

参数：

| 参数 | 类型 | 说明 |
|---|---|---|
| `cwd` | `str \| None` | 命令的工作目录。 |
| `method` | `str` | 要调用的 `TerraformCommand` 方法名，例如 `"validate"`、`"apply"`。 |
| `*args` / `**kwargs` | | 转发给该方法的参数。 |

返回值：`concurrent.futures.Future` —— 结果为 `CommandResult`。

### `run(cmd, args=None, options=None, chdir=None, check=False, json=False)`

镜像 `TerraformCommand.run()`，但返回 `Future` 而非阻塞等待。其 `Future` 结果为
`(retcode, stdout, stderr)` 元组。参数含义与 `TerraformCommand.run()` 相同。

返回值：`concurrent.futures.Future` —— 结果为 `(retcode, stdout, stderr)` 元组。

### `map(method, cwds, *args, **kwargs)`

将 `method` 并行地分发到 `cwds` 中的每个目录，按 `cwds` 给定的顺序返回结果迭代器，
语义与 `concurrent.futures.Executor.map` 一致。相同的 `*args` / `**kwargs` 会传给每条
命令。迭代过程中遇到的第一个命令错误会被重新抛出。

参数：

| 参数 | 类型 | 说明 |
|---|---|---|
| `method` | `str` | 要在每个目录上调用的 `TerraformCommand` 方法名。 |
| `cwds` | `Iterable[str]` | 工作目录集合，每个目录对应一个 worker。 |
| `*args` / `**kwargs` | | 传给每条命令的相同参数。 |

返回值：`Iterator` —— 按顺序产出各目录的 `CommandResult`。

### `shutdown(wait=True, *, cancel_futures=False)`

关闭底层执行器与 worker 管理器。

参数：

| 参数 | 类型 | 说明 |
|---|---|---|
| `wait` | `bool` | 是否等待已提交的任务执行完成。 |
| `cancel_futures` | `bool` | 是否取消尚未开始执行的 future。 |

### 上下文管理器

`TerraformPool` 支持 `with` 语句。退出 `with` 块时会自动调用 `shutdown(wait=True)`。

```python
with TerraformPool(max_workers=4) as pool:
    ...
# 退出时自动关闭进程池
```

### `PoolCommand` 代理

由 `pool.command(cwd)` 返回。它镜像 `TerraformCommand` 的全部公开命令方法（如
`init`、`validate`、`plan`、`apply` 等），但每个方法都返回 `concurrent.futures.Future`
而非直接返回结果。对返回的 future 调用 `cancel()` 即可请求取消（详见上文「取消」一节）。

::: libterraform.pool.TerraformPool
    options:
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
