import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_verify_module():
    module_path = ROOT / "scripts" / "verify_release_matrix.py"
    spec = importlib.util.spec_from_file_location("verify_release_matrix", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_release_matrix_matches_checked_out_repository():
    verifier = load_verify_module()

    matrix = verifier.load_matrix(ROOT / "release-matrix.json")
    project_version = verifier.read_project_version(ROOT / "pyproject.toml")
    entry = verifier.current_entry(matrix, project_version)

    assert entry["libterraform_minor"] == "0.8"
    assert entry["libterraform_version"] == project_version
    assert entry["terraform_version"] == verifier.read_terraform_version(
        ROOT / "terraform" / "version" / "VERSION"
    )
    assert entry["go_plugin_version"] == verifier.read_required_module_version(
        ROOT / "terraform" / "go.mod",
        "github.com/hashicorp/go-plugin",
    ).removeprefix("v")
    assert entry["branch"] == "release/0.8"


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

