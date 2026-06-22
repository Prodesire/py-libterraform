# API 参考

包根路径导出以下公开接口：

```python
from libterraform import (
    AsyncTerraformCommand,
    TerraformCommand,
    TerraformConfig,
    TerraformPool,
)
```

异常类位于 `libterraform.exceptions`。

## 页面

- [TerraformCommand](terraform-command.md)：命令执行、`CommandResult`、
  参数转换、JSON 解析和 Terraform CLI 辅助方法。
- [AsyncTerraformCommand](async-terraform-command.md)：面向 asyncio 应用的异步
  兼容命令执行。
- [TerraformPool](terraform-pool.md)：基于多进程的 Terraform 命令并行执行。
- [结果与流式](results.md)：结构化的 `PlanResult` / `ApplyResult` 类型，以及
  `TerraformStream` 流式辅助类型。
- [TerraformConfig](terraform-config.md)：Terraform 配置解析。
- [异常](exceptions.md)：包内异常类型。

参考页面通过 mkdocstrings 从 Python 源码生成接口结构。中文页维护中文说明，
并在生成接口时隐藏英文 docstring，避免中英文混排。
