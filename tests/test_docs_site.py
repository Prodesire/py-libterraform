import ast
from pathlib import Path
from typing import Any

import tomli


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def markdown_corpus() -> str:
    paths = [
        ROOT / "README.md",
        ROOT / "README.zh-CN.md",
        *sorted((ROOT / "docs").glob("**/*.md")),
    ]
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def nav_titles(items: list[dict[str, Any]]) -> list[str]:
    titles = []
    for item in items:
        for title, value in item.items():
            titles.append(title)
            if isinstance(value, list):
                titles.extend(nav_titles(value))
    return titles


def public_methods(path: str, class_name: str) -> list[str]:
    module = ast.parse(read_text(path))
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return [
                item.name
                for item in node.body
                if isinstance(item, ast.FunctionDef) and not item.name.startswith("_")
            ]
    raise AssertionError(f"{class_name} not found in {path}")


def test_zensical_config_generates_api_docs_for_project_pages_url():
    assert not (ROOT / "mkdocs.yml").exists()

    config = tomli.loads(read_text("zensical.toml"))
    project = config["project"]
    titles = nav_titles(project["nav"])

    assert project["site_url"] == "https://prodesire.github.io/py-libterraform/"
    assert project["site_name"] == "Python libterraform"
    assert project["docs_dir"] == "docs/en"
    assert project["site_dir"] == "site"
    assert project["edit_uri"] == "edit/main/docs/en/"
    assert {"TerraformCommand": "api/terraform-command.md"} in project["nav"][2][
        "API Reference"
    ]

    python_handler = project["plugins"]["mkdocstrings"]["handlers"]["python"]
    assert python_handler["paths"] == ["src"]
    assert python_handler["options"]["docstring_style"] == "sphinx"
    assert python_handler["options"]["show_source"] is False
    assert "中文" not in titles
    assert project["extra"]["alternate"] == [
        {
            "name": "English",
            "link": "https://prodesire.github.io/py-libterraform/",
            "lang": "en",
        },
        {
            "name": "中文",
            "link": "https://prodesire.github.io/py-libterraform/zh/",
            "lang": "zh",
        },
    ]


def test_chinese_zensical_config_uses_separate_language_site():
    config = tomli.loads(read_text("zensical.zh.toml"))
    project = config["project"]
    titles = nav_titles(project["nav"])

    assert project["site_url"] == "https://prodesire.github.io/py-libterraform/zh/"
    assert project["docs_dir"] == "docs/zh"
    assert project["site_dir"] == "site/zh"
    assert project["edit_uri"] == "edit/main/docs/zh/"
    assert project["theme"]["language"] == "zh"
    assert "首页" in titles
    assert "安装" in titles
    assert "快速开始" in titles
    assert "API 参考" in titles
    assert "发布策略" in titles
    assert "Home" not in titles
    assert "Getting Started" not in titles
    assert project["extra"]["alternate"] == [
        {
            "name": "English",
            "link": "https://prodesire.github.io/py-libterraform/",
            "lang": "en",
        },
        {
            "name": "中文",
            "link": "https://prodesire.github.io/py-libterraform/zh/",
            "lang": "zh",
        },
    ]


def test_readme_and_docs_remove_historical_memory_leak_notice():
    corpus = markdown_corpus()

    assert "historical memory leak" not in corpus
    assert "memory leak problem" not in corpus
    assert "solves the memory leak" not in corpus


def test_readme_and_docs_provide_chinese_content():
    readme = read_text("README.md")
    chinese_readme = read_text("README.zh-CN.md")

    assert "README.zh-CN.md" in readme
    assert "中文" in readme
    assert "## 中文说明" not in readme
    assert "https://prodesire.github.io/py-libterraform/" in readme
    assert "Python libterraform" in chinese_readme
    assert "English" in chinese_readme
    assert "## 安装" in chinese_readme
    assert "## 使用" in chinese_readme


def test_chinese_docs_cover_public_python_interfaces():
    index_page = read_text("docs/zh/index.md")
    command_page = read_text("docs/zh/api/terraform-command.md")
    config_page = read_text("docs/zh/api/terraform-config.md")
    exceptions_page = read_text("docs/zh/api/exceptions.md")

    assert "Python 绑定" in index_page
    assert "::: libterraform.cli.TerraformCommand" in command_page
    assert "show_docstring_description: false" in command_page
    assert "show_docstring_parameters: false" in command_page
    assert "show_docstring_returns: false" in command_page
    assert "执行 Terraform 命令" in command_page or "TerraformCommand" in command_page
    assert "load_config_dir" in config_page
    assert "TerraformCommandError" in exceptions_page


def test_chinese_api_reference_has_method_descriptions_and_parameters():
    command_page = read_text("docs/zh/api/terraform-command.md")
    config_page = read_text("docs/zh/api/terraform-config.md")
    exceptions_page = read_text("docs/zh/api/exceptions.md")

    for method in public_methods("src/libterraform/cli.py", "TerraformCommand"):
        assert f"::: libterraform.cli.TerraformCommand.{method}" in command_page

    for phrase in [
        "#### 通用参数",
        "`check`",
        "`json`",
        "`options`",
        "`cmd`",
        "`args`",
        "`backend_config`",
        "`detailed_exitcode`",
        "`auto_approve`",
        "`lock_timeout`",
        "`var_files`",
        "`target_dir`",
        "`from_provider`",
        "`to_provider`",
        "`cloud_run`",
        "`test_directory`",
    ]:
        assert phrase in command_page

    assert "### `load_config_dir(path)`" in config_page
    assert "`path`" in config_page
    assert "返回值" in config_page
    assert "### `TerraformCommandError`" in exceptions_page
    assert "`retcode`" in exceptions_page
    assert "`stdout`" in exceptions_page
    assert "`stderr`" in exceptions_page


def test_chinese_development_docs_include_release_policy_and_full_sections():
    development_page = read_text("docs/zh/development.md")
    release_policy_page = read_text("docs/zh/release-policy.md")

    for phrase in [
        "仓库结构",
        "更新 Terraform 版本",
        "故障排查",
        "[发布策略](release-policy.md)",
        "release-matrix.json",
        "python scripts/verify_release_matrix.py",
    ]:
        assert phrase in development_page

    for phrase in [
        "# 发布策略",
        "版本线",
        "分支规则",
        "补丁规则",
        "回移规则",
        "发布检查清单",
    ]:
        assert phrase in release_policy_page


def test_docs_dependency_group_declares_zensical_toolchain():
    pyproject = tomli.loads(read_text("pyproject.toml"))
    docs_deps = pyproject["dependency-groups"]["docs"]

    assert any(dep.startswith("zensical>=") for dep in docs_deps)
    assert any(dep.startswith("mkdocstrings-python>=") for dep in docs_deps)
    assert not any(dep.startswith("mkdocs>=") for dep in docs_deps)
    assert not any(dep.startswith("mkdocs-material") for dep in docs_deps)


def test_api_reference_pages_generate_public_python_interfaces():
    command_page = read_text("docs/en/api/terraform-command.md")
    config_page = read_text("docs/en/api/terraform-config.md")
    exceptions_page = read_text("docs/en/api/exceptions.md")

    assert "::: libterraform.cli.TerraformCommand" in command_page
    assert "load_config_dir" in config_page
    assert "TerraformCommandError" in exceptions_page


def test_docs_workflow_builds_and_deploys_github_pages():
    workflow = read_text(".github/workflows/docs.yml")

    assert "uv run --group docs zensical build --strict -f zensical.toml" in workflow
    assert "uv run --group docs zensical build --strict -f zensical.zh.toml" in workflow
    assert "mkdocs" not in workflow
    assert "actions/configure-pages@v6" in workflow
    assert "actions/upload-pages-artifact@v5" in workflow
    assert "actions/deploy-pages@v5" in workflow
    assert "pages: write" in workflow
    assert "id-token: write" in workflow


def test_makefile_exposes_docs_build_and_serve_targets():
    makefile = read_text("Makefile")

    assert "docs-build" in makefile
    assert "doc-serve" in makefile
    assert ".PHONY:" in makefile
    assert (
        "uv run $(UV_PYTHON_FLAG) --group docs zensical build --strict -f zensical.toml"
        in makefile
    )
    assert (
        "uv run $(UV_PYTHON_FLAG) --group docs zensical build --strict -f zensical.zh.toml"
        in makefile
    )
    assert "python -m http.server" in makefile
    assert "docs-build: ## Build the documentation site" in makefile
    assert "doc-serve: ## Serve the documentation site locally" in makefile
