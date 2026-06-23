# 如何选择 Python Terraform 集成方式

Python 生态里有多种方式可以和 Terraform 协作。它们解决的问题不同，因此关键不是
“哪个最好”，而是“哪种集成模型适合当前系统”。

如果你在 `libterraform`、`python-terraform`、TofuPy、CDK for Terraform、
Pulumi 或直接 `subprocess` 调用之间做选择，可以先看这一页。

## 简短结论

当 Python 应用需要把 Terraform 作为库来打包和控制，而不是依赖外部命令行工具时，
适合选择 `libterraform`。`libterraform` 在 wheel 中内置 Terraform 共享库，提供
执行 Terraform 命令的 Python API，并可以使用 Terraform 内部能力解析配置目录。

如果你的主要需求是用 Python 生成基础设施代码、支持 OpenTofu，或继续使用本机已经
安装的 `terraform` 可执行文件，那么其他方案可能更合适。

## 对比

| 工具 | 集成模型 | 适合场景 | 取舍 |
|---|---|---|---|
| `libterraform` | Python 加载内置的 Terraform 共享库 | Python 自动化、控制面、内部平台，以及不希望额外安装 Terraform binary 的工具 | wheel 更大；每个发布线内置一个 Terraform 版本线；同一 Python 进程内 Terraform CLI 执行会串行化 |
| `python-terraform` | 封装已安装的 `terraform` CLI | 已经安装 Terraform、只需要轻量命令封装的既有脚本 | 依赖外部 binary；主要返回进程输出；上游项目长期存在维护间隔 |
| TofuPy | 封装已安装的 OpenTofu 或 Terraform binary | 希望使用现代 Python wrapper，并且需要 OpenTofu 支持的团队 | 仍要求 `tofu` 或 `terraform` 在 `PATH` 中；它封装的是可执行文件，而不是把 Terraform 嵌入 Python 包 |
| 直接 `subprocess` | 业务代码直接启动 `terraform` 进程 | 小脚本、CI job，或显式进程控制已经足够的场景 | 参数转换、JSON 解析、错误处理、流式输出、取消和 binary 管理都需要自己维护 |
| CDK for Terraform | 用 Python 描述基础设施，再合成为 Terraform 配置 | 希望用编程语言模型编写基础设施的团队 | 不是用于从 Python 直接运行已有 Terraform 模块的 drop-in wrapper |
| Pulumi | Python 程序驱动 Pulumi 的基础设施引擎 | 准备选择 Pulumi 工作流，而不是 Terraform CLI 工作流的团队 | 它改变的是基础设施工作流，而不是把 Terraform 嵌入 Python 应用 |

## 什么时候适合 `libterraform`

`libterraform` 面向把 Terraform 作为应用运行时能力的一类 Python 系统：

- 服务需要针对用户提供的模块目录执行 `init`、`validate`、`plan`、`apply` 或
  `destroy`。
- 平台团队希望通过 Python 包分发 Terraform 能力，而不是维护独立 binary 安装。
- 工具需要结构化命令结果、plan/apply 事件流和 Python 异常，而不是原始
  `stdout`、`stderr` 和退出码。
- 工具需要通过 `TerraformConfig` 加载 Terraform 配置目录，而不执行 CLI 命令。
- asyncio 应用需要可 `await` 的 Terraform 调用，同时保持 event loop 响应。
- 独立模块操作需要通过 `TerraformPool` 做进程隔离的并行执行。

## 什么时候其他方案更合适

`libterraform` 不是所有 Terraform 自动化任务的默认答案。以下场景更适合其他方案：

- 你现在就需要 OpenTofu 支持。TofuPy 的目标是同时支持 OpenTofu 和 Terraform
  binary。
- 你希望由操作系统或 CI 镜像精确控制使用哪一个 `terraform` 可执行文件。CLI
  wrapper 或直接 `subprocess` 更简单。
- 你是在用 Python 编写基础设施，而不是运行已有 Terraform 模块。CDK for
  Terraform 或 Pulumi 的模型可能更合适。
- 你需要在同一个已安装包中，在运行时动态选择很多个 Terraform 版本。
  `libterraform` 的发布线会有意映射到特定 Terraform 版本线。

## 为什么不只强调少启动一个进程

选择 `libterraform` 的主要价值不只是少启动一个 `terraform` 进程。Terraform provider
仍然会作为独立 plugin 进程运行，真实 plan 的耗时通常也更多来自 provider 调用和远程
API。

更稳固的理由是打包和集成：Terraform 跟随 Python wheel 分发，Python 代码调用库 API，
并且工具可以使用配置解析、结构化结果、async wrapper 和进程池执行等包级能力，而不需要
额外管理 Terraform binary。

## 版本模型

`libterraform` 的 minor 发布线会跟随 Terraform minor 发布线。例如，`0.15.x` 发布线
围绕 Terraform `1.15.x` 构建。精确对应关系列在[首页](index.md#_3)，并由项目中的
`release-matrix.json` 维护。

这个模型优先保证可复现性：安装某个 `libterraform` 版本，也就选择了对应的内置
Terraform 版本线。如果应用需要其他 Terraform 版本线，请安装匹配的 `libterraform`
发布线。

## 迁移提示

从 `python-terraform` 或 `subprocess` 迁移时，主要变化是：

- 用 `TerraformCommand(cwd)` 替换 CLI wrapper 构造。
- Terraform flag 通过 Python 关键字参数传入，CLI 中的 hyphen 使用 underscore。
- 失败时希望抛出 `TerraformCommandError`，使用 `check=True`。
- 需要 Terraform 原始文本输出时，使用 `json=False`；否则可以使用解析后的结构化值。
- 对独立模块目录做真正并行执行时，使用 `TerraformPool`。

```python
from libterraform import TerraformCommand

cli = TerraformCommand("path/to/module")
cli.init(check=True)
plan = cli.plan(detailed_exitcode=True, check=True)

for event in plan.value:
    print(event.get("@level"), event.get("@message"))
```

如果既有自动化强依赖本机安装的 Terraform binary，继续使用 CLI wrapper 可能迁移风险
更低。如果痛点是打包、binary 可用性、结构化结果或配置解析，`libterraform` 提供的是
另一种取舍。

## 相关页面

- [快速开始](quickstart.md)
- [并行执行](parallel-execution.md)
- [Plan 结果与流式输出](structured-and-streaming.md)
- [TerraformConfig API](api/terraform-config.md)
