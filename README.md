# Python libterraform

[![Release](https://github.com/Prodesire/py-libterraform/actions/workflows/release.yml/badge.svg)](https://github.com/Prodesire/py-libterraform/actions/workflows/release.yml)

Python binding for Terraform.


## Installation
```bash
$ pip install libterraform
```

## Usage
For now, only supply `TerraformConfig.load_config_dir` method which reads the .tf and .tf.json files in the given directory
as config files and then combines these files into a single Module. This method returns `(mod, diags)` 
which are both dict, corresponding to the [*Module](https://github.com/hashicorp/terraform/blob/2a5420cb9acf8d5f058ad077dade80214486f1c4/internal/configs/module.go#L14) 
and [hcl.Diagnostic](https://github.com/hashicorp/hcl/blob/v2.11.1/diagnostic.go#L26) structures in Terraform respectively.
```python
>>> from libterraform import TerraformConfig
>>> mod, _ =TerraformConfig.load_config_dir('tests/config/sleep')
>>> mod['ManagedResources'].keys()
dict_keys(['time_sleep.wait'])
```
