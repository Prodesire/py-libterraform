import json
from pathlib import Path

from scripts import inspect_upstream


ROOT = Path(__file__).resolve().parents[1]


def test_release_html_detects_latest_patch_and_next_minor_prereleases():
    html = """
    <a href="terraform_1.15.5/">terraform_1.15.5</a>
    <a href="terraform_1.15.6/">terraform_1.15.6</a>
    <a href="terraform_1.16.0-alpha20260610/">terraform_1.16.0-alpha20260610</a>
    <a href="terraform_1.14.9/">terraform_1.14.9</a>
    """

    versions = inspect_upstream.parse_release_versions(html)
    current = {
        "terraform_minor": "1.15",
        "terraform_version": "1.15.5",
    }

    report = inspect_upstream.inspect_release_versions(versions, current)

    assert report == {
        "current_minor": "1.15",
        "current_version": "1.15.5",
        "latest_patch": "1.15.6",
        "patch_update_available": True,
        "next_minor": "1.16",
        "next_minor_prereleases": ["1.16.0-alpha20260610"],
    }


def test_repository_inspection_reports_contract_gaps_as_structured_data():
    report = inspect_upstream.inspect_repository(ROOT)

    assert report["release_matrix"]["current"]["terraform_version"] == "1.15.5"
    assert report["command_contract"]["upstream_missing_in_bridge"] == []
    assert report["command_contract"]["bridge_extra_commands"] == []
    assert report["python_wrappers"]["missing_methods"] == []
    assert report["docs"]["missing_english_method_entries"] == []
    assert report["docs"]["missing_chinese_method_entries"] == []
    assert "cloud" in report["python_wrappers"]["intentionally_unwrapped_commands"]


def test_inspection_cli_outputs_json():
    output = inspect_upstream.main(["--root", str(ROOT), "--json"])

    report = json.loads(output)

    assert report["release_matrix"]["current"]["libterraform_version"] == "0.15.0"
    assert "command_contract" in report
