"""Ratchet: Cedar pack / candid always export enter_setup.

The GOS installer calls enter_setup on every new realm. A stale file_registry
WASM that dropped the method surfaces as IC0536. Do not leftover-free or add
a per-deploy sandbox gate that can omit this export.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import pack_realm_backend as pack  # noqa: E402


def _main_py() -> Path:
    return REPO_ROOT / "src" / "realm_backend" / "main.py"


def _source_did() -> Path:
    return REPO_ROOT / "src" / "realm_backend" / "realm_backend.did"


def _declaration_did() -> Path:
    return REPO_ROOT / "src" / "declarations" / "realm_backend" / "realm_backend.did"


def _is_update_decorated(func: ast.FunctionDef) -> bool:
    for dec in func.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "update":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == "update":
            return True
        if isinstance(dec, ast.Call):
            target = dec.func
            if isinstance(target, ast.Name) and target.id == "update":
                return True
            if isinstance(target, ast.Attribute) and target.attr == "update":
                return True
    return False


def test_required_pack_exports_include_enter_setup():
    assert "enter_setup" in pack.REQUIRED_UPDATE_EXPORTS


def test_source_did_exports_enter_setup():
    text = _source_did().read_text()
    assert '"enter_setup"' in text
    assert '"enter_setup" : (principal, text, text) -> (text);' in text


def test_declarations_did_exports_enter_setup():
    text = _declaration_did().read_text()
    assert '"enter_setup"' in text
    assert '"enter_setup" : (principal, text, text) -> (text);' in text


def test_main_py_defines_update_enter_setup():
    tree = ast.parse(_main_py().read_text())
    found = False
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "enter_setup":
            assert _is_update_decorated(node), "@update missing on enter_setup"
            found = True
            break
    assert found, "enter_setup is not defined in main.py"


def test_basilisk_extracts_enter_setup_as_update():
    from basilisk.wasm_manipulator import extract_methods_from_python

    methods, _types, _lifecycle = extract_methods_from_python(_main_py().read_text())
    enter = next((m for m in methods if m["name"] == "enter_setup"), None)
    assert enter is not None, "basilisk AST extract dropped enter_setup"
    assert enter["method_type"] == "update"


def test_pack_assert_required_exports_accepts_source_did():
    pack._assert_required_exports(_source_did())


def test_pack_assert_required_exports_rejects_missing(tmp_path):
    did = tmp_path / "empty.did"
    did.write_text("service : { \"get_setup_state\" : () -> (text) query; }\n")
    try:
        pack._assert_required_exports(did)
    except SystemExit as exc:
        assert "enter_setup" in str(exc)
    else:
        raise AssertionError("expected SystemExit when enter_setup is missing")
