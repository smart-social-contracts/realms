"""CDK compatibility layer.

This module centralizes all imports from the Internet Computer CDK (currently Basilisk).
To switch CDKs, only this file needs to be modified.
"""

from basilisk import *  # noqa: F401, F403
from basilisk import ic  # noqa: F401 - explicit for IDE support

# Re-export management canister sub-package
# In CPython template mode the basilisk.canisters.management subpackage
# is not available, so fall back to inline definitions.
try:
    from basilisk.canisters.management import (  # noqa: F401
        HttpResponse,
        HttpTransformArgs,
        management_canister,
    )
except (ImportError, ModuleNotFoundError):
    from basilisk import Service, Principal  # noqa: F401

    HttpResponse = dict
    HttpTransformArgs = dict
    management_canister = Service(principal=Principal.management_canister())
