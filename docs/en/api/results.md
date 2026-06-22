# Results & Streaming

Structured result types returned by `plan()` / `apply()` and the streaming
helpers. Import them from the package root:

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

## Result types

`plan()` returns a `PlanResult` and `apply()` / `destroy()` return an
`ApplyResult`. Both subclass `CommandResult`, so `.retcode`, `.value` and
`.error` are unchanged, and add lazily-parsed structured views over the `-json`
output (empty when `json=False`).

::: libterraform.cli.PlanResult
    options:
      heading_level: 3
      members: false

`PlanResult` adds: `changes` (`list[ResourceChange]`), `drift`
(`list[ResourceChange]`, resources changed outside Terraform), `summary`
(`ChangeSummary`) and `outputs` (`list[OutputChange]`).

::: libterraform.cli.ApplyResult
    options:
      heading_level: 3
      members: false

`ApplyResult` adds: `changes` (`list[ResourceChange]`), `summary`
(`ChangeSummary`) and `outputs` (`list[OutputChange]`).

## Models

The structured properties return these dataclasses.

::: libterraform.models.ResourceChange
    options:
      heading_level: 3
      members: false

| Field | Type | Description |
|---|---|---|
| `address` | `str` | Resource address, e.g. `module.app.aws_instance.web`. |
| `action` | `str` | Terraform action: `create`, `update`, `delete`, `replace`, `read`, `import`, `move`, `forget` or `no-op`. |
| `resource_type` | `str` | Resource type, e.g. `aws_instance`. |
| `name` | `str` | Resource name. |
| `module` | `str` | Module path (empty for the root module). |
| `provider` | `Optional[str]` | Implied provider. |

::: libterraform.models.ChangeSummary
    options:
      heading_level: 3
      members: false

| Field | Type | Description |
|---|---|---|
| `add` | `int` | Resources to add. |
| `change` | `int` | Resources to change. |
| `remove` | `int` | Resources to remove. |
| `import_` | `int` | Resources to import (`import` is a Python keyword). |
| `operation` | `str` | `plan` or `apply`. |

::: libterraform.models.OutputChange
    options:
      heading_level: 3
      members: false

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Output name. |
| `action` | `str` | Change action for the output. |
| `sensitive` | `bool` | Whether the output is sensitive. |

## Streaming

The `stream()` / `plan_stream()` / `apply_stream()` methods return a
`TerraformStream`. Iterating it yields parsed `-json` events (or text lines when
`json=False`); after iteration, `retcode` and `stderr` are set. Use it as a
context manager (or call `close()`) to stop early, and `cancel()` to request
cooperative cancellation.

::: libterraform.cli.TerraformStream
    options:
      heading_level: 3
      members: false
