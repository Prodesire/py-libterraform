#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


VALID_STATUSES = {"released", "planned"}
VALID_MAINTENANCE = {"active", "passive", "planned"}


def load_matrix(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_project_version(path):
    content = Path(path).read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if match is None:
        raise RuntimeError(f"Cannot find project version in {path}")
    return match.group(1)


def read_terraform_version(path):
    return Path(path).read_text(encoding="utf-8").strip()


def read_required_module_version(path, module_name):
    content = Path(path).read_text(encoding="utf-8")
    module_pattern = re.escape(module_name)
    match = re.search(rf"^\s*{module_pattern}\s+(v\S+)", content, re.MULTILINE)
    if match is None:
        raise RuntimeError(f"Cannot find {module_name} in {path}")
    return match.group(1)


def minor_from_version(version):
    parts = version.split(".")
    if len(parts) < 2:
        raise RuntimeError(f"Invalid semantic version: {version}")
    return ".".join(parts[:2])


def current_entry(matrix, project_version):
    project_minor = minor_from_version(project_version)
    for entry in matrix["releases"]:
        if entry["libterraform_minor"] == project_minor:
            return entry
    raise RuntimeError(f"No release matrix entry for libterraform {project_minor}.x")


def validate_release_entries(matrix):
    errors = []
    seen_minors = set()
    for entry in matrix.get("releases", []):
        minor = entry.get("libterraform_minor")
        if minor in seen_minors:
            errors.append(f"Duplicate libterraform minor entry: {minor}")
        seen_minors.add(minor)

        expected_branch = f"release/{minor}"
        if entry.get("branch") != expected_branch:
            errors.append(f"{minor}: branch must be {expected_branch}")
        if entry.get("status") not in VALID_STATUSES:
            errors.append(f"{minor}: invalid status {entry.get('status')!r}")
        if entry.get("maintenance") not in VALID_MAINTENANCE:
            errors.append(f"{minor}: invalid maintenance {entry.get('maintenance')!r}")
    return errors


def verify(root):
    errors = validate_release_entries(load_matrix(root / "release-matrix.json"))
    matrix = load_matrix(root / "release-matrix.json")
    project_version = read_project_version(root / "pyproject.toml")
    entry = current_entry(matrix, project_version)

    if entry["libterraform_version"] != project_version:
        errors.append(
            "Current matrix entry version "
            f"{entry['libterraform_version']} does not match pyproject {project_version}"
        )

    terraform_version = read_terraform_version(
        root / "vendor" / "terraform" / "version" / "VERSION"
    )
    if entry["terraform_version"] != terraform_version:
        errors.append(
            "Current matrix entry Terraform version "
            f"{entry['terraform_version']} does not match checked-out {terraform_version}"
        )

    go_plugin_version = read_required_module_version(
        root / "vendor" / "terraform" / "go.mod",
        "github.com/hashicorp/go-plugin",
    ).removeprefix("v")
    if entry["go_plugin_version"] != go_plugin_version:
        errors.append(
            "Current matrix entry go-plugin version "
            f"{entry['go_plugin_version']} does not match "
            f"vendor/terraform/go.mod {go_plugin_version}"
        )

    return errors


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    root = Path(argv[0]) if argv else Path(__file__).resolve().parents[1]
    errors = verify(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("release matrix verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
