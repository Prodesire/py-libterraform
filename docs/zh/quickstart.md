# 快速开始

## 准备一个模块

本页的示例都针对一个真实的 Terraform 模块目录运行。如果手头已有模块，直接指向它
即可；否则可用下面这段代码创建一个随处可运行的最小模块——它使用 Terraform 内置的
`terraform_data` 资源，无需云凭证，也不会下载任何 provider：

```python
import os
import tempfile

module_dir = tempfile.mkdtemp()
with open(os.path.join(module_dir, "main.tf"), "w") as f:
    f.write(
        '''
        variable "environment" {
          type    = string
          default = "dev"
        }

        resource "terraform_data" "example" {
          input = var.environment
        }

        output "environment" {
          value = terraform_data.example.output
        }
        '''
    )
```

下面所有示例都以 `module_dir` 作为工作目录。

## 执行 Terraform 命令

为模块目录创建 `TerraformCommand`，然后初始化并校验：

```python
from libterraform import TerraformCommand

cli = TerraformCommand(module_dir)

cli.init(check=True)
validation = cli.validate(check=True)

print(validation.value["valid"])  # True
```

`check=True` 会在 Terraform 报告失败时抛出 `TerraformCommandError`，让错误立即暴露，
而不是隐藏在返回码里。

生成 plan。支持 JSON 输出的方法会返回解析后的 Python 值，因此 `plan.value` 是
Terraform 日志事件组成的列表：

```python
plan = cli.plan(check=True)

for event in plan.value:
    print(event.get("@level"), event.get("@message"))
```

应用 plan。`auto_approve` 跳过交互式确认，`input=False` 关闭交互式输入，这通常是
自动化场景所需要的：

```python
apply = cli.apply(auto_approve=True, input=False, check=True)
print(apply.retcode)  # 0
```

传入 `json=False` 可以保留 Terraform 的纯文本输出，而非解析后的 JSON：

```python
version = cli.version(json=False)
print(version.value)
```

## 传递 Terraform 选项

Python 关键字参数会被转换为 Terraform CLI flag。下划线会转换为连字符，因此
`detailed_exitcode` 会映射为 `-detailed-exitcode`：

```python
plan = cli.plan(
    detailed_exitcode=True,
    vars={"environment": "prod"},
)
```

转换规则覆盖了常见的 flag 形态：

- `True` / `False` 会转换为 Terraform 的小写布尔值，例如 `lock=False` 对应 `-lock=false`。
- dict 会展开为多个 `key=value` flag，例如 `vars={"a": "1", "b": "2"}` 对应 `-var=a=1 -var=b=2`。
- list 会展开为同名 flag 的多次出现，例如 `var_files=["a.tfvars", "b.tfvars"]`。

## 解析 Terraform 配置

`TerraformConfig` 在不执行命令的情况下，返回 Terraform 自身对配置目录的解析结果：

```python
from libterraform import TerraformConfig

module, diagnostics = TerraformConfig.load_config_dir(module_dir)

print(list(module["ManagedResources"]))  # ['terraform_data.example']
print(diagnostics)
```

## 使用 asyncio

`AsyncTerraformCommand` 让 asyncio 应用可以等待 Terraform 操作而不阻塞 event loop：

```python
from libterraform import AsyncTerraformCommand

cli = AsyncTerraformCommand(module_dir)
validation = await cli.validate(check=True)
```

默认情况下调用运行在 worker thread 中，因此 Terraform CLI 执行在共享库内部仍是
串行的。取消 coroutine 会请求 Terraform 进入协作式 shutdown 流程，但不会直接终止
worker thread。

要让 Terraform 命令真正同时执行——跨多个模块、同步或异步——请见
[并行执行](parallel-execution.md)，其中介绍了 `TerraformPool` 以及如何让
`AsyncTerraformCommand` 运行在进程池上。

完整接口见 [API 参考](api/index.md)。
