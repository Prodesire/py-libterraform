# Development Guide

This project builds a Python package that bundles Terraform as a shared library.
The Python code lives under `src/libterraform`, while the Go sources needed to
build the shared library are assembled from `upstream/` and `native/go/` during
the wheel build.

## Requirements

- Python 3.9 through 3.14
- Go 1.21.5 or newer
- A C compiler for CGO
- `uv`

## Initial Setup

Initialize the upstream submodules:

```bash
git submodule init
git submodule update
```

Install Python development dependencies:

```bash
uv sync
```

The Makefile also installs the local Git hooks:

```bash
make install
```

## Build

Build the wheel before running tests that import `libterraform` from the source
tree, because `src/libterraform/__init__.py` loads the compiled shared library
at import time:

```bash
uv build --wheel
```

The Hatch build hook:

1. Copies `native/go/plugin_patch.go` into `upstream/go-plugin/`.
2. Adds a temporary `replace` directive for go-plugin in
   `upstream/terraform/go.mod`.
3. Copies `native/go/libterraform.go` into `upstream/terraform/`.
4. Runs `go build -buildmode=c-shared`.
5. Moves the resulting shared library into `src/libterraform/`.
6. Restores temporary upstream file changes.

To cross-build a macOS x86_64 shared library on macOS, set `TARGET_ARCH=amd64`.

## Test And Lint

Run the full test suite:

```bash
uv run pytest --color=yes
```

Or use Make:

```bash
make test
```

Run static checks:

```bash
make lint
```

Format Python files:

```bash
make format
```

The test suite uses Terraform fixtures under `tests/tf/`. Some tests exercise
real Terraform state behavior, so build first and inspect failing stderr before
assuming failures are Python-only.

## Documentation Site

The documentation site uses Zensical and mkdocstrings. English and Chinese are
built as separate Zensical projects and deployed under the same GitHub Pages
artifact.

Preview it locally:

```bash
make doc-serve
```

Build it with the same strictness used by CI:

```bash
make docs-build
```

The generated English site is written to `site/`, and the Chinese site is
written to `site/zh/`. The GitHub Pages workflow deploys the combined `site/`
artifact when changes are pushed to `main`.

## Repository Layout

```text
src/libterraform/       Python package and public API
native/go/              Go bridge files copied during build
upstream/terraform/     Terraform submodule
upstream/go-plugin/     go-plugin submodule patched during build
tests/                  Python tests and Terraform fixtures
scripts/                Build, release, and validation helpers
docs/                   Project documentation
```

## Updating Terraform Versions

Version-line policy is described in [Release Policy](release-policy.md). In
practice, a Terraform update usually includes:

1. Update `release-matrix.json`.
2. Update `src/libterraform/__init__.py`.
3. Update `tests/consts.py`.
4. Update README examples and version table.
5. Move `upstream/terraform/` to the intended Terraform tag.
6. Move `upstream/go-plugin/` to the go-plugin version required by Terraform.
7. Run the matrix verifier, tests, and wheel build:

```bash
python scripts/verify_release_matrix.py
uv run pytest --color=yes
uv build --wheel
```

## Troubleshooting

If importing `libterraform` fails because the shared library is missing, build
the wheel first or install a built package that contains `libterraform.so` or
`libterraform.dll`.

If the build hook reports missing upstream directories, initialize the Git
submodules.

If Terraform command tests fail with provider or state output differences, run
the single failing test with `-vv` and check `CommandResult.error` or captured
stderr. The Python wrappers mostly translate arguments and parse stdout; the
underlying behavior is Terraform's.
