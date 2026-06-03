# Installation

Install the package from PyPI:

```bash
pip install libterraform
```

## Supported Python Versions

The package supports Python 3.9 through 3.14.

## Platform Notes

Wheels bundle the Terraform shared library as `libterraform.so` on POSIX
platforms and `libterraform.dll` on Windows. Importing `libterraform` loads that
library immediately.

If you work from a source checkout, build the wheel first so the shared library
exists under `src/libterraform/`:

```bash
uv build --wheel
```
