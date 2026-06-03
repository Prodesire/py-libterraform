# Quick Start

## Run Terraform Commands

Create a command wrapper for a Terraform module directory:

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

The wrapper converts underscores to hyphens, so `detailed_exitcode` maps to
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

See the [API Reference](api/index.md) for generated interface documentation.
