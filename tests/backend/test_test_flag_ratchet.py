"""Test-mode flags may not regain the privileges they used to grant.

These are source and config scans rather than behavioural tests, deliberately:
the properties being defended are about what the shipped canister *contains*,
and a runtime test can only observe the paths it happens to exercise. See
realms#395.

Three things are held in place here:

1. ``test_mode_skip_authentication`` — which made ``_check_access`` return True
   for every caller and every operation — stays deleted.
2. ``can_test_mode`` — the switch that permits test flags on a production
   network — stays settable only through the controller-gated parameter, never
   from the ``test_flags`` payload that ``set_test_flags_json`` accepts without
   authentication.
3. The network gate stays an allowlist, so an unset or unrecognised network
   fails closed.
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
BACKEND = REPO_ROOT / "src" / "realm_backend"
MAIN_PY = BACKEND / "main.py"
RUNTIME_FLAGS = BACKEND / "core" / "runtime_flags.py"
REALM_ENTITY = BACKEND / "ggg" / "governance" / "realm.py"
ACCESS_PY = BACKEND / "core" / "access.py"

REMOVED_FLAG = "test_mode_skip_authentication"

# The migration that drops stored values is the only place the backend may still
# name the removed flag: it has to know the key to delete it.
ALLOWED_FLAG_MENTIONS = {REALM_ENTITY}


def _backend_sources():
    return [p for p in BACKEND.rglob("*.py") if "/tests/" not in p.as_posix()]


def test_skip_authentication_flag_is_gone_from_the_backend():
    offenders = []
    for path in _backend_sources():
        if path in ALLOWED_FLAG_MENTIONS:
            continue
        if REMOVED_FLAG in path.read_text():
            offenders.append(path.relative_to(REPO_ROOT).as_posix())
    assert not offenders, (
        f"{REMOVED_FLAG} disabled every permission check and was removed. "
        "It reappears in:\n" + "\n".join(f"  - {o}" for o in offenders)
    )


def test_access_check_has_no_realm_flag_bypass():
    """No ``return True`` driven by a flag read off the Realm entity."""
    source = ACCESS_PY.read_text()
    assert REMOVED_FLAG not in source
    # A getattr against the realm followed by an unconditional grant is the
    # shape of the bypass that was removed; keep that shape from coming back.
    assert not re.search(
        r"getattr\(\s*realm\s*,\s*[\"']test_mode[\w\"']*\s*,[^)]*\)\s*:\s*\n\s*return True",
        source,
    ), "a test-mode flag on the Realm entity must not short-circuit _check_access"


def test_can_test_mode_is_stripped_from_the_test_flags_payload():
    source = MAIN_PY.read_text()
    assert 'flags.pop("can_test_mode", None)' in source, (
        "set_test_flags_json is callable without authentication, so the shared "
        "config path must discard can_test_mode from its payload"
    )
    assert not re.search(r"realm\.can_test_mode\s*=\s*bool\(\s*flags", source), (
        "can_test_mode must never be assigned from the test_flags payload; it is "
        "settable only via the controller-gated set_canister_config parameter"
    )


def test_network_gate_is_an_allowlist_that_fails_closed():
    import sys

    sys.path.insert(0, str(BACKEND))
    from core.runtime_flags import NON_PRODUCTION_NETWORKS, test_flags_allowed

    assert "ic" not in NON_PRODUCTION_NETWORKS
    assert "production" not in NON_PRODUCTION_NETWORKS

    for unknown in ("", "   ", "mainnet", "prod", "ic-1", "unknown"):
        assert test_flags_allowed(unknown, False) is False, (
            f"network {unknown!r} must not permit test flags: the field is "
            "self-declared, so anything unrecognised is treated as production"
        )


@pytest.mark.parametrize(
    "descriptor", sorted((REPO_ROOT / "deployment-descriptors").glob("*mundus*.yml"))
)
def test_descriptors_do_not_enable_the_removed_flag(descriptor):
    assert "SKIP_AUTHENTICATION" not in descriptor.read_text(), (
        f"{descriptor.name} still sets the removed authentication bypass"
    )


@pytest.mark.parametrize(
    "arrangement", sorted((REPO_ROOT / "casals-config" / "arrangements").glob("*.json"))
)
def test_arrangements_do_not_enable_the_removed_flag(arrangement):
    raw = arrangement.read_text()
    assert "skip_authentication" not in raw, (
        f"{arrangement.name} still sets the removed authentication bypass"
    )
    # Guard the escalation path too: an arrangement must not hand a realm the
    # production override through the test_flags blob.
    doc = json.loads(raw)

    def _walk(node):
        if isinstance(node, dict):
            flags = node.get("test_flags")
            if isinstance(flags, dict):
                assert "can_test_mode" not in flags, (
                    f"{arrangement.name} sets can_test_mode via test_flags"
                )
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for value in node:
                _walk(value)

    _walk(doc)


def test_test_mode_is_gated_on_the_build_variant():
    """Every is_test_mode() caller uses it to permit a test-only shortcut.

    Upgrading a test realm to a production WASM leaves ``test_mode: true`` in
    the database, so reading the row alone would keep those shortcuts reachable
    on the build that is supposed to have removed them.
    """
    source = RUNTIME_FLAGS.read_text()
    body = source.split("def is_test_mode(")[1].split("\ndef ")[0]
    assert "test_flags_available" in body, (
        "is_test_mode must consult the build variant, otherwise a stale "
        "test_mode row re-enables test-only paths in a production build"
    )


def test_unauthenticated_flag_editor_accepts_only_test_only_flags():
    """set_test_flags_json has no @require, so its surface must stay narrow.

    Product configuration (disable_monetary_tokens, demo_notice, …) is not
    network-gated, so accepting it here would let an anonymous caller change
    real realm settings.
    """
    source = MAIN_PY.read_text()
    body = source.split("def set_test_flags_json(")[1].split("\n@update")[0]
    assert "is_test_only_flag" in body, (
        "set_test_flags_json must reject non-test flags; it is callable without "
        "authentication and product flags bypass the network gate"
    )


def test_can_test_mode_is_not_lifted_out_of_a_flags_blob():
    """A copied test_flags blob must not silently unlock a production network."""
    source = MAIN_PY.read_text()
    body = source.split("def set_canister_config_json(")[1].split("\n@update")[0]
    assert "can_test_mode = test_flags_dict.pop(" not in body
    assert "can_test_mode = parsed_flags.pop(" not in body
    assert "_reject_nested" in body, (
        "nested can_test_mode must be rejected with an error rather than "
        "honoured, so unlocking production is always written down explicitly"
    )
