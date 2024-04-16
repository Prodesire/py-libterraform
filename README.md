# Python libterraform

[![libterraform](https://img.shields.io/pypi/v/libterraform.svg)](https://pypi.python.org/pypi/libterraform)
[![libterraform](https://img.shields.io/pypi/l/libterraform.svg)](https://pypi.python.org/pypi/libterraform)
[![libterraform](https://img.shields.io/pypi/pyversions/libterraform.svg)](https://pypi.python.org/pypi/libterraform)
[![Test](https://github.com/Prodesire/py-libterraform/actions/workflows/test.yml/badge.svg)](https://github.com/Prodesire/py-libterraform/actions/workflows/test.yml)
[![libterraform](https://img.shields.io/pypi/dm/libterraform)](https://pypi.python.org/pypi/libterraform)

Python binding for [Terraform](https://www.terraform.io/).

## Installation

```bash
$ pip install libterraform
```

> **NOTE**
> - Please install version **0.3.1** or above, which solves the memory leak problem.
> - This library does **not support** multithreading.

## Usage

### Terraform CLI

`TerraformCommand` is used to invoke various Terraform commands.

Now, support all commands (`plan`, `apply`, `destroy` etc.), and return a `CommandResult` object. The `CommandResult`
object has the following properties:

- `retcode` indicates the command return code. A value of 0 or 2 is normal, otherwise is abnormal.
- `value` represents command output. If `json=True` is specified when executing the command, the output will be loaded
  as json.
- `json` indicates whether to load the output as json.
- `error` indicates command error output.

To get Terraform verison:

```python
>>> from libterraform import TerraformCommand
>>> TerraformCommand().version()
<CommandResult retcode=0 json=True>
>>> _.value
{'terraform_version': '1.2.2', 'platform': 'darwin_arm64', 'provider_selections': {}, 'terraform_outdated': False}
>>> TerraformCommand().version(json=False)
<CommandResult retcode=0 json=False>
>>> _.value
'Terraform v1.2.2\non darwin_arm64\n'
```

To `init` and `apply` according to Terraform configuration files in the specified directory:

```python
>>> from libterraform import TerraformCommand
>>> cli = TerraformCommand('your_terraform_configuration_directory')
>>> cli.init()
<CommandResult retcode=0 json=False>
>>> cli.apply()
<CommandResult retcode=0 json=True>
```

Additionally, `run()` can execute arbitrary commands, returning a tuple `(retcode, stdout, stderr)`.

```python
>>> TerraformCommand.run('version')
(0, 'Terraform v1.2.2\non darwin_arm64\n', '')
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
>>> mod, _ = TerraformConfig.load_config_dir('your_terraform_configuration_directory')
>>> mod['ManagedResources'].keys()
dict_keys(['time_sleep.wait1', 'time_sleep.wait2'])
```

## Version comparison

| libterraform                                          | Terraform                                                   |
|-------------------------------------------------------|-------------------------------------------------------------|
| [0.6.0](https://pypi.org/project/libterraform/0.6.0/) | [1.5.7](https://github.com/hashicorp/terraform/tree/v1.5.7) |
| [0.5.0](https://pypi.org/project/libterraform/0.5.0/) | [1.3.0](https://github.com/hashicorp/terraform/tree/v1.3.0) |
| [0.4.0](https://pypi.org/project/libterraform/0.4.0/) | [1.2.2](https://github.com/hashicorp/terraform/tree/v1.2.2) |
| [0.3.1](https://pypi.org/project/libterraform/0.3.1/) | [1.1.7](https://github.com/hashicorp/terraform/tree/v1.1.7) |

## Building & Testing

If you want to develop this library, should first prepare the following environments:

- [GoLang](https://go.dev/dl/) (Version 1.18+)
- [Python](https://www.python.org/downloads/) (Version 3.7~3.11)
- GCC

Then, initialize git submodule:

```bash
$ git submodule init
$ git submodule update
```

`pip install` necessary tools:

```bash
$ pip install poetry pytest
```

Now, we can build and test:

```bash
$ poetry build -f wheel
$ pytest
```

## Why use this library?

Terraform is a great tool for deploying resources. If you need to call the Terraform command in the Python program for
deployment, a new process needs to be created to execute the Terraform command on the system. A typical example of this
is the [python-terraform](https://github.com/beelit94/python-terraform) library. Doing so has the following problems:

- Requires Terraform commands on the system.
- The overhead of starting a new process is relatively high.

This library compiles Terraform as a **dynamic link library** in advance, and then loads it for calling. So there is no
need to install Terraform, nor to start a new process.

In addition, since the Terraform dynamic link library is loaded, this library can further call Terraform's
**internal capabilities**, such as parsing Terraform config files.
