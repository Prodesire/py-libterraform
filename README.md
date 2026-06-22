<p align="center">
  <img src="docs/assets/py-libterraform-logo.png" alt="Python libterraform logo" width="180">
</p>

<h1 align="center">Python libterraform</h1>

<p align="center">
  <em>Python binding for <a href="https://www.terraform.io/">Terraform</a>. Bundles Terraform as a shared library so you can run Terraform commands and parse configurations from Python without a separate <code>terraform</code> binary.</em>
</p>

<p align="center">
  <a href="https://github.com/Prodesire/py-libterraform/actions/workflows/test.yml"><img src="https://github.com/Prodesire/py-libterraform/actions/workflows/test.yml/badge.svg" alt="Test"></a>
  <a href="https://pypi.python.org/pypi/libterraform"><img src="https://img.shields.io/pypi/v/libterraform.svg" alt="PyPI"></a>
  <a href="https://pypi.python.org/pypi/libterraform"><img src="https://img.shields.io/pypi/pyversions/libterraform.svg" alt="Python"></a>
  <a href="https://pypi.python.org/pypi/libterraform"><img src="https://img.shields.io/pypi/dm/libterraform" alt="Downloads"></a>
</p>

<p align="center">
  <strong>Language:</strong> English | <a href="README.zh-CN.md">中文</a>
</p>

> **Documentation:** https://prodesire.github.io/py-libterraform/

## Installation

```bash
pip install libterraform
```

> **Threading:** `TerraformCommand` can be called from multiple Python threads,
> but Terraform CLI execution is serialized inside the shared library because
> Terraform uses process-wide state. Use `TerraformPool` (or separate processes)
> if you need truly parallel Terraform operations.

## Usage

```python
from libterraform import TerraformCommand, TerraformConfig

# Run Terraform commands
cli = TerraformCommand("path/to/module")
cli.init(check=True)
cli.plan(check=True)

# Parse Terraform configuration
module, diagnostics = TerraformConfig.load_config_dir("path/to/module")
```

Asyncio applications can use `AsyncTerraformCommand` to await Terraform
operations without blocking the event loop:

```python
from libterraform import AsyncTerraformCommand

cli = AsyncTerraformCommand("path/to/module")
await cli.validate(check=True)
```

Use `TerraformPool` to run Terraform commands in parallel across worker
processes:

```python
from libterraform import TerraformPool

with TerraformPool(max_workers=4) as pool:
    for result in pool.map("validate", ["modules/a", "modules/b"], check=True):
        print(result.value["valid"])
```

The pool starts worker processes, so this must run under an
`if __name__ == "__main__":` guard. The
[Quick Start](https://prodesire.github.io/py-libterraform/quickstart/) creates a
runnable module in seconds, and
[Parallel Execution](https://prodesire.github.io/py-libterraform/parallel-execution/)
has a complete pool example.

## Contributing

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
make install        # Install dependencies and Git hooks
make build          # Build the shared library
make test           # Run tests
make lint           # Run linters
make doc-serve      # Preview documentation site
```

See the [Development Guide](https://prodesire.github.io/py-libterraform/development/) for details.
