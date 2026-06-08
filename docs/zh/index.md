# Python libterraform

`libterraform` 是 Terraform 的 Python 绑定。它把 Terraform 打包为共享库，
并提供 Python API 来执行 Terraform CLI 命令、解析 Terraform 配置目录。

## 提供能力

- `TerraformCommand`：从 Python 调用 Terraform 命令。
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
| [0.11.0](https://pypi.org/project/libterraform/0.11.0/) | [1.11.4](https://github.com/hashicorp/terraform/tree/v1.11.4) |
| [0.10.0](https://pypi.org/project/libterraform/0.10.0/) | [1.10.5](https://github.com/hashicorp/terraform/tree/v1.10.5) |
| [0.9.0](https://pypi.org/project/libterraform/0.9.0/) | [1.9.8](https://github.com/hashicorp/terraform/tree/v1.9.8) |
| [0.8.0](https://pypi.org/project/libterraform/0.8.0/) | [1.8.4](https://github.com/hashicorp/terraform/tree/v1.8.4) |
| [0.7.0](https://pypi.org/project/libterraform/0.7.0/) | [1.6.6](https://github.com/hashicorp/terraform/tree/v1.6.6) |
| [0.6.0](https://pypi.org/project/libterraform/0.6.0/) | [1.5.7](https://github.com/hashicorp/terraform/tree/v1.5.7) |
| [0.5.0](https://pypi.org/project/libterraform/0.5.0/) | [1.3.0](https://github.com/hashicorp/terraform/tree/v1.3.0) |
| [0.4.0](https://pypi.org/project/libterraform/0.4.0/) | [1.2.2](https://github.com/hashicorp/terraform/tree/v1.2.2) |
| [0.3.1](https://pypi.org/project/libterraform/0.3.1/) | [1.1.7](https://github.com/hashicorp/terraform/tree/v1.1.7) |

## 运行约束

`libterraform` 当前不支持多线程调用。Terraform 操作仍可能影响真实基础设施，
因此执行 `apply`、`destroy`、状态命令、导入和测试时，应保持与直接使用
Terraform CLI 相同的谨慎程度。
