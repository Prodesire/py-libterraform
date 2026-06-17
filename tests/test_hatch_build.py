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


def test_makefile_install_sets_git_hooks_without_install_hooks_target():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "install-hooks" not in makefile
    assert "git config core.hooksPath $(GIT_HOOKS_PATH)" in makefile
    assert '@echo "Git hooks installed from $(GIT_HOOKS_PATH)."' in makefile


def test_makefile_clean_merges_python_and_build_cleanup():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "clean-pyc" not in makefile
    assert "clean-build" not in makefile
    assert "clean: clean-pyc clean-build" not in makefile
    assert "find . -name '*.pyc' -exec rm -f {} +" in makefile
    assert "find . -name '__pycache__' -exec rm -rf {} +" in makefile
    assert "rm -rf build dist *.egg-info .eggs" in makefile
    assert "find . -name '*.h' -exec rm -f {} +" in makefile


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


def test_build_hook_uses_python_abi_independent_platform_wheel_tags():
    assert (
        hatch_build.wheel_tag("Linux", "linux-x86_64")
        == "py3-none-manylinux_2_35_x86_64"
    )
    assert (
        hatch_build.wheel_tag("Darwin", "macosx-14.0-arm64")
        == "py3-none-macosx_14_0_arm64"
    )
    assert hatch_build.wheel_tag("Windows", "win-amd64") == "py3-none-win_amd64"


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
