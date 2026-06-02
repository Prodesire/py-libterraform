# Release Line Governance Design

## Goal

Manage libterraform as a set of Terraform-minor compatibility lines. Each libterraform minor line owns one Terraform minor line, so `0.9.x` adapts Terraform `1.9.x`, `0.10.x` adapts Terraform `1.10.x`, and patch releases stay inside their line.

## Branch Model

- `main` is the development branch for the next Terraform minor adaptation.
- `release/0.x` is the maintenance branch for libterraform `0.x.y`.
- Tags are created from the matching release branch, using `v0.x.y`.
- A release branch must not cross Terraform minor boundaries. For example, `release/0.9` may move from Terraform `1.9.8` to `1.9.9`, but never to `1.10.x`.
- Common fixes land on `main` first, then are cherry-picked to active release branches.
- All release branches may remain in the repository, but only the latest two release lines are actively maintained by default.

## Version Meaning

- `libterraform` minor version means "adapted to this Terraform minor line".
- `libterraform` patch version means "bugfix or Terraform patch update within the same Terraform minor line".
- The package version alone is not the source of truth. A machine-readable release matrix records the exact Terraform and go-plugin versions for each line.

## Compatibility Data

The repository owns a `release-matrix.json` file. It records:

- libterraform minor line and current package version
- Terraform minor and exact Terraform patch version
- go-plugin version required by the Terraform tag
- release branch name
- status and maintenance mode

Tests and release scripts validate the matrix against the checked-out repository state.

## Adaptation Requirements

Publishing a new minor release requires more than moving the Terraform submodule. The release must verify:

- Terraform CLI wrapper behavior still matches command and flag expectations.
- JSON outputs used by Python wrappers are still parsed correctly.
- `TerraformConfig.load_config_dir()` still matches Terraform internal struct changes.
- New Terraform features that affect the Python API have fixtures or tests.
- The build hook replaces the exact go-plugin module version required by `terraform/go.mod`.

## Initial Implementation Scope

The first implementation adds governance foundations and prepares the current `0.8.x` line:

- Add `release-matrix.json`.
- Add a release policy document.
- Add a verification script and tests for matrix consistency.
- Add exact Terraform version tests.
- Make `hatch_build.py` derive the go-plugin replacement version dynamically.
- Make CI initialize submodules before selecting Go from `terraform/go.mod`.

The actual `0.9.0` release happens after these guardrails pass.

