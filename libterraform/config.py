import json
from ctypes import *

from libterraform import _lib_tf, _free
from libterraform.exceptions import LibTerraformError


class LoadConfigDirResult(Structure):
    _fields_ = [("r0", c_void_p),
                ("r1", c_void_p),
                ("r2", c_void_p)]


_load_config_dir = _lib_tf.ConfigLoadConfigDir
_load_config_dir.argtypes = [c_char_p]
_load_config_dir.restype = LoadConfigDirResult


class TerraformConfig:
    @staticmethod
    def load_config_dir(path: str) -> (dict, dict):
        """
        load_config_dir reads the .tf and .tf.json files in the given directory
        as config files and then combines these files into a single Module.

        .tf files are parsed using the HCL native syntax while .tf.json files are
        parsed using the HCL JSON syntax.
        """
        ret = _load_config_dir(path.encode('utf-8'))
        r_mod = cast(ret.r0, c_char_p).value
        _free(ret.r0)
        r_diags = cast(ret.r1, c_char_p).value
        _free(ret.r1)
        err = cast(ret.r2, c_char_p).value
        _free(ret.r2)

        if err:
            raise LibTerraformError(err)
        if r_mod is None:
            msg = f'The given directory {path!r} does not exist at all or could not be opened for some reason.'
            raise LibTerraformError(msg)

        mod = json.loads(r_mod)
        diags = json.loads(r_diags)

        return mod, diags
