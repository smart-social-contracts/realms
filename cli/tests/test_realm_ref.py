"""Unit tests for RealmRef — the realm:// universal address parser/formatter.

Pure logic; no canister, no DB. Runs in CI's `unit` job (pytest cli/tests/).
"""

import os
import sys
import types

import pytest

# realm_backend is not an installable package; add src/ to path for direct import.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# core/__init__.py imports core.extensions which does `from _cdk import Async`.
# _cdk is a canister-only module; stub it so the pure core modules import under
# plain CPython during tests.
if "_cdk" not in sys.modules:
    _cdk_stub = types.ModuleType("_cdk")

    class _Async:  # subscriptable stand-in (extensions.py uses Async[Any])
        def __class_getitem__(cls, item):
            return cls

    _cdk_stub.Async = _Async
    sys.modules["_cdk"] = _cdk_stub

from realm_backend.core.realm_ref import (  # noqa: E402
    InvalidRealmRef,
    RealmRef,
    make_ref,
)


class TestParse:
    def test_basic_parse(self):
        ref = RealmRef.parse("realm://abc-cai/User/alice")
        assert ref.canister_id == "abc-cai"
        assert ref.entity_type == "User"
        assert ref.entity_id == "alice"

    def test_round_trip(self):
        uri = "realm://abc-cai/Proposal/42"
        assert RealmRef.parse(uri).format() == uri

    def test_id_may_contain_slashes(self):
        # Only the first two '/' delimit canister and type; the id keeps the rest.
        ref = RealmRef.parse("realm://c1/Doc/path/to/thing")
        assert ref.entity_type == "Doc"
        assert ref.entity_id == "path/to/thing"

    def test_principal_as_id(self):
        pid = "rdmx6-jaaaa-aaaaa-aaadq-cai"
        ref = RealmRef.parse(f"realm://cap-cai/User/{pid}")
        assert ref.entity_id == pid

    def test_whitespace_is_trimmed(self):
        ref = RealmRef.parse("  realm://c1/User/a  ")
        assert ref.canister_id == "c1"

    @pytest.mark.parametrize(
        "bad",
        [
            "",
            "User/alice",  # no scheme
            "http://c1/User/a",  # wrong scheme
            "realm://c1/User",  # missing id
            "realm://c1",  # missing type + id
            "realm://",  # nothing
            "realm:///User/a",  # empty canister
        ],
    )
    def test_invalid_raises(self, bad):
        with pytest.raises(InvalidRealmRef):
            RealmRef.parse(bad)

    def test_non_string_raises(self):
        with pytest.raises(InvalidRealmRef):
            RealmRef.parse(None)

    def test_try_parse_returns_none(self):
        assert RealmRef.try_parse("not a ref") is None
        assert RealmRef.try_parse("realm://c1/User/a") is not None

    def test_is_ref(self):
        assert RealmRef.is_ref("realm://c1/User/a") is True
        assert RealmRef.is_ref("garbage") is False


class TestConstruct:
    def test_missing_parts_raise(self):
        with pytest.raises(InvalidRealmRef):
            RealmRef("", "User", "a")
        with pytest.raises(InvalidRealmRef):
            RealmRef("c1", "", "a")
        with pytest.raises(InvalidRealmRef):
            RealmRef("c1", "User", "")

    def test_slash_in_canister_or_type_rejected(self):
        with pytest.raises(InvalidRealmRef):
            RealmRef("c/1", "User", "a")
        with pytest.raises(InvalidRealmRef):
            RealmRef("c1", "Us/er", "a")

    def test_make_ref_helper(self):
        assert make_ref("c1", "User", "a") == "realm://c1/User/a"


class TestHelpers:
    def test_is_local(self):
        ref = RealmRef.parse("realm://c1/User/a")
        assert ref.is_local("c1") is True
        assert ref.is_local("c2") is False
        assert ref.is_local("") is False

    def test_with_canister(self):
        ref = RealmRef.parse("realm://c1/User/a")
        moved = ref.with_canister("c2")
        assert moved.canister_id == "c2"
        assert moved.entity_type == "User"
        assert moved.entity_id == "a"
        # original is unchanged (immutable semantics)
        assert ref.canister_id == "c1"

    def test_equality_and_hash(self):
        a = RealmRef.parse("realm://c1/User/x")
        b = RealmRef.parse("realm://c1/User/x")
        c = RealmRef.parse("realm://c2/User/x")
        assert a == b
        assert a != c
        assert hash(a) == hash(b)
        assert len({a, b, c}) == 2
