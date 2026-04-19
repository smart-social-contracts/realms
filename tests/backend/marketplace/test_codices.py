"""Unit tests for api/codices.py."""

from marketplace_backend.api import codices as cx_api


def _create(**overrides):
    base = dict(
        developer="dev-1",
        codex_id="syntropia/membership",
        realm_type="syntropia",
        name="Membership",
        description="Onboarding flow",
        version="0.1.0",
        price_e8s=0,
        icon="📜",
        categories="governance",
        file_registry_canister_id="fr-1",
        file_registry_namespace="codex/syntropia/membership/0.1.0",
    )
    base.update(overrides)
    return cx_api.create_codex(**base)


def test_slash_safe_alias_round_trip():
    r = _create()
    assert r["success"] is True
    detail = cx_api.get_codex_details("syntropia/membership")
    assert detail["success"] is True
    c = detail["codex"]
    assert c["codex_id"] == "syntropia/membership"
    assert c["codex_alias"] == "syntropia__membership"
    assert c["realm_type"] == "syntropia"


def test_create_validates_id():
    r = cx_api.create_codex(
        developer="dev-1",
        codex_id="too/many/parts",
        realm_type="x",
        name="bad",
        description="",
        version="0.1.0",
        price_e8s=0,
        icon="",
        categories="other",
        file_registry_canister_id="fr-1",
        file_registry_namespace="codex/too/many/parts/0.1.0",
    )
    assert r["success"] is False
    assert "at most one" in r["error"]


def test_buy_increments_installs():
    _create()
    cx_api.buy_codex("user-A", "syntropia/membership")
    cx_api.buy_codex("user-A", "syntropia/membership")  # idempotent
    cx_api.buy_codex("user-B", "syntropia/membership")
    c = cx_api.get_codex_details("syntropia/membership")["codex"]
    assert c["installs"] == 2


def test_search_matches_realm_type():
    _create()
    _create(codex_id="dominion/treasury", realm_type="dominion", name="Treasury", file_registry_namespace="codex/dominion/treasury/0.1.0")
    rs = cx_api.search_codices("syntropia", False)
    assert {c["codex_id"] for c in rs} == {"syntropia/membership"}
    rs2 = cx_api.search_codices("dominion", False)
    assert {c["codex_id"] for c in rs2} == {"dominion/treasury"}


def test_delist_hides_from_listings():
    _create()
    cx_api.delist_codex("dev-1", "syntropia/membership")
    r = cx_api.list_codices(1, 20, False)
    assert all(c["codex_id"] != "syntropia/membership" for c in r["listings"])
    # And get_details now reports not-found.
    assert cx_api.get_codex_details("syntropia/membership")["success"] is False
