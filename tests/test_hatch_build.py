import pytest

from pathlib import Path

from scripts import hatch_build


ROOT = Path(__file__).resolve().parents[1]


def test_build_hook_lives_under_scripts():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert 'path = "scripts/hatch_build.py"' in pyproject
    assert "hatch_build.py scripts" not in makefile
    assert "scripts" in makefile
    assert (ROOT / "scripts" / "hatch_build.py").exists()
    assert not (ROOT / "hatch_build.py").exists()


def test_build_hook_resolves_repository_root_from_scripts_dir():
    assert Path(hatch_build.repository_root()) == ROOT


def test_build_hook_uses_upstream_submodule_paths():
    terraform_dirname, plugin_dirname = hatch_build.submodule_paths(str(ROOT))

    assert Path(terraform_dirname) == ROOT / "upstream" / "terraform"
    assert Path(plugin_dirname) == ROOT / "upstream" / "go-plugin"


def test_build_hook_uses_native_go_sources():
    tf_path, plugin_patch_path = hatch_build.native_go_source_paths(str(ROOT))

    assert Path(tf_path) == ROOT / "native" / "go" / "libterraform.go"
    assert Path(plugin_patch_path) == ROOT / "native" / "go" / "plugin_patch.go"
    assert not (ROOT / "libterraform.go").exists()
    assert not (ROOT / "plugin_patch.go").exists()


def test_go_plugin_version_from_mod_reads_required_module():
    mod_content = """
module github.com/hashicorp/terraform

go 1.22.7

require (
    github.com/hashicorp/go-plugin v1.6.0
    github.com/hashicorp/hcl/v2 v2.20.0
)
"""

    assert hatch_build.go_plugin_version_from_mod(mod_content) == "v1.6.0"


def test_go_plugin_version_from_mod_requires_go_plugin_module():
    with pytest.raises(RuntimeError, match="github.com/hashicorp/go-plugin"):
        hatch_build.go_plugin_version_from_mod(
            "module github.com/hashicorp/terraform\n"
        )


def test_go_plugin_replace_content_removes_stale_replace():
    mod_content = """
module github.com/hashicorp/terraform

go 1.22.7

require (
    github.com/hashicorp/go-plugin v1.6.0
)

replace github.com/hashicorp/go-plugin v1.6.0 => ../go-plugin
"""

    clean_content, patched_content = hatch_build.go_mod_content_with_go_plugin_replace(
        mod_content,
        "../go-plugin",
    )

    assert "replace github.com/hashicorp/go-plugin" not in clean_content
    assert patched_content.count("replace github.com/hashicorp/go-plugin") == 1
    assert patched_content.endswith(
        "\nreplace github.com/hashicorp/go-plugin v1.6.0 => ../go-plugin\n"
    )
