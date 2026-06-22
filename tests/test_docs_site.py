import ast
import json
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


def release_matrix() -> dict[str, Any]:
    return json.loads(read_text("release-matrix.json"))


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
    assert project["extra_javascript"] == ["assets/language-redirect.js"]
    assert {"TerraformCommand": "api/terraform-command.md"} in project["nav"][2][
        "API Reference"
    ]
    assert {"AsyncTerraformCommand": "api/async-terraform-command.md"} in project[
        "nav"
    ][2]["API Reference"]
    assert {"TerraformPool": "api/terraform-pool.md"} in project["nav"][2][
        "API Reference"
    ]
    assert {"Parallel Execution": "parallel-execution.md"} in project["nav"][1][
        "Getting Started"
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
            "link": "https://prodesire.github.io/py-libterraform/zh/?lang=zh",
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
    assert project["extra_javascript"] == ["assets/language-redirect.js"]
    assert project["theme"]["language"] == "zh"
    assert "首页" in titles
    assert "安装" in titles
    assert "快速开始" in titles
    assert "并行执行" in titles
    assert "API 参考" in titles
    assert "发布策略" in titles
    assert "Home" not in titles
    assert "Getting Started" not in titles
    assert {"并行执行": "parallel-execution.md"} in project["nav"][1]["入门"]
    assert {"TerraformPool": "api/terraform-pool.md"} in project["nav"][2]["API 参考"]
    assert project["extra"]["alternate"] == [
        {
            "name": "English",
            "link": "https://prodesire.github.io/py-libterraform/?lang=en",
            "lang": "en",
        },
        {
            "name": "中文",
            "link": "https://prodesire.github.io/py-libterraform/zh/",
            "lang": "zh",
        },
    ]


def test_docs_language_redirect_script_rewrites_local_alternate_links():
    script = read_text("docs/en/assets/language-redirect.js")

    assert 'var productionOrigin = "https://prodesire.github.io"' in script
    assert 'var productionBasePath = "/py-libterraform"' in script
    assert "function rewriteLanguageAlternates()" in script
    assert "function isLocalPreview()" in script
    assert "function currentPreviewPathname()" in script
    assert "window.location.hostname" in script
    assert "window.location.pathname" in script
    assert 'hostname === "localhost"' in script
    assert 'hostname === "127.0.0.1"' in script
    assert 'hostname === "::1"' in script
    assert "document.querySelectorAll" in script
    assert 'a.md-select__link[href], link[rel="alternate"][href]' in script
    assert 'node.getAttribute("hreflang")' in script
    assert 'targetLanguage === "zh"' in script
    assert 'targetLanguage === "en"' in script
    assert 'targetPathname = "/zh" + targetPathname' in script
    assert 'targetPathname = targetPathname.slice(3) || "/"' in script
    assert "node.setAttribute" in script


def test_docs_language_redirect_script_detects_browser_language():
    english_script = read_text("docs/en/assets/language-redirect.js")
    chinese_script = read_text("docs/zh/assets/language-redirect.js")

    assert chinese_script == english_script
    assert 'var storageKey = "py-libterraform-docs-language"' in english_script
    assert 'params.get("lang")' in english_script
    assert (
        "window.localStorage.setItem(storageKey, requestedLanguage)" in english_script
    )
    assert "navigator.languages" in english_script
    assert "navigator.language" in english_script
    assert "isEnglishRoot" in english_script
    assert 'preferredLanguage === "en"' in english_script
    assert 'language.indexOf("zh") === 0' in english_script
    assert (
        'window.location.replace(new URL("zh/", window.location.href).toString())'
        in english_script
    )
    assert "window.location.replace" not in english_script.split("isEnglishRoot")[0]


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


def test_readmes_do_not_include_current_compatibility_section():
    readme = read_text("README.md")
    chinese_readme = read_text("README.zh-CN.md")

    assert "## Compatibility" not in readme
    assert "## 兼容性" not in chinese_readme
    assert "0.13.0 bundles Terraform 1.13.5" not in readme
    assert "0.13.0 内置 Terraform 1.13.5" not in chinese_readme


def test_docs_include_0_15_version_mapping():
    english_index = read_text("docs/en/index.md")
    chinese_index = read_text("docs/zh/index.md")
    english_policy = read_text("docs/en/release-policy.md")
    chinese_policy = read_text("docs/zh/release-policy.md")

    for page in [english_index, chinese_index]:
        assert "libterraform/0.15.0/" in page
        assert "terraform/tree/v1.15.5" in page

    assert "`0.15.x` | `1.15.x` | `release/0.15`" in english_policy
    assert "`0.15.x` | `1.15.x` | `release/0.15`" in chinese_policy


def test_docs_version_tables_include_release_matrix_entries():
    pages = [
        read_text("docs/en/index.md"),
        read_text("docs/zh/index.md"),
    ]

    for entry in release_matrix()["releases"]:
        libterraform_version = entry["libterraform_version"]
        terraform_version = entry["terraform_version"]
        expected = (
            f"| [{libterraform_version}]"
            f"(https://pypi.org/project/libterraform/{libterraform_version}/) | "
            f"[{terraform_version}]"
            f"(https://github.com/hashicorp/terraform/tree/v{terraform_version}) |"
        )

        for page in pages:
            assert expected in page


def test_chinese_docs_cover_public_python_interfaces():
    index_page = read_text("docs/zh/index.md")
    command_page = read_text("docs/zh/api/terraform-command.md")
    async_command_page = read_text("docs/zh/api/async-terraform-command.md")
    config_page = read_text("docs/zh/api/terraform-config.md")
    exceptions_page = read_text("docs/zh/api/exceptions.md")

    assert "Python 绑定" in index_page
    assert "::: libterraform.cli.TerraformCommand" in command_page
    assert "::: libterraform.async_cli.AsyncTerraformCommand" in async_command_page
    assert "asyncio 兼容" in async_command_page
    assert "协作式取消" in async_command_page
    pool_page = read_text("docs/zh/api/terraform-pool.md")
    assert "::: libterraform.pool.TerraformPool" in pool_page
    assert "真正并行" in pool_page
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
    cli_source = read_text("src/libterraform/cli.py")
    bad_state_identities_link = "/".join(
        ["https://developer.hashicorp.com/terraform/cli/commands/state", "identities"]
    )

    for method in public_methods("src/libterraform/cli.py", "TerraformCommand"):
        assert f"::: libterraform.cli.TerraformCommand.{method}" in command_page

    assert bad_state_identities_link not in command_page
    assert bad_state_identities_link not in cli_source

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
        "`identity_id`",
        "`cloud_run`",
        "`junit_xml`",
        "`run_parallelism`",
        "`test_directory`",
        "`plugin_cache_dir`",
        "`generate_config_out`",
        "`enable_pluggable_state_storage_experiment`",
        "`create_default_workspace`",
        "`module_depth`",
        "`verbose`",
        "`query`",
        "`allow_deferral`",
        "Terraform 1.11 起支持人类可读输出",
        "Terraform 1.12 起提供该命令",
        "Terraform 1.13 起提供该命令",
        "Terraform 1.14 起默认注册该命令",
        "传入 `json=False` 可获取原始文本",
        "将 JUnit XML 测试报告写入指定文件",
        "`junit_xml` 仅支持本地测试执行，不能与 `cloud_run` 同时使用",
        "限制同一测试文件内可并行执行的 run block 数量",
        "允许测试操作使用 deferral",
        "执行 Terraform Stacks 子命令",
        "执行 Terraform query 命令",
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
        "make inspect-upstream",
        "Trusted Publishing",
        "py3-none-manylinux_2_35_x86_64",
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
    async_command_page = read_text("docs/en/api/async-terraform-command.md")
    config_page = read_text("docs/en/api/terraform-config.md")
    exceptions_page = read_text("docs/en/api/exceptions.md")

    pool_page = read_text("docs/en/api/terraform-pool.md")

    assert "::: libterraform.cli.TerraformCommand" in command_page
    assert "::: libterraform.async_cli.AsyncTerraformCommand" in async_command_page
    assert "asyncio-compatible" in async_command_page
    assert "cooperative cancellation" in async_command_page
    assert "::: libterraform.pool.TerraformPool" in pool_page
    assert "true parallel Terraform operations" in pool_page
    assert "load_config_dir" in config_page
    assert "TerraformCommandError" in exceptions_page


def test_parallel_execution_docs_explain_process_isolation():
    english_page = read_text("docs/en/parallel-execution.md")
    chinese_page = read_text("docs/zh/parallel-execution.md")

    for page in [english_page, chinese_page]:
        assert "ProcessPoolExecutor" in page
        assert "TerraformCommand" in page
        assert "AsyncTerraformCommand" in page

    assert "true parallel Terraform operations" in english_page
    assert "one Python process" in english_page
    assert "真正并行" in chinese_page
    assert "单个 Python 进程" in chinese_page


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


def test_makefile_exposes_doc_build_and_serve_targets():
    makefile = read_text("Makefile")

    assert "docs-build" not in makefile
    assert "doc-build" in makefile
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
    assert "doc-build: ## Build the documentation site" in makefile
    assert "doc-serve: ## Serve the documentation site locally" in makefile
    assert "inspect-upstream: ## Inspect Terraform release and bridge drift" in makefile
    assert "scripts/inspect_upstream.py --releases-url" in makefile
