# 异常

从 `libterraform.exceptions` 导入异常：

```python
from libterraform.exceptions import LibTerraformError, TerraformCommandError
```

## 异常类型

### `LibTerraformError`

本包的基础异常类型。配置解析和命令执行相关异常都会继承它。

### `TerraformCommandError`

继承自 `LibTerraformError`。当 `TerraformCommand.run()` 启用 `check=True`，
且 Terraform 返回码不是 `0` 或 `2` 时抛出。

属性：

| 属性 | 类型 | 说明 |
|---|---|---|
| `retcode` | `int` | Terraform 返回码。 |
| `cmd` | `list` | 实际执行的 Terraform 参数列表。 |
| `stdout` | `str` | Terraform stdout。 |
| `stderr` | `str` | Terraform stderr。 |

### `TerraformFdReadError`

继承自 `LibTerraformError`。当 `TerraformCommand.run()` 无法读取 stdout
或 stderr 时抛出。

属性：

| 属性 | 类型 | 说明 |
|---|---|---|
| `fd` | `int` | 读取失败的文件描述符。 |
