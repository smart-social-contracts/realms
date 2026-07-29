"""Unit tests for the codex hook API dispatch layer (issue #244).

Covers core/codex_hooks.py:
  - codex_api_version gating
  - one-codex-per-realm singleton rule
  - active codex discovery from extension manifests (kind: codex)
  - get_config merge semantics (codex config over Realm.manifest_data)
  - extension override resolution (hook + manifest + legacy shim)
  - on_user_register dispatch behavior
  - invoice-accounting event dispatch
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))

# Mock IC-specific modules before importing anything that uses them
sys.modules.setdefault("_cdk", MagicMock())

import core.codex_hooks as codex_hooks  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_caches(monkeypatch):
    """Each test starts with cold discovery caches and clean module mocks."""
    codex_hooks.invalidate_cache()
    yield
    codex_hooks.invalidate_cache()
    sys.modules.pop("core.runtime_extensions", None)
    sys.modules.pop("core.runtime_codex", None)
    sys.modules.pop("ggg", None)


def _mock_runtime_extensions(manifests=None, modules=None):
    """Install a mock core.runtime_extensions with given manifests/modules."""
    mock = MagicMock()
    mock.get_all_extension_manifests.return_value = manifests or {}
    mock._load_module.side_effect = lambda ext_id: (modules or {}).get(ext_id)
    sys.modules["core.runtime_extensions"] = mock
    return mock


def _mock_runtime_codex(installed=None, manifests=None, overrides=None):
    mock = MagicMock()
    mock.list_installed.return_value = installed or []
    mock.get_all_codex_manifests.return_value = manifests or {}
    mock.get_extension_overrides.return_value = overrides or {}
    sys.modules["core.runtime_codex"] = mock
    return mock


def _mock_ggg(manifest_data="{}"):
    mock = MagicMock()
    realm = MagicMock()
    realm.manifest_data = manifest_data
    mock.Realm.instances.return_value = [realm]
    sys.modules["ggg"] = mock
    return mock


# ---------------------------------------------------------------------------
# codex_api_version gating
# ---------------------------------------------------------------------------


class TestApiVersionGate:
    def test_missing_version_is_legacy_and_accepted(self):
        assert codex_hooks.unsupported_api_version({}) is None

    def test_supported_version_accepted(self):
        assert codex_hooks.unsupported_api_version({"codex_api_version": 1}) is None

    def test_future_version_rejected(self):
        err = codex_hooks.unsupported_api_version({"codex_api_version": 99})
        assert err is not None
        assert "99" in err

    def test_garbage_version_rejected(self):
        err = codex_hooks.unsupported_api_version({"codex_api_version": "banana"})
        assert err is not None


# ---------------------------------------------------------------------------
# Singleton + discovery
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_no_codex_installed_allows_install(self):
        _mock_runtime_extensions(manifests={"voting": {"name": "voting"}})
        _mock_runtime_codex(installed=[])
        assert codex_hooks.singleton_violation("agora") is None

    def test_second_codex_blocked(self):
        _mock_runtime_extensions(
            manifests={"agora": {"kind": "codex", "id": "agora"}}
        )
        _mock_runtime_codex(installed=[])
        err = codex_hooks.singleton_violation("syntropia")
        assert err is not None
        assert "agora" in err

    def test_same_id_upgrade_allowed(self):
        _mock_runtime_extensions(
            manifests={"agora": {"kind": "codex", "id": "agora"}}
        )
        _mock_runtime_codex(installed=[])
        assert codex_hooks.singleton_violation("agora") is None

    def test_legacy_package_counts_toward_singleton(self):
        _mock_runtime_extensions(manifests={})
        _mock_runtime_codex(installed=["dominion"])
        err = codex_hooks.singleton_violation("agora")
        assert err is not None
        assert "dominion" in err

    def test_active_codex_found_by_kind(self):
        _mock_runtime_extensions(
            manifests={
                "voting": {"name": "voting"},
                "agora": {"kind": "codex", "id": "agora"},
            }
        )
        assert codex_hooks.get_active_codex() == "agora"

    def test_no_active_codex(self):
        _mock_runtime_extensions(manifests={"voting": {"name": "voting"}})
        assert codex_hooks.get_active_codex() is None


# ---------------------------------------------------------------------------
# get_config
# ---------------------------------------------------------------------------


class TestGetConfig:
    def test_manifest_config_blocks_extracted(self):
        blocks = codex_hooks._manifest_config_blocks({
            "id": "agora",
            "kind": "codex",
            "codex_api_version": 1,
            "dependencies": ["voting"],
            "fees": {"registration": 1.0},
            "governance": {"quorum_percent": 20},
        })
        assert blocks == {
            "fees": {"registration": 1.0},
            "governance": {"quorum_percent": 20},
        }

    def test_codex_manifest_config_over_manifest_data(self):
        _mock_ggg(manifest_data=json.dumps({
            "lifecycle": {"population_target": 5, "total_deposits": 42},
            "departments": ["Health"],
        }))
        module = MagicMock(spec=[])  # no get_config hook
        _mock_runtime_extensions(
            manifests={
                "agora": {
                    "kind": "codex",
                    "id": "agora",
                    "lifecycle": {"population_target": 100000},
                },
            },
            modules={"agora": module},
        )
        config = codex_hooks.get_config()
        # codex value wins, runtime-seeded key survives, unrelated key kept
        assert config["lifecycle"]["population_target"] == 100000
        assert config["lifecycle"]["total_deposits"] == 42
        assert config["departments"] == ["Health"]

    def test_get_config_hook_is_authoritative(self):
        _mock_ggg(manifest_data="{}")
        module = MagicMock()
        module.get_config = lambda args: json.dumps({"fees": {"registration": 9.0}})
        _mock_runtime_extensions(
            manifests={"agora": {"kind": "codex", "id": "agora"}},
            modules={"agora": module},
        )
        assert codex_hooks.get_config()["fees"]["registration"] == 9.0

    def test_reentrant_get_config_does_not_redispatch_the_hook(self):
        """A sandboxed ``get_config`` hook reading ``config`` back through the
        bridge must not re-enter the hook that is producing it."""
        _mock_ggg(manifest_data=json.dumps({"fees": {"registration": 2.0}}))
        calls = []
        module = MagicMock()

        def _hook(args):
            calls.append(args)
            # Simulates the hook reading config.get over rpc mid-execution.
            nested = codex_hooks.get_config()
            return json.dumps({"nested_fee": nested["fees"]["registration"]})

        module.get_config = _hook
        _mock_runtime_extensions(
            manifests={"agora": {"kind": "codex", "id": "agora"}},
            modules={"agora": module},
        )

        config = codex_hooks.get_config()

        assert len(calls) == 1  # dispatched once, not recursively
        assert config["nested_fee"] == 2.0  # inner read saw the manifest data

    def test_no_codex_falls_back_to_manifest_data(self):
        _mock_ggg(manifest_data=json.dumps({"fees": {"registration": 2.0}}))
        _mock_runtime_extensions(manifests={})
        _mock_runtime_codex(manifests={})
        assert codex_hooks.get_config()["fees"]["registration"] == 2.0

    def test_legacy_codex_manifest_served(self):
        _mock_ggg(manifest_data="{}")
        _mock_runtime_extensions(manifests={})
        _mock_runtime_codex(manifests={
            "dominion": {"id": "dominion", "fees": {"registration": 1.0}},
        })
        assert codex_hooks.get_config()["fees"]["registration"] == 1.0

    def test_config_overrides_beat_codex_config(self):
        """Wizard parameter choices (manifest_data.config_overrides, issue
        #253) are applied last — they beat the codex-declared values, which
        otherwise win over manifest_data."""
        _mock_ggg(manifest_data=json.dumps({
            "lifecycle": {"critical_mass": 9999, "total_deposits": 42},
            "config_overrides": {"lifecycle": {"critical_mass": 25}},
        }))
        module = MagicMock(spec=[])  # no get_config hook
        _mock_runtime_extensions(
            manifests={
                "syntropia": {
                    "kind": "codex",
                    "id": "syntropia",
                    "lifecycle": {"critical_mass": 10000, "beta_proving_days": 30},
                },
            },
            modules={"syntropia": module},
        )
        config = codex_hooks.get_config()
        assert config["lifecycle"]["critical_mass"] == 25  # override wins
        assert config["lifecycle"]["beta_proving_days"] == 30  # codex kept
        assert config["lifecycle"]["total_deposits"] == 42  # runtime kept
        assert "config_overrides" not in config  # internal key stripped

    def test_config_overrides_deep_merge_preserves_siblings(self):
        _mock_ggg(manifest_data=json.dumps({
            "config_overrides": {"governance": {"voting_window_days": 0.0007}},
        }))
        module = MagicMock(spec=[])
        _mock_runtime_extensions(
            manifests={
                "syntropia": {
                    "kind": "codex",
                    "id": "syntropia",
                    "governance": {
                        "voting_window_days": 7,
                        "quorum_percent": 20,
                        "approval_threshold": 0.5,
                    },
                },
            },
            modules={"syntropia": module},
        )
        governance = codex_hooks.get_config()["governance"]
        assert governance["voting_window_days"] == 0.0007
        assert governance["quorum_percent"] == 20
        assert governance["approval_threshold"] == 0.5

    def test_config_overrides_beat_get_config_hook(self):
        """Overrides are applied by the core even when the codex serves its
        config through the get_config hook."""
        _mock_ggg(manifest_data=json.dumps({
            "config_overrides": {"fees": {"registration": 0.0}},
        }))
        module = MagicMock()
        module.get_config = lambda args: json.dumps({
            "fees": {"registration": 9.0, "deposit": 0.01},
        })
        _mock_runtime_extensions(
            manifests={"syntropia": {"kind": "codex", "id": "syntropia"}},
            modules={"syntropia": module},
        )
        fees = codex_hooks.get_config()["fees"]
        assert fees["registration"] == 0.0
        assert fees["deposit"] == 0.01

    def test_parameters_block_is_not_config(self):
        """The wizard-facing ``parameters`` declaration is packaging
        metadata, not realm configuration."""
        blocks = codex_hooks._manifest_config_blocks({
            "id": "syntropia",
            "kind": "codex",
            "parameters": [{"path": "lifecycle.critical_mass", "default": 10000}],
            "lifecycle": {"critical_mass": 10000},
        })
        assert "parameters" not in blocks
        assert "lifecycle" in blocks


# ---------------------------------------------------------------------------
# extension overrides
# ---------------------------------------------------------------------------


class TestExtensionOverrides:
    def test_manifest_overrides_served(self):
        module = MagicMock(spec=[])  # no get_extension_overrides hook
        _mock_runtime_extensions(
            manifests={
                "agora": {
                    "kind": "codex",
                    "extension_overrides": {"member_dashboard": "agora_dashboard"},
                },
            },
            modules={"agora": module},
        )
        _mock_runtime_codex(overrides={})
        overrides = codex_hooks.get_extension_overrides()
        assert overrides == {"member_dashboard": "agora_dashboard"}

    def test_hook_overrides_win_over_legacy(self):
        module = MagicMock()
        module.get_extension_overrides = lambda args: json.dumps(
            {"member_dashboard": "hooked_dashboard"}
        )
        _mock_runtime_extensions(
            manifests={"agora": {"kind": "codex"}},
            modules={"agora": module},
        )
        _mock_runtime_codex(overrides={
            "member_dashboard": "legacy_dashboard",
            "voting": "legacy_voting",
        })
        overrides = codex_hooks.get_extension_overrides()
        assert overrides["member_dashboard"] == "hooked_dashboard"
        assert overrides["voting"] == "legacy_voting"

    def test_cache_invalidation(self):
        module = MagicMock(spec=[])
        mock_rt = _mock_runtime_extensions(
            manifests={"agora": {"kind": "codex", "extension_overrides": {"a": "b"}}},
            modules={"agora": module},
        )
        _mock_runtime_codex(overrides={})
        assert codex_hooks.get_extension_overrides() == {"a": "b"}
        # Simulate codex replacement, stale cache would still say {"a": "b"}
        mock_rt.get_all_extension_manifests.return_value = {
            "agora": {"kind": "codex", "extension_overrides": {"a": "c"}}
        }
        assert codex_hooks.get_extension_overrides() == {"a": "b"}  # cached
        codex_hooks.invalidate_cache()
        assert codex_hooks.get_extension_overrides() == {"a": "c"}


# ---------------------------------------------------------------------------
# on_user_register dispatch
# ---------------------------------------------------------------------------


class TestOnUserRegister:
    def test_no_codex_returns_false(self):
        _mock_runtime_extensions(manifests={})
        assert codex_hooks.dispatch_on_user_register("u1") is False

    def test_codex_without_hook_returns_false(self):
        module = MagicMock(spec=[])
        _mock_runtime_extensions(
            manifests={"agora": {"kind": "codex"}},
            modules={"agora": module},
        )
        assert codex_hooks.dispatch_on_user_register("u1") is False

    def test_hook_called_with_user_id(self):
        calls = []
        module = MagicMock()
        module.on_user_register = lambda args: calls.append(json.loads(args))
        _mock_runtime_extensions(
            manifests={"agora": {"kind": "codex"}},
            modules={"agora": module},
        )
        assert codex_hooks.dispatch_on_user_register("u1") is True
        assert calls == [{"user_id": "u1"}]

    def test_hook_error_still_counts_as_handled(self):
        def _boom(args):
            raise RuntimeError("hook exploded")

        module = MagicMock()
        module.on_user_register = _boom
        _mock_runtime_extensions(
            manifests={"agora": {"kind": "codex"}},
            modules={"agora": module},
        )
        # Handled (no legacy double-fire), even though the hook failed.
        assert codex_hooks.dispatch_on_user_register("u1") is True


# ---------------------------------------------------------------------------
# invoice accounting hook
# ---------------------------------------------------------------------------


class TestInvoiceAccounting:
    def test_no_codex_hook_returns_false(self):
        _mock_runtime_extensions(manifests={})
        assert codex_hooks.dispatch_invoice_accounting("inv-1", "paid") is False

    def test_hook_receives_invoice_event(self):
        calls = []
        module = MagicMock()
        module.on_invoice_accounting = lambda args: calls.append(json.loads(args))
        _mock_runtime_extensions(
            manifests={"syntropia": {"kind": "codex"}},
            modules={"syntropia": module},
        )

        assert codex_hooks.dispatch_invoice_accounting("inv-1", "paid") is True
        assert calls == [{"invoice_id": "inv-1", "event": "paid"}]

    def test_hook_error_still_counts_as_handled(self):
        module = MagicMock()
        module.on_invoice_accounting = lambda args: (_ for _ in ()).throw(
            RuntimeError("hook exploded")
        )
        _mock_runtime_extensions(
            manifests={"syntropia": {"kind": "codex"}},
            modules={"syntropia": module},
        )
        assert codex_hooks.dispatch_invoice_accounting("inv-1", "paid") is True


# ---------------------------------------------------------------------------
# lifecycle transition hook
# ---------------------------------------------------------------------------


class TestLifecycleTransition:
    def test_no_codex_returns_none(self):
        _mock_runtime_extensions(manifests={})
        assert codex_hooks.check_lifecycle_transition("alpha", "beta") is None

    def test_verdict_normalized(self):
        module = MagicMock()
        module.check_lifecycle_transition = lambda args: json.dumps({
            "allowed": False,
            "missing": ["Citizens imported"],
        })
        _mock_runtime_extensions(
            manifests={"agora": {"kind": "codex"}},
            modules={"agora": module},
        )
        verdict = codex_hooks.check_lifecycle_transition("alpha", "beta")
        assert verdict == {"allowed": False, "missing": ["Citizens imported"]}


# ---------------------------------------------------------------------------
# codex dependency resolution (install path)
# ---------------------------------------------------------------------------


class TestDependencyResolution:
    @staticmethod
    def _resolve(manifest):
        # api.file_registry's import chain touches canister-only modules
        # (basilisk services, real ggg entities); mock them out.
        for mod in (
            "basilisk", "basilisk.services", "ggg", "ggg.system",
            "ggg.system.user_profile", "ic_python_db", "ic_basilisk_toolkit",
            "ic_basilisk_toolkit.crypto",
        ):
            if mod not in sys.modules:
                sys.modules[mod] = MagicMock()
        from api.file_registry import _resolve_codex_dependencies

        return _resolve_codex_dependencies(manifest, "test_codex")

    def test_list_dependencies(self):
        deps = self._resolve({"dependencies": ["voting", "vault"]})
        assert deps["voting"] == "" and deps["vault"] == ""

    def test_pinned_dependencies(self):
        deps = self._resolve({"dependencies": {"voting": "1.1.x"}})
        assert deps["voting"] == "1.1.x"

    def test_extension_overrides_are_implicit_dependencies(self):
        deps = self._resolve({
            "dependencies": [],
            "extension_overrides": {"member_dashboard": "agora_dashboard"},
        })
        assert "agora_dashboard" in deps

    def test_core_extensions_always_included(self):
        from core.core_extensions import CORE_EXTENSION_IDS

        deps = self._resolve({"dependencies": []})
        for core_ext in CORE_EXTENSION_IDS:
            assert core_ext in deps


class TestSandboxFallbackPolicy:
    """Which sandbox failures may be retried in-process (issue #265).

    A refusal must never earn the codex an in-process retry: the codex already
    ran and was denied, so re-running it with full host access would turn every
    capability check into a trivial bypass. Only infrastructure failures are
    eligible for the fallback.
    """

    def _sandbox_raising(self, monkeypatch, error, fallback=True):
        from core import runtime_sandbox

        def _call(*args, **kwargs):
            raise error

        monkeypatch.setattr(
            runtime_sandbox, "call_codex_hook_in_sandbox", _call
        )
        monkeypatch.setattr(
            runtime_sandbox, "get_config", lambda: {"fallback_in_process": fallback}
        )

    def test_denied_capability_is_not_retried_in_process(self, monkeypatch):
        self._sandbox_raising(
            monkeypatch, PermissionError("effect 'treasury.drain' denied")
        )
        handled, result = codex_hooks._call_hook_sandboxed("agora", "h", {})
        assert handled is True  # not retried, despite fallback being enabled
        assert result is None

    def test_leaked_object_is_not_retried_in_process(self, monkeypatch):
        from core.codex_bridge import BridgeSerializationError

        self._sandbox_raising(monkeypatch, BridgeSerializationError("live object"))
        handled, _ = codex_hooks._call_hook_sandboxed("agora", "h", {})
        assert handled is True

    def test_hook_logic_failure_is_not_retried_in_process(self, monkeypatch):
        from core.runtime_sandbox import CodexHookError

        self._sandbox_raising(monkeypatch, CodexHookError("hook raised"))
        handled, _ = codex_hooks._call_hook_sandboxed("agora", "h", {})
        assert handled is True

    def test_infrastructure_failure_falls_back_when_allowed(self, monkeypatch):
        self._sandbox_raising(monkeypatch, RuntimeError("spawn failed"), fallback=True)
        handled, _ = codex_hooks._call_hook_sandboxed("agora", "h", {})
        assert handled is False  # caller retries in-process

    def test_infrastructure_failure_fails_closed_when_disallowed(self, monkeypatch):
        self._sandbox_raising(monkeypatch, RuntimeError("spawn failed"), fallback=False)
        handled, _ = codex_hooks._call_hook_sandboxed("agora", "h", {})
        assert handled is True

    def test_successful_hook_result_is_returned(self, monkeypatch):
        from core import runtime_sandbox

        monkeypatch.setattr(
            runtime_sandbox,
            "call_codex_hook_in_sandbox",
            lambda *a, **kw: {"fees": {"registration": 5.0}},
        )
        handled, result = codex_hooks._call_hook_sandboxed("agora", "get_config", {})
        assert handled is True
        assert result == {"fees": {"registration": 5.0}}


AGORA_SOURCE = """
def role_assign_prehook(args):
    pass

def get_governance_params(args):
    pass
"""


class TestRoleHookDispatch:
    """Role-management hooks from a ``Codex.code`` column (issue #265).

    These used to be ``exec()``d in-process with full ``__builtins__``, which
    made the gate deciding who may hold ``admin`` the least protected code in
    the realm. They now go through the sandbox, and a gate that cannot be
    evaluated denies rather than allows.
    """

    def _installed(self, monkeypatch, source=AGORA_SOURCE, name="role_management_hook"):
        monkeypatch.setattr(
            codex_hooks, "_entity_codex", lambda names: (name, source)
        )

    def _sandbox(self, monkeypatch, result=None, error=None):
        from core import runtime_sandbox

        calls = []

        def _run(context_id, source, hook_name, params, capabilities, context=None):
            calls.append({
                "context_id": context_id,
                "hook": hook_name,
                "params": params,
                "capabilities": capabilities,
            })
            if error is not None:
                raise error
            return result

        monkeypatch.setattr(runtime_sandbox, "run_bridge_hook", _run)
        return calls

    def test_no_codex_installed_allows(self, monkeypatch):
        monkeypatch.setattr(codex_hooks, "_entity_codex", lambda names: (None, None))
        calls = self._sandbox(monkeypatch)
        assert codex_hooks.enforce_role_gate("role_assign_prehook", "u1", "admin", "p")
        assert calls == []

    def test_unimplemented_hook_allows_without_spawning(self, monkeypatch):
        self._installed(monkeypatch)
        calls = self._sandbox(monkeypatch)
        assert codex_hooks.enforce_role_gate("role_revoke_prehook", "u1", "admin", "p")
        assert calls == []

    def test_allowed_verdict_passes(self, monkeypatch):
        self._installed(monkeypatch)
        self._sandbox(monkeypatch, result={"allowed": True})
        assert codex_hooks.enforce_role_gate("role_assign_prehook", "u1", "admin", "p")

    def test_denied_verdict_raises_with_the_codex_reason(self, monkeypatch):
        self._installed(monkeypatch)
        self._sandbox(
            monkeypatch, result={"allowed": False, "reason": "needs a vote"}
        )
        with pytest.raises(PermissionError, match="needs a vote"):
            codex_hooks.enforce_role_gate("role_assign_prehook", "u1", "admin", "p")

    def test_denied_verdict_without_a_reason_still_denies(self, monkeypatch):
        self._installed(monkeypatch)
        self._sandbox(monkeypatch, result={"allowed": False})
        with pytest.raises(PermissionError, match="admin"):
            codex_hooks.enforce_role_gate("role_assign_prehook", "u1", "admin", "p")

    def test_unevaluable_gate_denies(self, monkeypatch):
        """The whole point: a broken governance gate must not wave roles through."""
        self._installed(monkeypatch)
        self._sandbox(monkeypatch, error=RuntimeError("spawn failed"))
        with pytest.raises(PermissionError):
            codex_hooks.enforce_role_gate("role_assign_prehook", "u1", "admin", "p")

    def test_capability_denial_denies_rather_than_retrying_in_process(
        self, monkeypatch
    ):
        self._installed(monkeypatch)
        self._sandbox(monkeypatch, error=PermissionError("verb 'user.set' denied"))
        with pytest.raises(PermissionError):
            codex_hooks.enforce_role_gate("role_assign_prehook", "u1", "admin", "p")

    def test_hook_receives_plain_args_and_read_only_capabilities(self, monkeypatch):
        self._installed(monkeypatch)
        calls = self._sandbox(monkeypatch, result={"allowed": True})
        codex_hooks.enforce_role_gate("role_assign_prehook", "u1", "admin", "alice")

        assert len(calls) == 1
        call = calls[0]
        assert call["context_id"] == "role_management_hook"
        assert call["params"] == {
            "user_id": "u1",
            "profile_name": "admin",
            "actor_principal": "alice",
        }
        from core import codex_bridge

        assert set(call["capabilities"]) <= codex_bridge.READ_VERBS

    def test_posthook_failure_does_not_raise(self, monkeypatch):
        """The role change already happened; refusing after the fact helps nobody."""
        self._installed(monkeypatch, source="def role_assign_posthook(args): pass")
        self._sandbox(monkeypatch, error=RuntimeError("spawn failed"))
        codex_hooks.notify_role_change("role_assign_posthook", "u1", "admin", "p")

    def test_registration_posthook_reports_when_no_codex_implements_it(
        self, monkeypatch
    ):
        self._installed(monkeypatch, source="def something_else(args): pass")
        self._sandbox(monkeypatch)
        assert codex_hooks.call_registration_posthook("u1") is False

    def test_registration_posthook_claims_the_registration(self, monkeypatch):
        self._installed(monkeypatch, source="def user_register_posthook(args): pass")
        calls = self._sandbox(monkeypatch, result=None)
        assert codex_hooks.call_registration_posthook("u1") is True
        assert calls[0]["params"] == {"user_id": "u1"}

    def test_registration_posthook_still_claims_it_after_a_failure(self, monkeypatch):
        """Falling through to the platform default would double-onboard the
        user, so a failed hook must not look like an absent one."""
        self._installed(monkeypatch, source="def user_register_posthook(args): pass")
        self._sandbox(monkeypatch, error=RuntimeError("spawn failed"))
        assert codex_hooks.call_registration_posthook("u1") is True

    def test_registration_hook_may_write_but_only_through_declared_verbs(self):
        from core import codex_bridge

        caps = set(codex_hooks.REGISTRATION_HOOK_CAPABILITIES)
        assert {"invoice.create", "notification.create"} <= caps
        assert caps <= set(codex_bridge.VERBS)

    def test_governance_params_survive_a_broken_codex(self, monkeypatch):
        self._installed(monkeypatch)
        self._sandbox(monkeypatch, error=RuntimeError("spawn failed"))
        assert (
            codex_hooks.call_role_hook(
                "get_governance_params", {"proposal_type": "x"}, fail_closed=False
            )
            is None
        )


# ---------------------------------------------------------------------------
# Federation assign / scale hooks (issue #265)
# ---------------------------------------------------------------------------

QUARTER_ASSIGNMENT_SOURCE = '''
ASSIGNMENT_STRATEGY = "least_populated"

def assign_quarter(principal, quarters, preferred):
    if preferred:
        for q in quarters:
            if q.canister_id == preferred:
                if q.population >= 100:
                    raise ValueError("quarter is full")
                return q.canister_id
        raise ValueError("quarter not found")
    target = min(quarters, key=lambda q: q.population)
    return target.canister_id

def should_deploy_quarter(populations, network, realm=None):
    pops = [int(p or 0) for p in (populations or [])]
    return bool(pops) and max(pops) >= 9
'''


class TestFederationHookDispatch:
    def _install(self, monkeypatch, source=QUARTER_ASSIGNMENT_SOURCE, name="quarter_assignment"):
        monkeypatch.setattr(
            codex_hooks, "_federation_codex", lambda: (name, source)
        )

    def _sandbox(self, monkeypatch, result=None, error=None):
        from core import runtime_sandbox

        calls = []

        def _run(context_id, source, hook_name, params, capabilities, context=None):
            calls.append({
                "context_id": context_id,
                "hook": hook_name,
                "params": params,
                "capabilities": list(capabilities),
                "source": source,
            })
            if error is not None:
                raise error
            return result

        monkeypatch.setattr(runtime_sandbox, "run_bridge_hook", _run)
        return calls

    def test_no_policy_returns_none(self, monkeypatch):
        monkeypatch.setattr(codex_hooks, "_federation_codex", lambda: (None, None))
        assert codex_hooks.call_assign_quarter("p", [], "") is None
        assert codex_hooks.call_should_deploy_quarter([1], "test") is None

    def test_assign_projects_quarters_and_runs_sandboxed(self, monkeypatch):
        self._install(monkeypatch)
        calls = self._sandbox(monkeypatch, result={"canister_id": "q-1"})

        class Q:
            def __init__(self, cid, pop):
                self.canister_id = cid
                self.name = cid
                self.population = pop

        result = codex_hooks.call_assign_quarter("alice", [Q("q-1", 3), Q("q-2", 1)], "")
        assert result == "q-1"
        assert calls[0]["hook"] == "assign_quarter_hook"
        assert calls[0]["capabilities"] == []
        assert calls[0]["params"]["quarters"] == [
            {"canister_id": "q-1", "name": "q-1", "population": 3},
            {"canister_id": "q-2", "name": "q-2", "population": 1},
        ]
        assert "assign_quarter_hook" in calls[0]["source"]

    def test_assign_rejection_is_fail_closed(self, monkeypatch):
        self._install(monkeypatch)
        self._sandbox(monkeypatch, error=RuntimeError("quarter is full"))
        with pytest.raises(PermissionError, match="quarter is full"):
            codex_hooks.call_assign_quarter("alice", [], "q-1")

    def test_scale_returns_the_verdict(self, monkeypatch):
        self._install(monkeypatch)
        self._sandbox(monkeypatch, result={"deploy": True})
        assert codex_hooks.call_should_deploy_quarter([9], "test") is True

    def test_scale_failure_falls_open_to_the_default(self, monkeypatch):
        self._install(monkeypatch)
        self._sandbox(monkeypatch, error=RuntimeError("spawn failed"))
        assert codex_hooks.call_should_deploy_quarter([9], "test") is None

    def test_prepare_strips_host_imports(self):
        prepared = codex_hooks._prepare_federation_source(
            "from datetime import datetime\nfrom ggg import Quarter\n"
            "def assign_quarter(p, q, pref): return 'x'\n"
        )
        assert "from datetime import datetime" not in prepared
        assert "from ggg import Quarter" not in prepared
        assert "def assign_quarter" in prepared
        assert "assign_quarter_hook" in prepared
