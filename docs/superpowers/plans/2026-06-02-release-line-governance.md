# Release Line Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add release-line governance foundations so libterraform minor lines can track Terraform minor lines and patch releases can be made from stable release branches.

**Architecture:** Store compatibility intent in `release-matrix.json`, document branch/version policy in `docs/release-policy.md`, and verify repository state with a small Python script. CI and the build hook read repository state instead of relying on hard-coded Terraform-era assumptions.

**Tech Stack:** Python 3.9 stdlib, pytest, Hatchling build hook, Git submodules, GitHub Actions, Go.

---

### Task 1: Matrix Tests

**Files:**
- Create: `tests/test_release_matrix.py`

- [ ] **Step 1: Add failing tests for release matrix consistency**

Create tests that import `scripts/verify_release_matrix.py`, load `release-matrix.json`, and assert the current `0.8.x` line matches `pyproject.toml`, `terraform/version/VERSION`, and the `github.com/hashicorp/go-plugin` requirement in `terraform/go.mod`.

- [ ] **Step 2: Run the new tests**

Run: `uv run pytest --color=yes tests/test_release_matrix.py`

Expected before implementation: failure because the verification script and matrix do not exist.

### Task 2: Matrix Implementation

**Files:**
- Create: `release-matrix.json`
- Create: `scripts/verify_release_matrix.py`

- [ ] **Step 1: Add the matrix**

Record `0.8.x` as the released current line and `0.9.x` through `0.15.x` as planned Terraform-minor lines.

- [ ] **Step 2: Add the verifier**

Implement Python 3.9-compatible JSON and regex parsing. Do not depend on `tomllib`.

- [ ] **Step 3: Re-run the matrix tests**

Run: `uv run pytest --color=yes tests/test_release_matrix.py`

Expected after implementation: pass.

### Task 3: Build Hook Guardrail

**Files:**
- Modify: `hatch_build.py`
- Create: `tests/test_hatch_build.py`

- [ ] **Step 1: Add failing tests for go-plugin version parsing**

Test that the build hook can parse `github.com/hashicorp/go-plugin v1.6.0` from Terraform `go.mod` content and raises a clear error when missing.

- [ ] **Step 2: Implement dynamic go-plugin replacement**

Replace the hard-coded `v1.4.3` in `hatch_build.py` with parsed module version logic.

- [ ] **Step 3: Re-run hook tests**

Run: `uv run pytest --color=yes tests/test_hatch_build.py`

Expected after implementation: pass.

### Task 4: Exact Terraform Version Tests

**Files:**
- Modify: `tests/consts.py`
- Modify: `tests/cli/test_version.py`

- [ ] **Step 1: Add exact expected Terraform version assertion**

Make `tests/cli/test_version.py` assert Terraform `1.8.4` on the current line.

- [ ] **Step 2: Re-run version tests**

Run: `uv run pytest --color=yes tests/cli/test_version.py`

Expected after implementation: pass.

### Task 5: Release Policy and CI

**Files:**
- Create: `docs/release-policy.md`
- Modify: `.github/workflows/test.yml`
- Modify: `.github/workflows/release.yml`

- [ ] **Step 1: Document release branch policy**

Write branch rules, tag rules, patch rules, active maintenance rules, and the `0.9.0` release checklist.

- [ ] **Step 2: Update CI submodule and Go setup**

Use `actions/checkout` with `submodules: recursive` before `actions/setup-go`, and configure `setup-go` with `go-version-file: terraform/go.mod`.

- [ ] **Step 3: Run focused local validation**

Run:

```bash
uv run pytest --color=yes tests/test_release_matrix.py tests/test_hatch_build.py tests/cli/test_version.py
python scripts/verify_release_matrix.py
```

Expected after implementation: all commands exit with status `0`.

### Task 6: Release Branch Preparation

**Files:**
- No file edits required.

- [ ] **Step 1: Create local maintenance branch if missing**

Run:

```bash
git branch release/0.8
```

Expected if missing: branch is created at the current commit. If it already exists, skip this step.

- [ ] **Step 2: Prepare next release line after guardrails pass**

Create `release/0.9` only after the Terraform `1.9.x` adaptation commit is ready. Tags for `v0.9.0` must come from `release/0.9`.

