"""Unit tests for the codex hook API dispatch layer (issue #244).

Covers core/codex_hooks.py:
  - codex_api_version gating
  - one-codex-per-realm singleton rule
  - active codex discovery from extension manifests (kind: codex)
  - get_config merge semantics (codex config over Realm.manifest_data)
  - extension override resolution (hook + manifest + legacy shim)
  - on_user_register dispatch behavior
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
