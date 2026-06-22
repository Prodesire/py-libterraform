# Quick Start

## Prepare a module

The examples on this page run against a real Terraform module directory. If you
already have one, point at it directly. Otherwise, this snippet creates a minimal
module that runs anywhere — it uses Terraform's built-in `terraform_data`
resource, so it needs no cloud credentials and downloads no providers:

```python
import os
import tempfile

module_dir = tempfile.mkdtemp()
with open(os.path.join(module_dir, "main.tf"), "w") as f:
    f.write(
        '''
        variable "environment" {
          type    = string
          default = "dev"
        }

        resource "terraform_data" "example" {
          input = var.environment
        }

        output "environment" {
          value = terraform_data.example.output
        }
        '''
    )
```

Every example below uses `module_dir` as the working directory.

## Run Terraform commands

Create a `TerraformCommand` for the module directory, then initialize and
validate it:

```python
from libterraform import TerraformCommand

cli = TerraformCommand(module_dir)

cli.init(check=True)
validation = cli.validate(check=True)

print(validation.value["valid"])  # True
```

`check=True` raises `TerraformCommandError` when Terraform reports failure, so
errors surface immediately instead of hiding in a return code.

Generate a plan. Methods that support JSON output return parsed Python values, so
`plan.value` is a list of Terraform's log events:

```python
plan = cli.plan(check=True)

for event in plan.value:
    print(event.get("@level"), event.get("@message"))
```

Apply the plan. `auto_approve` skips the interactive prompt and `input=False`
disables interactive input, which is what most automation wants:

```python
apply = cli.apply(auto_approve=True, input=False, check=True)
print(apply.retcode)  # 0
```

Pass `json=False` to keep Terraform's plain text output instead of parsed JSON:

```python
version = cli.version(json=False)
print(version.value)
```

## Pass Terraform options

Python keyword arguments become Terraform CLI flags. Underscores become hyphens,
so `detailed_exitcode` maps to `-detailed-exitcode`:

```python
plan = cli.plan(
    detailed_exitcode=True,
    vars={"environment": "prod"},
)
```

The conversion rules cover the common flag shapes:

- `True` / `False` become Terraform's lowercase booleans, e.g. `lock=False` is `-lock=false`.
- A dict expands to repeated `key=value` flags, e.g. `vars={"a": "1", "b": "2"}` is `-var=a=1 -var=b=2`.
- A list expands to a repeated flag, e.g. `var_files=["a.tfvars", "b.tfvars"]`.

## Parse Terraform configuration

`TerraformConfig` returns Terraform's own parsed view of a configuration
directory, without running a command:

```python
from libterraform import TerraformConfig

module, diagnostics = TerraformConfig.load_config_dir(module_dir)

print(list(module["ManagedResources"]))  # ['terraform_data.example']
print(diagnostics)
```

## Use asyncio

`AsyncTerraformCommand` lets an asyncio application await Terraform operations
without blocking the event loop:

```python
from libterraform import AsyncTerraformCommand

cli = AsyncTerraformCommand(module_dir)
validation = await cli.validate(check=True)
```

By default the call runs in a worker thread, so Terraform CLI execution is still
serialized inside the shared library. For true parallel Terraform operations, see
[Parallel Execution](parallel-execution.md). Cancelling the coroutine requests
Terraform's cooperative shutdown path; it does not terminate the worker thread
directly.

See the [API Reference](api/index.md) for the generated interface documentation.
