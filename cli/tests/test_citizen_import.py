"""Unit tests for citizen bulk import + II principal binding (issue #241).

Runs against the realms.testing mock harness — no replica required. The core
module is loaded by file path so core/__init__.py (which needs the kybra
runtime) is never executed.
"""

import importlib.util
import json
import os

from realms.testing import reset_registry, setup_test_env

setup_test_env()
reset_registry()

_MODULE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "src",
    "realm_backend",
    "core",
    "citizen_import.py",
)
_spec = importlib.util.spec_from_file_location("citizen_import_under_test", _MODULE_PATH)
ci = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(ci)

from ggg import RegistrationCode, User  # noqa: E402


def test_import_creates_single_use_codes():
    reset_registry()
    res = ci.import_citizens(
        [
            {"id": "C-1", "name": "Ada Lovelace", "quarter": "North Quarter"},
            {"id": "C-2", "name": "Alan Turing", "email": "alan@example.org"},
        ],
        created_by="admin-principal",
        frontend_url="https://realm.example",
    )
    assert res["success"], res
    data = res["data"]
    assert data["created_count"] == 2
    assert data["skipped_count"] == 0
    assert data["error_count"] == 0

    codes = RegistrationCode.instances()
    assert len(codes) == 2
    by_id = {c.user_id: c for c in codes}
    ada = by_id["C-1"]
    assert ada.max_uses == 1
    assert ada.profile == "member"
    meta = json.loads(ada.metadata)
    assert meta["kind"] == "citizen_import"
    assert meta["name"] == "Ada Lovelace"
    assert meta["quarter"] == "North Quarter"
    assert by_id["C-2"].email == "alan@example.org"

    # Personal invite handed back for distribution.
    assert data["created"][0]["code"]


def test_reimport_is_idempotent():
    reset_registry()
    ci.import_citizens([{"id": "C-1", "name": "Ada"}])
    res = ci.import_citizens([{"id": "C-1", "name": "Ada"}, {"id": "C-2", "name": "Alan"}])
    data = res["data"]
    assert data["created_count"] == 1
    assert data["skipped"] == ["C-1"]
    assert len(RegistrationCode.instances()) == 2


def test_validation_report():
    reset_registry()
    res = ci.import_citizens([{"name": "no id"}, "not-an-object", {"id": "OK-1"}])
    data = res["data"]
    assert data["created_count"] == 1
    assert data["error_count"] == 2
    assert {e["index"] for e in data["errors"]} == {0, 1}


def test_batch_cap():
    reset_registry()
    res = ci.import_citizens([{"id": f"C-{i}"} for i in range(ci.MAX_BATCH + 1)])
    assert not res["success"]
    assert "batches" in res["error"]


def test_bind_citizen_attaches_record_and_quarter():
    reset_registry()
    user = User(id="aaaaa-principal", nickname="", private_data="")
    consume_data = {
        "profile": "member",
        "department": "",
        "user_id": "C-1",
        "metadata": json.dumps({
            "kind": "citizen_import",
            "name": "Ada Lovelace",
            "quarter": "North Quarter",
            "extra": {"date_of_birth": "1815-12-10"},
        }),
    }
    quarter = ci.bind_citizen(user, consume_data)
    assert quarter == "North Quarter"
    assert user.nickname == "Ada Lovelace"
    private = json.loads(user.private_data)
    assert private["citizen_import"]["id"] == "C-1"
    assert private["citizen_import"]["date_of_birth"] == "1815-12-10"


def test_bind_ignores_non_import_codes():
    reset_registry()
    user = User(id="bbbbb-principal", nickname="Existing", private_data="")
    assert ci.bind_citizen(user, {"user_id": "x", "metadata": ""}) == ""
    assert ci.bind_citizen(user, {"user_id": "x", "metadata": "not json"}) == ""
    assert user.nickname == "Existing"


def test_bind_preserves_existing_nickname_and_private_data():
    reset_registry()
    user = User(
        id="ccccc-principal",
        nickname="ChosenName",
        private_data=json.dumps({"phone": "123"}),
    )
    ci.bind_citizen(user, {
        "user_id": "C-9",
        "metadata": json.dumps({"kind": "citizen_import", "name": "Imported Name", "quarter": ""}),
    })
    assert user.nickname == "ChosenName"
    private = json.loads(user.private_data)
    assert private["phone"] == "123"
    assert private["citizen_import"]["id"] == "C-9"


def test_import_status_counts_claims():
    reset_registry()
    ci.import_citizens([{"id": "C-1"}, {"id": "C-2"}, {"id": "C-3"}])
    codes = sorted(RegistrationCode.instances(), key=lambda c: c.user_id)
    codes[0].uses_count = 1  # C-1 claimed
    codes[1].revoked = 1     # C-2 revoked

    status = ci.import_status()
    assert status == {"total": 3, "claimed": 1, "revoked": 1, "pending": 1}


def _letter_row(i, **extra):
    row = {
        "id": f"C-{i}",
        "name": f"Citizen {i}",
        "address": f"{i} Postal Street",
    }
    row.update(extra)
    return row


def test_letter_mint_is_chunked():
    reset_registry()
    too_many = [_letter_row(i) for i in range(ci.LETTER_BATCH + 1)]
    res = ci.ensure_letter_codes(too_many)
    assert not res["success"]
    assert "batches" in res["error"]
    assert len(RegistrationCode.instances()) == 0

    ok = ci.ensure_letter_codes(too_many[: ci.LETTER_BATCH])
    assert ok["success"], ok
    assert ok["data"]["created_count"] == ci.LETTER_BATCH
    assert len(RegistrationCode.instances()) == ci.LETTER_BATCH


def test_second_generate_reuses_code():
    reset_registry()
    row = _letter_row(1)
    first = ci.ensure_letter_codes([row])
    assert first["success"], first
    code = first["data"]["letters"][0]["code"]
    assert code
    assert first["data"]["created_count"] == 1

    second = ci.ensure_letter_codes([row])
    assert second["success"], second
    letter = second["data"]["letters"][0]
    assert letter["reused"] is True
    assert letter["code"] == code
    assert second["data"]["created_count"] == 0
    assert second["data"]["reused_count"] == 1
    assert len(RegistrationCode.instances()) == 1


def test_redeem_consumes_once():
    reset_registry()
    res = ci.ensure_letter_codes([_letter_row(1)])
    plaintext = res["data"]["letters"][0]["code"]
    rc = next(c for c in RegistrationCode.instances() if c.code == plaintext)
    assert rc.max_uses == 1
    assert (rc.uses_count or 0) == 0

    def consume(principal: str) -> bool:
        if rc.used == 1 or (rc.uses_count or 0) >= rc.max_uses:
            return False
        if principal and principal in (rc.principals_redeemed or "").split(","):
            return False
        rc.uses_count = (rc.uses_count or 0) + 1
        if rc.principals_redeemed:
            rc.principals_redeemed += "," + principal
        else:
            rc.principals_redeemed = principal
        if rc.uses_count >= rc.max_uses:
            rc.used = 1
        return True

    assert consume("principal-one") is True
    assert rc.used == 1
    assert consume("principal-two") is False
    assert consume("principal-one") is False

    # Redeemed row still must not remint on a later generate.
    again = ci.ensure_letter_codes([_letter_row(1)])
    assert again["data"]["letters"][0]["code"] == plaintext
    assert again["data"]["letters"][0]["reused"] is True
    assert len(RegistrationCode.instances()) == 1


def test_resume_cursor_does_not_remint():
    """Pause after a prefix, then resume the full list — no second mint."""
    reset_registry()
    rows = [_letter_row(i) for i in range(5)]

    first_chunk = ci.ensure_letter_codes(rows[:3])
    assert first_chunk["data"]["created_count"] == 3
    first_codes = {row["id"]: row["code"] for row in first_chunk["data"]["letters"]}

    resumed = ci.ensure_letter_codes(rows)
    assert resumed["success"], resumed
    assert resumed["data"]["reused_count"] == 3
    assert resumed["data"]["created_count"] == 2
    by_id = {row["id"]: row for row in resumed["data"]["letters"]}
    for cid, code in first_codes.items():
        assert by_id[cid]["code"] == code
        assert by_id[cid]["reused"] is True
    assert len(RegistrationCode.instances()) == 5


def test_letter_requires_postal_address():
    reset_registry()
    res = ci.ensure_letter_codes([{"id": "C-1", "name": "Ada"}])
    assert res["success"]
    assert res["data"]["created_count"] == 0
    assert res["data"]["error_count"] == 1
    assert "postal address" in res["data"]["errors"][0]["error"]
    assert len(RegistrationCode.instances()) == 0


def test_import_stores_address_for_later_letter():
    reset_registry()
    ci.import_citizens([_letter_row(1, email="ada@example.org")])
    res = ci.ensure_letter_codes([_letter_row(1)])
    assert res["data"]["reused_count"] == 1
    assert res["data"]["letters"][0]["address"] == "1 Postal Street"
    meta = json.loads(RegistrationCode.instances()[0].metadata)
    assert meta["address"] == "1 Postal Street"
