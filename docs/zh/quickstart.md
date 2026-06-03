# 快速开始

## 执行 Terraform 命令

为一个 Terraform 模块目录创建命令包装器：

```python
from libterraform import TerraformCommand

cli = TerraformCommand("path/to/terraform/module")
```

初始化并校验模块：

```python
cli.init(check=True)
validation = cli.validate(check=True)

print(validation.retcode)
print(validation.value)
```

生成 plan：

```python
plan = cli.plan(check=True)

for event in plan.value:
    print(event.get("@level"), event.get("@message"))
```

默认情况下，支持 JSON 输出的方法会把 stdout 解析为 Python 值。传入
`json=False` 可以保留 Terraform 的文本输出：

```python
version = cli.version(json=False)
print(version.value)
```

## 传递 Terraform 选项

Python 关键字参数会被转换为 Terraform CLI flag：

```python
plan = cli.plan(
    detailed_exitcode=True,
    vars={"environment": "dev"},
    target=["module.network", "module.app"],
)
```

包装器会把下划线转换为连字符，因此 `detailed_exitcode` 会映射为
`-detailed-exitcode`。

## 解析 Terraform 配置

当你需要 Terraform 对配置目录的解析结果时，可以使用 `TerraformConfig`：

```python
from libterraform import TerraformConfig

module, diagnostics = TerraformConfig.load_config_dir("path/to/terraform/module")

print(module["ManagedResources"].keys())
print(diagnostics)
```

完整接口见 [API 参考](api/index.md)。
