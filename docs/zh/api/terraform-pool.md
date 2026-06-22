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

::: libterraform.pool.TerraformPool
    options:
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
