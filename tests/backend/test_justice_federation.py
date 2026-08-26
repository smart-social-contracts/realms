"""Justice federation pipe (issue #325).

Transfer freeze + dest live Case + restitution pending-if-no-ack.
No venue picker. No EntityMigration. Ciphertext only on the pipe.
"""

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))
sys.modules["basilisk"] = MagicMock()
sys.modules["basilisk.canisters.management"] = MagicMock()
sys.modules.setdefault("_cdk", MagicMock())
sys.modules["_cdk"].ic.id.return_value.to_str.return_value = "self-cai"

from core.justice import federation as jfed  # noqa: E402
from ggg.justice.case import CaseStatus, case_file, case_transfer  # noqa: E402
from ggg.justice.court import Court, CourtLevel  # noqa: E402
from ggg.justice.penalty import Penalty, PenaltyType, penalty_execute  # noqa: E402
from ggg.justice.verdict import Verdict  # noqa: E402
from ggg.system.user import User  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_seams():
    jfed.set_outbound_sender(None)
    jfed.set_collect_fn(None)
    yield
    jfed.set_outbound_sender(None)
    jfed.set_collect_fn(None)


def _court_and_parties(suffix=""):
    court = Court(
        name=f"Fed Court{suffix}",
        level=CourtLevel.FIRST_INSTANCE,
        status="active",
    )
    return court, User(id=f"plaintiff-{suffix or 'a'}"), User(id=f"defendant-{suffix or 'a'}")


_penalty_seq = 0


def _executing_case_with_penalty(kind=PenaltyType.RESTITUTION, amount=50.0):
    global _penalty_seq
    _penalty_seq += 1
    court, plaintiff, defendant = _court_and_parties(f"r{_penalty_seq}")
    case = case_file(court, plaintiff, defendant, "", "")
    case.status = CaseStatus.EXECUTING
    verdict = Verdict(decision="liable", reasoning="r", issued_date="2026-01-01")
    verdict.case = case
    case.verdict = verdict
    penalty = Penalty(
        id=f"PEN-REST-{_penalty_seq}",
        penalty_type=kind,
        amount=amount,
        status="pending",
        currency="REALMS",
    )
    penalty.verdict = verdict
    penalty.target_user = defendant
    return case, penalty


class TestDestCanisterAndAddress:
    def test_dest_canister_from_string_and_realm_ref(self):
        assert jfed.dest_canister_id("aaaaa-aa") == "aaaaa-aa"
        assert jfed.dest_canister_id({"id": "bbbbb-bb"}) == "bbbbb-bb"
        assert (
            jfed.dest_canister_id("realm://ccccc-cc/User/z32zf-principal")
            == "ccccc-cc"
        )

    def test_user_address_is_not_a_venue(self):
        parsed = jfed.parse_user_address(
            "realm://q0-cai/User/z32zf-ic72u-hae"
        )
        assert parsed["principal"] == "z32zf-ic72u-hae"
        assert parsed["canister_id"] == "q0-cai"
        assert jfed.parse_user_address("local-principal")["principal"] == "local-principal"


class TestTransferFreezeAndBody:
    def test_origin_freezes_with_dest_pointer(self):
        court, plaintiff, defendant = _court_and_parties("t")
        case = case_file(court, plaintiff, defendant, "SECRET TITLE", "SECRET BODY")
        case_transfer(case, dest={"id": "q0-cai"})
        assert case.status == CaseStatus.TRANSFERRED
        assert case.is_open() is False
        meta = json.loads(case.metadata)
        assert meta["transfer_dest"]["id"] == "q0-cai"
        assert meta.get("transferred") is True

    def test_transfer_body_is_ciphertext_only(self):
        court, plaintiff, defendant = _court_and_parties("c")
        case = case_file(court, plaintiff, defendant, "SECRET TITLE", "SECRET BODY")
        body = jfed.transfer_body(case, ciphertext="enc:v=2:blob", origin_scope="litigation:x")
        dumped = json.dumps(body)
        assert "SECRET TITLE" not in dumped
        assert "SECRET BODY" not in dumped
        assert body["ciphertext"] == "enc:v=2:blob"
        assert body["origin_case_id"] == str(case._id)
        assert body["plaintiff_id"] == plaintiff.id
        assert body["defendant_id"] == defendant.id


class TestDestCreatesLiveCase:
    def test_accept_transfer_creates_live_case(self, monkeypatch):
        court, *_ = _court_and_parties("d")
        from core.justice import courts

        monkeypatch.setattr(courts, "preferred_court", lambda: court)
        monkeypatch.setattr(courts, "ensure_default_court", lambda: court)

        result = jfed.accept_transfer("q1-cai", {
            "origin_case_id": "origin-9",
            "origin_case_number": "Q1-0009",
            "ciphertext": "enc:v=2:hello",
            "origin_scope": "litigation:Justice:filer:origin-9",
            "plaintiff_id": "cybi7-filer",
            "defendant_id": "z32zf-def",
            "filer_id": "cybi7-filer",
            "wrapped_deks": {"justice": "wrap-j", "filer": "wrap-f"},
        })
        assert result["success"] is True
        assert result["duplicate"] is False
        from ggg import Case

        live = Case[result["live_case_id"]]
        assert live.status == CaseStatus.FILED
        assert live.is_open() is True
        assert live.title == ""
        assert live.description == ""
        meta = json.loads(live.metadata)
        assert meta["origin_canister"] == "q1-cai"
        assert meta["origin_case_id"] == "origin-9"
        assert meta["origin_case_number"] == "Q1-0009"
        assert "wrapped_deks" in meta

    def test_accept_transfer_is_idempotent(self, monkeypatch):
        court, *_ = _court_and_parties("i")
        from core.justice import courts

        monkeypatch.setattr(courts, "preferred_court", lambda: court)
        monkeypatch.setattr(courts, "ensure_default_court", lambda: court)
        body = {
            "origin_case_id": "origin-idem",
            "origin_case_number": "Q1-IDEM",
            "plaintiff_id": "p-idem",
            "defendant_id": "d-idem",
            "filer_id": "p-idem",
            "ciphertext": "enc:x",
        }
        first = jfed.accept_transfer("q1-cai", body)
        second = jfed.accept_transfer("q1-cai", body)
        assert first["success"] and second["success"]
        assert second["duplicate"] is True
        assert second["live_case_id"] == first["live_case_id"]

    def test_origin_notify_records_dest_pointer(self):
        court, plaintiff, defendant = _court_and_parties("n")
        case = case_file(court, plaintiff, defendant, "", "")
        case_transfer(case, dest={"id": "q0-cai"})

        def sender(target, topic, body):
            assert target == "q0-cai"
            assert topic == jfed.TOPIC_TRANSFER
            assert "SECRET" not in json.dumps(body)
            assert body["ciphertext"] == "enc:pipe"
            return {
                "success": True,
                "live_case_id": "42",
                "live_case_number": "Q0-0042",
            }

        jfed.set_outbound_sender(sender)
        ack = jfed.notify_transfer(case, "q0-cai", ciphertext="enc:pipe")
        assert ack["success"] is True
        meta = json.loads(case.metadata)
        assert meta["transfer_dest"]["id"] == "q0-cai"
        assert meta["transfer_dest"]["live_case_id"] == "42"
        assert meta["transfer_acked"] is True


class TestRestitutionPendingIfNoAck:
    def test_no_funds_stays_pending(self):
        from core.justice.cases import execute_penalty

        case, penalty = _executing_case_with_penalty()
        jfed.set_collect_fn(lambda _p: False)
        updated = execute_penalty("judge1", penalty.id)
        assert updated.status == "pending"
        assert case.status == CaseStatus.EXECUTING

    def test_collected_but_no_ack_stays_pending(self, monkeypatch):
        from core.justice.cases import execute_penalty

        case, penalty = _executing_case_with_penalty()
        jfed.set_collect_fn(lambda _p: True)
        jfed.set_outbound_sender(
            lambda target, topic, body: {"success": False, "error": "no ack"}
        )
        monkeypatch.setattr(jfed, "plaintiff_home_quarter", lambda _c: "q1-home-cai")
        updated = execute_penalty("judge1", penalty.id)
        assert updated.status == "pending"
        meta = json.loads(updated.metadata or "{}")
        assert meta.get("collected") is True
        assert meta.get("restitution_awaiting_ack") is True

    def test_ack_marks_executed_and_is_not_treasury_revenue(self, monkeypatch):
        from core.justice.cases import execute_penalty, record_penalty_revenue

        case, penalty = _executing_case_with_penalty()
        jfed.set_collect_fn(lambda _p: True)
        jfed.set_outbound_sender(
            lambda target, topic, body: {"success": True, "credited": True}
        )
        monkeypatch.setattr(jfed, "plaintiff_home_quarter", lambda _c: "q1-home-cai")
        updated = execute_penalty("judge1", penalty.id)
        assert updated.status == "executed"
        assert record_penalty_revenue(updated) == 0

    def test_fine_still_executes_locally(self):
        from core.justice.cases import execute_penalty

        case, penalty = _executing_case_with_penalty(kind=PenaltyType.FINE)
        updated = execute_penalty("judge1", penalty.id)
        assert updated.status == "executed"


class TestHostDispatch:
    def test_justice_transfer_uses_host_when_codex_silent(self, monkeypatch):
        import core.codex_hooks as codex_hooks
        import core.federation as core_fed

        seen = {}

        def fake_accept(source, body):
            seen["source"] = source
            seen["body"] = body
            return {"success": True, "live_case_id": "7"}

        monkeypatch.setattr(codex_hooks, "dispatch_federation_message", lambda *a: None)
        monkeypatch.setattr(jfed, "accept_transfer", fake_accept)
        result = core_fed.dispatch_message(
            "justice.transfer", "q1-cai", {"origin_case_id": "1"}
        )
        assert result["success"] is True
        assert seen["source"] == "q1-cai"

    def test_other_topics_still_need_codex(self, monkeypatch):
        import core.codex_hooks as codex_hooks
        import core.federation as core_fed

        monkeypatch.setattr(codex_hooks, "dispatch_federation_message", lambda *a: None)
        result = core_fed.dispatch_message("tax.remit", "q1-cai", {})
        assert result["success"] is False
        assert "No codex handler" in result["error"]


class TestRealmRefDefendantAddress:
    """Cross-Mundus defendant is a ``realm://`` address, not a venue."""

    REF = "realm://q0-cai/User/z32zf-ic72u-hae"

    def test_parse_user_address_realm_ref(self):
        parsed = jfed.parse_user_address(self.REF)
        assert parsed["principal"] == "z32zf-ic72u-hae"
        assert parsed["canister_id"] == "q0-cai"
        assert parsed["ref"] == self.REF

    def test_local_principal_paste(self):
        parsed = jfed.parse_user_address("aaaaa-aa")
        assert parsed["principal"] == "aaaaa-aa"
        assert parsed["canister_id"] == ""
        assert parsed["ref"] == ""

    def test_defendant_metadata_stores_ref_not_court(self):
        from core.justice import cases

        _court, plaintiff, _defendant = _court_and_parties("ref")
        _user, meta, cross = cases._defendant_metadata(
            plaintiff.id, "user", self.REF, "", "", "",
        )
        parsed = json.loads(meta)
        assert parsed["defendant_ref"] == self.REF
        assert parsed["defendant_principal"] == "z32zf-ic72u-hae"
        assert parsed["defendant_quarter_id"] == "q0-cai"
        assert parsed.get("scope_tag") == "cross_quarter"
        assert "court" not in parsed
        assert "court_id" not in parsed
        assert "lives_in" not in parsed
        assert "lookup_hint" not in parsed
        assert cross is True

    def test_dest_canister_ignores_filer_address_fields(self):
        assert jfed.dest_canister_id({"lives_in": "q0-cai"}) == ""
        assert jfed.dest_canister_id({"defendant_quarter_id": "q0-cai"}) == ""
        assert jfed.dest_canister_id({"defendant_ref": self.REF}) == ""

    def test_transfer_without_judge_dest_does_not_send_to_address(self):
        sent = []
        jfed.set_outbound_sender(
            lambda target, topic, body: sent.append(target) or {"success": True}
        )
        court, plaintiff, defendant = _court_and_parties("addr")
        case = case_file(court, plaintiff, defendant, "", "")
        case.metadata = json.dumps({
            "defendant_ref": self.REF,
            "defendant_quarter_id": "q0-cai",
        })
        case_transfer(case, dest=None)
        assert jfed.dest_canister_id(None) == ""
        assert sent == []
        assert case.status == CaseStatus.TRANSFERRED

    def test_directory_is_local_only(self):
        from core.justice import directory as jdir

        assert not hasattr(jdir, "lookup")
        assert callable(jdir.list_local_entries)
