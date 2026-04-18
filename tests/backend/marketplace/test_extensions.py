"""Unit tests for api/extensions.py."""

from marketplace_backend.api import extensions as ext_api


def _create(**overrides):
    base = dict(
        developer="dev-1",
        extension_id="voting",
        name="Voting",
        description="Token-weighted voting",
        version="0.1.0",
        price_e8s=0,
        icon="🗳️",
        categories="public_services",
        file_registry_canister_id="fr-1",
        file_registry_namespace="ext/voting/0.1.0",
        download_url="",
    )
    base.update(overrides)
    return ext_api.create_extension(**base)


def test_create_then_get():
    r = _create()
    assert r["success"] is True
    assert r["action"] == "created"

    detail = ext_api.get_extension_details("voting")
    assert detail["success"] is True
    e = detail["extension"]
    assert e["name"] == "Voting"
    assert e["installs"] == 0
    assert e["likes"] == 0
    assert e["verification_status"] == "unverified"
    assert e["is_active"] is True


def test_update_requires_owner(as_caller):
    _create()
    # Different developer tries to update — should fail.
    r = ext_api.create_extension(
        developer="dev-2",
        extension_id="voting",
        name="Hostile rename",
        description="",
        version="0.2.0",
        price_e8s=0,
        icon="",
        categories="other",
        file_registry_canister_id="fr-1",
        file_registry_namespace="ext/voting/0.2.0",
    )
    assert r["success"] is False
    assert "owner" in r["error"].lower()

    # Same developer succeeds.
    r2 = _create(version="0.2.0", description="updated")
    assert r2["success"] is True
    assert r2["action"] == "updated"
    e = ext_api.get_extension_details("voting")["extension"]
    assert e["version"] == "0.2.0"
    assert e["description"] == "updated"


def test_update_resets_verified_to_unverified():
    _create()
    # Force a verified state, then push a new version.
    from marketplace_backend.core.models import ExtensionListingEntity
    listing = ExtensionListingEntity["voting"]
    listing.verification_status = "verified"
    listing.verification_notes = "looks good"

    _create(version="0.2.0")
    e = ext_api.get_extension_details("voting")["extension"]
    assert e["verification_status"] == "unverified"
    assert "Verification reset" in e["verification_notes"]


def test_delist():
    _create()
    r = ext_api.delist_extension("dev-1", "voting")
    assert r["success"] is True
    assert ext_api.get_extension_details("voting")["success"] is False


def test_list_pagination():
    for i in range(7):
        _create(extension_id=f"ext-{i}", name=f"Ext {i}")
    r = ext_api.list_extensions(page=1, per_page=3, verified_only=False)
    assert r["total_count"] == 7
    assert len(r["listings"]) == 3
    r2 = ext_api.list_extensions(page=3, per_page=3, verified_only=False)
    assert len(r2["listings"]) == 1


def test_search_matches_name_and_categories():
    _create(extension_id="voting", name="Voting", categories="public_services,governance")
    _create(extension_id="treasury", name="Treasury", description="ICP wallet", categories="finances")
    assert {e["extension_id"] for e in ext_api.search_extensions("vot", False)} == {"voting"}
    assert {e["extension_id"] for e in ext_api.search_extensions("finance", False)} == {"treasury"}
    assert {e["extension_id"] for e in ext_api.search_extensions("wallet", False)} == {"treasury"}


def test_buy_increments_installs_and_is_idempotent(as_caller):
    _create()
    r1 = ext_api.buy_extension("user-A", "voting")
    assert r1["success"] and r1["action"] == "created"
    r2 = ext_api.buy_extension("user-A", "voting")
    assert r2["success"] and r2["action"] == "exists"
    e = ext_api.get_extension_details("voting")["extension"]
    assert e["installs"] == 1   # idempotent — no double-count

    r3 = ext_api.buy_extension("user-B", "voting")
    assert r3["success"] and r3["action"] == "created"
    e = ext_api.get_extension_details("voting")["extension"]
    assert e["installs"] == 2


def test_my_purchases_returns_only_caller_rows():
    _create()
    ext_api.buy_extension("user-A", "voting")
    ext_api.buy_extension("user-B", "voting")
    rows = ext_api.get_my_purchases("user-A")
    assert len(rows) == 1
    assert rows[0]["item_kind"] == "ext"
    assert rows[0]["item_id"] == "voting"
