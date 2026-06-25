"""Tests for quarter auto-scaling / sharding policy (issue #156).

Two layers, both CI-friendly (no live replica):
  1. Pure policy — default_threshold_n, scale_at, should_scale_default,
     resolve_should_scale (codex override + fallback).
  2. In-memory runtime glue — maybe_request_quarter_scale sets the idempotent
     "scale in flight" flag on the Realm exactly once per threshold crossing.
"""

import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# Stub the canister-only _cdk module so core.* / ggg imports under plain CPython.
if "_cdk" not in sys.modules:
    _cdk_stub = types.ModuleType("_cdk")

    class _Async:  # subscriptable stand-in (extensions.py uses Async[Any])
        def __class_getitem__(cls, item):
            return cls

    _cdk_stub.Async = _Async
    sys.modules["_cdk"] = _cdk_stub

from ic_python_db import Database  # noqa: E402

from realm_backend.core import autoscale  # noqa: E402
from realm_backend.core.autoscale import (  # noqa: E402
    DEFAULT_N,
    LOW_THRESHOLD_N,
    default_threshold_n,
    maybe_request_quarter_scale,
    resolve_should_scale,
    scale_at,
    should_scale_default,
)


# ---------------------------------------------------------------------------
# default_threshold_n / scale_at — environment + 90% rule
# ---------------------------------------------------------------------------

class TestThresholds:
    def test_prod_default_n(self):
        assert default_threshold_n("ic") == DEFAULT_N == 2000
        assert default_threshold_n("") == 2000
        assert default_threshold_n("mainnet") == 2000

    def test_low_networks_use_small_n(self):
        for net in ("test", "staging", "demo", "TEST", " Demo "):
            assert default_threshold_n(net) == LOW_THRESHOLD_N == 10

    def test_scale_at_is_ceil_90pct(self):
        assert scale_at(10) == 9      # ceil(9.0)
        assert scale_at(2000) == 1800
        assert scale_at(1) == 1       # min 1
        assert scale_at(0) == 0       # unlimited / disabled
        assert scale_at(-5) == 0


# ---------------------------------------------------------------------------
# should_scale_default — fullest quarter vs threshold
# ---------------------------------------------------------------------------

class TestShouldScaleDefault:
    def test_below_threshold(self):
        assert should_scale_default([5, 8, 3], "test") is False  # max 8 < 9

    def test_at_threshold(self):
        assert should_scale_default([2, 9], "test") is True       # 9 >= 9

    def test_above_threshold(self):
        assert should_scale_default([12], "test") is True

    def test_prod_boundary(self):
        assert should_scale_default([1799], "ic") is False
        assert should_scale_default([1800], "ic") is True

    def test_empty_never_scales(self):
        assert should_scale_default([], "test") is False
        assert should_scale_default(None, "test") is False

    def test_n_override_disables_when_zero(self):
        assert should_scale_default([10_000], "test", n_override=0) is False

    def test_n_override_custom(self):
        # N=100 => threshold 90
        assert should_scale_default([89], "ic", n_override=100) is False
        assert should_scale_default([90], "ic", n_override=100) is True

    def test_handles_none_populations(self):
        assert should_scale_default([None, 9, None], "test") is True


# ---------------------------------------------------------------------------
# resolve_should_scale — codex override + safe fallback
# ---------------------------------------------------------------------------

class TestResolveShouldScale:
    def test_uses_default_when_no_codex(self):
        assert resolve_should_scale([9], "test") is True
        assert resolve_should_scale([8], "test") is False

    def test_codex_override_wins(self):
        # Codex says never scale, even though default would.
        assert resolve_should_scale([9999], "test", codex_fn=lambda p, n, r: False) is False
        # Codex says always scale, even below the default threshold.
        assert resolve_should_scale([1], "test", codex_fn=lambda p, n, r: True) is True

    def test_codex_receives_args(self):
        seen = {}

        def codex_fn(populations, network, realm):
            seen["pops"] = populations
            seen["net"] = network
            return max(populations) > 3

        assert resolve_should_scale([1, 5], "demo", codex_fn=codex_fn) is True
        assert seen["pops"] == [1, 5]
        assert seen["net"] == "demo"

    def test_broken_codex_falls_back_to_default(self):
        def boom(populations, network, realm):
            raise RuntimeError("bad codex")

        # Falls back to default: max 9 >= 9 (test) => True.
        assert resolve_should_scale([9], "test", codex_fn=boom) is True


# ---------------------------------------------------------------------------
# maybe_request_quarter_scale — in-memory Realm flag + idempotency
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_db():
    Database.get_instance().clear()
    yield
    Database.get_instance().clear()


def _make_realm(network="test", auto_scale_enabled=True):
    from realm_backend.ggg import Realm

    return Realm(
        name="Autoscale Test",
        manifesto="m",
        network=network,
        auto_scale_enabled=auto_scale_enabled,
    )


def _add_users(n):
    from realm_backend.ggg import User, UserProfile

    prof = UserProfile["member"] or UserProfile(name="member")
    for i in range(n):
        User(id=f"user-{i}-{id(object())}", profiles=[prof])


class TestMaybeRequestQuarterScale:
    def test_no_scale_below_threshold(self):
        realm = _make_realm()
        _add_users(8)  # 8 < 9 on test
        assert maybe_request_quarter_scale() is False
        from realm_backend.ggg import Realm
        assert bool(Realm.load("1").scale_in_flight) is False

    def test_scale_at_threshold_sets_flag(self):
        realm = _make_realm()
        _add_users(9)  # 9 >= 9 on test
        assert maybe_request_quarter_scale() is True
        from realm_backend.ggg import Realm
        assert bool(Realm.load("1").scale_in_flight) is True

    def test_idempotent_when_already_in_flight(self):
        realm = _make_realm()
        _add_users(20)
        assert maybe_request_quarter_scale() is True
        # Second call is a no-op while a scale is already queued.
        assert maybe_request_quarter_scale() is False

    def test_disabled_never_scales(self):
        realm = _make_realm(auto_scale_enabled=False)
        _add_users(50)
        assert maybe_request_quarter_scale() is False

    def test_no_realm_is_safe(self):
        # No Realm created => no-op, never raises.
        assert maybe_request_quarter_scale() is False
