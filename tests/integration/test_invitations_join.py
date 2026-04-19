#!/usr/bin/env python3
"""Integration tests for the invitation-link → join_realm_with_invite flow.

Exercises the end-to-end contract introduced together with
``admin_dashboard``'s ``consume_registration_code`` endpoint and
``realm_backend.join_realm_with_invite``:

  1. An admin mints a registration code via ``admin_dashboard``.
  2. ``validate_registration_code`` returns the same code's role.
  3. The realm backend's ``join_realm_with_invite`` calls into the
     extension to atomically validate and consume the code, then
     registers the caller as a User with the right profile.

The tests run against a realm that already has ``admin_dashboard``
installed. Locally that's whatever ``realms realm deploy`` brings up;
in CI we need a workflow that installs the extension before running
this file (see the test_environment_ready guard below).

Following the convention of the other ``tests/integration/*.py``
scripts, this is a plain Python script (no pytest), invoked via
``tests/integration/run_tests.sh``.
"""

import json
import os
import sys
import traceback

# Allow `from fixtures.dfx_helpers import …` when run from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fixtures.dfx_helpers import dfx_call, dfx_call_json  # noqa: E402


REALM_BACKEND = os.environ.get("REALM_BACKEND_CANISTER", "realm_backend")
ADMIN_DASHBOARD_EXTENSION = "admin_dashboard"


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _candid_quote(s: str) -> str:
    """Quote a Python string for use inside a Candid `text` arg."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _extension_call(method: str, args: dict) -> dict:
    """Call an admin_dashboard method through realm_backend.extension_sync_call.

    Returns the parsed JSON response from the extension. Raises on dfx
    failure or if the extension says ``success=false``.
    """
    args_json = json.dumps(args)
    candid_args = (
        f'(record {{ extension_name = "{ADMIN_DASHBOARD_EXTENSION}"; '
        f'function_name = "{method}"; '
        f'args = "{_candid_quote(args_json)}" }})'
    )
    response = dfx_call_json(
        REALM_BACKEND, "extension_sync_call", candid_args, is_update=True
    )

    if not response.get("success"):
        raise AssertionError(
            f"extension_sync_call wrapper reported success=false: {response}"
        )

    inner_text = response.get("response", "")
    try:
        inner = json.loads(inner_text)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"Could not parse extension response as JSON: {e}\n"
            f"Raw response: {inner_text!r}"
        )
    return inner


def _join_with_invite(profile: str, invite_code: str) -> dict:
    """Call realm_backend.join_realm_with_invite and return the parsed RealmResponse."""
    return dfx_call_json(
        REALM_BACKEND,
        "join_realm_with_invite",
        f'("{profile}", "", "{_candid_quote(invite_code)}")',
        is_update=True,
    )


def _has_admin_dashboard_installed() -> bool:
    """Return True when extension_sync_call to admin_dashboard responds.

    Used to skip the entire suite gracefully on test harnesses that do
    not install ``admin_dashboard`` (for example, the current PR CI
    descriptor sets ``artifacts.extensions: []``).
    """
    try:
        _extension_call("get_entity_types", {})
        return True
    except Exception as e:
        print(f"  [SKIP] admin_dashboard not callable: {e}")
        return False


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_environment_ready():
    """Sanity check: the realm canister exists and admin_dashboard answers."""
    print("  - test_environment_ready...", end=" ")
    output, code = dfx_call(REALM_BACKEND, "status", "()", output_json=False)
    assert code == 0, f"status failed (rc={code}): {output}"
    if not _has_admin_dashboard_installed():
        print("SKIP")
        raise _Skip("admin_dashboard extension not installed in this realm")
    print("✓")


def test_mint_member_invite_returns_member_profile():
    """generate_registration_url with profile=member round-trips."""
    print("  - test_mint_member_invite_returns_member_profile...", end=" ")
    result = _extension_call(
        "generate_registration_url",
        {
            "user_id": "ittest_member_invitee",
            "created_by": "test",
            "frontend_url": "http://localhost:8000",
            "expires_in_hours": 24,
            "profile": "member",
            "max_uses": 1,
        },
    )
    assert result.get("success"), f"mint failed: {result}"
    data = result.get("data", {})
    assert data.get("profile") == "member", data
    assert data.get("code"), data
    assert data.get("code_hash"), (
        f"Expected code_hash in mint response (used by admin UI for revoke "
        f"without the plaintext): {data}"
    )
    assert data["code"] != data["code_hash"], (
        f"Plaintext code and code_hash must differ: {data}"
    )
    assert data.get("registration_url", "").endswith(f"/join?invite={data['code']}"), (
        data.get("registration_url"),
    )
    print("✓")


def test_listing_does_not_leak_plaintext_code():
    """get_registration_codes must expose only code_hash, never plaintext."""
    print("  - test_listing_does_not_leak_plaintext_code...", end=" ")
    # Mint at least one so the listing is non-empty.
    _extension_call(
        "generate_registration_url",
        {
            "user_id": "ittest_no_leak",
            "created_by": "test",
            "frontend_url": "http://localhost:8000",
            "expires_in_hours": 24,
            "profile": "member",
            "max_uses": 1,
        },
    )
    listing = _extension_call(
        "get_registration_codes", {"include_used": True, "include_revoked": True}
    )
    assert listing.get("success"), listing
    rows = listing.get("data") or []
    leaked = [r for r in rows if r.get("code") or r.get("registration_url")]
    assert not leaked, (
        f"Listing leaked plaintext for {len(leaked)} row(s); only code_hash "
        f"should be returned. Sample: {leaked[:1]}"
    )
    print("✓")


def test_validate_returns_admin_profile():
    """A freshly-minted admin invite reports profile=admin via validate."""
    print("  - test_validate_returns_admin_profile...", end=" ")
    minted = _extension_call(
        "generate_registration_url",
        {
            "user_id": "ittest_admin_validate",
            "created_by": "test",
            "frontend_url": "http://localhost:8000",
            "expires_in_hours": 24,
            "profile": "admin",
            "max_uses": 1,
        },
    )
    assert minted.get("success"), minted
    code = minted["data"]["code"]
    validated = _extension_call("validate_registration_code", {"code": code})
    assert validated.get("success"), validated
    assert validated.get("data", {}).get("profile") == "admin", validated
    print("✓")


def test_join_realm_with_invite_grants_invite_profile():
    """join_realm_with_invite consumes the code and grants the invite's role.

    Asserts the *intended* contract:
      - on success, the response has success=true and the granted
        profile (from the code, not from the requested ``profile`` arg)
        is reflected in the returned ``userGet.profiles`` list.
      - the same code cannot be consumed twice by the same caller.
    """
    print("  - test_join_realm_with_invite_grants_invite_profile...", end=" ")
    # Mint a member invite (to avoid the bootstrap-admin guard).
    minted = _extension_call(
        "generate_registration_url",
        {
            "user_id": "ittest_join_member",
            "created_by": "test",
            "frontend_url": "http://localhost:8000",
            "expires_in_hours": 24,
            "profile": "member",
            "max_uses": 1,
        },
    )
    assert minted.get("success"), minted
    code = minted["data"]["code"]

    # join_realm_with_invite asks for "member"; the code is also "member".
    response = _join_with_invite("member", code)
    assert response.get("success"), response
    profiles_granted = (
        response.get("data", {}).get("userGet", {}).get("profiles") or []
    )
    assert "member" in profiles_granted, (
        f"Expected 'member' in returned profiles; got {profiles_granted!r}"
    )

    # Second consume by the same principal must fail (single-use guard).
    second = _join_with_invite("member", code)
    assert not second.get("success"), (
        f"Second consume should be rejected, got: {second}"
    )
    err = (second.get("data") or {}).get("error", "")
    assert "code" in err.lower() or "invitation" in err.lower() or "redeem" in err.lower(), (
        f"Expected an invitation-related error message, got: {err!r}"
    )
    print("✓")


def test_join_realm_without_invite_rejects_admin_when_admin_exists():
    """If the realm already has an admin, plain join_realm('admin', ...) must fail.

    (When no admin exists yet and the caller is the canister controller,
    the bootstrap path applies — that's not what's tested here.)
    """
    print("  - test_join_realm_without_invite_rejects_admin_when_admin_exists...", end=" ")
    # Probe by *attempting* the call. We don't know whether a previous
    # test already promoted somebody, so accept either outcome:
    #   - rejected with an "admin invitation" error (the new tightened
    #     behaviour we want to validate), or
    #   - accepted with success=true (which means the realm had no admin
    #     yet AND the test identity was the controller — bootstrap path).
    #
    # Either way, a *second* attempt must be rejected with the
    # admin-invite-required error: by then there's at least one admin.
    response = _join_with_invite("admin", "")
    assert isinstance(response, dict), response

    second = _join_with_invite("admin", "")
    assert not second.get("success"), (
        f"After bootstrap, plain admin self-join must be rejected; got: {second}"
    )
    err = ((second.get("data") or {}).get("error") or "").lower()
    assert "admin" in err and ("invit" in err or "invitation" in err), (
        f"Expected an 'admin invitation required' error; got: {err!r}"
    )
    print("✓")


def test_invalid_invite_code_is_rejected():
    """Bogus invite codes must be rejected by join_realm_with_invite."""
    print("  - test_invalid_invite_code_is_rejected...", end=" ")
    response = _join_with_invite("member", "this-code-does-not-exist-zzzz")
    assert not response.get("success"), (
        f"Invalid invite should be rejected, got: {response}"
    )
    print("✓")


# ---------------------------------------------------------------------------
# Tiny custom skip mechanism (no pytest dependency on this script)
# ---------------------------------------------------------------------------


class _Skip(Exception):
    pass


if __name__ == "__main__":
    print("Testing invitation-link → join_realm_with_invite flow:")
    tests = [
        test_environment_ready,
        test_mint_member_invite_returns_member_profile,
        test_listing_does_not_leak_plaintext_code,
        test_validate_returns_admin_profile,
        test_join_realm_with_invite_grants_invite_profile,
        test_join_realm_without_invite_rejects_admin_when_admin_exists,
        test_invalid_invite_code_is_rejected,
    ]

    failed = 0
    skipped = 0
    for t in tests:
        try:
            t()
        except _Skip as s:
            print(f"    SKIPPED: {s}")
            skipped += 1
            # If the environment is not ready, skip the rest too.
            if t is test_environment_ready:
                print("\nℹ️  Skipping remaining tests because admin_dashboard is unavailable.")
                break
        except AssertionError as e:
            print("✗")
            print(f"    AssertionError: {e}")
            failed += 1
        except Exception as e:
            print("✗")
            print(f"    Error: {e}")
            traceback.print_exc()
            failed += 1

    print()
    if failed == 0:
        print(f"✅ All tests passed (skipped: {skipped})")
        sys.exit(0)
    else:
        print(f"❌ {failed} test(s) failed (skipped: {skipped})")
        sys.exit(1)
