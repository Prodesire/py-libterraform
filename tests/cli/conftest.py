import os
import shutil
from pathlib import Path

import pytest

from libterraform import TerraformCommand
from tests.consts import TF_SLEEP_DIR


@pytest.fixture(scope="package")
def cli():
    cwd = TF_SLEEP_DIR
    tf = os.path.join(cwd, ".terraform")

    cli = TerraformCommand(cwd)
    if not os.path.exists(tf):
        cli.init()
    return cli


def prepare_sleep_module(module_dir: Path) -> Path:
    """Copy the sleep fixture module into ``module_dir`` and ensure it is init'd.

    Used by parallel/cancellation tests that need an isolated working directory
    per worker so that one operation does not interfere with another's state.
    """
    source_dir = Path(TF_SLEEP_DIR)
    module_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_dir / "main.tf", module_dir / "main.tf")
    if (source_dir / ".terraform.lock.hcl").exists():
        shutil.copyfile(
            source_dir / ".terraform.lock.hcl",
            module_dir / ".terraform.lock.hcl",
        )
    if (source_dir / ".terraform").exists():
        shutil.copytree(
            source_dir / ".terraform",
            module_dir / ".terraform",
            dirs_exist_ok=True,
        )
    if not (module_dir / ".terraform").exists():
        TerraformCommand(module_dir).init(check=True)
    return module_dir
