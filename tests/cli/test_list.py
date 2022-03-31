import os.path
import shutil

from libterraform import TerraformCommand


class TestTerraformCommandState:
    def test_state_list(self, cli: TerraformCommand):
        cli.apply()
        r = cli.state_list()
        assert r.retcode == 0, r.error
        assert r.value

        r = cli.state_list('time_sleep.wait1', 'time_sleep.wait2')
        assert r.retcode == 0, r.error
        assert r.value

    def test_state_list_with_ids(self, cli: TerraformCommand):
        cli.apply()
        r = cli.output()
        id1 = r.value['wait1_id']['value']
        id2 = r.value['wait2_id']['value']
        r = cli.state_list(ids=[id1, id2])
        assert r.retcode == 0, r.error
        assert r.value

    def test_state_list_with_state(self, cli: TerraformCommand):
        cli.apply()
        r = cli.state_list(state='terraform.tfstate')
        assert r.retcode == 0, r.error
        assert r.value

    def test_state_mv(self, cli: TerraformCommand):
        cli.apply()
        r = cli.state_mv('time_sleep.wait1', 'time_sleep.wait1_new', dry_run=True)
        assert r.retcode == 0, r.error
        assert r.value

    def test_state_pull(self, cli: TerraformCommand):
        cli.apply()
        r = cli.state_pull()
        assert r.retcode == 0, r.error
        assert isinstance(r.value, dict)

    def test_state_push(self, cli: TerraformCommand):
        cli.apply()
        r = cli.state_push('terraform.tfstate')
        assert r.retcode == 0, r.error

    def test_state_replace_provider(self, cli: TerraformCommand):
        cli.apply()
        r = cli.state_replace_provider('hashicorp/time', 'hashicorp/time')
        assert r.retcode == 0, r.error
        assert r.value

    def test_state_rm(self, cli: TerraformCommand):
        cli.apply()
        r = cli.state_rm('time_sleep.wait1', 'time_sleep.wait2', dry_run=True)
        assert r.retcode == 0, r.error
        assert r.value

    def test_state_show(self, cli: TerraformCommand):
        cli.apply()
        r = cli.state_rm('time_sleep.wait1')
        assert r.retcode == 0, r.error
        assert r.value
