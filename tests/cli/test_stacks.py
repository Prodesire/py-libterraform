from libterraform import TerraformCommand


class TestTerraformCommandStacks:
    def test_stacks_passes_args_and_plugin_cache_dir(self, monkeypatch):
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
            return 0, "stack output", ""

        monkeypatch.setattr(TerraformCommand, "run", staticmethod(fake_run))

        cli = TerraformCommand("/work")
        result = cli.stacks(
            args=["list"],
            plugin_cache_dir="/tmp/tf-stacks",
            check=True,
        )

        assert result.retcode == 0
        assert result.value == "stack output"
        assert result.json is False
        assert call == {
            "cmd": "stacks",
            "args": ["list"],
            "options": {
                "no_color": ...,
                "plugin_cache_dir": "/tmp/tf-stacks",
            },
            "chdir": "/work",
            "check": True,
            "json": False,
        }
