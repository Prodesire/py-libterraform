# AsyncTerraformCommand

从包根路径导入 `AsyncTerraformCommand`：

```python
from libterraform import AsyncTerraformCommand
```

`AsyncTerraformCommand` 为 `TerraformCommand` 提供 asyncio 兼容 API。它镜像同步命令
方法，并把阻塞的 Terraform 调用放到 worker thread 中执行，因此调用方可以
`await` Terraform 操作，而不会阻塞 event loop。

## 执行模型

`AsyncTerraformCommand` 不会让同一个 Python 进程内的 Terraform CLI 调用变成真正并行。
Terraform 仍然使用进程级全局状态，因此共享库内部仍会串行执行 CLI 调用。如需真正
并行的 Terraform 操作，请使用多个进程隔离。

如果 coroutine 被取消，等待中的 task 会被取消，但该 API 不会直接终止已经在线程
中运行的 Terraform 调用。`AsyncTerraformCommand` 会向 Terraform 的 shutdown channel 发送协作式取消
请求，然后重新抛出 `asyncio.CancelledError`。Terraform 或 provider 仍可能需要一些
时间从自己的 shutdown 流程中返回。

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

如果应用需要使用自己的线程池，可以传入 executor：

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=1) as executor:
    cli = AsyncTerraformCommand("path/to/terraform/module", executor=executor)
    validation = await cli.validate(check=True)
```

取消请求会限定到该 coroutine 启动的 Terraform run：

```python
task = asyncio.create_task(cli.apply(auto_approve=True))
task.cancel()
```

这会请求 Terraform 通过正常 interrupt 处理停止；它不会直接终止 worker thread。

::: libterraform.async_cli.AsyncTerraformCommand
    options:
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
