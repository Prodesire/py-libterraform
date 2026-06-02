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


def test_workflows_use_upstream_terraform_submodule_for_go_version():
    for workflow_name in ("test.yml", "release.yml"):
        content = (ROOT / ".github" / "workflows" / workflow_name).read_text(
            encoding="utf-8"
        )

        assert "go-version-file: upstream/terraform/go.mod" in content
        assert "go-version-file: vendor/terraform/go.mod" not in content
        assert "go-version-file: terraform/go.mod" not in content


def test_release_workflow_runs_tests_before_publishing():
    content = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    build_job = content.split("  build-macos-x64:", maxsplit=1)[0]
    macos_x64_job = content.split("  build-macos-x64:", maxsplit=1)[1].split(
        "  publish:",
        maxsplit=1,
    )[0]
    publish_job = content.split("  publish:", maxsplit=1)[1]

    assert (
        "      - name: Run tests\n        run: |\n          uv run pytest\n"
    ) in build_job
    assert build_job.index("uv build --wheel") < build_job.index("uv run pytest")
    assert build_job.index("uv run pytest") < build_job.index(
        "Upload distribution artifacts"
    )
    assert "uv run pytest" not in macos_x64_job
    assert "uv run pytest" not in publish_job


def test_release_workflow_retries_pypi_publish_three_times():
    content = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    publish_job = content.split("  publish:", maxsplit=1)[1]

    assert "for attempt in 1 2 3; do" in publish_job
    assert "uv publish --check-url https://pypi.org/simple/ dist/* && exit 0" in (
        publish_job
    )
    assert 'if [ "$attempt" -lt 3 ]; then' in publish_job
    assert "exit 1" in publish_job
