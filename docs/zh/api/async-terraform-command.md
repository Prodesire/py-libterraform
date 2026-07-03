# AsyncTerraformCommand

从包根路径导入 `AsyncTerraformCommand`：

```python
from libterraform import AsyncTerraformCommand
```

`AsyncTerraformCommand` 为 `TerraformCommand` 提供 asyncio 兼容 API。它镜像同步命令
方法，并把阻塞的 Terraform 调用移出 event-loop thread，因此调用方可以 `await`
Terraform 操作，而不会阻塞 event loop。

## 执行模型

`AsyncTerraformCommand` 默认使用 `TerraformCommand` 的 process backend。Terraform CLI
调用会在受控 worker 进程中执行，因此 Terraform 的进程级全局状态不会泄漏到
event-loop 进程。只有在明确需要当前进程后端时，才使用 `backend="thread"`。如果需要
复用 worker 进程或让独立 Terraform 操作真正并行执行，可传入
[`TerraformPool`](terraform-pool.md) 作为 `pool`。

如果 coroutine 被取消，等待中的 task 会被取消，并且当前 backend 会被请求停止该
Terraform run。使用默认 process backend 时，worker 进程会被中断。使用
`backend="thread"` 时，该 API 不会直接终止 worker thread；`AsyncTerraformCommand`
会向 Terraform 的 shutdown channel 发送协作式取消请求，然后重新抛出
`asyncio.CancelledError`。Terraform 或 provider 仍可能需要一些时间从自己的 shutdown
流程中返回。

## 使用

```python
from libterraform import AsyncTerraformCommand

cli = AsyncTerraformCommand("path/to/terraform/module")

await cli.init(check=True)
plan = await cli.plan(check=True)
```

`AsyncTerraformCommand.run()` 接收与 `TerraformCommand.run()` 相同的命令参数：

```python
retcode, stdout, stderr = await AsyncTerraformCommand.run("version")
```

如果应用需要使用自己的线程池，可以传入 executor。它只控制阻塞 Python wrapper 在哪里
等待，不会把 Terraform 执行切换为 thread backend：

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=1) as executor:
    cli = AsyncTerraformCommand("path/to/terraform/module", executor=executor)
    validation = await cli.validate(check=True)
```

如果要显式使用当前进程后端，请传入 `backend="thread"`：

```python
cli = AsyncTerraformCommand("path/to/terraform/module", backend="thread")
validation = await cli.validate(check=True)
```

传入 `TerraformPool` 作为 `pool`，即可等待在 worker 进程中执行的命令，从而获得真正
并行的 Terraform 执行。`AsyncTerraformCommand.run()` 同样接受 `pool` 参数。pool 会
启动 worker 进程，因此该程序必须运行在 `if __name__ == "__main__":` 保护之下；完整
可运行的搭建方式见[并行执行](../parallel-execution.md)。

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

取消请求会限定到该 coroutine 启动的 Terraform run：

```python
task = asyncio.create_task(cli.apply(auto_approve=True))
task.cancel()
```

这会请求当前 backend 停止 Terraform。使用默认 process backend 时，worker 进程会被
中断；使用 `backend="thread"` 时，它不会直接终止 worker thread；使用 `pool` 后端时，
该请求会投递到运行该命令的 worker 进程。

::: libterraform.async_cli.AsyncTerraformCommand
    options:
      heading_level: 2
      members: false
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false

`TerraformCommand` 的每个公开方法都会被镜像为可等待的 coroutine
（`await async_cli.plan(...)`）。下面记录的是直接定义在 `AsyncTerraformCommand` 上的方法。

::: libterraform.async_cli.AsyncTerraformCommand.run
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false

不阻塞 event loop 地运行任意命令，其结果为 `(retcode, stdout, stderr)` 三元组。参数与
`TerraformCommand.run()` 相同；额外可传入 `executor`（线程池）或 `pool`
（`TerraformPool`，在 worker 进程中执行）。

::: libterraform.async_cli.AsyncTerraformCommand.stream
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false

流式命令的异步迭代器，语义见 `TerraformCommand.stream()`。用法：
`async for event in async_cli.stream("plan"): ...`。取消消费端的 task 会请求对该命令的
协作式取消。

::: libterraform.async_cli.AsyncTerraformCommand.plan_stream
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false

`terraform plan` 输出的异步迭代器。`vars` / `var_files` 与 `TerraformCommand.plan_stream()`
一致；其余关键字选项按 flag 转换。

::: libterraform.async_cli.AsyncTerraformCommand.apply_stream
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false

`terraform apply` 输出的异步迭代器。默认 `auto_approve=True`、`input=False`。`vars` /
`var_files` 与 `TerraformCommand.apply_stream()` 一致。
