# API Reference

The public package exports:

```python
from libterraform import (
    AsyncTerraformCommand,
    TerraformCommand,
    TerraformConfig,
    TerraformPool,
)
```

Exception classes are available from `libterraform.exceptions`.

## Pages

- [TerraformCommand](terraform-command.md) covers command execution,
  `CommandResult`, option conversion, JSON parsing, and Terraform CLI helper
  methods.
- [AsyncTerraformCommand](async-terraform-command.md) covers asyncio-compatible
  command execution for asyncio applications.
- [TerraformPool](terraform-pool.md) covers process-based parallel execution of
  Terraform commands.
- [TerraformConfig](terraform-config.md) covers Terraform configuration parsing.
- [Exceptions](exceptions.md) covers package exception types.

The reference pages are generated from the Python source and docstrings with
mkdocstrings.
