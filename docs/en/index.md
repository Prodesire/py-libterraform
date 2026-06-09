# Python libterraform

`libterraform` is a Python binding for Terraform. It bundles Terraform as a
shared library and exposes Python APIs for running Terraform CLI commands and
parsing Terraform configuration directories.

## What It Provides

- `TerraformCommand` for invoking Terraform commands from Python.
- `TerraformConfig` for loading `.tf` and `.tf.json` files into Terraform's
  internal module representation.
- Wheels that include the Terraform shared library, so callers do not need a
  separate `terraform` executable on `PATH`.

## Start Here

- [Installation](installation.md)
- [Quick Start](quickstart.md)
- [API Reference](api/index.md)
- [Development Guide](development.md)
- [Version Comparison](#version-comparison)

## Version Comparison

| libterraform | Terraform |
|---|---|
| [0.12.0](https://pypi.org/project/libterraform/0.12.0/) | [1.12.2](https://github.com/hashicorp/terraform/tree/v1.12.2) |
| [0.11.0](https://pypi.org/project/libterraform/0.11.0/) | [1.11.4](https://github.com/hashicorp/terraform/tree/v1.11.4) |
| [0.10.0](https://pypi.org/project/libterraform/0.10.0/) | [1.10.5](https://github.com/hashicorp/terraform/tree/v1.10.5) |
| [0.9.0](https://pypi.org/project/libterraform/0.9.0/) | [1.9.8](https://github.com/hashicorp/terraform/tree/v1.9.8) |
| [0.8.0](https://pypi.org/project/libterraform/0.8.0/) | [1.8.4](https://github.com/hashicorp/terraform/tree/v1.8.4) |
| [0.7.0](https://pypi.org/project/libterraform/0.7.0/) | [1.6.6](https://github.com/hashicorp/terraform/tree/v1.6.6) |
| [0.6.0](https://pypi.org/project/libterraform/0.6.0/) | [1.5.7](https://github.com/hashicorp/terraform/tree/v1.5.7) |
| [0.5.0](https://pypi.org/project/libterraform/0.5.0/) | [1.3.0](https://github.com/hashicorp/terraform/tree/v1.3.0) |
| [0.4.0](https://pypi.org/project/libterraform/0.4.0/) | [1.2.2](https://github.com/hashicorp/terraform/tree/v1.2.2) |
| [0.3.1](https://pypi.org/project/libterraform/0.3.1/) | [1.1.7](https://github.com/hashicorp/terraform/tree/v1.1.7) |

## Runtime Constraints

`TerraformCommand` is safe to call from multiple Python threads, but Terraform
CLI execution is serialized inside the shared library. Terraform still uses
process-wide state such as the current working directory, stdio, checkpoint
state, and plugin client cleanup, so true parallel Terraform operations require
separate processes.

Terraform operations can still affect real infrastructure, so use `apply`,
`destroy`, state commands, imports, and tests with the same caution as the
Terraform CLI.
