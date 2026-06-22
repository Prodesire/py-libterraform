# 安装

从 PyPI 安装：

```bash
pip install libterraform
```

## 支持的 Python 版本

当前包支持 Python 3.9 到 3.14。

## 平台说明

wheel 会在 POSIX 平台携带 `libterraform.so`，在 Windows 平台携带
`libterraform.dll`。导入 `libterraform` 时会立即加载该共享库。

从源码仓库开发时，需要先构建 wheel，确保共享库出现在
`src/libterraform/` 下：

```bash
uv build --wheel
```
