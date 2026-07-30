"""Extensions must never take the caller's identity from their call args.

An extension endpoint is reached through ``extension_sync_call``, which
authenticates the caller and gates the *operation*
(``core/extension_access.py``). What that gate cannot check is *which rows*
the call then touches. When an extension answers "who is asking?" by reading
``user_id`` out of its own JSON args, every per-record check built on top of
that answer is decided by the client:

    user_id = params.get("user_id")                 # client says who they are
    is_owner = zone.user and zone.user.id == user_id
    if not is_owner and not _caller_is_admin():     # ... trivially satisfied
        deny

That shipped in ``zone_selector`` (delete/modify another member's zone),
``member_dashboard`` (read another member's invoices and payment accounts),
``notifications`` and ``justice_litigation``. All four had ``ic.caller()``
available in the same file; they simply did not use it for the check.

This test is the ratchet. Identity comes from ``ic.caller()``; args carry
*what* to act on, never *who* is acting.
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
EXTENSIONS_ROOT = REPO_ROOT / "extensions" / "extensions"

# Argument keys that name a principal or user. Reading one of these out of
# call args and using it as the actor is the bug this test prevents.
IDENTITY_KEYS = frozenset({
    "user_id",
    "caller",
    "caller_principal",
    "principal",
    "user_principal",
    "owner_id",
    "requester",
    "requester_id",
})

# (extension, function, key) -> why reading this from args is legitimate.
#
# The bar: the value must NOT be what an authorization decision for the
# *caller* is made against. A lookup argument behind an operation the caller
# already had to hold is fine; an ownership comparison is not.
ALLOWED = {
    ("vault", "lookup_balance", "principal"): (
        "Ledger lookup tool gated on treasury.view, which is not in the member "
        "baseline. The principal selects which subaccount to query; it is not "
        "a claim about who the caller is."
    ),
    # --- Target selectors: "which user to act ON", behind an operation the
    # caller must already hold. The caller's own identity still comes from
    # ic.caller() inside _check_access; these only choose the subject.
    ("access_manager", "_manage_department_member", "user_principal"): (
        "Member being added/removed. Authorization is _can_manage_dept() "
        "against _get_caller_user(), so the subject and the actor are "
        "separate values; policy-gated like position actions."
    ),
    ("access_manager", "grant_extension_to_user", "user_principal"): (
        "Grant target. Gated on role.assign with governed=true, so it is also "
        "subject to org policy / proposal replay."
    ),
    ("access_manager", "revoke_extension_from_user", "user_principal"): (
        "Revoke target. Gated on role.revoke with governed=true."
    ),
    ("access_manager", "get_user_access_summary", "user_principal"): (
        "Subject of a role/permission summary. Gated on realm.data_view; role "
        "assignments are realm governance data rather than member-private data."
    ),
    # extensions_manager's two entries are gone: grant and revoke now name
    # their target through the bridge, and the host checks role.assign /
    # role.revoke against the caller before honouring it.
    # member_manager's four entries are gone: it now addresses members through
    # the bridge's ``subject`` argument, and the host checks ``user.view``
    # before honouring it. The exemption is unnecessary once the gate moves
    # out of extension code, which is the outcome this list exists to drive.
    ("notifications", "create_notification", "user_id"): (
        "Recipient of the notification. Gated on notification.send, which is "
        "not in the member baseline."
    ),
    ("role_manager", "generate_registration_url", "user_id"): (
        "User the invite is minted for. Gated on invite.manage."
    ),
    ("role_manager", "get_registration_codes", "user_id"): (
        "Filter over issued invites. Gated on invite.manage."
    ),
    ("justice_litigation", "get_cases", "user_id"): (
        "Narrowing filter only. _can_view_case(caller) is applied after these "
        "filters, so this can shrink the result set but never widen it."
    ),
}


def _entry_files():
    if not EXTENSIONS_ROOT.is_dir():
        return []
    return sorted(EXTENSIONS_ROOT.glob("*/backend/**/*.py"))


def _args_derived_names(func):
    """Local names holding the decoded call args, e.g. ``params``/``args_dict``.

    Anything parsed out of the function's own ``args`` parameter is client
    input. Tracking the source this way keeps the check on *input* and off
    identically-named keys in host data or response payloads.
    """
    params = {a.arg for a in func.args.args} | {a.arg for a in func.args.kwonlyargs}
    # Helpers that receive the already-decoded dict are just as exposed as the
    # entry point that parsed it, so treat those parameter names as input too.
    derived = params & {"params", "args_dict"}
    if "args" not in params:
        return derived

    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue
        reads_args = any(
            isinstance(n, ast.Name) and n.id in ("args", *derived)
            for n in ast.walk(node.value)
        )
        if reads_args:
            derived.update(
                t.id for t in node.targets if isinstance(t, ast.Name)
            )
    return derived


def _identity_key(node, sources):
    """The identity key this node reads out of client input, if any.

    Matches ``params.get("user_id")`` and ``params["user_id"]`` in a *load*
    context, where ``params`` came from the call args.
    """
    if isinstance(node, ast.Call):
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "get"
            and isinstance(func.value, ast.Name)
            and func.value.id in sources
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value in IDENTITY_KEYS
        ):
            return node.args[0].value
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.ctx, ast.Load)
        and isinstance(node.value, ast.Name)
        and node.value.id in sources
        and isinstance(node.slice, ast.Constant)
        and node.slice.value in IDENTITY_KEYS
    ):
        return node.slice.value
    return None


def _violations(path):
    """(function, key, line) for every identity-from-args read in the file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        sources = _args_derived_names(func)
        if not sources:
            continue
        for node in ast.walk(func):
            key = _identity_key(node, sources)
            if key:
                found.append((func.name, key, node.lineno))
    return found


@pytest.mark.parametrize(
    "entry", _entry_files(), ids=lambda p: f"{p.parts[-3]}/{p.name}"
)
def test_extension_does_not_take_identity_from_args(entry):
    extension = entry.parts[-3]
    offenders = [
        (fn, key, line)
        for fn, key, line in _violations(entry)
        if (extension, fn, key) not in ALLOWED
    ]
    assert not offenders, (
        f"{extension} reads caller identity from call args at "
        + ", ".join(f"{fn}() line {line} -> '{key}'" for fn, key, line in offenders)
        + ". Use ic.caller() instead; args say what to act on, not who is acting. "
        "If this really is a lookup argument rather than an identity claim, add "
        "it to ALLOWED with the reason."
    )


def test_allowlist_entries_still_exist():
    """A stale exemption is an exemption nobody is checking."""
    live = set()
    for entry in _entry_files():
        extension = entry.parts[-3]
        for fn, key, _line in _violations(entry):
            live.add((extension, fn, key))

    stale = sorted(set(ALLOWED) - live)
    assert not stale, (
        f"ALLOWED exemptions no longer present in the source: {stale}. "
        "Remove them so the list reflects what is actually exempt."
    )
