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
    for workflow_name in ("test.yml", "release.yml", "docs.yml"):
        content = (ROOT / ".github" / "workflows" / workflow_name).read_text(
            encoding="utf-8"
        )

        assert "actions/setup-go@v6" in content
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
        "      - name: Run tests\n"
        "        timeout-minutes: 15\n"
        "        run: |\n"
        "          uv run python -X faulthandler -m pytest -vv "
        "--durations=20 --timeout=120 --timeout-method=thread\n"
    ) in build_job
    assert build_job.index("uv build --wheel") < build_job.index(
        "python -X faulthandler -m pytest"
    )
    assert build_job.index("python -X faulthandler -m pytest") < build_job.index(
        "Upload distribution artifacts"
    )
    assert "python -X faulthandler -m pytest" not in macos_x64_job
    assert "python -X faulthandler -m pytest" not in publish_job


def test_workflows_run_pytest_with_hang_diagnostics():
    expected = (
        "      - name: Run tests\n"
        "        timeout-minutes: 15\n"
        "        run: |\n"
        "          uv run python -X faulthandler -m pytest -vv "
        "--durations=20 --timeout=120 --timeout-method=thread\n"
    )

    for workflow_name in ("test.yml", "release.yml"):
        content = (ROOT / ".github" / "workflows" / workflow_name).read_text(
            encoding="utf-8"
        )

        assert expected in content


def test_release_workflow_retries_pypi_publish_three_times():
    content = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    publish_job = content.split("  publish:", maxsplit=1)[1]

    assert "for attempt in 1 2 3; do" in publish_job
    assert (
        "uv publish --trusted-publishing automatic "
        "--check-url https://pypi.org/simple/ dist/* && exit 0"
    ) in publish_job
    assert 'if [ "$attempt" -lt 3 ]; then' in publish_job
    assert "exit 1" in publish_job


def test_release_workflow_uses_trusted_publishing_without_pypi_token():
    content = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    publish_job = content.split("  publish:", maxsplit=1)[1]

    assert "permissions:" in publish_job
    assert "id-token: write" in publish_job
    assert "contents: write" in publish_job
    assert "environment:" in publish_job
    assert "name: pypi" in publish_job
    assert "UV_PUBLISH_TOKEN" not in publish_job
    assert "secrets.PYPI_TOKEN" not in publish_job
    assert "--trusted-publishing automatic" in publish_job


def test_release_workflow_normalizes_linux_wheel_tags_with_script():
    content = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert "python scripts/normalize_wheel_tags.py dist" in content
    assert "sed 's/linux_/manylinux_2_35_/'" not in content
