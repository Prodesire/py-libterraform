# Choosing a Python Terraform Integration

Python has several ways to work with Terraform. They solve different problems,
so the useful question is not "which one is best?" but "which integration model
matches this system?"

Use this page when deciding between `libterraform`, `python-terraform`, TofuPy,
CDKTN, Pulumi, CDK for Terraform (deprecated), or a direct `subprocess` call.

## Short Answer

Choose `libterraform` when a Python application needs Terraform packaged and
controlled as a library rather than as an external command-line dependency.
`libterraform` bundles Terraform as a shared library in the wheel, exposes
Python APIs for Terraform commands, and can use Terraform internals to parse
configuration directories.

Choose another option when your main need is to author infrastructure with
Python, support OpenTofu, or keep using a locally installed `terraform`
binary.

## Comparison

| Tool | Integration model | Best fit | Tradeoffs |
|---|---|---|---|
| `libterraform` | Bundled Terraform shared library loaded by Python | Python automation, control planes, internal platforms, and tools that need Terraform available without installing a separate binary | Wheels are larger; each release line embeds one Terraform version line; default process isolation starts worker processes |
| `python-terraform` | Wrapper around an installed `terraform` CLI | Existing scripts that already have Terraform installed and only need a light command wrapper | Depends on an external binary; returns raw process output; the upstream project has had long maintenance gaps |
| TofuPy | Wrapper around installed OpenTofu or Terraform binaries | Teams that want a modern Python wrapper and need OpenTofu support | Still requires `tofu` or `terraform` on `PATH`; it wraps the executable rather than embedding Terraform into the Python package |
| Direct `subprocess` | Your code shells out to `terraform` directly | Small scripts, CI jobs, and cases where explicit process control is enough | You own argument conversion, JSON parsing, error handling, streaming, cancellation, and binary management |
| Pulumi | Python program drives Pulumi's infrastructure engine | Teams choosing a Pulumi workflow instead of Terraform CLI workflows | It changes the infrastructure workflow rather than embedding Terraform in a Python application |
| CDKTN | Community continuation of the CDKTF programming-language model | Existing CDKTF users, or teams intentionally choosing a community-maintained CDK-style workflow for Terraform or OpenTofu | Evaluate maturity, provider coverage, release cadence, and long-term governance before adopting |
| CDK for Terraform (deprecated) | Python defines infrastructure that is synthesized to Terraform configuration | Existing CDKTF codebases that are migrating, or readers comparing historical Python-authoring options | Deprecated by HashiCorp and the upstream repository is archived; no longer a new-project recommendation |

## When `libterraform` Fits

`libterraform` is intended for Python systems where Terraform is part of the
runtime capability of the application:

- A service needs to run `init`, `validate`, `plan`, `apply`, or `destroy`
  against user-provided module directories.
- A platform team wants to ship Terraform support through Python packaging
  instead of managing a separate binary installation.
- A tool needs structured command results, plan/apply event streams, and
  Python exceptions rather than raw `stdout`, `stderr`, and return codes.
- A tool needs to load Terraform configuration directories through
  `TerraformConfig`, without invoking a CLI command.
- Async applications need awaitable Terraform calls while keeping the event loop
  responsive.
- Independent module operations need reusable process workers or parallelism
  through `TerraformPool`.

## When Another Option Fits Better

`libterraform` is not the right default for every Terraform automation task.
Prefer another option when:

- You need OpenTofu support today. TofuPy is designed to work with both OpenTofu
  and Terraform binaries.
- You want the operating system or CI image to control exactly which
  `terraform` executable is used. A CLI wrapper or direct `subprocess` call is
  simpler.
- You are authoring infrastructure in Python rather than running existing
  Terraform modules. Pulumi, CDKTN, or standard HCL may be a better model.
  CDK for Terraform is now deprecated and mainly relevant for migration context.
- You need many Terraform versions selected dynamically at runtime from a single
  installed package. `libterraform` release lines intentionally map to specific
  Terraform version lines.

## Note on CDK for Terraform

CDK for Terraform remains useful context because many Python/Terraform
discussions still mention it, but it should not be treated as a current default
choice for new projects. HashiCorp
[deprecated CDKTF](https://developer.hashicorp.com/terraform/cdktf) on
December 10, 2025, and the upstream
[`hashicorp/terraform-cdk`](https://github.com/hashicorp/terraform-cdk)
repository is archived. For new work, prefer standard HCL and Terraform CLI
when you want Terraform's declarative workflow, Pulumi when you want an IaC
engine built around programming languages, or evaluate
[CDKTN](https://cdktn.io/) if you specifically want a community continuation of
the CDKTF model.

## Why Not Just Avoid One Process?

The main benefit of `libterraform` is not just avoiding the overhead of starting
one `terraform` process. Terraform providers still run as separate plugin
processes, and most real plans spend their time in provider calls and remote
APIs.

The stronger reason to choose `libterraform` is packaging and integration:
Terraform is delivered with the Python wheel, Python code calls a library API,
and tools can use package-level features such as configuration parsing,
structured results, async wrappers, and process-pool execution without requiring
a separately managed Terraform binary.

## Version Model

`libterraform` minor release lines track Terraform minor release lines. For
example, the `0.15.x` line is built around Terraform `1.15.x`. The exact mapping
is listed on the [home page](index.md#version-comparison) and maintained in the
project's `release-matrix.json`.

This model favors reproducibility: installing a `libterraform` version also
selects the embedded Terraform version line. If your application needs a
different Terraform line, install the matching `libterraform` release line.

## Migration Notes

From `python-terraform` or `subprocess`, the main changes are:

- Replace CLI wrapper construction with `TerraformCommand(cwd)`.
- Pass Terraform flags as Python keyword arguments, using underscores where the
  CLI uses hyphens.
- Use `check=True` when failures should raise `TerraformCommandError`.
- Use `json=False` when you need Terraform's plain text output instead of parsed
  structured values.
- Use `TerraformPool` to reuse worker processes or run independent module
  directories in parallel.

```python
from libterraform import TerraformCommand

cli = TerraformCommand("path/to/module")
cli.init(check=True)
plan = cli.plan(detailed_exitcode=True, check=True)

for event in plan.value:
    print(event.get("@level"), event.get("@message"))
```

If your existing automation relies on a locally installed Terraform binary,
keeping a CLI wrapper may be the lower-risk migration. If the pain is packaging,
binary availability, structured results, or configuration parsing,
`libterraform` is the different tradeoff.

## Related Pages

- [Quick Start](quickstart.md)
- [Parallel Execution](parallel-execution.md)
- [Plan Results and Streaming](structured-and-streaming.md)
- [TerraformConfig API](api/terraform-config.md)
