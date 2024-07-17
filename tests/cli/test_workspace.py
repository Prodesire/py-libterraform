from libterraform import TerraformCommand


class TestTerraformCommandWorkSpace:
    def test_all(self, cli: TerraformCommand):
        default_name = "default"
        name = "test"
        r = cli.workspace_new(name)
        assert r.retcode == 0, r.error
        assert "Created and switched to workspace" in r.value

        r = cli.workspace_show()
        assert r.retcode == 0, r.error
        assert name in r.value

        r = cli.workspace_list()
        assert r.retcode == 0, r.error
        assert name in r.value
        assert default_name in r.value

        r = cli.workspace_select(default_name)
        assert r.retcode == 0, r.error

        r = cli.workspace_delete(name)
        assert r.retcode == 0, r.error
