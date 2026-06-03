# TerraformConfig

Import `TerraformConfig` from the package root:

```python
from libterraform import TerraformConfig
```

`TerraformConfig.load_config_dir()` parses `.tf` and `.tf.json` files in a
directory and returns Terraform's combined module representation plus
diagnostics.

## Method

### `load_config_dir(path)`

Reads the `.tf` and `.tf.json` files in the given directory as config files
and then combines these files into a single Module. `.tf` files are parsed
using the HCL native syntax while `.tf.json` files are parsed using the HCL
JSON syntax.

Parameters:

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | Terraform configuration directory path. |

Returns: `Tuple[dict, dict]`

| Value | Type | Description |
|---|---|---|
| `module` | `dict` | Terraform's combined Module representation. |
| `diagnostics` | `dict` | Diagnostics returned by Terraform when parsing the configuration. |

Raises:

- `LibTerraformError` — if the directory does not exist, cannot be opened, or an underlying Terraform error occurs.
