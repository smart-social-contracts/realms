"""Unit tests for api/licenses.py, api/config.py, api/verification.py."""

import pytest

from marketplace_backend.api import codices as cx_api
from marketplace_backend.api import config as cfg_api
from marketplace_backend.api import extensions as ext_api
from marketplace_backend.api import licenses as lic_api
from marketplace_backend.api import verification as ver_api


def _create_ext(extension_id="voting", developer="dev-1"):
    return ext_api.create_extension(
        developer=developer,
        extension_id=extension_id,
        name=extension_id,
        description="",
        version="0.1.0",
        price_e8s=0,
        icon="",
        categories="other",
        file_registry_canister_id="fr-1",
        file_registry_namespace=f"ext/{extension_id}/0.1.0",
    )


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_only_controller_can_set_config(as_caller):
    as_caller("anon-1", controller=False)
    r = cfg_api.set_file_registry_canister_id("fr-test")
    assert r["success"] is False

    as_caller("admin", controller=True)
    r2 = cfg_api.set_file_registry_canister_id("fr-test")
    assert r2["success"] is True
    assert cfg_api.get_file_registry_canister_id() == "fr-test"


def test_init_config_from_args_idempotent(as_caller):
    cfg_api.init_config_from_args("fr-1", "billing-1")
    assert cfg_api.get_file_registry_canister_id() == "fr-1"
    assert cfg_api.get_billing_service_principal() == "billing-1"
    # Empty strings don't clobber
    cfg_api.init_config_from_args("", "")
    assert cfg_api.get_file_registry_canister_id() == "fr-1"


def test_default_license_pricing():
    p = cfg_api.get_license_pricing()["pricing"]
    assert p["license_price_usd_cents"] == cfg_api.DEFAULT_LICENSE_PRICE_USD_CENTS
    assert p["license_duration_seconds"] == cfg_api.DEFAULT_LICENSE_DURATION_SECONDS


# ---------------------------------------------------------------------------
# Licenses
# ---------------------------------------------------------------------------

def test_record_license_payment_rejects_non_billing_principal(as_caller):
    as_caller("billing-svc", controller=False)
    cfg_api.set_file_registry_canister_id  # smoke

    # Configure billing principal as someone else.
    as_caller("admin", controller=True)
    cfg_api.set_billing_service_principal("billing-other")

    # Now a different non-controller principal tries.
    as_caller("attacker", controller=False)
    r = lic_api.record_license_payment(
        principal="dev-1", stripe_session_id="cs_x", duration_seconds=86400
    )
    assert r["success"] is False
    assert "Unauthorized" in r["error"]


def test_record_license_payment_works_for_billing_principal(as_caller):
    as_caller("admin", controller=True)
    cfg_api.set_billing_service_principal("billing-svc")

    as_caller("billing-svc", controller=False)
    r = lic_api.record_license_payment(
        principal="dev-1", stripe_session_id="cs_xyz", duration_seconds=86400
    )
    assert r["success"] is True
    assert lic_api.has_active_license("dev-1") is True


def test_grant_manual_license_controller_only(as_caller):
    as_caller("anon", controller=False)
    r = lic_api.grant_manual_license(principal="dev-1", duration_seconds=3600, note="hi")
    assert r["success"] is False

    as_caller("admin", controller=True)
    r2 = lic_api.grant_manual_license(principal="dev-1", duration_seconds=3600, note="hi")
    assert r2["success"] is True
    assert lic_api.has_active_license("dev-1") is True


def test_license_expiry(as_caller, advance_time):
    as_caller("admin", controller=True)
    lic_api.grant_manual_license(principal="dev-1", duration_seconds=10, note="short")
    assert lic_api.has_active_license("dev-1") is True
    advance_time(seconds_from_now=20)
    assert lic_api.has_active_license("dev-1") is False


def test_revoke_license_controller_only(as_caller):
    as_caller("admin", controller=True)
    lic_api.grant_manual_license(principal="dev-1", duration_seconds=3600, note="")
    as_caller("anon", controller=False)
    assert lic_api.revoke_license("dev-1")["success"] is False
    as_caller("admin", controller=True)
    assert lic_api.revoke_license("dev-1")["success"] is True
    assert lic_api.has_active_license("dev-1") is False


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def test_request_audit_requires_license(as_caller):
    as_caller("dev-1", controller=False)
    _create_ext()
    r = ver_api.request_audit(caller="dev-1", item_kind="ext", item_id="voting")
    assert r["success"] is False
    assert "license" in r["error"].lower()

    # Grant license, retry.
    as_caller("admin", controller=True)
    lic_api.grant_manual_license(principal="dev-1", duration_seconds=3600, note="")
    as_caller("dev-1", controller=False)
    r2 = ver_api.request_audit(caller="dev-1", item_kind="ext", item_id="voting")
    assert r2["success"] is True
    assert r2["verification_status"] == "pending_audit"


def test_request_audit_only_owner(as_caller):
    as_caller("admin", controller=True)
    lic_api.grant_manual_license(principal="dev-2", duration_seconds=3600, note="")
    as_caller("dev-1", controller=False)
    _create_ext(developer="dev-1")
    as_caller("dev-2", controller=False)
    r = ver_api.request_audit(caller="dev-2", item_kind="ext", item_id="voting")
    assert r["success"] is False
    assert "owner" in r["error"].lower()


def test_set_verification_status_controller_only(as_caller):
    _create_ext()
    as_caller("anon", controller=False)
    r = ver_api.set_verification_status(item_kind="ext", item_id="voting", status="verified", notes="x")
    assert r["success"] is False

    as_caller("admin", controller=True)
    r2 = ver_api.set_verification_status(item_kind="ext", item_id="voting", status="verified", notes="ok")
    assert r2["success"] is True
    e = ext_api.get_extension_details("voting")["extension"]
    assert e["verification_status"] == "verified"
    assert e["verification_notes"] == "ok"


def test_set_verification_status_validates_status(as_caller):
    _create_ext()
    as_caller("admin", controller=True)
    r = ver_api.set_verification_status(item_kind="ext", item_id="voting", status="bogus", notes="")
    assert r["success"] is False


def test_list_pending_audits_controller_only(as_caller):
    _create_ext()
    as_caller("admin", controller=True)
    lic_api.grant_manual_license(principal="dev-1", duration_seconds=3600, note="")
    as_caller("dev-1", controller=False)
    ver_api.request_audit(caller="dev-1", item_kind="ext", item_id="voting")

    as_caller("anon", controller=False)
    assert ver_api.list_pending_audits() == []
    as_caller("admin", controller=True)
    rows = ver_api.list_pending_audits()
    assert len(rows) == 1
    assert rows[0]["item_id"] == "voting"
