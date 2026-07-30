"""Execution-mode resolution for extensions (issue #245).

The in-process fallback was removed: an extension that resolves to ``sandbox``
either runs in the subinterpreter or its call fails. Running with host access
is therefore a declaration made before the call — core/system membership, a
manifest ``"runtime"``, or an explicit admin override — and never a runtime
downgrade. These tests pin that resolution and the guards that stop an admin
from configuring a mode which is known in advance to fail.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))

sys.modules.setdefault("_cdk", MagicMock())

from core import runtime_sandbox  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_policy(monkeypatch, tmp_path):
    """Cold config cache, a scratch policy file, and no real manifests."""
    monkeypatch.setattr(runtime_sandbox, "_config_cache", None, raising=False)
    monkeypatch.setattr(
        runtime_sandbox, "CONFIG_PATH", str(tmp_path / "sandbox_config.json")
    )
    monkeypatch.setattr(runtime_sandbox, "is_system_extension", lambda _id: False)
    monkeypatch.setattr(runtime_sandbox, "manifest_runtime_mode", lambda _id: None)
    monkeypatch.setattr(runtime_sandbox, "_is_codex_package", lambda _id: False)
    yield
    monkeypatch.setattr(runtime_sandbox, "_config_cache", None, raising=False)


def _declare(monkeypatch, **modes):
    monkeypatch.setattr(
        runtime_sandbox, "manifest_runtime_mode", lambda ext_id: modes.get(ext_id)
    )


class TestModeResolution:
    def test_default_is_sandbox(self):
        assert runtime_sandbox.resolve_mode("hello_world") == (
            "sandbox",
            "realm default",
        )
        assert runtime_sandbox.should_sandbox("hello_world") is True

    def test_system_extension_is_never_sandboxed(self, monkeypatch):
        monkeypatch.setattr(runtime_sandbox, "is_system_extension", lambda _id: True)
        mode, reason = runtime_sandbox.resolve_mode("admin_dashboard")
        assert mode == "in_process"
        assert reason == "core/system extension"

    def test_manifest_declaration_wins_over_realm_default(self, monkeypatch):
        _declare(monkeypatch, justice_litigation="in_process")
        mode, reason = runtime_sandbox.resolve_mode("justice_litigation")
        assert mode == "in_process"
        assert reason == "declared by manifest"
        assert runtime_sandbox.should_sandbox("justice_litigation") is False

    def test_manifest_declaration_beats_admin_override(self, monkeypatch):
        """An override cannot resurrect a spawn that is known to fail."""
        _declare(monkeypatch, notifications="in_process")
        runtime_sandbox.update_config({"extensions": {"notifications": "in_process"}})
        assert runtime_sandbox.resolve_mode("notifications") == (
            "in_process",
            "declared by manifest",
        )

    def test_admin_override_applies_to_undeclared_extension(self):
        runtime_sandbox.update_config({"extensions": {"welcome": "in_process"}})
        assert runtime_sandbox.resolve_mode("welcome") == (
            "in_process",
            "admin override",
        )

    def test_codex_package_is_never_routed_through_the_extension_sandbox(
        self, monkeypatch
    ):
        """Codex isolation is per-hook via the bridge, not this switch."""
        monkeypatch.setattr(runtime_sandbox, "_is_codex_package", lambda _id: True)
        mode, reason = runtime_sandbox.resolve_mode("syntropia")
        assert mode == "in_process"
        assert "capability bridge" in reason

    def test_disabling_sandboxing_puts_everything_in_process(self):
        runtime_sandbox.update_config({"enabled": False})
        mode, reason = runtime_sandbox.resolve_mode("hello_world")
        assert mode == "in_process"
        assert reason == "sandboxing disabled"


class TestConfigSurface:
    def test_fallback_key_is_gone(self):
        assert "fallback_in_process" not in runtime_sandbox.DEFAULT_CONFIG
        assert "fallback_in_process" not in runtime_sandbox.get_config()

    def test_fallback_key_is_rejected(self):
        with pytest.raises(ValueError, match="unknown sandbox config keys"):
            runtime_sandbox.update_config({"fallback_in_process": True})

    def test_cannot_sandbox_a_system_extension(self, monkeypatch):
        monkeypatch.setattr(runtime_sandbox, "is_system_extension", lambda _id: True)
        with pytest.raises(ValueError, match="core/system extension"):
            runtime_sandbox.update_config({"extensions": {"vault": "sandbox"}})

    def test_cannot_sandbox_an_extension_declaring_in_process(self, monkeypatch):
        _declare(monkeypatch, procurement="in_process")
        with pytest.raises(ValueError, match="no in-process fallback"):
            runtime_sandbox.update_config({"extensions": {"procurement": "sandbox"}})

    def test_cannot_sandbox_a_codex(self, monkeypatch):
        monkeypatch.setattr(runtime_sandbox, "_is_codex_package", lambda _id: True)
        with pytest.raises(ValueError, match="is a codex"):
            runtime_sandbox.update_config({"extensions": {"syntropia": "sandbox"}})


class TestStatus:
    def test_status_marks_declared_extensions_locked(self, monkeypatch):
        _declare(monkeypatch, role_manager="in_process")
        mock = MagicMock()
        mock.list_installed.return_value = ["role_manager", "hello_world"]
        monkeypatch.setitem(sys.modules, "core.runtime_extensions", mock)

        by_id = {e["id"]: e for e in runtime_sandbox.get_status()["extensions"]}

        assert by_id["role_manager"]["locked"] is True
        assert by_id["role_manager"]["resolved_mode"] == "in_process"
        assert by_id["hello_world"]["locked"] is False
        assert by_id["hello_world"]["resolved_mode"] == "sandbox"


class TestExtensionCallPath:
    @pytest.fixture(autouse=True)
    def _has_backend(self, monkeypatch):
        from core import extensions as core_extensions

        monkeypatch.setattr(core_extensions, "_has_backend", lambda _id: True)

    def test_frontend_only_extension_skips_the_sandbox(self, monkeypatch):
        """Nothing to isolate, so no spawn is attempted for a missing entry.py."""
        from core import extensions as core_extensions

        monkeypatch.setattr(core_extensions, "_has_backend", lambda _id: False)
        monkeypatch.setattr(runtime_sandbox, "should_sandbox", lambda _id: True)

        def _never(*_args, **_kwargs):
            raise AssertionError("sandbox must not be reached")

        monkeypatch.setattr(runtime_sandbox, "call_in_sandbox", _never)

        mock_rt = MagicMock()
        mock_rt.resolve_extension_id.side_effect = lambda ext_id: ext_id
        mock_rt.get_func.return_value = None
        monkeypatch.setitem(sys.modules, "core.runtime_extensions", mock_rt)

        with pytest.raises(TypeError):
            core_extensions.call_extension_function("metrics", "anything", "{}")

    def test_missing_sandbox_image_raises_instead_of_degrading(self, monkeypatch):
        """The old behavior here was a warning plus a privileged call."""
        from core import extensions as core_extensions

        monkeypatch.setattr(runtime_sandbox, "should_sandbox", lambda _id: True)
        monkeypatch.setattr(runtime_sandbox, "is_sandbox_available", lambda: False)

        mock_rt = MagicMock()
        mock_rt.resolve_extension_id.side_effect = lambda ext_id: ext_id
        monkeypatch.setitem(sys.modules, "core.runtime_extensions", mock_rt)

        with pytest.raises(RuntimeError, match="no _basilisk_sandbox"):
            core_extensions.call_extension_function("hello_world", "greet", "{}")

        mock_rt.get_func.assert_not_called()

    def test_spawn_failure_is_not_retried_in_process(self, monkeypatch):
        from core import extensions as core_extensions

        monkeypatch.setattr(runtime_sandbox, "should_sandbox", lambda _id: True)
        monkeypatch.setattr(runtime_sandbox, "is_sandbox_available", lambda: True)

        def _boom(*_args, **_kwargs):
            raise RuntimeError("spawn failed")

        monkeypatch.setattr(runtime_sandbox, "call_extension_in_sandbox", _boom)

        mock_rt = MagicMock()
        mock_rt.resolve_extension_id.side_effect = lambda ext_id: ext_id
        monkeypatch.setitem(sys.modules, "core.runtime_extensions", mock_rt)

        with pytest.raises(RuntimeError, match="spawn failed"):
            core_extensions.call_extension_function("hello_world", "greet", "{}")

        mock_rt.get_func.assert_not_called()
