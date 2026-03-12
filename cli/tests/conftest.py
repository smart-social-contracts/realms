"""Shared test fixtures for CLI tests that import realm_backend."""

import os
import sys

# realm_backend is not an installable package; add src/ to path for `realm_backend.ggg` imports
_src = os.path.join(os.path.dirname(__file__), "..", "..", "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
