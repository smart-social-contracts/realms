"""Tests for the quarter-local self-bootstrap plan + state machine (issue #156).

CI-friendly (no live replica): ``build_bootstrap_plan`` and ``step_plan`` are
pure (json + logging only), so we load ``core/quarter_bootstrap.py`` directly by
path — avoiding ``core/__init__.py`` and the canister-only lazy imports inside
``advance_bootstrap``/``seed_*`` (which only run in-canister).
"""

import importlib.util
import os

# Load core/quarter_bootstrap.py by path (no package __init__ side effects).
_QB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "src", "realm_backend", "core", "quarter_bootstrap.py",
)
_spec = importlib.util.spec_from_file_location("quarter_bootstrap_under_test", _QB_PATH)
qb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qb)


# ---------------------------------------------------------------------------
# build_bootstrap_plan
# ---------------------------------------------------------------------------

class TestBuildBootstrapPlan:
    def test_empty_spec_is_complete(self):
        plan = qb.build_bootstrap_plan({})
        assert plan["items"] == []
        assert plan["status"] == "complete"
        assert plan["cursor"] == 0
        assert plan["done"] == [] and plan["failed"] == []

    def test_no_registry_means_no_items(self):
        # Codex + extensions given, but nothing to pull them from.
        plan = qb.build_bootstrap_plan({
            "codex": {"codex_id": "agora/gov"},
            "extensions": ["realm_settings", "public_dashboard"],
        })
        assert plan["items"] == []
        assert plan["status"] == "complete"

    def test_codex_first_then_extensions(self):
        plan = qb.build_bootstrap_plan({
            "parent_realm_canister_id": "cap-1",
            "registry_canister_id": "reg-1",
            "frontend_canister_id": "fe-1",
            "codex": {"codex_id": "agora/gov", "version": None, "run_init": True},
            "extensions": [
                {"ext_id": "realm_settings", "version": None},
                {"ext_id": "public_dashboard"},
                "voting",  # plain-string form
                {"ext_id": ""},  # skipped (blank)
            ],
        })
        assert plan["parent"] == "cap-1"
        assert plan["registry"] == "reg-1"
        assert plan["frontend"] == "fe-1"
        kinds = [(i["kind"], i["id"]) for i in plan["items"]]
        assert kinds == [
            ("codex", "agora/gov"),
            ("extension", "realm_settings"),
            ("extension", "public_dashboard"),
            ("extension", "voting"),
        ]
        assert plan["status"] == "pending"

    def test_blank_codex_id_skipped(self):
        plan = qb.build_bootstrap_plan({
            "registry_canister_id": "reg-1",
            "codex": {"codex_id": "  "},
            "extensions": ["voting"],
        })
        assert [i["kind"] for i in plan["items"]] == ["extension"]

    def test_codices_list_installs_all_before_extensions(self):
        # The auto-derived path mirrors a capital with >1 codex package.
        plan = qb.build_bootstrap_plan({
            "registry_canister_id": "reg-1",
            "codices": [
                {"codex_id": "agora", "version": "0.2.0", "run_init": True},
                {"codex_id": "agora/gov", "version": None},
                {"codex_id": "  "},  # skipped (blank)
            ],
            "extensions": ["voting"],
        })
        kinds = [(i["kind"], i["id"]) for i in plan["items"]]
        assert kinds == [
            ("codex", "agora"),
            ("codex", "agora/gov"),
            ("extension", "voting"),
        ]
        # run_init carried through; default True when omitted.
        codex_items = [i for i in plan["items"] if i["kind"] == "codex"]
        assert codex_items[0]["run_init"] is True
        assert codex_items[1]["run_init"] is True

    def test_codices_list_takes_precedence_over_single_codex(self):
        plan = qb.build_bootstrap_plan({
            "registry_canister_id": "reg-1",
            "codex": {"codex_id": "legacy-single"},
            "codices": [{"codex_id": "derived"}],
        })
        assert [i["id"] for i in plan["items"] if i["kind"] == "codex"] == ["derived"]


# ---------------------------------------------------------------------------
# apply_quarter_config — mirror capital runtime config + branding onto a quarter
# ---------------------------------------------------------------------------

class _FakeRealm:
    """Minimal stand-in for a ggg Realm: just holds attributes."""
    pass


class TestApplyQuarterConfig:
    def test_applies_identity_branding_and_flags(self):
        realm = _FakeRealm()
        applied = qb.apply_quarter_config(realm, {
            "name": "Agora",
            "manifesto": "A digital polis",
            "welcome_message": "Welcome!",
            "network": "staging",
            "accounting_currency": "ckUSDC",
            "accounting_currency_decimals": 6,
            "open_registration": True,
            "ai_assistant_enabled": False,
            "file_registry_canister_id": "iebdk-x",
            "test_flags": {
                "test_mode_user_self_registration": True,
                "test_mode_ii_bypass": True,
            },
        })
        assert realm.name == "Agora"
        assert realm.manifesto == "A digital polis"
        assert realm.network == "staging"
        assert realm.accounting_currency == "ckUSDC"
        assert realm.accounting_currency_decimals == 6
        assert realm.open_registration is True
        assert realm.ai_assistant_enabled is False
        assert realm.file_registry_canister_id == "iebdk-x"
        assert realm.test_mode_user_self_registration is True
        assert realm.test_mode_ii_bypass is True
        # Reported applied fields cover identity, bools, ints, and nested flags.
        for f in ("name", "open_registration", "accounting_currency_decimals",
                  "test_mode_user_self_registration"):
            assert f in applied

    def test_blank_string_does_not_clobber(self):
        # An empty name must not overwrite (Realm.name has a min length).
        realm = _FakeRealm()
        realm.name = "Existing"
        applied = qb.apply_quarter_config(realm, {"name": "", "manifesto": "M"})
        assert realm.name == "Existing"
        assert "name" not in applied
        assert realm.manifesto == "M"

    def test_demo_data_is_never_propagated(self):
        realm = _FakeRealm()
        applied = qb.apply_quarter_config(realm, {
            "test_flags": {"test_mode_demo_data": True, "test_mode": True},
        })
        assert getattr(realm, "test_mode_demo_data", None) is None
        assert "test_mode_demo_data" not in applied
        assert realm.test_mode is True

    def test_empty_config_is_noop(self):
        realm = _FakeRealm()
        assert qb.apply_quarter_config(realm, {}) == []
        assert qb.apply_quarter_config(realm, None) == []


# ---------------------------------------------------------------------------
# step_plan — cursor / retry state machine
# ---------------------------------------------------------------------------

def _plan(n=2):
    items = [{"kind": "extension", "id": f"ext{i}"} for i in range(n)]
    return {
        "items": items, "cursor": 0, "attempts": 0,
        "done": [], "failed": [], "status": "pending",
    }


class TestStepPlan:
    def test_success_advances_and_records(self):
        st = _plan(2)
        qb.step_plan(st, True)
        assert st["cursor"] == 1
        assert st["done"] == ["ext0"]
        assert st["attempts"] == 0
        assert st["status"] == "pending"

    def test_success_on_last_item_completes(self):
        st = _plan(1)
        qb.step_plan(st, True)
        assert st["cursor"] == 1
        assert st["status"] == "complete"
        assert st["done"] == ["ext0"]

    def test_failure_retries_without_advancing(self):
        st = _plan(2)
        qb.step_plan(st, False, error="boom")
        # First two failures only bump attempts (MAX_ATTEMPTS_PER_ITEM == 3).
        assert st["cursor"] == 0
        assert st["attempts"] == 1
        assert st["failed"] == []
        qb.step_plan(st, False, error="boom")
        assert st["cursor"] == 0
        assert st["attempts"] == 2

    def test_failure_gives_up_after_max_attempts(self):
        st = _plan(2)
        for _ in range(qb.MAX_ATTEMPTS_PER_ITEM):
            qb.step_plan(st, False, error="still broken")
        # After MAX attempts the item is recorded failed and the cursor advances.
        assert st["cursor"] == 1
        assert st["attempts"] == 0
        assert len(st["failed"]) == 1
        assert st["failed"][0]["id"] == "ext0"
        assert "still broken" in st["failed"][0]["error"]
        assert st["status"] == "pending"

    def test_retry_then_success_resets_attempts(self):
        st = _plan(2)
        qb.step_plan(st, False, error="transient")
        assert st["attempts"] == 1 and st["cursor"] == 0
        qb.step_plan(st, True)
        assert st["cursor"] == 1
        assert st["attempts"] == 0
        assert st["done"] == ["ext0"]
        assert st["failed"] == []

    def test_cursor_past_end_is_complete(self):
        st = _plan(1)
        st["cursor"] = 5
        qb.step_plan(st, True)
        assert st["status"] == "complete"


# ---------------------------------------------------------------------------
# Recurring-task shims — a typo here means the task silently never runs, so
# guard the constants + generated step code (issue #156).
# ---------------------------------------------------------------------------

class TestRecurringTaskShims:
    def test_autoscale_shim_is_async_and_targets_right_fn(self):
        assert qb.AUTOSCALE_TASK_NAME
        assert qb.AUTOSCALE_INTERVAL_S > 0
        code = qb.AUTOSCALE_STEP_CODE
        assert "def async_task()" in code
        assert "yield from" in code
        assert "run_autoscale_tick" in code

    def test_population_sync_shim_is_async_and_targets_right_fn(self):
        assert qb.POP_SYNC_TASK_NAME == "quarter_population_sync"
        assert qb.POP_SYNC_INTERVAL_S > 0
        code = qb.POP_SYNC_STEP_CODE
        assert "def async_task()" in code
        assert "yield from" in code
        assert "run_population_sync_tick" in code

    def test_recurring_task_names_are_distinct(self):
        names = {qb.BOOTSTRAP_TASK_NAME, qb.AUTOSCALE_TASK_NAME, qb.POP_SYNC_TASK_NAME}
        assert len(names) == 3

    def test_population_sync_step_code_compiles(self):
        # The framework exec()s this string; a SyntaxError would wedge the task.
        compile(qb.POP_SYNC_STEP_CODE, "<pop_sync_step>", "exec")
