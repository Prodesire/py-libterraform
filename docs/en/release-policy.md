# Release Policy

## Version Lines

libterraform minor versions track Terraform minor versions:

| libterraform line | Terraform line | Branch |
|---|---|---|
| `0.15.x` | `1.15.x` | `release/0.15` |
| `0.14.x` | `1.14.x` | `release/0.14` |
| `0.13.x` | `1.13.x` | `release/0.13` |

The exact version mapping is stored in `release-matrix.json`. The matrix is the source of truth; README tables and release notes are summaries.

## Branch Rules

- `main` carries the next Terraform minor adaptation.
- `release/0.x` carries patch work for libterraform `0.x.y`.
- A release branch must stay inside its Terraform minor line.
- Tags are created from the matching release branch and use `v0.x.y`.
- Keep all release branches, but actively maintain only the latest two lines by default.

## Patch Rules

Patch releases may include:

- A Terraform patch update inside the same Terraform minor line, such as `1.9.8` to `1.9.9`.
- A libterraform bugfix for the same Terraform minor line.
- A compatibility fix for Python, build tooling, or CI that does not change Terraform minor line.

Patch releases must not include:

- A Terraform minor upgrade.
- A Python API compatibility break.
- A release matrix change that points the branch outside its line.

## Backport Rules

Make shared fixes on `main` first. Cherry-pick them into active release branches after tests pass on `main`.

For a release-branch-only fix, commit directly on that release branch, then cherry-pick to `main` if it also applies to future lines.

## Release Checklist

Before tagging a release:

1. Update `release-matrix.json`.
2. Update `src/libterraform/__init__.py`.
3. Update `tests/consts.py`.
4. Update README examples and version table.
5. Ensure `upstream/terraform/` points at the intended Terraform tag.
6. Ensure `upstream/go-plugin/` points at the go-plugin version required by `upstream/terraform/go.mod`.
7. Run:

```bash
python scripts/verify_release_matrix.py
uv run pytest --color=yes
uv build --wheel
```

8. Create the release branch if it does not exist.
9. Tag from the release branch:

```bash
git tag -a v0.x.y -m "libterraform 0.x.y with Terraform 1.x.z"
```

10. Push the branch and tag. The tag triggers the release workflow.
