# Plan 结果与流式输出

`plan()` 和 `apply()` 会返回结构化结果，流式方法则在命令运行过程中实时透传 Terraform
输出。两者都基于 Terraform 的 `-json` 输出。

下面的代码片段针对一个最小模块运行，无需云凭证，也不会下载任何 provider：

```python
import os
import tempfile

module_dir = tempfile.mkdtemp()
with open(os.path.join(module_dir, "main.tf"), "w") as f:
    f.write(
        '''
        resource "terraform_data" "a" {
          input = "x"
        }

        output "id" {
          value = terraform_data.a.id
        }
        '''
    )

from libterraform import TerraformCommand

cli = TerraformCommand(module_dir)
cli.init(check=True)
```

## 结构化结果

`plan()` 返回 `PlanResult`，`apply()` / `destroy()` 返回 `ApplyResult`。两者都是
`CommandResult` 的子类，因此 `.retcode`、`.value`、`.error` 与之前完全一致，并在其上
新增了结构化视图：

```python
result = cli.plan(check=True)

for change in result.changes:               # list[ResourceChange]
    print(change.address, change.action)    # terraform_data.a create

print(result.summary.add, result.summary.change, result.summary.remove)  # 1 0 0
print([o.name for o in result.outputs])     # ['id']
print(result.drift)                         # 在 Terraform 之外被修改的资源
```

`apply()` 以同样的方式暴露已应用的资源以及 apply 汇总：

```python
applied = cli.apply(auto_approve=True, input=False, check=True)

print([c.address for c in applied.changes])   # ['terraform_data.a']
print(applied.summary.operation)              # apply
```

`ResourceChange` 包含 `address`、`action`（Terraform 的动作：`create`、`update`、
`delete`、`replace` 等）、`resource_type`、`name`、`module` 和 `provider`。当
`json=False` 时结构化属性为空；原始文本仍保存在 `.value` 中。

## 流式输出

`plan_stream()` 和 `apply_stream()`（以及通用的 `stream()`）返回一个
`TerraformStream`，在命令运行时产出输出——默认产出解析后的 `-json` 事件，`json=False`
时产出原始文本行。这样长耗时的 `apply` 过程是可见的，而不必等整条命令结束：

```python
with cli.apply_stream(auto_approve=True) as stream:
    for event in stream:
        if event.get("type") == "apply_complete":
            print("applied", event["hook"]["resource"]["addr"])

print(stream.retcode)
```

迭代结束后，`stream.retcode` 与 `stream.stderr` 会被填充。传入 `check=True` 可在失败时
于结束处抛出 `TerraformCommandError`。将流用作上下文管理器（或调用 `close()`）可提前停止
长耗时命令；`cancel()` 显式请求 Terraform 的协作式 shutdown。

### 异步流式

`AsyncTerraformCommand` 以异步迭代器的形式暴露相同的方法，因此 asyncio 应用可以用
`async for` 消费 Terraform 输出：

```python
from libterraform import AsyncTerraformCommand

async_cli = AsyncTerraformCommand(module_dir)
async for event in async_cli.apply_stream(auto_approve=True):
    print(event.get("@message"))
```

取消消费端的 task 会请求对该 run 的协作式取消。

完整 API 见[结果与流式](api/results.md)。
