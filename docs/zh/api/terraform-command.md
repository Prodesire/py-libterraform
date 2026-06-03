# TerraformCommand

从包根路径导入 `TerraformCommand`：

```python
from libterraform import TerraformCommand
```

`TerraformCommand` 负责执行 Terraform 命令，并把常用子命令封装为 Python
方法。构造时可传入 `cwd` 作为默认 Terraform 工作目录。多数高层方法会返回
`CommandResult`。

## CommandResult

`CommandResult` 暴露以下字段：

- `retcode`：Terraform 返回码。`0` 和部分命令的 `2` 通常表示正常结果。
- `value`：解析后的 JSON 或原始 stdout，取决于方法和 `json=` 参数。
- `error`：stderr。
- `json`：stdout 是否按 JSON 解析。

## 参数规则

#### 通用参数

| 参数 | 说明 |
|---|---|
| `check` | 是否检查 Terraform 返回码。为 `True` 且返回码不是 `0` 或 `2` 时抛出 `TerraformCommandError`。 |
| `json` | 是否请求或解析 JSON 输出。支持 JSON 的方法默认通常为 `True`。 |
| `no_color` | 是否添加 `-no-color`，避免输出 ANSI 颜色。 |
| `input` | 是否允许交互式输入；自动化场景通常设为 `False`。 |
| `lock` | 是否持有 state lock。 |
| `lock_timeout` | 获取 state lock 的等待时间。 |
| `vars` | Terraform 变量字典，会转换为多个 `-var=key=value`。 |
| `var_files` | 变量文件列表，会转换为多个 `-var-file=...`。 |
| `target` | 目标资源地址或地址列表。 |
| `parallelism` | Terraform 并发操作数量。 |
| `state` | 指定 state 文件路径。 |
| `options` | 额外 Terraform 参数。下划线会转换为连字符，例如 `detailed_exitcode` 转为 `-detailed-exitcode`。 |

#### 传参转换

- `True` / `False` 会转换为 Terraform 使用的小写布尔值。
- `...` 表示无值 flag，例如 `flag(True)` 会生成 `-json`。
- list 会展开为多个同名参数。
- dict 会展开为 `-name=key=value` 形式。

## TerraformCommand

::: libterraform.cli.TerraformCommand.run
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

执行任意 Terraform 子命令，返回 `(retcode, stdout, stderr)` 三元组。

如果 `check` 为 `True` 且返回码不是 `0` 或 `2`，将抛出
`TerraformCommandError`。该异常的 `retcode` 属性包含返回码，`stdout` 和
`stderr` 属性包含输出。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `cmd` | `CmdType` | Terraform 子命令，或已经拆分好的命令片段列表。 | *必填* |
| `args` | `Optional[Sequence[str]]` | 位置参数列表，追加到命令末尾。 | `None` |
| `options` | `Optional[dict]` | Terraform option 字典，按上面的传参转换规则处理。 | `None` |
| `chdir` | | 执行子命令前切换到指定目录，对应 Terraform 的 `-chdir`。 | `None` |
| `check` | `bool` | 是否在异常返回码时抛出 `TerraformCommandError`。 | `False` |
| `json` | | 是否追加 `-json`。仅部分命令支持此参数。 | `False` |

::: libterraform.cli.TerraformCommand.version
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/version>

显示 Terraform 版本及所有已安装插件的版本信息。

默认以 JSON 格式输出。`json=True` 时返回值会解析为 Python
对象；`json=False` 时保留文本输出。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `check` | `bool` | 是否检查返回码。 | `False` |
| `json` | `bool` | 是否以 JSON 格式输出。 | `True` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.init
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/init>

初始化新的或已有的 Terraform 工作目录：创建初始文件、加载远端 state、下载
模块和 provider，并配置 backend。

对于每台机器上的新配置或已有配置，这都是应该首先执行的命令。它会设置
Terraform 运行所需的全部本地数据（这些数据通常不提交到版本控制系统）。

该命令可以安全地多次运行。后续运行可能会报错，但不会删除已有配置或 state。
即便如此，如果有重要信息，建议在运行前先做好备份。

默认以 JSON 格式输出。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `check` | `bool` | 是否检查返回码。 | `False` |
| `backend` | `bool` | 设为 `False` 可禁用 backend 或 HCP Terraform 初始化，而使用之前已初始化的配置。 | `None` |
| `backend_config` | `Union[str, List[str]]` | 与配置文件中 `backend` 块合并的配置。可以是 HCL key/value 文件路径（格式同 `terraform.tfvars`）或 `key=value` 字符串，支持多次指定。backend 类型必须在配置文件中定义。 | `None` |
| `force_copy` | `bool` | 初始化新 state backend 时跳过关于复制 state 的确认提示，等同于对所有确认回答 "yes"。 | `None` |
| `from_module` | `str` | 初始化前将给定 module 的内容复制到目标目录。 | `None` |
| `get` | `bool` | 设为 `False` 可禁用下载模块。 | `None` |
| `input` | `bool` | 设为 `False` 可禁用交互式提示。注意某些操作需要交互式提示，禁用后会报错。 | `False` |
| `lock` | `bool` | 设为 `False` 可在 backend 迁移时不持有 state lock。如果其他人可能同时对同一 workspace 执行命令，这样做是危险的。 | `None` |
| `lock_timeout` | `str` | 获取 state lock 的重试等待时间。 | `None` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `plugin_dirs` | `List[str]` | 包含 plugin 二进制文件的目录列表。此选项会覆盖所有默认 plugin 搜索路径，并阻止自动安装 plugin。 | `None` |
| `reconfigure` | `bool` | 重新配置 backend，忽略之前保存的配置。 | `None` |
| `migrate_state` | `bool` | 重新配置 backend，并尝试迁移已有 state。 | `None` |
| `upgrade` | `bool` | 安装配置约束范围内最新的 module 和 provider 版本，覆盖 dependency lockfile 中记录的精确版本。 | `None` |
| `lockfile` | `str` | 设置 dependency lockfile 模式，目前 Terraform 仅支持 `readonly`。 | `None` |
| `ignore_remote_version` | `bool` | 仅用于 HCP Terraform 和 remote backend 的少见选项。设置后将忽略本地和远端 Terraform 版本兼容性检查，允许在可能存在 state 表示不匹配时继续操作。 | `None` |
| `test_directory` | `str` | Terraform test 目录，默认为 `"tests"`。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.validate
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/validate>

校验当前目录中的 Terraform 配置文件，仅检查配置本身，不访问任何远端服务
（如远端 state、provider API 等）。

该命令检查配置在语法和内部一致性上是否有效，与已提供的变量或已有 state
无关。因此它主要适用于可复用模块的通用验证，包括属性名和值类型的正确性。

可以安全地自动运行此命令，例如作为文本编辑器的保存后检查，或 CI 系统中
可复用模块的测试步骤。

校验需要一个已初始化的工作目录（已安装所有引用的 plugin 和模块）。要在不
访问已配置 remote backend 的情况下初始化工作目录用于校验，可以使用：
`cli.init(backend=False)`。

如果需要在特定运行上下文（特定 workspace、输入变量值等）中验证配置，请改用
`cli.plan()`，它包含隐式的校验检查。

默认以 JSON 格式输出。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `check` | `bool` | 是否检查返回码。 | `False` |
| `json` | `bool` | 是否以 JSON 格式输出。 | `True` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `no_test` | `bool` | 设置后 Terraform 将不校验测试文件。 | `None` |
| `test_directory` | `str` | 设置 Terraform 测试目录，默认为 `"tests"`。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.plan
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/plan>

生成推测性执行计划，展示 Terraform 为应用当前配置将要采取的操作。此命令不会
实际执行计划中的操作。

可以选择将 plan 保存到文件，然后将该文件传给 `cli.apply()` 来精确执行 plan
中描述的操作。

默认以 JSON 格式输出。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `check` | `bool` | 是否检查返回码。 | `False` |
| `json` | `bool` | 是否以 JSON 格式输出。 | `True` |
| `destroy` | `bool` | 选择 "destroy" 计划模式，创建一个销毁当前配置管理的所有对象的 plan，而非通常的行为。 | `None` |
| `refresh_only` | `bool` | 选择 "refresh only" 计划模式，仅检查远端对象是否仍与最近一次 `apply` 的结果匹配，不提议任何操作来撤销 Terraform 外部的变更。 | `None` |
| `refresh` | `bool` | 跳过创建 plan 时对远端对象外部变更的检查。这可以加快计划速度，但代价是可能基于远端系统状态的过时记录来做计划。 | `None` |
| `replace` | `Union[str, List[str]]` | 使用资源地址强制替换某个资源实例。如果 plan 通常会为该实例生成 update 或 no-op 操作，Terraform 将改为计划替换它。可以多次指定以替换多个对象。 | `None` |
| `target` | `Union[str, List[str]]` | 将计划操作限定为给定的 module、资源或资源实例及其所有依赖。可以多次指定以包含多个对象。此选项仅用于特殊情况。 | `None` |
| `vars` | `dict` | 设置根模块中的变量。 | `None` |
| `var_files` | `List[str]` | 从给定文件加载变量值，追加到默认文件 `terraform.tfvars` 和 `*.auto.tfvars` 之上。 | `None` |
| `compact_warnings` | `bool` | 如果 Terraform 产生了不伴随错误的 warning，以更紧凑的形式显示，仅包含摘要信息。 | `None` |
| `detailed_exitcode` | `bool` | 返回详细退出码。退出码含义变为：`0` 成功且无差异，`1` 错误，`2` 成功且有差异。 | `None` |
| `generate_config_out` | `str` | （实验性）如果配置中存在 import 块，指示 Terraform 为尚未存在的导入资源生成 HCL 配置。配置写入 PATH 指定的新文件（该文件不能已存在）。 | `None` |
| `input` | `bool` | 设为 `False` 可禁用交互式提示。注意某些操作需要交互式提示，禁用后会报错。 | `False` |
| `lock` | `bool` | 设为 `False` 可在操作期间不持有 state lock。如果其他人可能同时对同一 workspace 执行命令，这样做是危险的。 | `None` |
| `lock_timeout` | `str` | 获取 state lock 的重试等待时间。 | `None` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `out` | `str` | 将 plan 文件写入指定路径，之后可作为 `show` 或 `apply` 命令的输入。 | `None` |
| `parallelism` | `int` | 限制并发操作数量，默认 10。 | `None` |
| `state` | `str` | 仅用于 local backend 的遗留选项。详见 local backend 文档。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.show
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/show>

读取并以人类可读的形式输出 Terraform state 或 plan 文件。如果未指定
`path`，则显示当前 state。

默认以 JSON 格式输出。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `path` | `str` | Terraform state 或 plan 文件路径。 | `None` |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `json` | `bool` | 是否以 JSON 格式输出。 | `True` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.apply
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/apply>

根据当前目录中的 Terraform 配置文件创建或更新基础设施。

默认情况下，Terraform 会生成一个新的 plan 并在采取任何操作前等待用户批准。
也可以传入通过 `cli.plan()` 生成的 plan 文件，此时 Terraform 将直接执行
plan 中的操作而不再提示确认。

如果未提供 plan 文件，此方法也接受 `plan` 方法支持的所有计划定制选项。

默认以 JSON 格式输出。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `plan` | `str` | 要应用的 plan 文件路径。 | `None` |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `json` | `bool` | 是否以 JSON 格式输出。 | `True` |
| `auto_approve` | `bool` | 跳过 plan 应用前的交互式确认。 | `True` |
| `backup` | `str` | 修改 state 前的备份路径。默认为 `state_out` 路径加 `.backup` 后缀。设为 `"-"` 可禁用备份。 | `None` |
| `compact_warnings` | `bool` | 如果 Terraform 产生了不伴随错误的 warning，以更紧凑的形式显示，仅包含摘要信息。 | `None` |
| `input` | `bool` | 设为 `False` 可禁用交互式提示。注意某些操作需要交互式提示，禁用后会报错。 | `False` |
| `lock` | `bool` | 设为 `False` 可在操作期间不持有 state lock。如果其他人可能同时对同一 workspace 执行命令，这样做是危险的。 | `None` |
| `lock_timeout` | `str` | 获取 state lock 的重试等待时间。 | `None` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `parallelism` | `int` | 限制并发操作数量，默认 10。 | `None` |
| `state` | `str` | 读取和保存 state 的路径（除非指定了 `state_out`）。默认为 `"terraform.tfstate"`。 | `None` |
| `state_out` | `str` | state 输出路径，可以与 `state` 不同，用于保留旧 state。 | `None` |
| `destroy` | `bool` | 选择 "destroy" 计划模式，创建一个销毁当前配置管理的所有对象的 plan。 | `None` |
| `vars` | `dict` | 设置根模块中的变量。在 Terraform 1.10 及更高版本中，应用已保存的 plan 文件时也可以用于提供 apply-time 临时变量。 | `None` |
| `var_files` | `List[str]` | 从给定文件加载变量值，追加到默认文件 `terraform.tfvars` 和 `*.auto.tfvars` 之上。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.destroy
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/destroy>

销毁当前 Terraform 配置管理的基础设施。

此命令是 `terraform apply -destroy` 的便捷别名，同时也接受 `plan` 方法支持
的许多计划定制选项。

默认以 JSON 格式输出。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `check` | `bool` | 是否检查返回码。 | `False` |
| `json` | `bool` | 是否以 JSON 格式输出。 | `True` |
| `auto_approve` | `bool` | 跳过交互式确认。 | `True` |
| `backup` | `str` | 修改 state 前的备份路径。默认为 `state_out` 路径加 `.backup` 后缀。设为 `"-"` 可禁用备份。 | `None` |
| `compact_warnings` | `bool` | 以更紧凑的形式显示 warning。 | `None` |
| `input` | `bool` | 设为 `False` 可禁用交互式提示。 | `False` |
| `lock` | `bool` | 设为 `False` 可在操作期间不持有 state lock。 | `None` |
| `lock_timeout` | `str` | 获取 state lock 的重试等待时间。 | `None` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `parallelism` | `int` | 限制并发操作数量，默认 10。 | `None` |
| `state` | `str` | 读取和保存 state 的路径。默认为 `"terraform.tfstate"`。 | `None` |
| `state_out` | `str` | state 输出路径，用于保留旧 state。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.fmt
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/fmt>

将所有 Terraform 配置文件重写为标准格式。所有配置文件（`.tf`）、变量文件
（`.tfvars`）和测试文件（`.tftest.hcl`）都会被更新。JSON 文件（`.tf.json`、
`.tfvars.json` 或 `.tftest.json`）不会被修改。

默认情况下 `fmt` 扫描当前目录的配置文件。如果为 `dir` 参数提供目录，则扫描
该目录；如果提供文件，则只处理该文件；如果提供 `"-"`，则从标准输入读取。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `dir` | `Union[str, List[str]]` | 要格式化的文件或目录，可为字符串或列表。 | `None` |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `list` | `bool` | 设为 `False` 可不列出格式有差异的文件（使用 STDIN 时始终禁用）。 | `None` |
| `write` | `bool` | 设为 `False` 可不写回源文件（使用 STDIN 或 `check_input=True` 时始终禁用）。 | `None` |
| `diff` | `bool` | 显示格式化变更的 diff。 | `None` |
| `check_input` | `bool` | 检查输入是否已格式化。如果所有输入格式正确则退出码为 `0`，否则为非零。 | `None` |
| `recursive` | `bool` | 同时处理子目录中的文件。默认只处理指定目录（或当前目录）。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.force_unlock
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/force-unlock>

手动解除当前配置对应的 state lock。

此命令不会修改基础设施。它会移除当前 workspace 的 state lock。lock 的行为
取决于所使用的 backend。本地 state 文件无法被其他进程解锁。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `lock_id` | `str` | 要解除的 lock ID。 | *必填* |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `force` | `bool` | 设为 `True` 跳过解锁确认提示。 | `True` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.get
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/get>

下载并安装当前工作目录中配置所需的 modules。

此命令会递归下载所有需要的 module，包括 module 导入的 module 等。如果
module 已下载，则不会重新下载或检查更新，除非指定了 `update`。

module 安装默认也作为 `terraform init` 命令的一部分自动进行，因此通常很少
需要单独运行此命令。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `update` | `bool` | 检查已下载 module 的可用更新并安装最新版本。 | `None` |
| `test_directory` | `str` | 设置 Terraform 测试目录，默认为 `"tests"`。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.graph
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/graph>

生成当前配置和 state 中不同对象之间依赖关系的图形表示。

默认情况下，该图仅显示配置中资源之间关系的摘要，因为资源是具有重要排序意义
的有副作用的主要对象。可以通过指定 `type` 选项来生成反映 Terraform 实际评估
策略的更详细图形。

图形以 DOT 语言呈现。读取此格式的典型程序是 GraphViz，也有许多 Web 服务
支持此格式。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `plan` | `str` | 使用指定的 plan 文件渲染图形，隐含 `type=apply`。 | `None` |
| `draw_cycles` | `bool` | 用彩色边高亮图中的任何循环，帮助诊断循环错误。仅在使用 `type` 选择真实评估图时有效。 | `None` |
| `type` | `str` | 输出的操作图类型。可选 `plan`、`plan-refresh-only`、`plan-destroy` 或 `apply`。默认仅显示资源关系摘要。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.import_resource
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/import>

将已有基础设施导入 Terraform state。

该命令会查找并导入指定的资源到 Terraform state 中，使已有基础设施可以纳入
Terraform 管理，而无需先由 Terraform 创建。

`addr` 是导入目标的资源地址（详见 Terraform 文档中关于资源地址的说明）。
`id` 是资源特定的 ID，用于标识被导入的资源，通常直接对应 provider 使用的
ID，具体语法请参考对应资源类型的文档。

此命令不会直接修改基础设施，但会发起网络请求以检查与被导入资源相关的基础
设施部分。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `addr` | `str` | 导入资源的目标地址。 | *必填* |
| `id` | `str` | 资源特定的 ID，用于标识被导入的资源。通常直接对应 provider 使用的 ID。 | *必填* |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `config` | `str` | Terraform 配置文件所在目录的路径，用于配置 provider。默认为当前目录。如果没有配置文件，必须通过输入提示或环境变量提供。 | `None` |
| `input` | `bool` | 设为 `False` 可禁用交互式提示。注意某些操作需要交互式提示，禁用后会报错。 | `False` |
| `lock` | `bool` | 设为 `False` 可在操作期间不持有 state lock。如果其他人可能同时对同一 workspace 执行命令，这样做是危险的。 | `None` |
| `lock_timeout` | `str` | 获取 state lock 的重试等待时间。 | `None` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `vars` | `dict` | 设置 Terraform 配置中的变量。仅在使用 `config` 选项时有用。 | `None` |
| `var_files` | `List[str]` | 从给定文件加载变量值，追加到默认文件 `terraform.tfvars` 和 `*.auto.tfvars` 之上。 | `None` |
| `ignore_remote_version` | `bool` | 仅用于 remote backend 的少见选项。详见 remote backend 文档。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.output
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/output>

从 Terraform state 文件中读取 output 变量并输出其值。如果未指定 `name`，则
输出根模块的所有 output。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `name` | `str` | output 变量名称。为空时输出全部 output。 | `None` |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `json` | `bool` | 是否以 JSON 格式输出。 | `True` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `state` | `str` | state 文件路径。默认为 `"terraform.tfstate"`。使用 remote state 时忽略此参数。 | `None` |
| `raw` | `bool` | 对于可自动转换为字符串的值类型，直接输出原始字符串，而非人类可读的值表示。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.modules
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/modules>

输出当前工作目录中 Terraform 配置声明的所有 modules 的 source 和 version
信息。

Terraform 1.10 要求此命令以 JSON 格式输出，因此默认以 JSON 格式输出。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `check` | `bool` | 是否检查返回码。 | `False` |
| `json` | `bool` | 是否以 JSON 格式输出。 | `True` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.providers
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/providers>

输出引用配置中按 module 标注的 provider requirements 树，提供所有引用 module
的 provider 需求概览，帮助理解为什么需要特定的 provider plugin 以及为什么选择
了特定版本。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `subcmd` | `str` | 子命令：`lock`、`mirror`、`schema`。 | `None` |
| `args` | `Sequence[str]` | 子命令参数。 | `None` |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `json` | `bool` | 是否以 JSON 格式输出。仅在 `subcmd=schema` 时有效。 | `False` |
| `test_directory` | `str` | 设置 Terraform 测试目录，默认为 `"tests"`。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.providers_lock
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/providers/lock>

为 provider dependency lock file（`.terraform.lock.hcl`）生成或更新 provider
校验和。

通常 dependency lock file 由 `terraform init` 自动更新，但如果从文件系统或
网络 mirror 安装 provider，可用信息可能受限，生成的 lock file 可能不完整。
`providers lock` 子命令基于源 registry 中的官方包来更新 lock file，忽略
当前配置的安装策略，从而解决此问题。

此命令成功后，lock file 将包含适当的校验和，允许在所有选定平台上安装当前
配置所需的 provider。

默认情况下，此命令为配置中声明的每个 provider 更新 lock file。可以在命令行上
提供一个或多个 provider 源地址来覆盖此行为。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `*providers` | `str` | 要锁定的 provider 源地址（可变参数）。 | |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `fs_mirror` | `str` | 为给定的每个 provider 使用指定的文件系统 mirror 目录代替源 registry。当 provider 仅通过 mirror 可用而未在上游 registry 发布时需要此选项。此时有效校验和集仅限于 Terraform 能从 mirror 目录数据中获取的内容。 | `None` |
| `net_mirror` | `str` | 为给定的每个 provider 使用指定的网络 mirror（给定为 base URL）代替源 registry。当 provider 仅通过 mirror 可用而未在上游 registry 发布时需要此选项。此时有效校验和集仅限于 Terraform 能从 mirror 索引数据中获取的内容。 | `None` |
| `platform` | `Union[str, List[str]]` | 选择要请求包校验和的目标平台。默认情况下 Terraform 仅请求适合运行此命令的当前平台的校验和。可多次指定以包含多个目标系统的校验和。目标名由操作系统和 CPU 架构组成，例如 `"linux_amd64"`。 | `None` |
| `enable_plugin_cache` | `bool` | 启用全局配置的 plugin cache。这会加速锁定过程，但 provider 不会从权威来源加载。 | `False` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.providers_mirror
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/providers/mirror>

将当前配置所需的 provider plugin 副本填充到本地目录，使该目录可以直接用作
文件系统 mirror 或作为网络 mirror 的基础，从而在未来无需访问源 registry
即可获取这些 provider。

mirror 目录将包含 JSON 索引文件，可以与 mirror 的包一起发布到静态 HTTP
文件服务器上以构建网络 mirror。如果该目录作为本地文件系统 mirror 使用，
这些索引文件会被忽略。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `target_dir` | `str` | 构建 mirror 的目标目录。 | *必填* |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `platform` | `Union[str, List[str]]` | 选择要构建 mirror 的目标平台。默认情况下 Terraform 获取适合运行此命令的当前平台的 plugin 包。可多次指定以包含多个目标系统的包。目标名由操作系统和 CPU 架构组成，例如 `"linux_amd64"`。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.providers_schema
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/providers>

输出当前配置使用的所有 providers 的 schema 的 JSON 表示。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.refresh
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/refresh>

使用与物理资源匹配的元数据更新基础设施的 state 文件。

此命令不会修改基础设施，但可能修改 state 文件以更新元数据。这些元数据可能
导致在下次生成 plan 或调用 apply 时产生新的变更。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `check` | `bool` | 是否检查返回码。 | `False` |
| `json` | `bool` | 是否以 JSON 格式输出。 | `True` |
| `target` | `Union[str, List[str]]` | 目标资源地址。操作将限定于此资源及其依赖。可多次指定。 | `None` |
| `vars` | `dict` | 设置 Terraform 配置中的变量。 | `None` |
| `var_files` | `List[str]` | 从给定文件加载变量值。 | `None` |
| `compact_warnings` | `bool` | 以更紧凑的形式显示 warning。 | `None` |
| `input` | `bool` | 设为 `False` 可禁用交互式提示。 | `False` |
| `lock` | `bool` | 设为 `False` 可在操作期间不持有 state lock。 | `None` |
| `lock_timeout` | `str` | 获取 state lock 的重试等待时间。 | `None` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `parallelism` | `int` | 限制并发操作数量，默认 10。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.state
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/state>

执行 Terraform state 高级管理子命令。

这些子命令可用于切割和操作 Terraform state。这在高级场景中有时是必要的。为了
安全，所有修改 state 的 state 管理命令都会在修改前创建 state 的带时间戳备份。

命令的结构和输出专门设计为与 `grep`、`awk` 等常见 Unix 工具配合良好。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `subcmd` | `str` | state 子命令名：`list`、`mv`、`pull`、`push`、`replace-provider`、`rm`、`show`。 | *必填* |
| `args` | `Sequence[str]` | 子命令参数。 | `None` |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `json` | `bool` | 是否以 JSON 格式输出。 | `False` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.state_list
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/state/list>

列出 Terraform state 中的资源。

如果给定的过滤地址中有任何资源或 module 在 state 中不存在，将返回错误。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `*addrs` | `str` | 可用于按资源或 module 过滤实例（可变参数）。如果未给定，则列出所有资源实例。地址必须是 module 地址或绝对资源地址，例如 `aws_instance.example`、`module.example`。 | |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `state` | `str` | state 文件路径。默认使用当前选定 workspace 的 state。 | `None` |
| `ids` | `Sequence[str]` | 按资源 ID 过滤结果，仅包含资源类型中 `id` 属性值在给定列表中的实例。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.state_mv
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/state/mv>

将 state 中匹配给定地址的项目移动到目标地址。此命令也可以移动到完全不同的
state 文件中的目标地址。

可用于简单的资源重命名、将项目移入或移出 module、移动整个 module 等。因为
此命令也可以移动数据到全新的 state，还可用于将一个配置重构为多个独立管理的
Terraform 配置。

此命令会在保存任何更改前输出 state 的备份副本。备份不可禁用。由于此命令的
破坏性特点，备份是必须的。如果要将项目移动到不同的 state 文件，会为每个
state 文件创建备份。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `src` | `str` | 源资源地址。 | *必填* |
| `dst` | `str` | 目标资源地址。 | *必填* |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `dry_run` | `bool` | 设为 `True` 仅打印将要移动的内容而不实际移动。 | `None` |
| `lock` | `bool` | 设为 `False` 可在操作期间不持有 state lock。 | `None` |
| `lock_timeout` | `str` | 获取 state lock 的重试等待时间。 | `None` |
| `ignore_remote_version` | `bool` | 仅用于 remote backend 的少见选项。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.state_pull
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/state/pull>

从其存储位置拉取 state，升级本地副本的格式并输出。在此过程中 Terraform 会将
本地副本的 state 格式升级到当前版本。

此命令主要用于远端存储的 state。对于本地 state 文件仍可使用，但用处较小。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.state_push
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/state/push>

从指定路径的本地 state 文件更新远端 state。此命令会保护你免于写入更旧的
serial 或不同的 state 文件世系，除非指定了 `force`。

此命令也可用于本地 state（会覆盖本地 state），但此用例下用处较小。

如果 `path` 为 `"-"`，则从 stdin 读取要推送的 state。从 stdin 读取的数据不会
流式传输到 backend：会完整加载（直到管道关闭），验证后再推送。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `path` | `str` | 本地 state 文件路径。设为 `"-"` 可从 stdin 读取。 | *必填* |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `force` | `bool` | 设为 `True` 时即使世系不匹配或远端 serial 更高也写入 state。 | `None` |
| `lock` | `bool` | 设为 `False` 可在操作期间不持有 state lock。 | `None` |
| `lock_timeout` | `str` | 获取 state lock 的重试等待时间。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.state_replace_provider
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/state/replace-provider>

替换 Terraform state 中资源使用的 provider 地址。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `from_provider` | `str` | 源 provider FQN。 | *必填* |
| `to_provider` | `str` | 目标 provider FQN。 | *必填* |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `auto_approve` | `bool` | 跳过交互式确认。 | `True` |
| `lock` | `bool` | 设为 `False` 可在操作期间不持有 state lock。 | `None` |
| `lock_timeout` | `str` | 获取 state lock 的重试等待时间。 | `None` |
| `ignore_remote_version` | `bool` | 仅用于 remote backend 的少见选项。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.state_rm
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/state/rm>

从 Terraform state 中移除一个或多个项目，让 Terraform "忘记" 这些项目，
但不会先在远端系统中销毁它们。

此命令根据给定的地址从 state 中移除一个或多个资源实例。可以使用
`state_list` 查看和列出可用的实例。

如果给定整个 module 的地址，该 module 及其所有子 module 中的所有实例都会
从 state 中移除。

如果给定的资源设置了 `count` 或 `for_each`，该资源的所有实例都会从 state
中移除。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `*addrs` | `str` | 要移除的资源地址列表（可变参数）。 | |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `dry_run` | `bool` | 设为 `True` 仅打印将要移除的内容而不实际移除。 | `None` |
| `backup` | `str` | 备份 state 文件的路径。 | `None` |
| `lock` | `bool` | 设为 `False` 可在操作期间不持有 state lock。 | `None` |
| `lock_timeout` | `str` | 获取 state lock 的重试等待时间。 | `None` |
| `state` | `str` | 要更新的 state 文件路径。默认使用当前 workspace 的 state。 | `None` |
| `ignore_remote_version` | `bool` | 即使本地和远端 Terraform 版本不兼容也继续操作。可能导致 workspace 不可用，请谨慎使用。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.state_show
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/state/show>

展示 Terraform state 中单个资源的属性。

此命令显示 state 中单个资源的属性。`addr` 参数必须指定单个资源的地址。
可以使用 `state_list` 查看可用的资源列表。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `addr` | `str` | 资源地址。 | *必填* |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `state` | `str` | state 文件路径。默认使用当前 workspace 的 state。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.taint
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/taint>

Terraform 使用 "tainted" 来描述可能不完全正常运行的资源实例——要么因为
其创建部分失败，要么因为你使用此命令手动将其标记为 tainted。

此命令不会直接修改基础设施，但后续的 Terraform plan 将包含销毁远端对象并
创建新对象来替换它的操作。

可以使用 `untaint` 命令从资源实例上移除 "tainted" 状态。

地址使用常见的资源地址语法，例如：`aws_instance.foo`、
`aws_instance.bar[1]`、`module.foo.module.bar.aws_instance.baz`。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `addr` | `str` | 资源地址。 | *必填* |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `allow_missing_config` | `bool` | 设为 `True` 时即使资源配置缺失，命令也会成功（退出码 0）。 | `None` |
| `lock` | `bool` | 设为 `False` 可在操作期间不持有 state lock。 | `None` |
| `lock_timeout` | `str` | 获取 state lock 的重试等待时间。 | `None` |
| `ignore_remote_version` | `bool` | 仅用于 remote backend 的少见选项。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.untaint
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/untaint>

从资源实例上移除 "tainted" 状态，使 Terraform 将其视为完全正常运行、无需
替换。

此命令不会直接修改基础设施，仅避免 Terraform 在未来操作中计划替换被标记为
tainted 的实例。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `addr` | `str` | 资源地址。 | *必填* |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `allow_missing_config` | `bool` | 设为 `True` 时即使资源配置缺失，命令也会成功（退出码 0）。 | `None` |
| `lock` | `bool` | 设为 `False` 可在操作期间不持有 state lock。 | `None` |
| `lock_timeout` | `str` | 获取 state lock 的重试等待时间。 | `None` |
| `ignore_remote_version` | `bool` | 仅用于 remote backend 的少见选项。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.test
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/test>

对当前 Terraform 配置执行自动化集成测试。

Terraform 会在当前配置和测试目录中搜索 `.tftest.hcl` 文件，然后按顺序执行
测试文件中的测试运行块，并对创建的基础设施验证条件检查和断言。

此命令会创建真实的基础设施，并在完成后尝试清理测试基础设施。请仔细监控输出
以确保清理过程成功。

默认以 JSON 格式输出。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `check` | `bool` | 是否检查返回码。 | `False` |
| `vars` | `dict` | 设置根模块中的变量。 | `None` |
| `var_files` | `List[str]` | 从给定文件加载变量值，追加到默认文件 `terraform.tfvars` 和 `*.auto.tfvars` 之上。 | `None` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `cloud_run` | `str` | 如果指定，Terraform 将使用 HCP Terraform 或 Terraform Enterprise 远程执行此测试运行。需要指定在私有模块注册表中注册的模块源作为参数。 | `None` |
| `filter` | `Union[str, List[str]]` | 用于筛选测试文件或测试名。 | `None` |
| `json` | `bool` | 是否以 JSON 格式输出。 | `True` |
| `test_directory` | `str` | 设置 Terraform 测试目录，默认为 `"tests"`。 | `None` |
| `verbose` | `bool` | 在每个测试运行块执行时打印 plan 或 state。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.workspace
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/workspace>

执行 Terraform workspace 子命令：new、list、show、select 和 delete。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `subcmd` | `str` | workspace 子命令名。 | *必填* |
| `args` | `Sequence[str]` | 子命令参数。 | `None` |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.workspace_new
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/workspace/new>

创建新的 Terraform workspace。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `name` | `str` | workspace 名称。 | *必填* |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `lock` | `bool` | 设为 `False` 可在操作期间不持有 state lock。 | `None` |
| `lock_timeout` | `str` | 获取 state lock 的重试等待时间。 | `None` |
| `state` | `str` | 将已有 state 文件复制到新 workspace。 | `None` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.workspace_list
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/workspace/list>

列出 Terraform workspaces。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.workspace_show
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/workspace/show>

显示当前 Terraform workspace 名称。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.workspace_select
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/workspace/select>

切换到指定 Terraform workspace。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `name` | `str` | 目标 workspace 名称。 | *必填* |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `**options` | | 额外命令选项。 | |

::: libterraform.cli.TerraformCommand.workspace_delete
    options:
      heading_level: 3
      show_root_full_path: false
      show_docstring_description: false
      show_docstring_parameters: false
      show_docstring_returns: false
      show_docstring_raises: false
      show_docstring_warns: false
      show_docstring_examples: false

参考 <https://developer.hashicorp.com/terraform/cli/commands/workspace/delete>

删除 Terraform workspace。

参数：

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `name` | `str` | workspace 名称。 | *必填* |
| `check` | `bool` | 是否检查返回码。 | `False` |
| `no_color` | `bool` | 是否禁用颜色输出。 | `True` |
| `force` | `bool` | 设为 `True` 时即使 workspace 非空也强制删除。 | `None` |
| `lock` | `bool` | 设为 `False` 可在操作期间不持有 state lock。 | `None` |
| `lock_timeout` | `str` | 获取 state lock 的重试等待时间。 | `None` |
| `**options` | | 额外命令选项。 | |
