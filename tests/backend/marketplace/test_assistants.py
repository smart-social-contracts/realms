"""Unit tests for api/assistants.py + the assistant branches added to
api/likes.py, api/rankings.py, api/verification.py, api/status.py.

Mirrors test_codices.py + assertions on the AI-specific fields.
"""

import pytest

from marketplace_backend.api import assistants as a_api
from marketplace_backend.api import licenses as lic_api
from marketplace_backend.api import likes as likes_api
from marketplace_backend.api import rankings as rank_api
from marketplace_backend.api import status as status_api
from marketplace_backend.api import verification as ver_api


def _create(**overrides):
    base = dict(
        developer="dev-1",
        assistant_id="smart-social-contracts/ashoka",
        name="Ashoka",
        description="Governance-domain LLM agent",
        version="0.4.2",
        price_e8s=0,
        pricing_summary="$200/year per realm",
        icon="🤖",
        categories="oversight",
        runtime="openai",
        endpoint_url="https://api.openai.com/v1/chat/completions",
        base_model="gpt-4o",
        requested_role="auditor",
        requested_permissions="read_proposals,read_treasury,submit_proposal",
        domains="governance,tax",
        languages="en,es",
        training_data_summary="Trained on Indian tax law and Realms governance corpus.",
        eval_report_url="https://example.org/evals/ashoka-2026-04-15.md",
        file_registry_canister_id="fr-1",
        file_registry_namespace="assistant/smart-social-contracts/ashoka/0.4.2",
    )
    base.update(overrides)
    return a_api.create_assistant(**base)


def test_slash_safe_alias_round_trip():
    r = _create()
    assert r["success"] is True
    detail = a_api.get_assistant_details("smart-social-contracts/ashoka")
    assert detail["success"] is True
    a = detail["assistant"]
    assert a["assistant_id"] == "smart-social-contracts/ashoka"
    assert a["assistant_alias"] == "smart-social-contracts__ashoka"
    assert a["runtime"] == "openai"
    assert a["base_model"] == "gpt-4o"
    assert a["requested_role"] == "auditor"


def test_create_validates_runtime():
    r = a_api.create_assistant(
        developer="dev-1",
        assistant_id="bad",
        name="bad",
        description="",
        version="0.1.0",
        price_e8s=0,
        pricing_summary="",
        icon="",
        categories="other",
        runtime="not-a-valid-runtime",
        endpoint_url="",
        base_model="",
        requested_role="",
        requested_permissions="",
        domains="",
        languages="",
        training_data_summary="",
        eval_report_url="",
        file_registry_canister_id="fr-1",
        file_registry_namespace="assistant/bad/0.1.0",
    )
    assert r["success"] is False
    assert "runtime must be one of" in r["error"]


def test_create_validates_id():
    r = a_api.create_assistant(
        developer="dev-1",
        assistant_id="too/many/slashes",
        name="bad",
        description="",
        version="0.1.0",
        price_e8s=0,
        pricing_summary="",
        icon="",
        categories="other",
        runtime="openai",
        endpoint_url="",
        base_model="",
        requested_role="",
        requested_permissions="",
        domains="",
        languages="",
        training_data_summary="",
        eval_report_url="",
        file_registry_canister_id="fr-1",
        file_registry_namespace="assistant/too/many/slashes/0.1.0",
    )
    assert r["success"] is False
    assert "at most one" in r["error"]


def test_update_resets_verified_to_unverified(as_caller):
    _create()
    from marketplace_backend.core.models import AssistantListingEntity
    listing = AssistantListingEntity["smart-social-contracts__ashoka"]
    listing.verification_status = "verified"
    listing.verification_notes = "looks good"

    _create(version="0.5.0")
    a = a_api.get_assistant_details("smart-social-contracts/ashoka")["assistant"]
    assert a["verification_status"] == "unverified"
    assert "Verification reset" in a["verification_notes"]


def test_buy_assistant_idempotent_and_increments_installs():
    _create()
    r1 = a_api.buy_assistant("realm-A", "smart-social-contracts/ashoka")
    assert r1["success"] and r1["action"] == "created"
    r2 = a_api.buy_assistant("realm-A", "smart-social-contracts/ashoka")
    assert r2["success"] and r2["action"] == "exists"
    a = a_api.get_assistant_details("smart-social-contracts/ashoka")["assistant"]
    assert a["installs"] == 1
    a_api.buy_assistant("realm-B", "smart-social-contracts/ashoka")
    a = a_api.get_assistant_details("smart-social-contracts/ashoka")["assistant"]
    assert a["installs"] == 2


def test_search_matches_runtime_and_role():
    _create()
    _create(
        assistant_id="other/agent",
        name="Other",
        runtime="anthropic",
        requested_role="proposer",
        domains="justice",
        file_registry_namespace="assistant/other/agent/0.1.0",
    )
    by_runtime = {a["assistant_id"] for a in a_api.search_assistants("anthropic", False)}
    assert by_runtime == {"other/agent"}
    by_role = {a["assistant_id"] for a in a_api.search_assistants("auditor", False)}
    assert by_role == {"smart-social-contracts/ashoka"}
    by_domain = {a["assistant_id"] for a in a_api.search_assistants("justice", False)}
    assert by_domain == {"other/agent"}


def test_delist_hides_from_listings():
    _create()
    a_api.delist_assistant("dev-1", "smart-social-contracts/ashoka")
    r = a_api.list_assistants(1, 20, False)
    assert all(a["assistant_id"] != "smart-social-contracts/ashoka" for a in r["listings"])
    assert a_api.get_assistant_details("smart-social-contracts/ashoka")["success"] is False


# ---------------------------------------------------------------------------
# Cross-cutting: likes, rankings, verification, status
# ---------------------------------------------------------------------------

def test_like_assistant():
    _create()
    r = likes_api.like_item("user-A", "assistant", "smart-social-contracts/ashoka")
    assert r["action"] == "created"
    a = a_api.get_assistant_details("smart-social-contracts/ashoka")["assistant"]
    assert a["likes"] == 1
    likes_api.unlike_item("user-A", "assistant", "smart-social-contracts/ashoka")
    a = a_api.get_assistant_details("smart-social-contracts/ashoka")["assistant"]
    assert a["likes"] == 0


def test_top_assistants_by_downloads():
    _create()
    _create(assistant_id="other/agent", file_registry_namespace="assistant/other/agent/0.1.0")
    a_api.buy_assistant("realm-A", "smart-social-contracts/ashoka")
    a_api.buy_assistant("realm-B", "smart-social-contracts/ashoka")
    a_api.buy_assistant("realm-A", "other/agent")
    top = rank_api.top_assistants_by_downloads(10)
    ids = [t["assistant_id"] for t in top]
    assert ids[:2] == ["smart-social-contracts/ashoka", "other/agent"]


def test_top_assistants_by_likes_with_verified_only():
    _create()
    _create(assistant_id="other/agent", file_registry_namespace="assistant/other/agent/0.1.0")
    likes_api.like_item("u1", "assistant", "other/agent")
    # Mark only one as verified
    from marketplace_backend.core.models import AssistantListingEntity
    AssistantListingEntity["smart-social-contracts__ashoka"].verification_status = "verified"

    by_likes = rank_api.top_assistants_by_likes(10)
    assert {t["assistant_id"] for t in by_likes} == {"smart-social-contracts/ashoka", "other/agent"}

    by_likes_verified = rank_api.top_assistants_by_likes(10, verified_only=True)
    assert {t["assistant_id"] for t in by_likes_verified} == {"smart-social-contracts/ashoka"}


def test_request_audit_for_assistant_requires_license(as_caller):
    as_caller("dev-1", controller=False)
    _create()
    r = ver_api.request_audit(caller="dev-1", item_kind="assistant", item_id="smart-social-contracts/ashoka")
    assert r["success"] is False
    assert "license" in r["error"].lower()

    as_caller("admin", controller=True)
    lic_api.grant_manual_license(principal="dev-1", duration_seconds=3600, note="")
    as_caller("dev-1", controller=False)
    r2 = ver_api.request_audit(caller="dev-1", item_kind="assistant", item_id="smart-social-contracts/ashoka")
    assert r2["success"] is True
    assert r2["verification_status"] == "pending_audit"


def test_set_verification_status_for_assistant_controller_only(as_caller):
    _create()
    as_caller("anon", controller=False)
    r = ver_api.set_verification_status(
        item_kind="assistant", item_id="smart-social-contracts/ashoka", status="verified", notes="x",
    )
    assert r["success"] is False

    as_caller("admin", controller=True)
    r2 = ver_api.set_verification_status(
        item_kind="assistant", item_id="smart-social-contracts/ashoka", status="verified", notes="audited",
    )
    assert r2["success"] is True
    a = a_api.get_assistant_details("smart-social-contracts/ashoka")["assistant"]
    assert a["verification_status"] == "verified"
    assert a["verification_notes"] == "audited"


def test_status_includes_assistants_count():
    _create()
    _create(assistant_id="other/agent", file_registry_namespace="assistant/other/agent/0.1.0")
    s = status_api.get_status()
    assert s["assistants_count"] == 2
    assert "extensions_count" in s
    assert "codices_count" in s


def test_pending_audits_includes_assistant(as_caller):
    _create()
    as_caller("admin", controller=True)
    lic_api.grant_manual_license(principal="dev-1", duration_seconds=3600, note="")
    as_caller("dev-1", controller=False)
    ver_api.request_audit(caller="dev-1", item_kind="assistant", item_id="smart-social-contracts/ashoka")
    as_caller("admin", controller=True)
    rows = ver_api.list_pending_audits()
    assert any(r["item_kind"] == "assistant" and r["item_id"] == "smart-social-contracts/ashoka" for r in rows)
