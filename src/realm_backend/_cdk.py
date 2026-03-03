"""CDK compatibility layer.

This module centralizes all imports from the Internet Computer CDK (currently Basilisk).
To switch CDKs, only this file needs to be modified.
"""

from basilisk import *  # noqa: F401, F403
from basilisk import ic  # noqa: F401 - explicit for IDE support

# Re-export management canister sub-package
from basilisk.canisters.management import (  # noqa: F401
    HttpResponse,
    HttpTransformArgs,
    management_canister,
)
