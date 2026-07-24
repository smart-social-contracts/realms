"""Unit tests for the lifecycle gates (issue #253).

Covers the pure decision logic of ``auto_milestones_ready`` and
``beta_to_production_ready`` with a stubbed ``ggg`` module; the full
integration (realm_settings extension, codex hooks) is exercised by the
lifecycle E2E suites in realms-codices/testing/e2e.
"""

import json
import sys
import types


# ---------------------------------------------------------------------------
# Stub ggg / _cdk before importing the module under test
# ---------------------------------------------------------------------------


class _FakeUser:
    _users = []

    def __init__(self, principal, departments=()):
        self.id = principal
        self.departments = list(departments)

    @classmethod
    def count(cls):
        return len(cls._users)

    @classmethod
    def max_id(cls):
        return len(cls._users)

    @classmethod
    def load_some(cls, from_id=1, count=100):
        return cls._users[from_id - 1 : from_id - 1 + count]


class _FakeDept:
    _depts = []

    def __init__(self, name, is_root=False, m=1, n=1, quorum=0, member_count=0):
        self.name = name
        self.is_root = is_root
        self.policy_threshold_m = m
        self.policy_threshold_n = n
        self.policy_quorum_percent = quorum
        self._member_count = member_count
        self.head = None

    def reverse_count(self, relation):
        return self._member_count

    @classmethod
    def instances(cls):
        return cls._depts


class _FakeRealm:
    def __init__(self, manifest):
        self.manifest_data = json.dumps(manifest)
        self.status = "beta"

    @classmethod
    def instances(cls):
        return []


_ggg = types.ModuleType("ggg")
_ggg.User = _FakeUser
_ggg.Department = _FakeDept
_ggg.ROOT_ORG_NAME = "root"

# The canister CDK is unavailable off-chain; core/__init__ pulls it in via
# core.extensions, so stub just enough for imports to resolve.
if "_cdk" not in sys.modules:
    import typing

    _cdk = types.ModuleType("_cdk")
    _cdk.Async = typing.Iterator  # subscriptable stand-in for annotations

    class _FakeIc:
        @staticmethod
        def time():
            return 0

    _cdk.ic = _FakeIc()
    sys.modules["_cdk"] = _cdk

# lifecycle_gate does `from core.membership import ...` (canister-style
# imports); alias the package so it resolves off-chain too.
if "core" not in sys.modules:
    import src.realm_backend.core as _core_pkg

    sys.modules["core"] = _core_pkg

# core.codex_hooks.get_config would return {} (no realm, no codex) and hide
# the manifest under test — force the manifest_data fallback path.
_hooks = types.ModuleType("core.codex_hooks")


def _raise():
    raise RuntimeError("no codex in unit tests")


_hooks.get_config = _raise

import pytest  # noqa: E402

from src.realm_backend.core.lifecycle_gate import (  # noqa: E402
    auto_milestones_ready,
    beta_to_production_ready,
    transition_mode,
)


@pytest.fixture(autouse=True)
def _stub_modules(monkeypatch):
    """Install the ggg/codex_hooks stubs per test (restored automatically)."""
    monkeypatch.setitem(sys.modules, "ggg", _ggg)
    monkeypatch.setitem(sys.modules, "core.codex_hooks", _hooks)
    # core.membership caches nothing, but ensure it resolves the stubbed ggg.
    yield


def _realm_with(lifecycle, users=0, root_members=0):
    _FakeUser._users = [_FakeUser(f"principal-{i}") for i in range(users)]
    root = _FakeDept("root", is_root=True, member_count=root_members)
    _FakeDept._depts = [root]
    return _FakeRealm({"lifecycle": lifecycle}), root


# ---------------------------------------------------------------------------
# auto_milestones (alpha→beta, e.g. Syntropia critical mass)
# ---------------------------------------------------------------------------


def test_transition_mode_reads_manifest():
    realm, _ = _realm_with(
        {"transitions": {"alpha_to_beta": {"mode": "auto_milestones"}}}
    )
    assert transition_mode(realm, "alpha", "beta") == "auto_milestones"
    assert transition_mode(realm, "beta", "production") == "admin_approval"


def test_critical_mass_blocks_until_reached():
    lifecycle = {
        "critical_mass": 25,
        "transitions": {
            "alpha_to_beta": {"mode": "auto_milestones", "milestones": ["critical_mass"]}
        },
    }
    realm, _ = _realm_with(lifecycle, users=10)
    ready, missing = auto_milestones_ready(realm)
    assert not ready
    assert "10 of 25" in missing[0]

    realm, _ = _realm_with(lifecycle, users=25)
    ready, missing = auto_milestones_ready(realm)
    assert ready, missing


def test_boolean_milestones():
    lifecycle = {
        "land_acquired": False,
        "transitions": {
            "alpha_to_beta": {"mode": "auto_milestones", "milestones": ["land_acquired"]}
        },
    }
    realm, _ = _realm_with(lifecycle)
    ready, missing = auto_milestones_ready(realm)
    assert not ready and "land_acquired" in missing[0]

    lifecycle["land_acquired"] = True
    realm, _ = _realm_with(lifecycle)
    ready, missing = auto_milestones_ready(realm)
    assert ready, missing


# ---------------------------------------------------------------------------
# beta→production (proving period + root handover; the governance vote is
# provided by the generic governed-action gate, issue #262)
# ---------------------------------------------------------------------------


def test_production_blocked_without_root_handover():
    realm, _ = _realm_with({}, users=5, root_members=0)
    ready, missing = beta_to_production_ready(realm)
    assert not ready
    assert any("Root not handed" in m for m in missing)


def test_production_ready_after_root_handover():
    realm, root = _realm_with({}, users=5, root_members=2)
    _FakeUser._users[0].departments = [root]
    _FakeUser._users[1].departments = [root]

    ready, missing = beta_to_production_ready(realm)
    assert ready, missing


def test_production_proving_period(monkeypatch):
    realm, root = _realm_with({"beta_proving_days": 30}, users=5, root_members=1)
    _FakeUser._users[0].departments = [root]

    # Pin the gate's clock: other suites may stub _cdk.ic.time() with
    # arbitrary values, so wall-clock timestamps are not reliable here.
    now = 100 * 86400
    monkeypatch.setattr(
        "src.realm_backend.core.lifecycle_gate._now_seconds", lambda: now
    )

    # No timestamped beta entry in history → blocked with explanation.
    ready, missing = beta_to_production_ready(realm)
    assert not ready
    assert any("Proving period" in m for m in missing)

    # Beta entered 40 days ago → passes.
    manifest = json.loads(realm.manifest_data)
    manifest["lifecycle"]["history"] = [
        {"stage": "beta", "at": now - 40 * 86400}
    ]
    realm.manifest_data = json.dumps(manifest)
    ready, missing = beta_to_production_ready(realm)
    assert ready, missing
