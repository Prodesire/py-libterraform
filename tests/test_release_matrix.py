import importlib.util
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_verify_module():
    module_path = ROOT / "scripts" / "verify_release_matrix.py"
    spec = importlib.util.spec_from_file_location("verify_release_matrix", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_release_matrix_matches_checked_out_repository():
    verifier = load_verify_module()

    assert verifier.verify(ROOT) == []

    matrix = verifier.load_matrix(ROOT / "release-matrix.json")
    project_version = verifier.read_project_version(ROOT / "pyproject.toml")
    entry = verifier.current_entry(matrix, project_version)

    assert entry["libterraform_minor"] == verifier.minor_from_version(project_version)
    assert entry["libterraform_version"] == project_version
    assert entry["status"] == "released"
    assert entry["maintenance"] == "active"
    assert entry["terraform_version"] == verifier.read_terraform_version(
        ROOT / "upstream" / "terraform" / "version" / "VERSION"
    )
    assert entry["go_plugin_version"] == verifier.read_required_module_version(
        ROOT / "upstream" / "terraform" / "go.mod",
        "github.com/hashicorp/go-plugin",
    ).removeprefix("v")
    assert entry["branch"] == f"release/{entry['libterraform_minor']}"


def test_project_version_is_loaded_from_package_init():
    verifier = load_verify_module()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package_init = (ROOT / "src" / "libterraform" / "__init__.py").read_text(
        encoding="utf-8"
    )
    match = re.search(r'^__version__ = "([^"]+)"', package_init, re.MULTILINE)

    assert re.search(r"^version\s*=", pyproject, re.MULTILINE) is None
    assert 'dynamic = ["version"]' in pyproject
    assert "[tool.hatch.version]" in pyproject
    assert 'path = "src/libterraform/__init__.py"' in pyproject
    assert match is not None
    assert verifier.read_project_version(ROOT / "pyproject.toml") == match.group(1)


def test_planned_release_lines_have_scoped_branches():
    verifier = load_verify_module()
    matrix = verifier.load_matrix(ROOT / "release-matrix.json")

    releases = matrix["releases"]
    by_minor = {entry["libterraform_minor"]: entry for entry in releases}

    assert by_minor["0.9"]["terraform_minor"] == "1.9"
    assert by_minor["0.9"]["terraform_version"] == "1.9.8"
    for entry in releases:
        assert entry["branch"] == f"release/{entry['libterraform_minor']}"
        assert entry["status"] in {"released", "planned"}
        assert entry["maintenance"] in {"active", "passive", "planned"}


def test_submodules_live_under_upstream():
    gitmodules = (ROOT / ".gitmodules").read_text(encoding="utf-8")

    assert "\tpath = upstream/terraform" in gitmodules
    assert "\tpath = upstream/go-plugin" in gitmodules
    assert not (ROOT / "vendor").exists()
    assert not (ROOT / "terraform").exists()
    assert not (ROOT / "go-plugin").exists()
