import inspect

from libterraform import TerraformCommand


class TestTerraformCommandGraph:
    def test_graph_declares_terraform_1_15_options(self):
        params = inspect.signature(TerraformCommand.graph).parameters

        assert "vars" in params
        assert "var_files" in params
        assert "module_depth" in params
        assert "verbose" in params

    def test_graph_accepts_terraform_1_15_options(self, monkeypatch):
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
            return 0, "digraph {}", ""

        monkeypatch.setattr(TerraformCommand, "run", staticmethod(fake_run))

        cli = TerraformCommand("/work")
        r = cli.graph(
            vars={"name": "demo"},
            var_files=["graph.tfvars"],
            module_depth=2,
            verbose=True,
        )

        assert r.retcode == 0
        assert call["cmd"] == "graph"
        assert call["options"]["var"] == {"name": "demo"}
        assert call["options"]["var_file"] == ["graph.tfvars"]
        assert call["options"]["module_depth"] == 2
        assert call["options"]["verbose"] is ...
        assert call["chdir"] == "/work"

    def test_graph(self, cli: TerraformCommand):
        r = cli.graph(draw_cycles=True)
        assert r.retcode == 0, r.error
        assert "digraph" in r.value

    def test_graph_by_plan(self, cli: TerraformCommand):
        tfplan_path = "sleep.tfplan"
        cli.plan(out=tfplan_path)
        r = cli.graph(plan=tfplan_path, draw_cycles=True)
        assert r.retcode == 0, r.error
        assert "digraph" in r.value
