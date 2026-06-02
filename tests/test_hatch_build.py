import pytest

import hatch_build


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
        hatch_build.go_plugin_version_from_mod("module github.com/hashicorp/terraform\n")

