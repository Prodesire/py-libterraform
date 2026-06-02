from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def workflow_block(path, header):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    start = lines.index(header)
    block = []
    for line in lines[start + 1 :]:
        if line and not line.startswith(" "):
            break
        block.append(line)
    return block


def test_test_workflow_uses_representative_matrix():
    content = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")

    assert "os: [ ubuntu-22.04, windows-2022, macos-14 ]" in content
    assert "python-version: [ '3.14' ]" in content
    assert "include:" in content
    assert "os: ubuntu-22.04\n            python-version: '3.9'" in content
    assert (
        "python-version: [ '3.9', '3.10', '3.11', '3.12', '3.13', '3.14' ]"
        not in content
    )


def test_test_workflow_runs_on_branch_pushes_but_not_tag_pushes():
    block = workflow_block(ROOT / ".github" / "workflows" / "test.yml", "on:")

    assert "  push:" in block
    assert "    branches:" in block
    assert "      - '**'" in block
    assert "    tags-ignore:" in block
    assert "      - '*'" in block


def test_workflows_use_vendored_terraform_submodule_for_go_version():
    for workflow_name in ("test.yml", "release.yml"):
        content = (ROOT / ".github" / "workflows" / workflow_name).read_text(
            encoding="utf-8"
        )

        assert "go-version-file: vendor/terraform/go.mod" in content
        assert "go-version-file: terraform/go.mod" not in content
