"""Unit tests for Codex module-entity seeding (manifest ``codex_modules``).

The host used to turn every ``backend/modules/*.py`` file into a Codex DB
entity. That is now opt-in via the manifest:

  - key absent  → seed every top-level ``modules/*.py`` (legacy default)
  - key present → seed only those stems that exist as ``modules/<name>.py``
  - empty list  → seed none

These tests load ``api/file_registry.py`` in isolation (same pattern as
``test_marketplace_approval_gate.py``) so they can exercise the seeder
without pulling in the rest of the canister import graph.
"""

import importlib.util
import sys
import types
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))


def _build_cdk_stub():
    cdk = types.ModuleType("_cdk")

    class _Subscriptable:
        def __class_getitem__(cls, item):
            return cls

    class Service:
        def __init__(self, principal=None):
            self.principal = principal

    class Principal:
        def __init__(self, text_value=""):
            self.text_value = text_value

        @staticmethod
        def from_str(value):
            return Principal(value)

        def to_str(self):
            return self.text_value

    def _identity_decorator(fn):
        return fn

    class _IC:
        @staticmethod
        def caller():
            return Principal("test-caller")

        @staticmethod
        def id():
            return Principal("self-cai")

        @staticmethod
        def time():
            return 1_000_000

    cdk.Async = _Subscriptable
    cdk.CallResult = _Subscriptable
    cdk.Opt = _Subscriptable
    cdk.Vec = _Subscriptable
    cdk.Principal = Principal
    cdk.Record = type("Record", (), {})
    cdk.Service = Service
    cdk.blob = bytes
    cdk.text = str
    cdk.void = None
    cdk.nat = int
    cdk.ic = _IC
    cdk.service_query = _identity_decorator
    cdk.service_update = _identity_decorator
    cdk.__getattr__ = lambda name: _Subscriptable
    return cdk


def _load_file_registry_module():
    previous = sys.modules.get("_cdk")
    sys.modules["_cdk"] = _build_cdk_stub()
    try:
        path = src_path / "api" / "file_registry.py"
        spec = importlib.util.spec_from_file_location(
            "realm_api_file_registry_codex_seed", path
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is None:
            sys.modules.pop("_cdk", None)
        else:
            sys.modules["_cdk"] = previous


fr = _load_file_registry_module()


MODULE_FILES = {
    "manifest.json": '{"kind": "codex"}',
    "entry.py": "def init(args): pass",
    "modules/quarter_assignment.py": "# quarter_assignment",
    "modules/membership.py": "# membership",
    "modules/leftover_helper.py": "# leftover — must not seed when allow-listed",
    "modules/nested/ignored.py": "# nested paths are never Codex entities",
    "helpers/not_a_module.py": "# wrong directory",
}


def _stems(pairs):
    return [name for name, _content in pairs]


class TestCodexModulesToSeed:
    def test_absent_key_seeds_every_top_level_module(self):
        """Dominion / unpublished packages: no key → today's behavior."""
        stems = _stems(fr._codex_modules_to_seed(MODULE_FILES, {"kind": "codex"}))
        assert stems == ["quarter_assignment", "membership", "leftover_helper"]

        stems_none = _stems(fr._codex_modules_to_seed(MODULE_FILES, None))
        assert stems_none == ["quarter_assignment", "membership", "leftover_helper"]

        stems_empty_manifest = _stems(fr._codex_modules_to_seed(MODULE_FILES, {}))
        assert stems_empty_manifest == [
            "quarter_assignment",
            "membership",
            "leftover_helper",
        ]

    def test_present_list_seeds_only_listed_stems_that_exist(self):
        """Syntropia/Agora leftover-free: honor the allow-list, skip leftovers."""
        pairs = fr._codex_modules_to_seed(
            MODULE_FILES,
            {"kind": "codex", "codex_modules": ["quarter_assignment", "missing"]},
        )
        assert _stems(pairs) == ["quarter_assignment"]
        assert pairs[0][1] == "# quarter_assignment"

        both = _stems(
            fr._codex_modules_to_seed(
                MODULE_FILES,
                {"codex_modules": ["membership", "quarter_assignment"]},
            )
        )
        assert both == ["membership", "quarter_assignment"]

    def test_empty_list_seeds_none(self):
        stems = _stems(
            fr._codex_modules_to_seed(MODULE_FILES, {"codex_modules": []})
        )
        assert stems == []


class _FakeCodex:
    """Minimal Codex stand-in: Codex[name] lookup + Codex(name=, code=)."""

    store = {}

    def __init__(self, name, code):
        self.name = name
        self.code = code
        type(self).store[name] = self

    @classmethod
    def reset(cls):
        cls.store = {}

    @classmethod
    def __class_getitem__(cls, name):
        return cls.store.get(name)


def test_seed_codex_module_entities_honors_allow_list(monkeypatch):
    """End-to-end through the seeder: listed stems become Codex rows."""
    _FakeCodex.reset()
    ggg = types.ModuleType("ggg")
    ggg.Codex = _FakeCodex
    monkeypatch.setitem(sys.modules, "ggg", ggg)

    seeded = fr._seed_codex_module_entities(
        "syntropia",
        MODULE_FILES,
        {"codex_modules": ["quarter_assignment"]},
    )
    assert seeded == ["quarter_assignment"]
    assert set(_FakeCodex.store) == {"quarter_assignment"}
    assert _FakeCodex.store["quarter_assignment"].code == "# quarter_assignment"

    # Absent key still seeds every top-level module (legacy default).
    _FakeCodex.reset()
    seeded_all = fr._seed_codex_module_entities("dominion", MODULE_FILES, {})
    assert seeded_all == ["quarter_assignment", "membership", "leftover_helper"]

    # Empty list seeds none.
    _FakeCodex.reset()
    assert fr._seed_codex_module_entities("agora", MODULE_FILES, {"codex_modules": []}) == []
    assert _FakeCodex.store == {}
