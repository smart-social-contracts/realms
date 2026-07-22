"""Unit tests for sandbox policy config (no canister required)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "src" / "realm_backend" / "core"
sys.path.insert(0, str(CORE.parent))


class TestRuntimeSandboxConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.tmp.name, "sandbox_config.json")
        # Import after path setup
        import core.runtime_sandbox as rs

        self.rs = rs
        self._orig_path = rs.CONFIG_PATH
        rs.CONFIG_PATH = self.config_path
        rs._config_cache = None

    def tearDown(self):
        self.rs.CONFIG_PATH = self._orig_path
        self.rs._config_cache = None
        self.tmp.cleanup()

    def test_default_enabled(self):
        cfg = self.rs.get_config()
        self.assertTrue(cfg["enabled"])
        self.assertEqual(cfg["default_mode"], "sandbox")
        self.assertEqual(cfg["codex_hooks"]["default_mode"], "sandbox")

    def test_update_codex_hooks(self):
        cfg = self.rs.update_config({
            "codex_hooks": {
                "default_mode": "in_process",
                "hooks": {"role_assign_prehook": "sandbox"},
            }
        })
        self.assertEqual(cfg["codex_hooks"]["default_mode"], "in_process")
        self.assertEqual(cfg["codex_hooks"]["hooks"]["role_assign_prehook"], "sandbox")
        # Persisted
        with open(self.config_path) as f:
            stored = json.load(f)
        self.assertEqual(stored["codex_hooks"]["hooks"]["role_assign_prehook"], "sandbox")

    def test_force_in_process_hook_rejects_sandbox(self):
        with self.assertRaises(ValueError):
            self.rs.update_config({
                "codex_hooks": {"hooks": {"on_treasury_send": "sandbox"}}
            })

    def test_resolve_hook_not_compatible(self):
        self.rs.update_config({"enabled": True})
        with mock.patch.object(self.rs, "is_sandbox_available", return_value=True):
            mode = self.rs.resolve_hook_mode("role_assign_prehook")
            self.assertIn("not sandbox-compatible", mode)
            self.assertFalse(self.rs.should_sandbox_hook("role_assign_prehook"))
        forced = self.rs.resolve_hook_mode("init")
        self.assertEqual(forced, "in_process (forced)")

    def test_describe_patch(self):
        summary = self.rs.describe_config_patch({"enabled": False})
        self.assertIn("disable sandboxing", summary)

    def test_unknown_key_rejected(self):
        with self.assertRaises(ValueError):
            self.rs.update_config({"nope": True})


if __name__ == "__main__":
    unittest.main()
