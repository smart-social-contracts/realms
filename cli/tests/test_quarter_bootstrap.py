"""Tests for the quarter-local self-bootstrap plan + state machine (issue #156).

CI-friendly (no live replica): ``build_bootstrap_plan`` and ``step_plan`` are
pure (json + logging only), so we load ``core/quarter_bootstrap.py`` directly by
path — avoiding ``core/__init__.py`` and the canister-only lazy imports inside
``advance_bootstrap``/``seed_*`` (which only run in-canister).
"""

import importlib.util
import json
import os
import sys
import types

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

    def test_extensions_first_then_codex(self):
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
            ("extension", "public_dashboard"),
            ("extension", "realm_settings"),
            ("extension", "voting"),
            ("codex", "agora/gov"),
        ]
        assert plan["install_codex_dependencies"] is False
        assert plan["status"] == "pending"

    def test_blank_codex_id_skipped(self):
        plan = qb.build_bootstrap_plan({
            "registry_canister_id": "reg-1",
            "codex": {"codex_id": "  "},
            "extensions": ["voting"],
        })
        assert [i["kind"] for i in plan["items"]] == ["extension"]

    def test_codices_list_installs_extensions_before_codices(self):
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
            ("extension", "voting"),
            ("codex", "agora"),
            ("codex", "agora/gov"),
        ]
        # run_init carried through; default True when omitted.
        codex_items = [i for i in plan["items"] if i["kind"] == "codex"]
        assert codex_items[0]["run_init"] is True
        assert codex_items[1]["run_init"] is True
        assert plan["install_codex_dependencies"] is False

    def test_extension_priority_member_dashboard_first(self):
        plan = qb.build_bootstrap_plan({
            "registry_canister_id": "reg-1",
            "extensions": [
                "voting",
                "hello_world",
                "member_dashboard",
                "realm_settings",
            ],
        })
        kinds = [(i["kind"], i["id"]) for i in plan["items"]]
        assert kinds == [
            ("extension", "member_dashboard"),
            ("extension", "realm_settings"),
            ("extension", "voting"),
            ("extension", "hello_world"),
        ]

    def test_codices_list_takes_precedence_over_single_codex(self):
        plan = qb.build_bootstrap_plan({
            "registry_canister_id": "reg-1",
            "codex": {"codex_id": "legacy-single"},
            "codices": [{"codex_id": "derived"}],
        })
        assert [i["id"] for i in plan["items"] if i["kind"] == "codex"] == ["derived"]

    def test_codex_only_plan_installs_dependencies_inline(self):
        plan = qb.build_bootstrap_plan({
            "registry_canister_id": "reg-1",
            "codex": {"codex_id": "agora/gov", "run_init": True},
        })
        assert plan["items"] == [
            {"kind": "codex", "id": "agora/gov", "version": None, "run_init": True},
        ]
        assert plan["install_codex_dependencies"] is True

    def test_plan_with_extensions_sets_install_codex_dependencies_false(self):
        plan = qb.build_bootstrap_plan({
            "registry_canister_id": "reg-1",
            "codex": {"codex_id": "agora"},
            "extensions": ["voting"],
        })
        assert plan["install_codex_dependencies"] is False


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

    def test_copies_require_marketplace_approval(self):
        realm = _FakeRealm()
        realm.require_marketplace_approval = True
        applied = qb.apply_quarter_config(realm, {"require_marketplace_approval": False})
        assert realm.require_marketplace_approval is False
        assert "require_marketplace_approval" in applied

        realm.require_marketplace_approval = False
        qb.apply_quarter_config(realm, {"require_marketplace_approval": True})
        assert realm.require_marketplace_approval is True

    def test_missing_governance_keys_leave_fields_untouched(self):
        realm = _FakeRealm()
        realm.require_marketplace_approval = False
        realm.trusted_approvers = "abc-principal"
        realm.status = "alpha"
        applied = qb.apply_quarter_config(realm, {"name": "Agora"})
        assert realm.require_marketplace_approval is False
        assert realm.trusted_approvers == "abc-principal"
        assert realm.status == "alpha"
        assert "require_marketplace_approval" not in applied
        assert "trusted_approvers" not in applied
        assert "status" not in applied

    def test_copies_trusted_approvers_including_empty_string(self):
        realm = _FakeRealm()
        realm.trusted_approvers = "keep-me"
        applied = qb.apply_quarter_config(realm, {"trusted_approvers": ""})
        assert realm.trusted_approvers == ""
        assert "trusted_approvers" in applied

        qb.apply_quarter_config(realm, {"trusted_approvers": "a,b,c"})
        assert realm.trusted_approvers == "a,b,c"

    def test_copies_status_and_rejects_invalid(self):
        realm = _FakeRealm()
        realm.status = "setup"
        applied = qb.apply_quarter_config(realm, {"status": "alpha"})
        assert realm.status == "alpha"
        assert "status" in applied

        realm.status = "setup"
        qb.apply_quarter_config(realm, {"status": "not-a-real-status"})
        assert realm.status == "setup"

        realm.status = "alpha"
        qb.apply_quarter_config(realm, {"status": ""})
        assert realm.status == "alpha"


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
# Bounded bootstrap_state persistence (issue: overflow kills installer)
# ---------------------------------------------------------------------------

_REALISTIC_EXT_IDS = (
    "member_dashboard",
    "public_dashboard",
    "realm_settings",
    "voting",
    "admin_dashboard",
    "access_manager",
    "role_manager",
    "codex_viewer",
    "task_monitor",
    "import_export",
    "vault",
    "mundus_explorer",
    "hello_world",
    "member_profile",
    "notifications",
    "search",
    "calendar",
    "treasury_view",
    "governance_proposals",
    "land_registry",
    "marketplace",
    "analytics",
    "audit_log",
    "api_gateway",
)


def _state_that_forces_spilling():
    """A plan whose failure list is too big to fit even as bare ids, so
    ``_bounded_state`` has to reach its overflow-spilling stage."""
    ids = [f"extension-with-a-very-long-descriptive-name-{i}" for i in range(200)]
    return {
        "parent": "cap-1",
        "registry": "reg-1",
        "frontend": "",
        "items": [{"kind": "extension", "id": i, "version": None} for i in ids[:5]],
        "cursor": 5,
        "attempts": 0,
        "done": [],
        "failed": [{"id": i, "error": "e" * 400} for i in ids],
        "status": "complete",
    }


class TestBoundedBootstrapState:
    def test_step_plan_many_long_failures_stays_under_limit(self):
        spec = {
            "registry_canister_id": "reg-1",
            "extensions": list(_REALISTIC_EXT_IDS),
        }
        st = qb.build_bootstrap_plan(spec)
        long_err = "x" * 350
        for _ in st["items"]:
            for _ in range(qb.MAX_ATTEMPTS_PER_ITEM):
                st = qb.step_plan(st, False, error=long_err)
        assert len(st["failed"]) >= len(_REALISTIC_EXT_IDS)
        assert st["status"] == "complete"
        assert len(json.dumps(st)) <= qb.BOOTSTRAP_STATE_MAX_LENGTH

    def test_save_state_bounds_oversized_state(self):
        class _Realm:
            bootstrap_state = ""

        realm = _Realm()
        huge_failed = [
            {"id": f"ext{i}", "error": "e" * 500}
            for i in range(40)
        ]
        state = {
            "parent": "cap-1",
            "registry": "reg-1",
            "frontend": "",
            "items": [{"kind": "extension", "id": f"ext{i}"} for i in range(24)],
            "cursor": 24,
            "attempts": 0,
            "done": list(_REALISTIC_EXT_IDS),
            "failed": huge_failed,
            "status": "complete",
        }
        qb.save_state(realm, state)
        assert len(realm.bootstrap_state) <= qb.BOOTSTRAP_STATE_MAX_LENGTH
        persisted = json.loads(realm.bootstrap_state)
        assert persisted["status"] == "complete"
        assert persisted["cursor"] == 24

    def test_rebounding_keeps_the_overflow_count(self):
        """A tick bounds twice (step_plan then save_state); the second pass must
        not erase the failures the first pass already spilled."""
        state = _state_that_forces_spilling()
        once = qb._bounded_state(state)
        assert once.get("failed_overflow"), "expected the first pass to spill"
        twice = qb._bounded_state(once)
        assert twice.get("failed_overflow") == once["failed_overflow"]
        assert len(twice.get("failed") or []) == len(once.get("failed") or [])
        assert qb._state_json_len(twice) <= qb.BOOTSTRAP_STATE_MAX_LENGTH

    def test_overflow_count_survives_shedding_ids(self):
        """Trimming the id list to fit must not shrink the number of failures."""
        state = _state_that_forces_spilling()
        total = len(state["failed"])
        bounded = qb._bounded_state(state)
        assert qb._state_json_len(bounded) <= qb.BOOTSTRAP_STATE_MAX_LENGTH
        accounted = bounded.get("failed_overflow", 0) + len(bounded.get("failed") or [])
        assert accounted == total
        assert len(bounded.get("failed_overflow_ids") or []) <= bounded["failed_overflow"]


# ---------------------------------------------------------------------------
# Recurring-task shims — a typo here means the task silently never runs, so
# guard the constants + generated step code (issue #156).
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# derive_capital_install_set — live install-set mirroring (issue #156, #244)
# ---------------------------------------------------------------------------

def _install_core_stubs(
    *,
    ext_ids,
    ext_sources=None,
    ext_manifests=None,
    codex_ids=None,
    codex_manifests=None,
    active_codex=None,
):
    """Inject minimal ``core.*`` stubs for derive_capital_install_set."""
    ext_sources = ext_sources or {}
    ext_manifests = ext_manifests or {}
    codex_ids = codex_ids if codex_ids is not None else []
    codex_manifests = codex_manifests or {}

    runtime_ext = types.ModuleType("core.runtime_extensions")
    runtime_ext.list_installed = lambda: list(ext_ids)
    runtime_ext.get_extension_source = lambda ext_id: ext_sources.get(ext_id)
    runtime_ext.get_all_extension_manifests = lambda: dict(ext_manifests)

    runtime_codex = types.ModuleType("core.runtime_codex")
    runtime_codex.list_installed = lambda: list(codex_ids)
    runtime_codex.get_all_codex_manifests = lambda: dict(codex_manifests)

    codex_hooks = types.ModuleType("core.codex_hooks")
    codex_hooks.get_active_codex = lambda: active_codex

    core_pkg = sys.modules.get("core")
    if core_pkg is None:
        core_pkg = types.ModuleType("core")
        sys.modules["core"] = core_pkg

    saved = {
        "core": sys.modules.get("core"),
        "core.runtime_extensions": sys.modules.get("core.runtime_extensions"),
        "core.runtime_codex": sys.modules.get("core.runtime_codex"),
        "core.codex_hooks": sys.modules.get("core.codex_hooks"),
    }
    sys.modules["core.runtime_extensions"] = runtime_ext
    sys.modules["core.runtime_codex"] = runtime_codex
    sys.modules["core.codex_hooks"] = codex_hooks
    core_pkg.runtime_extensions = runtime_ext
    core_pkg.runtime_codex = runtime_codex
    core_pkg.codex_hooks = codex_hooks
    return saved


def _restore_core_stubs(saved):
    for name, mod in saved.items():
        if mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = mod


class TestDeriveCapitalInstallSet:
    def test_unified_codex_extension_emitted_as_codex_not_extension(self):
        ext_ids = ["agora", "voting", "realm_settings"]
        saved = _install_core_stubs(
            ext_ids=ext_ids,
            ext_sources={
                "agora": {"version": "0.9.5", "registry_canister_id": "reg-live"},
                "voting": {"version": "1.0.0", "registry_canister_id": "reg-live"},
                "realm_settings": {"version": "2.0.0", "registry_canister_id": "reg-live"},
            },
            ext_manifests={"agora": {"kind": "codex", "version": "0.9.5"}},
            codex_ids=[],
            active_codex="agora",
        )
        try:
            derived = qb.derive_capital_install_set("reg-default")
        finally:
            _restore_core_stubs(saved)

        assert derived["registry_canister_id"] == "reg-live"
        assert derived["codices"] == [
            {"codex_id": "agora", "version": "0.9.5", "run_init": True},
        ]
        ext_ids_out = [e["ext_id"] for e in derived["extensions"]]
        assert "agora" not in ext_ids_out
        assert ext_ids_out == ["voting", "realm_settings"]

    def test_unified_codex_plans_extensions_before_codex(self):
        ext_ids = ["agora", "voting", "member_dashboard"]
        saved = _install_core_stubs(
            ext_ids=ext_ids,
            ext_sources={
                "agora": {"version": "0.9.5", "registry_canister_id": "reg-1"},
                "voting": {"version": None, "registry_canister_id": "reg-1"},
                "member_dashboard": {"version": None, "registry_canister_id": "reg-1"},
            },
            ext_manifests={"agora": {"kind": "codex", "version": "0.9.5"}},
            codex_ids=[],
            active_codex="agora",
        )
        try:
            derived = qb.derive_capital_install_set("reg-1")
            plan = qb.build_bootstrap_plan({
                "registry_canister_id": derived["registry_canister_id"],
                "codices": derived["codices"],
                "extensions": derived["extensions"],
            })
        finally:
            _restore_core_stubs(saved)

        assert plan["items"][0] == {
            "kind": "extension",
            "id": "member_dashboard",
            "version": None,
        }
        assert plan["items"][-1] == {
            "kind": "codex",
            "id": "agora",
            "version": "0.9.5",
            "run_init": True,
        }
        assert plan["install_codex_dependencies"] is False

    def test_no_codex_derives_empty_codices_list(self):
        saved = _install_core_stubs(
            ext_ids=["voting"],
            ext_sources={"voting": {"version": "1.0.0", "registry_canister_id": "reg-1"}},
            active_codex=None,
        )
        try:
            derived = qb.derive_capital_install_set("")
        finally:
            _restore_core_stubs(saved)

        assert derived["codices"] == []
        assert derived["extensions"] == [{"ext_id": "voting", "version": "1.0.0"}]

    def test_legacy_codex_not_double_emitted(self):
        saved = _install_core_stubs(
            ext_ids=["voting"],
            ext_sources={"voting": {"version": "1.0.0", "registry_canister_id": "reg-1"}},
            codex_ids=["agora/gov"],
            codex_manifests={"agora/gov": {"version": "0.1.0"}},
            active_codex=None,
        )
        try:
            derived = qb.derive_capital_install_set("")
        finally:
            _restore_core_stubs(saved)

        assert derived["codices"] == [
            {"codex_id": "agora/gov", "version": "0.1.0", "run_init": True},
        ]
        assert derived["extensions"] == [{"ext_id": "voting", "version": "1.0.0"}]


class TestReorderPendingBootstrapItems:
    def test_reorders_codex_first_plan_from_cursor(self):
        state = {
            "items": [
                {"kind": "codex", "id": "agora", "version": "0.9.5", "run_init": True},
                {"kind": "extension", "id": "voting", "version": None},
                {"kind": "extension", "id": "member_dashboard", "version": None},
            ],
            "cursor": 0,
        }
        changed = qb.reorder_pending_bootstrap_items(state)
        assert changed is True
        assert [(i["kind"], i["id"]) for i in state["items"]] == [
            ("extension", "member_dashboard"),
            ("extension", "voting"),
            ("codex", "agora"),
        ]
        assert state["install_codex_dependencies"] is False

    def test_only_reorders_tail_after_cursor(self):
        state = {
            "items": [
                {"kind": "codex", "id": "agora", "version": None, "run_init": True},
                {"kind": "extension", "id": "voting", "version": None},
                {"kind": "extension", "id": "member_dashboard", "version": None},
            ],
            "cursor": 1,
            "done": ["agora"],
        }
        changed = qb.reorder_pending_bootstrap_items(state)
        assert changed is True
        assert [(i["kind"], i["id"]) for i in state["items"]] == [
            ("codex", "agora"),
            ("extension", "member_dashboard"),
            ("extension", "voting"),
        ]
        assert state["install_codex_dependencies"] is False

    def test_no_change_when_already_ordered(self):
        state = {
            "items": [
                {"kind": "extension", "id": "member_dashboard", "version": None},
                {"kind": "extension", "id": "voting", "version": None},
                {"kind": "codex", "id": "agora", "version": None, "run_init": True},
            ],
            "cursor": 0,
            "install_codex_dependencies": False,
        }
        changed = qb.reorder_pending_bootstrap_items(state)
        assert changed is False


class TestRecurringTaskShims:
    def test_autoscale_shim_is_async_and_targets_right_fn(self):
        assert qb.AUTOSCALE_TASK_NAME
        assert qb.AUTOSCALE_INTERVAL_S > 0
        code = qb.AUTOSCALE_STEP_CODE
        assert "def async_task()" in code
        assert "yield from" in code
        assert "run_autoscale_tick" in code

    def test_recurring_task_names_are_distinct(self):
        names = {qb.BOOTSTRAP_TASK_NAME, qb.AUTOSCALE_TASK_NAME}
        assert len(names) == 2
