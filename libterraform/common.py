import json
import os
from typing import List, Union

# ===================================================================
# OS constants
# ===================================================================

WINDOWS = os.name == 'nt'

# ===================================================================
# Type
# ===================================================================

CmdType = Union[str, List]


# ===================================================================
# utils
# ===================================================================

def json_loads(string, split=False):
    if split:
        value = []
        for line in string.split('\n'):
            if not line:
                continue
            value.append(json.loads(line))
    else:
        value = json.loads(string)
    return value
