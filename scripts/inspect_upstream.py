#!/usr/bin/env python3
import argparse
import ast
import json
import re
import urllib.request
from pathlib import Path


RELEASE_RE = re.compile(r"terraform_([0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?)")
COMMAND_RE = re.compile(r'^\s*"([^"]+)":\s*(?:func\(\)|rpcapi\.)', re.MULTILINE)
COMMAND_ASSIGN_RE = re.compile(r'^\s*[Cc]ommands?\["([^"]+)"\]\s*=', re.MULTILINE)

INTENTIONALLY_UNWRAPPED_COMMANDS = {
    "cloud",
    "console",
    "env",
    "env delete",
    "env list",
    "env new",
    "env select",
    "login",
    "logout",
    "metadata",
    "metadata functions",
    "push",
    "rpcapi",
    "test cleanup",
}


def parse_release_versions(html):
    return sorted(set(RELEASE_RE.findall(html)), key=version_sort_key)


def version_parts(version):
    main, _, prerelease = version.partition("-")
    major, minor, patch = (int(part) for part in main.split("."))
    return major, minor, patch, prerelease


def version_sort_key(version):
    major, minor, patch, prerelease = version_parts(version)
    prerelease_key = (1, "") if not prerelease else (0, prerelease)
    return major, minor, patch, prerelease_key


def version_minor(version):
    major, minor, _, _ = version_parts(version)
    return f"{major}.{minor}"


def minor_key(minor):
    major, minor_part = minor.split(".")
    return int(major), int(minor_part)


def inspect_release_versions(versions, current):
    current_minor = current["terraform_minor"]
    current_version = current["terraform_version"]
    stable_current_line = [
        version
        for version in versions
        if version_minor(version) == current_minor and "-" not in version
    ]
    latest_patch = stable_current_line[-1] if stable_current_line else None

    prerelease_by_minor = {}
    for version in versions:
        minor = version_minor(version)
        if "-" not in version or minor_key(minor) <= minor_key(current_minor):
            continue
        prerelease_by_minor.setdefault(minor, []).append(version)

    next_minor = (
        min(prerelease_by_minor, key=minor_key) if prerelease_by_minor else None
    )

    return {
        "current_minor": current_minor,
        "current_version": current_version,
        "latest_patch": latest_patch,
        "patch_update_available": latest_patch is not None
        and latest_patch != current_version,
        "next_minor": next_minor,
        "next_minor_prereleases": prerelease_by_minor.get(next_minor, []),
    }


def read_project_version(root):
    package_init = (root / "src" / "libterraform" / "__init__.py").read_text(
        encoding="utf-8"
    )
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', package_init, re.MULTILINE)
    if match is None:
        raise RuntimeError(
            "Cannot find package version in src/libterraform/__init__.py"
        )
    return match.group(1)


def load_current_matrix_entry(root):
    matrix = json.loads((root / "release-matrix.json").read_text(encoding="utf-8"))
    project_version = read_project_version(root)
    project_minor = ".".join(project_version.split(".")[:2])
    for entry in matrix["releases"]:
        if entry["libterraform_minor"] == project_minor:
            return entry
    raise RuntimeError(f"No release matrix entry for libterraform {project_minor}.x")


def extract_registered_commands(source):
    return sorted(
        set(COMMAND_RE.findall(source)) | set(COMMAND_ASSIGN_RE.findall(source))
    )


def python_method_for_command(command):
    if command == "import":
        return "import_resource"
    return command.replace("-", "_").replace(" ", "_")


def public_methods(root):
    source = (root / "src" / "libterraform" / "cli.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == "TerraformCommand":
            return {
                item.name
                for item in node.body
                if isinstance(item, ast.FunctionDef) and not item.name.startswith("_")
            }
    raise RuntimeError("TerraformCommand class not found")


def missing_doc_entries(root, methods, language):
    path = root / "docs" / language / "api" / "terraform-command.md"
    page = path.read_text(encoding="utf-8")
    class_directive = "::: libterraform.cli.TerraformCommand"
    if language == "en" and class_directive in page:
        return []
    return sorted(
        method
        for method in methods
        if f"::: libterraform.cli.TerraformCommand.{method}" not in page
    )


def inspect_repository(root, releases_html=None):
    root = Path(root)
    current_entry = load_current_matrix_entry(root)

    upstream_commands = extract_registered_commands(
        (root / "upstream" / "terraform" / "commands.go").read_text(encoding="utf-8")
    )
    bridge_commands = extract_registered_commands(
        (root / "native" / "go" / "libterraform.go").read_text(encoding="utf-8")
    )
    method_names = public_methods(root)
    missing_methods = []
    for command in bridge_commands:
        if command in INTENTIONALLY_UNWRAPPED_COMMANDS:
            continue
        method = python_method_for_command(command)
        if method not in method_names:
            missing_methods.append({"command": command, "expected_method": method})

    report = {
        "release_matrix": {
            "current": current_entry,
        },
        "command_contract": {
            "upstream_missing_in_bridge": sorted(
                set(upstream_commands) - set(bridge_commands)
            ),
            "bridge_extra_commands": sorted(
                set(bridge_commands) - set(upstream_commands)
            ),
            "upstream_commands": upstream_commands,
            "bridge_commands": bridge_commands,
        },
        "python_wrappers": {
            "missing_methods": missing_methods,
            "intentionally_unwrapped_commands": sorted(
                INTENTIONALLY_UNWRAPPED_COMMANDS & set(bridge_commands)
            ),
        },
        "docs": {
            "missing_english_method_entries": missing_doc_entries(
                root, method_names, "en"
            ),
            "missing_chinese_method_entries": missing_doc_entries(
                root, method_names, "zh"
            ),
        },
    }

    if releases_html:
        versions = parse_release_versions(releases_html)
        report["terraform_releases"] = inspect_release_versions(versions, current_entry)

    return report


def fetch_text(url):
    with urllib.request.urlopen(url, timeout=20) as response:
        return response.read().decode("utf-8")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Inspect upstream Terraform drift and local bridge coverage."
    )
    parser.add_argument(
        "--root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Repository root to inspect.",
    )
    parser.add_argument(
        "--releases-url",
        help="Optional Terraform releases index URL to inspect.",
    )
    parser.add_argument(
        "--releases-html",
        type=Path,
        help="Optional saved Terraform releases HTML file.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    releases_html = None
    if args.releases_html:
        releases_html = args.releases_html.read_text(encoding="utf-8")
    elif args.releases_url:
        releases_html = fetch_text(args.releases_url)

    report = inspect_repository(args.root, releases_html=releases_html)
    if args.json:
        output = json.dumps(report, indent=2, sort_keys=True)
    else:
        current = report["release_matrix"]["current"]
        lines = [
            f"libterraform {current['libterraform_version']} -> Terraform {current['terraform_version']}",
            "command contract:",
            f"  upstream missing in bridge: {report['command_contract']['upstream_missing_in_bridge']}",
            f"  bridge extra commands: {report['command_contract']['bridge_extra_commands']}",
            f"python wrapper gaps: {report['python_wrappers']['missing_methods']}",
            "docs gaps:",
            f"  en: {report['docs']['missing_english_method_entries']}",
            f"  zh: {report['docs']['missing_chinese_method_entries']}",
        ]
        if "terraform_releases" in report:
            releases = report["terraform_releases"]
            lines.extend(
                [
                    "terraform releases:",
                    f"  latest patch: {releases['latest_patch']}",
                    f"  patch update available: {releases['patch_update_available']}",
                    f"  next minor prereleases: {releases['next_minor_prereleases']}",
                ]
            )
        output = "\n".join(lines)

    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    main()
