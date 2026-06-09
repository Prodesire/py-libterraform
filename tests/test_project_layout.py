from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_python_package_uses_src_layout():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'packages = ["src/libterraform"]' in pyproject
    assert (
        'artifacts = ["src/libterraform/libterraform.so", "src/libterraform/libterraform.dll"]'
        in pyproject
    )
    assert (ROOT / "src" / "libterraform" / "__init__.py").exists()
    assert not (ROOT / "libterraform").exists()


def test_native_go_sources_are_not_at_repository_root():
    assert (ROOT / "native" / "go" / "libterraform.go").exists()
    assert (ROOT / "native" / "go" / "plugin_patch.go").exists()
    assert not (ROOT / "libterraform.go").exists()
    assert not (ROOT / "plugin_patch.go").exists()


def test_makefile_lints_and_formats_project_owned_go_sources():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "GO_CHECK_PATHS=native/go" in makefile
    assert "gofmt -l $(GO_CHECK_PATHS)" in makefile
    assert "gofmt -w $(GO_CHECK_PATHS)" in makefile
    assert "upstream/terraform" not in makefile
    assert "upstream/go-plugin" not in makefile
