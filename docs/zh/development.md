# 开发指南

本项目构建的是一个携带 Terraform 共享库的 Python 包。Python 代码位于
`src/libterraform`，构建共享库需要的 Go 源码会在 wheel 构建阶段从
`upstream/` 和 `native/go/` 组合生成。

## 环境要求

- Python 3.9 到 3.14
- Go 1.21.5 或更新版本
- 支持 CGO 的 C 编译器
- `uv`

## 初始化

初始化 upstream 子模块：

```bash
git submodule init
git submodule update
```

安装 Python 开发依赖：

```bash
uv sync
```

Makefile 会同时安装本地 Git hooks：

```bash
make install
```

## 构建

从源码树运行会导入 `libterraform` 的测试前，需要先构建 wheel，因为
`src/libterraform/__init__.py` 在导入时会加载已编译的共享库：

```bash
uv build --wheel
```

Hatch 构建 hook：

1. 将 `native/go/plugin_patch.go` 复制到 `upstream/go-plugin/`。
2. 在 `upstream/terraform/go.mod` 中添加临时的 go-plugin `replace` 指令。
3. 将 `native/go/libterraform.go` 复制到 `upstream/terraform/`。
4. 执行 `go build -buildmode=c-shared`。
5. 将生成的共享库移动到 `src/libterraform/`。
6. 恢复临时修改的 upstream 文件。

如需在 macOS 上交叉构建 x86_64 共享库，可以设置 `TARGET_ARCH=amd64`。

## 测试和检查

运行测试：

```bash
uv run pytest --color=yes
```

或使用 Make：

```bash
make test
```

运行 Python 静态检查和 Go 桥接代码格式检查：

```bash
make lint
```

格式化 Python 文件和项目自有 Go 桥接文件：

```bash
make format
```

测试套件使用 `tests/tf/` 下的 Terraform fixtures。部分测试会执行真实的
Terraform state 行为，因此请先构建 wheel，并在发现测试失败时检查 stderr，
不要假设失败仅由 Python 引起。

## 文档站

文档站使用 Zensical 和 mkdocstrings。英文和中文分别作为独立 Zensical
项目构建，最终合并到同一个 GitHub Pages artifact。

本地预览：

```bash
make doc-serve
```

按 CI 严格模式构建：

```bash
make doc-build
```

英文站点写入 `site/`，中文站点写入 `site/zh/`。GitHub Pages workflow 会在
推送到 `main` 后部署合并后的 `site/` artifact。

## 仓库结构

```text
src/libterraform/       Python 包和公开 API
native/go/              构建时复制的 Go 桥接文件
upstream/terraform/     Terraform submodule
upstream/go-plugin/     构建时会被临时 patch 的 go-plugin submodule
tests/                  Python 测试和 Terraform fixtures
scripts/                构建、发布和校验脚本
docs/                   项目文档
```

## 更新 Terraform 版本

版本线策略见 [发布策略](release-policy.md)。实际更新 Terraform 时通常需要：

1. 更新 `release-matrix.json`。
2. 更新 `src/libterraform/__init__.py`。
3. 更新 `tests/consts.py`。
4. 更新 README 示例和版本对应表。
5. 将 `upstream/terraform/` 移动到目标 Terraform tag。
6. 将 `upstream/go-plugin/` 移动到 `upstream/terraform/go.mod` 要求的
   go-plugin 版本。
7. 运行矩阵校验、测试和 wheel 构建：

```bash
python scripts/verify_release_matrix.py
uv run pytest --color=yes
uv build --wheel
```

开始 Terraform 更新前，先检查上游漂移：

```bash
make inspect-upstream
```

该检查会读取当前 release matrix 条目，对比 Terraform 注册命令和 native bridge，
报告 Python wrapper 与文档缺口，并可读取 Terraform releases index 来识别 patch
更新和下一个 minor prerelease。

wheel 构建使用与 Python ABI 无关的平台 tag，例如
`py3-none-macosx_14_0_arm64` 和 `py3-none-manylinux_2_35_x86_64`，因为本包通过
`ctypes` 加载内置 Terraform 共享库，而不是 CPython extension module。发布构建期间，
Linux wheel tag 也会由 `scripts/normalize_wheel_tags.py` 作为防护统一规范化。
release workflow 每个平台目标只构建一个 distribution，并使用 Python 3.14 作为构建
环境，因为 wheel 与 Python ABI 无关。发布通过
`uv publish --trusted-publishing never` 和 `PYPI_TOKEN` secret 完成。

## 故障排查

如果导入 `libterraform` 时提示共享库缺失，先构建 wheel，或安装包含
`libterraform.so` / `libterraform.dll` 的已构建包。

如果构建 hook 报告缺少 upstream 目录，先初始化 Git submodule。

如果 Terraform 命令测试因为 provider 或 state 输出差异失败，使用 `-vv`
运行单个失败测试，并检查 `CommandResult.error` 或捕获的 stderr。Python
包装层主要负责参数转换和 stdout 解析，底层行为仍由 Terraform 决定。
