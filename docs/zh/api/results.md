# 结果与流式

`plan()` / `apply()` 返回的结构化结果类型，以及流式辅助类型。从包根路径导入：

```python
from libterraform import (
    ApplyResult,
    ChangeSummary,
    OutputChange,
    PlanResult,
    ResourceChange,
    TerraformStream,
)
```

## 结果类型

`plan()` 返回 `PlanResult`，`apply()` / `destroy()` 返回 `ApplyResult`。两者都是
`CommandResult` 的子类，因此 `.retcode`、`.value`、`.error` 保持不变，并在 `-json`
输出之上新增惰性解析的结构化视图（`json=False` 时为空）。

::: libterraform.cli.PlanResult
    options:
      heading_level: 3
      members: false
      show_root_full_path: false
      show_docstring_description: false

`PlanResult` 新增：`changes`（`list[ResourceChange]`）、`drift`
（`list[ResourceChange]`，在 Terraform 之外被修改的资源）、`summary`
（`ChangeSummary`）、`outputs`（`list[OutputChange]`）。

::: libterraform.cli.ApplyResult
    options:
      heading_level: 3
      members: false
      show_root_full_path: false
      show_docstring_description: false

`ApplyResult` 新增：`changes`（`list[ResourceChange]`）、`summary`
（`ChangeSummary`）、`outputs`（`list[OutputChange]`）。

## 数据模型

结构化属性返回以下数据类。

::: libterraform.models.ResourceChange
    options:
      heading_level: 3
      members: false
      show_root_full_path: false
      show_docstring_description: false

| 字段 | 类型 | 说明 |
|---|---|---|
| `address` | `str` | 资源地址，例如 `module.app.aws_instance.web`。 |
| `action` | `str` | Terraform 动作：`create`、`update`、`delete`、`replace`、`read`、`import`、`move`、`forget` 或 `no-op`。 |
| `resource_type` | `str` | 资源类型，例如 `aws_instance`。 |
| `name` | `str` | 资源名称。 |
| `module` | `str` | 模块路径（根模块为空）。 |
| `provider` | `Optional[str]` | 推断出的 provider。 |

::: libterraform.models.ChangeSummary
    options:
      heading_level: 3
      members: false
      show_root_full_path: false
      show_docstring_description: false

| 字段 | 类型 | 说明 |
|---|---|---|
| `add` | `int` | 待新增的资源数。 |
| `change` | `int` | 待变更的资源数。 |
| `remove` | `int` | 待删除的资源数。 |
| `import_` | `int` | 待导入的资源数（`import` 是 Python 关键字）。 |
| `operation` | `str` | `plan` 或 `apply`。 |

::: libterraform.models.OutputChange
    options:
      heading_level: 3
      members: false
      show_root_full_path: false
      show_docstring_description: false

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | `str` | 输出名称。 |
| `action` | `str` | 该输出的变更动作。 |
| `sensitive` | `bool` | 该输出是否敏感。 |

## 流式

`stream()` / `plan_stream()` / `apply_stream()` 方法返回 `TerraformStream`。迭代它会
产出解析后的 `-json` 事件（`json=False` 时产出文本行）；迭代结束后会设置 `retcode`
与 `stderr`。将其用作上下文管理器（或调用 `close()`）可提前停止，`cancel()` 用于请求
协作式取消。

::: libterraform.cli.TerraformStream
    options:
      heading_level: 3
      members: false
      show_root_full_path: false
      show_docstring_description: false
