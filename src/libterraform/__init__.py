import os
from ctypes import c_void_p, cdll

from libterraform.common import WINDOWS

__version__ = "0.15.1"

root = os.path.dirname(os.path.abspath(__file__))
_lib_filename = "libterraform.dll" if WINDOWS else "libterraform.so"
_lib_tf = cdll.LoadLibrary(os.path.join(root, _lib_filename))

_free = _lib_tf.Free
_free.argtypes = [c_void_p]

# Import after loading the shared library; these modules import _lib_tf above.
from .cli import (  # noqa: E402
    ApplyResult,
    CommandResult,
    PlanResult,
    TerraformCommand,
    TerraformStream,
)
from .async_cli import AsyncTerraformCommand  # noqa: E402
from .config import TerraformConfig  # noqa: E402
from .models import ChangeSummary, OutputChange, ResourceChange  # noqa: E402
from .pool import TerraformPool  # noqa: E402

__all__ = [
    "ApplyResult",
    "AsyncTerraformCommand",
    "ChangeSummary",
    "CommandResult",
    "OutputChange",
    "PlanResult",
    "ResourceChange",
    "TerraformCommand",
    "TerraformConfig",
    "TerraformPool",
    "TerraformStream",
]
