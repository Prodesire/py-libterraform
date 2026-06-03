<h1 align="center">Python libterraform</h1>

<p align="center">
  <em><a href="https://www.terraform.io/">Terraform</a> 的 Python 绑定。将 Terraform 打包为共享库，无需单独安装 <code>terraform</code> 即可从 Python 执行 Terraform 命令和解析配置。</em>
</p>

<p align="center">
  <a href="https://github.com/Prodesire/py-libterraform/actions/workflows/test.yml"><img src="https://github.com/Prodesire/py-libterraform/actions/workflows/test.yml/badge.svg" alt="Test"></a>
  <a href="https://pypi.python.org/pypi/libterraform"><img src="https://img.shields.io/pypi/v/libterraform.svg" alt="PyPI"></a>
  <a href="https://pypi.python.org/pypi/libterraform"><img src="https://img.shields.io/pypi/pyversions/libterraform.svg" alt="Python"></a>
  <a href="https://pypi.python.org/pypi/libterraform"><img src="https://img.shields.io/pypi/dm/libterraform" alt="Downloads"></a>
</p>

<p align="center">
  <strong>语言：</strong> <a href="README.md">English</a> | 中文
</p>

> **文档：** https://prodesire.github.io/py-libterraform/zh/

## 安装

```bash
pip install libterraform
```

> **注意：** 当前版本不支持多线程调用。

## 使用

```python
from libterraform import TerraformCommand, TerraformConfig

# 执行 Terraform 命令
cli = TerraformCommand("path/to/module")
cli.init(check=True)
cli.plan(check=True)

# 解析 Terraform 配置
module, diagnostics = TerraformConfig.load_config_dir("path/to/module")
```

## 贡献

安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)，然后：

```bash
make install        # 安装依赖和 Git hooks
make build          # 构建共享库
make test           # 运行测试
make lint           # 运行检查
make doc-serve      # 预览文档站
```

详见[开发指南](https://prodesire.github.io/py-libterraform/zh/development/)。
