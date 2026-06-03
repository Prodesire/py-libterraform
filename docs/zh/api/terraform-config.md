# TerraformConfig

从包根路径导入 `TerraformConfig`：

```python
from libterraform import TerraformConfig
```

`TerraformConfig.load_config_dir()` 会解析目录中的 `.tf` 和 `.tf.json`
文件，并返回 Terraform 合并后的模块表示和诊断信息。

## 方法

### `load_config_dir(path)`

解析 Terraform 配置目录，把目录中的 `.tf` 和 `.tf.json` 文件合并为 Terraform
内部 Module 表示。`.tf` 文件使用 HCL 原生语法解析，`.tf.json` 文件使用 HCL
JSON 语法解析。

参数：

| 参数 | 类型 | 说明 |
|---|---|---|
| `path` | `str` | Terraform 配置目录路径。 |

返回值：`Tuple[dict, dict]`

| 返回值 | 类型 | 说明 |
|---|---|---|
| `module` | `dict` | Terraform 合并后的 Module 表示。 |
| `diagnostics` | `dict` | Terraform 解析配置时返回的诊断信息。 |

异常：

- `LibTerraformError` — 如果目录不存在、无法打开，或底层 Terraform 返回错误。
