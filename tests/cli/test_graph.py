from libterraform import TerraformCommand


class TestTerraformCommandGraph:
    def test_graph(self, cli: TerraformCommand):
        r = cli.graph(draw_cycles=True)
        assert r.retcode == 0, r.error
        assert 'digraph' in r.value

    def test_graph_by_plan(self, cli: TerraformCommand):
        tfplan_path = 'sleep.tfplan'
        cli.plan(out=tfplan_path)
        r = cli.graph(plan=tfplan_path, draw_cycles=True)
        assert r.retcode == 0, r.error
        assert 'digraph' in r.value
