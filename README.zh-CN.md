<p align="center">
  <img src="docs/assets/py-libterraform-logo.png" alt="Python libterraform logo" width="180">
</p>

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

> **线程说明：** `TerraformCommand` 可以被多个 Python 线程调用，但由于
> Terraform CLI 使用进程级全局状态，共享库内部会串行执行 Terraform 命令。如需
> 真正并行的 Terraform 操作，请使用 `TerraformPool`（或多个进程隔离）。

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

asyncio 应用可以使用 `AsyncTerraformCommand` 等待 Terraform 操作，同时避免阻塞
event loop：

```python
from libterraform import AsyncTerraformCommand

cli = AsyncTerraformCommand("path/to/module")
await cli.validate(check=True)
```

使用 `TerraformPool` 可以在多个 worker 进程间并行执行 Terraform 命令：

```python
from libterraform import TerraformPool

with TerraformPool(max_workers=4) as pool:
    for result in pool.map("validate", ["modules/a", "modules/b"], check=True):
        print(result.value["valid"])
```

pool 会启动 worker 进程，因此上述代码必须运行在 `if __name__ == "__main__":`
保护之下。[快速开始](https://prodesire.github.io/py-libterraform/zh/quickstart/)
可在几秒内创建一个可运行的模块，[并行执行](https://prodesire.github.io/py-libterraform/zh/parallel-execution/)
提供了完整的 pool 示例。

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
