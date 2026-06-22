# Python libterraform

<p align="center">
  <img src="../assets/py-libterraform-logo.png" alt="Python libterraform logo" width="180" />
</p>

`libterraform` 是 Terraform 的 Python 绑定。它把 Terraform 打包为共享库，
并提供 Python API 来执行 Terraform CLI 命令、解析 Terraform 配置目录。

## 提供能力

- `TerraformCommand`：从 Python 调用 Terraform 命令。
- `AsyncTerraformCommand`：在 asyncio 应用中等待 Terraform 命令，同时避免阻塞
  event loop。
- `TerraformConfig`：把 `.tf` 和 `.tf.json` 文件加载为 Terraform 内部模块表示。
- 预构建 wheel 内包含 Terraform 共享库，调用方通常不需要在 `PATH` 中额外安装
  `terraform` 可执行文件。

## 从这里开始

- [安装](installation.md)
- [快速开始](quickstart.md)
- [API 参考](api/index.md)
- [开发指南](development.md)
- [发布策略](release-policy.md)
- [版本对应关系](#_3)

## 版本对应关系

| libterraform | Terraform |
|---|---|
| [0.15.0](https://pypi.org/project/libterraform/0.15.0/) | [1.15.5](https://github.com/hashicorp/terraform/tree/v1.15.5) |
| [0.14.0](https://pypi.org/project/libterraform/0.14.0/) | [1.14.9](https://github.com/hashicorp/terraform/tree/v1.14.9) |
| [0.13.0](https://pypi.org/project/libterraform/0.13.0/) | [1.13.5](https://github.com/hashicorp/terraform/tree/v1.13.5) |
| [0.12.0](https://pypi.org/project/libterraform/0.12.0/) | [1.12.2](https://github.com/hashicorp/terraform/tree/v1.12.2) |
| [0.11.0](https://pypi.org/project/libterraform/0.11.0/) | [1.11.4](https://github.com/hashicorp/terraform/tree/v1.11.4) |
| [0.10.0](https://pypi.org/project/libterraform/0.10.0/) | [1.10.5](https://github.com/hashicorp/terraform/tree/v1.10.5) |
| [0.9.0](https://pypi.org/project/libterraform/0.9.0/) | [1.9.8](https://github.com/hashicorp/terraform/tree/v1.9.8) |
| [0.8.2](https://pypi.org/project/libterraform/0.8.2/) | [1.8.4](https://github.com/hashicorp/terraform/tree/v1.8.4) |
| [0.7.0](https://pypi.org/project/libterraform/0.7.0/) | [1.6.6](https://github.com/hashicorp/terraform/tree/v1.6.6) |
| [0.6.0](https://pypi.org/project/libterraform/0.6.0/) | [1.5.7](https://github.com/hashicorp/terraform/tree/v1.5.7) |
| [0.5.0](https://pypi.org/project/libterraform/0.5.0/) | [1.3.0](https://github.com/hashicorp/terraform/tree/v1.3.0) |
| [0.4.0](https://pypi.org/project/libterraform/0.4.0/) | [1.2.2](https://github.com/hashicorp/terraform/tree/v1.2.2) |
| [0.3.1](https://pypi.org/project/libterraform/0.3.1/) | [1.1.7](https://github.com/hashicorp/terraform/tree/v1.1.7) |

## 运行约束

`TerraformCommand` 可以被多个 Python 线程安全调用，但 Terraform CLI 会在共享库
内部串行执行。Terraform 仍使用当前工作目录、stdio、checkpoint 状态和 plugin
client 清理等进程级全局状态，因此真正并行的 Terraform 操作需要使用多个进程隔离。

`AsyncTerraformCommand` 也遵循同样的 Terraform 执行约束。它让同步 API 可以在
asyncio 应用中被 `await`，但不会让同一个 Python 进程内的 Terraform CLI 执行变成
真正并行。

Terraform 操作仍可能影响真实基础设施，因此执行 `apply`、`destroy`、状态命令、
导入和测试时，应保持与直接使用 Terraform CLI 相同的谨慎程度。
