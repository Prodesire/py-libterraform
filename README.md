# Python libterraform

[![Release](https://github.com/Prodesire/py-libterraform/actions/workflows/release.yml/badge.svg)](https://github.com/Prodesire/py-libterraform/actions/workflows/release.yml)

Python binding for Terraform.

## Installation

```bash
$ pip install libterraform
```

## Usage

### Terraform CLI

`TerraformCommand` is used to invoke various Terraform commands.

Currently, supports `version` and `init` commands, returning a `CommandResult` object. The `CommandResult` object has
the following properties:

- `retcode` indicates the command return code. A value of 0 is normal, non-zero is abnormal.
- `value` represents command output. If `json=True` is specified when executing the command, the output will be loaded
  as json.
- `json` indicates whether to load the output as json.
- `error` indicates command error output.

```python
>>> from libterraform import TerraformCommand
>>> TerraformCommand().version()
<CommandResult retcode=0 json=True>
>>> _.value
{'terraform_version': '1.1.7', 'platform': 'darwin_arm64', 'provider_selections': {}, 'terraform_outdated': False}
>>> TerraformCommand().version(json=False)
<CommandResult retcode=0 json=False>
>>> _.value
'Terraform v1.1.7\non darwin_arm64\n'
```

Additionally, `run()` can execute arbitrary commands, returning a tuple `(retcode, stdout, stderr)`.

```python
>>> TerraformCommand.run('version')
(0, 'Terraform v1.1.7\non darwin_arm64\n', '')
>>> TerraformCommand.run('invalid')
(1, '', 'Terraform has no command named "invalid".\n\nTo see all of Terraform\'s top-level commands, run:\n  terraform -help\n\n')
```

### Terraform Config Parser

`TerraformConfig` is used to parse Terraform config files.

For now, only supply `TerraformConfig.load_config_dir` method which reads the .tf and .tf.json files in the given
directory as config files and then combines these files into a single Module. This method returns `(mod, diags)`
which are both dict, corresponding to
the [*Module](https://github.com/hashicorp/terraform/blob/2a5420cb9acf8d5f058ad077dade80214486f1c4/internal/configs/module.go#L14)
and [hcl.Diagnostic](https://github.com/hashicorp/hcl/blob/v2.11.1/diagnostic.go#L26) structures in Terraform
respectively.

```python
>>> from libterraform import TerraformConfig
>>> mod, _ = TerraformConfig.load_config_dir('tests/tf/sleep')
>>> mod['ManagedResources'].keys()
dict_keys(['time_sleep.wait'])
```


## Why use this libray?
Terraform is a great tool for deploying resources. If you need to call the Terraform command in the Python program
for deployment, a new process needs to be created to execute the Terraform command on the system. A typical example 
of this is the [python-terraform](https://github.com/beelit94/python-terraform) library. 
Doing so has the following problems:
- Requires Terraform commands on the system.
- The overhead of starting a new process is relatively high.

This library compiles Terraform as a **dynamic link library** in advance, and then loads it for calling. 
So there is no need to install Terraform, nor to start a new process.

In addition, since the Terraform dynamic link library is loaded, this library can further call Terraform's 
**internal capabilities**, such as parsing Terraform config files.
