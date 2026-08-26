"""Local helpers for scripts/shell_e2e_realmtest6.py — no IC, no realmtest6."""

import base64
import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "shell_e2e_realmtest6.py"


def _load():
    spec = importlib.util.spec_from_file_location("shell_e2e_realmtest6", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestShellE2EHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e2e = _load()

    def test_seed_layout_matches_js_and_roster(self):
        seed0 = self.e2e.test_identity_seed(0)
        self.assertEqual(seed0[0], 0xED)
        self.assertEqual(seed0[1], 0x57)
        self.assertEqual(seed0[2:], bytes(30))
        seed1 = self.e2e.test_identity_seed(1)
        self.assertEqual(seed1[2], 1)
        self.assertEqual(seed1[3], 0)
        roster = self.e2e.load_roster()
        self.assertEqual(
            roster[0]["principal"],
            "2eqns-rmzes-7npxw-dxpw2-qdy2s-mw6ix-svdo2-oya7o-a6ldc-sqgwh-bqe",
        )
        self.assertEqual(
            roster[1]["principal"],
            "z32zf-ic72u-jhtqq-ojjqp-jblhx-dxxin-vqelt-ljmo4-ymwmh-gcnzo-hae",
        )

    def test_pkcs8_pem_is_ed25519_seed(self):
        seed = self.e2e.test_identity_seed(0)
        pem = self.e2e.ed25519_seed_to_pkcs8_pem(seed)
        self.assertTrue(pem.startswith("-----BEGIN PRIVATE KEY-----"))
        body = "".join(
            line for line in pem.splitlines() if not line.startswith("-----")
        )
        der = base64.b64decode(body)
        self.assertTrue(der.startswith(bytes.fromhex("302e020100300506032b657004220420")))
        self.assertTrue(der.endswith(seed))

    def test_denial_classifier_access_denied(self):
        blob = (
            "Error: Canister rejected: AccessDenied: "
            "Access denied: user abc lacks permission 'realm.admin'"
        )
        info = self.e2e.denial_info(blob)
        self.assertTrue(info["access_denied"] and info["permission_error"])
        self.assertEqual(info["operation"], "realm.admin")
        shell = self.e2e.denial_info(
            "PermissionError: Access denied: user abc lacks permission 'realm.admin'"
        )
        ok, _ = self.e2e.same_denial(info, shell)
        self.assertTrue(ok)

    def test_forbidden_identities_do_not_include_ii_bypass_names(self):
        self.assertIn("deployer", self.e2e.FORBIDDEN_IDENTITY_NAMES)
        self.assertIn("my_dev_identity_1", self.e2e.FORBIDDEN_IDENTITY_NAMES)
        self.assertNotIn(self.e2e.identity_name(0), self.e2e.FORBIDDEN_IDENTITY_NAMES)
        self.assertIn(
            "ah6ac-cc73l-bb2zc-ni7bh-jov4q-roeyj-6k2ob-mkg5j-pequi-vuaa6-2ae",
            self.e2e.CONTROLLER_PRINCIPALS,
        )

    def test_extract_extension_record_with_escaped_json(self):
        blob = (
            '(record { success = true; response = "{\\"ok\\":true,\\"n\\":1}"; })'
        )
        rec = self.e2e.extract_extension_record(blob)
        self.assertEqual(rec, {"success": True, "response": '{"ok":true,"n":1}'})


if __name__ == "__main__":
    unittest.main()
