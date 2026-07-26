"""End-to-end (logic) tests for the migrated agora/syntropia sandbox hooks
(issue #265).

For each codex we reproduce the exact sandbox path off-canister: build the
combined source (SDK loader + the codex's real ``sandbox_hooks.py``), inject an
``rpc`` builtin wired to the *real* host bridge handler, and back the verbs with
fakes (so no ``ggg``/DB is needed). The handler is granted exactly the
capabilities declared in the codex manifest — so a hook that calls a verb it
did not declare fails here, catching capability drift.

The real subinterpreter (``_basilisk_sandbox``) is WASM-only; this validates the
hook logic + capability wiring, which is what changed in the migration.
"""

import builtins
import json
import os

import pytest

from core import codex_bridge, runtime_sandbox

_REALM_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CODICES = os.path.join(_REALM_BACKEND, "..", "..", "codices", "codices")


def _manifest(codex):
    with open(os.path.join(_CODICES, codex, "manifest.json")) as f:
        return json.load(f)


def _sandbox_source(codex):
    manifest = _manifest(codex)
    module = manifest["sandbox_module"]
    with open(os.path.join(_CODICES, codex, "backend", module)) as f:
        return f.read()


def _run_hook(codex, hook_name, args, fake_verbs):
    """Run ``codex``'s sandboxed ``hook_name`` exactly as the subinterpreter
    would, with ``fake_verbs`` backing the registry and the manifest's declared
    capabilities. Returns (parsed_result, recorded_calls)."""
    manifest = _manifest(codex)
    capabilities = manifest["capabilities"]
    source = runtime_sandbox._build_codex_sandbox_source(_sandbox_source(codex))

    calls = []
    saved = {}
    for name, fn in fake_verbs.items():
        saved[name] = codex_bridge.VERBS.get(name)

        def _wrap(fn):
            def _v(**kwargs):
                calls.append((_v.action, kwargs))
                return fn(**kwargs)
            return _v

        w = _wrap(fn)
        w.action = name
        codex_bridge.VERBS[name] = w

    handler = codex_bridge.make_rpc_handler(codex, capabilities)
    builtins.rpc = lambda action, **kwargs: handler(codex, action, kwargs)
    try:
        g = {}
        exec(compile(source, f"{codex}/sandbox_hooks.py", "exec"), g)
        raw = g[hook_name](args=json.dumps(args))
        return json.loads(raw), calls
    finally:
        del builtins.rpc
        for name, prev in saved.items():
            if prev is None:
                codex_bridge.VERBS.pop(name, None)
            else:
                codex_bridge.VERBS[name] = prev


def _verbs_by_action(calls):
    seen = {}
    for action, kwargs in calls:
        seen.setdefault(action, []).append(kwargs)
    return seen


# ---------------------------------------------------------------------------
# Syntropia — greenfield deposit invoice
# ---------------------------------------------------------------------------


def test_syntropia_on_user_register_creates_deposit_invoice():
    config = {
        "fees": {"deposit": 0.05},
        "lifecycle": {"deposit_label": "a house in a zone"},
        "membership": {"invoice_validity_days": 30},
    }
    fakes = {
        "config.get": lambda **k: config,
        "currency.get": lambda **k: "ckBTC",
        "time.now": lambda **k: {"epoch": 0, "ns": 0},
        "user.get": lambda user_id="", **k: {"id": user_id, "name": "Citizen"},
        "invoice.create": lambda **k: {"id": "inv-1"},
        "notification.create": lambda **k: {"id": "ntf-1"},
    }
    result, calls = _run_hook(
        "syntropia", "on_user_register", {"user_id": "u1"}, fakes
    )
    assert result == {"success": True, "invoice_id": "inv-1"}

    by = _verbs_by_action(calls)
    assert by["invoice.create"][0]["metadata"] == "deposit invoice - a house in a zone"
    assert by["invoice.create"][0]["amount"] == 0.05
    assert by["invoice.create"][0]["currency"] == "ckBTC"
    assert by["invoice.create"][0]["user_id"] == "u1"
    assert by["notification.create"][0]["topic"] == "welcome"
    assert by["notification.create"][0]["metadata"] == "invoice_id:inv-1"


def test_syntropia_unknown_user_short_circuits():
    fakes = {
        "config.get": lambda **k: {},
        "currency.get": lambda **k: "ckBTC",
        "time.now": lambda **k: {"epoch": 0, "ns": 0},
        "user.get": lambda user_id="", **k: None,
        "invoice.create": lambda **k: {"id": "x"},
        "notification.create": lambda **k: {"id": "x"},
    }
    result, calls = _run_hook(
        "syntropia", "on_user_register", {"user_id": "ghost"}, fakes
    )
    assert result == {"success": False, "error": "user not found"}
    assert "invoice.create" not in _verbs_by_action(calls)


# ---------------------------------------------------------------------------
# Agora — incumbent migration (activation + phase-aware invoicing)
# ---------------------------------------------------------------------------


def _agora_fakes(stage, fee):
    config = {
        "fees": {"registration": fee},
        "membership": {"invoice_validity_days": 30},
    }
    return {
        "config.get": lambda **k: config,
        "currency.get": lambda **k: "REALMS",
        "time.now": lambda **k: {"epoch": 0, "ns": 0},
        "user.get": lambda user_id="", **k: {"id": user_id, "name": "Resident"},
        "realm.get": lambda **k: {"status": stage},
        "member.activate": lambda **k: {"accepted": True, "member_id": "m1"},
        "invoice.create": lambda **k: {"id": "inv-9"},
        "notification.create": lambda **k: {"id": "ntf-9"},
    }


def test_agora_beta_issues_registration_invoice_and_activates():
    result, calls = _run_hook(
        "agora", "on_user_register", {"user_id": "u2"},
        _agora_fakes(stage="beta", fee=2.0),
    )
    assert result == {"success": True, "invoice_id": "inv-9"}
    by = _verbs_by_action(calls)
    # Migration activation always happens...
    assert by["member.activate"][0]["user_id"] == "u2"
    assert by["member.activate"][0]["identity_verification"] == "verified"
    # ...and beta with a fee issues a registration invoice.
    assert by["invoice.create"][0]["metadata"] == "registration invoice"
    assert by["invoice.create"][0]["amount"] == 2.0
    assert by["notification.create"][0]["icon"] == "wallet"


def test_agora_alpha_activates_but_issues_no_invoice():
    result, calls = _run_hook(
        "agora", "on_user_register", {"user_id": "u3"},
        _agora_fakes(stage="alpha", fee=2.0),
    )
    assert result == {"success": True, "stage": "alpha"}
    by = _verbs_by_action(calls)
    assert "member.activate" in by
    assert "invoice.create" not in by  # no payment during alpha
    assert by["notification.create"][0]["icon"] == "information_circle"


def test_agora_capabilities_cover_every_verb_used():
    # If a hook calls a verb absent from the manifest capabilities, the handler
    # raises PermissionError; a green run above already proves coverage, but
    # assert the declared set matches the registry names too.
    declared = set(_manifest("agora")["capabilities"])
    assert declared <= set(codex_bridge.known_verbs())
    declared_s = set(_manifest("syntropia")["capabilities"])
    assert declared_s <= set(codex_bridge.known_verbs())
