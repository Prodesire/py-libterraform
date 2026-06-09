# TerraformCommand

Import `TerraformCommand` from the package root:

```python
from libterraform import TerraformCommand
```

Most high-level methods return a `CommandResult`.

## Threading

`TerraformCommand` can be called from multiple Python threads. Calls are
thread-safe, but Terraform CLI execution is serialized inside the shared
library because Terraform uses process-wide state. Use separate processes for
true parallel Terraform operations.

## CommandResult

`CommandResult` exposes:

- `retcode`: Terraform return code.
- `value`: parsed JSON or raw stdout, depending on the method and `json=`.
- `error`: stderr.
- `json`: whether stdout was parsed as JSON.

## Parameter Rules

### Common Parameters

Many `TerraformCommand` methods share the following keyword arguments:

| Parameter | Description |
|---|---|
| `check` | Whether to check the Terraform return code. When `True`, raises `TerraformCommandError` if the return code is not `0` or `2`. |
| `json` | Whether to request or parse JSON output. Methods that support JSON typically default to `True`. |
| `no_color` | Whether to add `-no-color` to suppress ANSI color codes in output. |
| `input` | Whether to allow interactive prompts. Automation scenarios typically set this to `False`. |
| `lock` | Whether to hold a state lock during the operation. |
| `lock_timeout` | Duration to wait when acquiring a state lock. |
| `vars` | A dict of Terraform variables, converted to multiple `-var=key=value` flags. |
| `var_files` | A list of variable files, converted to multiple `-var-file=...` flags. |
| `target` | Target resource address or list of addresses. |
| `parallelism` | Number of concurrent Terraform operations. |
| `state` | Path to the state file. |
| `options` | Additional Terraform options. Underscores are converted to hyphens, e.g. `detailed_exitcode` becomes `-detailed-exitcode`. |

### Option Conversion

- `True` / `False` are converted to Terraform's lowercase boolean strings.
- `...` (Ellipsis) is treated as a value-less flag, e.g. `{"json": ...}` produces `-json`.
- Lists are expanded to multiple flags with the same name.
- Dicts are expanded to `-name=key=value` form.

::: libterraform.cli.TerraformCommand
