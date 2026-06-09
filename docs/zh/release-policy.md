# 发布策略

## 版本线

libterraform 的 minor 版本跟随 Terraform 的 minor 版本：

| libterraform 版本线 | Terraform 版本线 | 分支 |
|---|---|---|
| `0.13.x` | `1.13.x` | `release/0.13` |
| `0.12.x` | `1.12.x` | `release/0.12` |
| `0.11.x` | `1.11.x` | `release/0.11` |

准确的版本映射存放在 `release-matrix.json`。该矩阵是事实来源；README
表格和 release notes 只是摘要。

## 分支规则

- `main` 承载下一个 Terraform minor 版本适配。
- `release/0.x` 承载 libterraform `0.x.y` 的 patch 工作。
- release 分支必须保持在自己的 Terraform minor 版本线内。
- tag 从匹配的 release 分支创建，格式为 `v0.x.y`。
- 保留所有 release 分支，但默认只主动维护最近两条版本线。

## 补丁规则

patch release 可以包含：

- 同一 Terraform minor 版本线内的 Terraform patch 更新，例如从 `1.9.8`
  更新到 `1.9.9`。
- 同一 Terraform minor 版本线内的 libterraform bugfix。
- 不改变 Terraform minor 版本线的 Python、构建工具或 CI 兼容性修复。

patch release 不应包含：

- Terraform minor 升级。
- Python API 兼容性破坏。
- 指向分支所属版本线之外的 release matrix 变更。

## 回移规则

共享修复先合入 `main`。在 `main` 测试通过后，再 cherry-pick 到仍在维护的
release 分支。

如果某个修复只适用于 release 分支，可以直接提交到该 release 分支；如果它
同样适用于未来版本线，再 cherry-pick 回 `main`。

## 发布检查清单

打 tag 前需要：

1. 更新 `release-matrix.json`。
2. 更新 `src/libterraform/__init__.py`。
3. 更新 `tests/consts.py`。
4. 更新 README 示例和版本对应表。
5. 确认 `upstream/terraform/` 指向目标 Terraform tag。
6. 确认 `upstream/go-plugin/` 指向 `upstream/terraform/go.mod` 要求的
   go-plugin 版本。
7. 运行：

```bash
python scripts/verify_release_matrix.py
uv run pytest --color=yes
uv build --wheel
```

8. 如果 release 分支不存在，创建它。
9. 从 release 分支创建 tag：

```bash
git tag -a v0.x.y -m "libterraform 0.x.y with Terraform 1.x.z"
```

10. 推送分支和 tag。tag 会触发 release workflow。
