import os.path

import pytest

import py_terraform

cur_dirname = os.path.dirname(os.path.abspath(__file__))
sleep_dirname = os.path.join(cur_dirname, 'sleep')


def test_load_config_dir():
    mod, diags = py_terraform.load_config_dir(sleep_dirname)
    assert 'time_sleep.wait' in mod['ManagedResources']


def test_load_config_dir_no_exits():
    with pytest.raises(py_terraform.LibTerraformError):
        py_terraform.load_config_dir('not-exits')
