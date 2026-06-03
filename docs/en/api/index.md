# API Reference

The public package exports:

```python
from libterraform import TerraformCommand, TerraformConfig
```

Exception classes are available from `libterraform.exceptions`.

## Pages

- [TerraformCommand](terraform-command.md) covers command execution,
  `CommandResult`, option conversion, JSON parsing, and Terraform CLI helper
  methods.
- [TerraformConfig](terraform-config.md) covers Terraform configuration parsing.
- [Exceptions](exceptions.md) covers package exception types.

The reference pages are generated from the Python source and docstrings with
mkdocstrings.
