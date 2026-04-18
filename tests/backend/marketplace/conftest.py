"""Shared pytest fixtures for marketplace_backend unit tests.

These tests run in plain CPython against the real ``ic_python_db`` and
``basilisk`` packages, but without an Internet Computer runtime. We
mock ``ic.caller``, ``ic.time``, and ``ic.is_controller`` so each test
can simulate an arbitrary principal.

Imports note: the marketplace canister's own ``main.py`` does
``from core.models import …`` because basilisk puts the canister dir
on sys.path at runtime. In tests we must NOT add
``src/marketplace_backend`` to sys.path (that would collide with
``src/realm_registry_backend``'s identically-named ``core`` /
``api`` subpackages and break the registry tests). Instead we import
the api modules through their full dotted path
(``marketplace_backend.api.foo``) and re-expose them under the short
names the canister code uses.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Make src importable so `marketplace_backend.api.foo` resolves.
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# Mock the ic module BEFORE importing any marketplace api module.
import basilisk  # noqa: E402

mock_ic = MagicMock()
mock_ic.time.return_value = int(time.time() * 1_000_000_000)
mock_ic.caller.return_value = "anon-principal"
mock_ic.is_controller.return_value = False
basilisk.ic = mock_ic

# The marketplace_backend's _cdk.py does ``from basilisk import ic``;
# but tests import its api modules via marketplace_backend.api.* and the
# api modules do ``from _cdk import ic``. _cdk lives at
# src/marketplace_backend/_cdk.py and isn't reachable via that name from
# tests because src/marketplace_backend is not on sys.path. Wire up the
# import name manually.
import importlib  # noqa: E402
import importlib.util  # noqa: E402


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


_MP = SRC / "marketplace_backend"
# Load _cdk (with our mocked basilisk). Stash under a private name and
# install the short `_cdk` alias only long enough for the api modules
# to import — then pop it so other test suites that load their own
# canister's _cdk aren't affected.
_load_module("_cdk_marketplace", _MP / "_cdk.py")
sys.modules["_cdk"] = sys.modules["_cdk_marketplace"]


# The marketplace api modules use absolute imports of the form
# ``from core.models import …`` and ``from api.foo import …`` because
# basilisk runs the canister with the canister directory on sys.path.
# To load those modules in tests we temporarily alias the short names
# to the fully-qualified marketplace_backend.* packages, load all api
# modules so their cached references are bound, then *remove* the
# aliases so other test suites (e.g. realm_registry) that use the same
# names with their own packages aren't polluted.

_short_aliases = ["core", "core.models", "api"]
_api_short_modules = [
    "api.config", "api.extensions", "api.codices", "api.likes",
    "api.rankings", "api.licenses", "api.verification",
]

# 1. Install short-name aliases pointing at marketplace_backend.*.
sys.modules["core"] = importlib.import_module("marketplace_backend.core")
sys.modules["core.models"] = importlib.import_module("marketplace_backend.core.models")
sys.modules["api"] = importlib.import_module("marketplace_backend.api")
for short in _api_short_modules:
    full = "marketplace_backend." + short
    sys.modules[short] = importlib.import_module(full)

# Re-import them under the full path so test files have a stable handle.
ext_api = sys.modules["api.extensions"]
codices_api = sys.modules["api.codices"]
likes_api = sys.modules["api.likes"]
rankings_api = sys.modules["api.rankings"]
licenses_api = sys.modules["api.licenses"]
config_api = sys.modules["api.config"]
verification_api = sys.modules["api.verification"]

# 2. Drop the short-name aliases from sys.modules so other test
#    suites that import a different package's `core`, `api`, or `_cdk`
#    don't accidentally pick up ours. The api modules already hold
#    direct references to the imported symbols, so removal is safe for
#    them.
for short in _short_aliases + _api_short_modules + ["_cdk"]:
    sys.modules.pop(short, None)


from ic_python_db import Database  # noqa: E402

# We defer Database.init() until the first marketplace test is actually
# run — doing it at module load time would race with sibling test suites
# (e.g. realm_registry) that also call Database.init() at module load.
_db_initialised = False


class MockStorage:
    def __init__(self) -> None:
        self.data: dict = {}

    def get(self, key):
        return self.data.get(key)

    def insert(self, key, value):
        self.data[key] = value

    def remove(self, key):
        self.data.pop(key, None)

    def items(self):
        return list(self.data.items())

    def keys(self):
        return list(self.data.keys())

    def values(self):
        return list(self.data.values())

    def __contains__(self, key):
        return key in self.data

    def __len__(self):
        return len(self.data)


_storage = MockStorage()


def _ensure_db():
    global _db_initialised
    if _db_initialised:
        return
    try:
        Database.init(db_storage=_storage, audit_enabled=False)
    except RuntimeError as e:
        if "already exists" not in str(e):
            raise
    _db_initialised = True


@pytest.fixture(autouse=True)
def _reset_state():
    _ensure_db()
    """Wipe all marketplace entities before each test."""
    from marketplace_backend.core.models import (
        CodexListingEntity,
        DeveloperLicenseEntity,
        ExtensionListingEntity,
        LikeEntity,
        MarketplaceConfigEntity,
        PurchaseEntity,
    )
    for cls in (
        ExtensionListingEntity,
        CodexListingEntity,
        PurchaseEntity,
        LikeEntity,
        DeveloperLicenseEntity,
        MarketplaceConfigEntity,
    ):
        try:
            for inst in list(cls.instances()):
                inst.delete()
        except Exception:
            pass
    mock_ic.time.return_value = int(time.time() * 1_000_000_000)
    mock_ic.caller.return_value = "anon-principal"
    mock_ic.is_controller.return_value = False
    yield


@pytest.fixture
def as_caller():
    def _set(principal: str, *, controller: bool = False):
        mock_ic.caller.return_value = principal
        mock_ic.is_controller.return_value = controller
    return _set


@pytest.fixture
def advance_time():
    def _set(seconds_from_now: float = 0):
        mock_ic.time.return_value = int((time.time() + seconds_from_now) * 1_000_000_000)
    return _set
