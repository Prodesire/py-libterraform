# Exceptions

Import exceptions from `libterraform.exceptions`:

```python
from libterraform.exceptions import LibTerraformError, TerraformCommandError
```

## Exception Types

### `LibTerraformError`

Base exception type for the package. All configuration parsing and command
execution exceptions inherit from it.

### `TerraformCommandError`

Inherits from `LibTerraformError`. Raised when `TerraformCommand.run()` is
called with `check=True` and the process returns a non-zero exit status
(other than `2`).

Attributes:

| Attribute | Type | Description |
|---|---|---|
| `retcode` | `int` | Terraform return code. |
| `cmd` | `list` | The actual Terraform argument list executed. |
| `stdout` | `str` | Terraform stdout. |
| `stderr` | `str` | Terraform stderr. |

### `TerraformFdReadError`

Inherits from `LibTerraformError`. Raised when `TerraformCommand.run()`
cannot read stdout or stderr.

Attributes:

| Attribute | Type | Description |
|---|---|---|
| `fd` | `int` | The file descriptor that failed to read. |
