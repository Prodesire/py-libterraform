# Quick Start

## Run Terraform Commands

Create a `TerraformCommand` for a Terraform module directory:

```python
from libterraform import TerraformCommand

cli = TerraformCommand("path/to/terraform/module")
```

Initialize the module and validate it:

```python
cli.init(check=True)
validation = cli.validate(check=True)

print(validation.retcode)
print(validation.value)
```

Generate a plan:

```python
plan = cli.plan(check=True)

for event in plan.value:
    print(event.get("@level"), event.get("@message"))
```

By default, methods that support JSON output parse stdout into Python values.
Pass `json=False` to keep Terraform's text output:

```python
version = cli.version(json=False)
print(version.value)
```

## Pass Terraform Options

Python keyword arguments are converted into Terraform CLI flags:

```python
plan = cli.plan(
    detailed_exitcode=True,
    vars={"environment": "dev"},
    target=["module.network", "module.app"],
)
```

`TerraformCommand` converts underscores to hyphens, so `detailed_exitcode` maps to
`-detailed-exitcode`.

## Parse Terraform Configuration

Use `TerraformConfig` when you need Terraform's parsed representation of a
configuration directory:

```python
from libterraform import TerraformConfig

module, diagnostics = TerraformConfig.load_config_dir("path/to/terraform/module")

print(module["ManagedResources"].keys())
print(diagnostics)
```

## Use Asyncio

Use `AsyncTerraformCommand` when an asyncio application needs to await
Terraform operations without blocking the event loop:

```python
from libterraform import AsyncTerraformCommand

cli = AsyncTerraformCommand("path/to/terraform/module")
validation = await cli.validate(check=True)
```

Terraform CLI execution is still serialized inside the shared library. Use
separate processes for true parallel Terraform operations.
Cancelling the coroutine requests Terraform's cooperative shutdown path; it
does not terminate the worker thread directly.

See the [API Reference](api/index.md) for generated interface documentation.
