from libterraform import TerraformCommand


class TestTerraformCommandQuery:
    def test_query_defaults_to_json_and_supports_generate_config_out(self, monkeypatch):
        call = {}

        def fake_run(cmd, args=None, options=None, chdir=None, check=False, json=False):
            call.update(
                cmd=cmd,
                args=args,
                options=options,
                chdir=chdir,
                check=check,
                json=json,
            )
            return 0, '{"type":"query_summary"}\n', ""

        monkeypatch.setattr(TerraformCommand, "run", staticmethod(fake_run))

        cli = TerraformCommand("/work")
        result = cli.query(
            vars={"name": "demo"},
            var_files=["query.tfvars"],
            generate_config_out="generated.tf",
        )

        assert result.retcode == 0
        assert result.value == [{"type": "query_summary"}]
        assert result.json is True
        assert call == {
            "cmd": "query",
            "args": None,
            "options": {
                "var": {"name": "demo"},
                "var_file": ["query.tfvars"],
                "generate_config_out": "generated.tf",
                "no_color": ...,
            },
            "chdir": "/work",
            "check": False,
            "json": True,
        }
