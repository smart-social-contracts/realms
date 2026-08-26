#!/usr/bin/env python3
"""Live __shell__ / Candid permission-gate E2E for realmtest6 (realms#313).

On-demand only. Not a GitHub Actions job. Do not point CI at this realm.

This is the live counterpart of ``tests/backend/test_repl_ui_parity.py`` and
``docs/issues/repl-ui-parity-spec.md``. It clicks the same host surface from
``__shell__`` (``api.call`` / ``ext.call``) that the SPA hits via Candid.

How to run (from the realms repo root):

    python3 scripts/shell_e2e_realmtest6.py
    python3 scripts/shell_e2e_realmtest6.py --canister wtn66-6qaaa-aaaae-agz6a-cai --network test

Requires ``icp`` (>= 1.3.0; ``npm i -g @icp-sdk/icp-cli``). No dfx. No
controller / deployer PEM.

Identities (hard rule):
  NEVER ``deployer`` / ``my_dev_identity_1``. Controllers bypass ``@require``.
  This script derives the test-mode II-bypass Ed25519 keys from
  ``src/realm_frontend/src/lib/test-identities.js``
  (roster: ``config/deterministic-test-identity-principals.json``).

  --member-index 0  → 2eqns-rmzes-…  Identity 1 (Creator). Founder on
      realmtest6; a *member*, the same principal the browser uses with
      ``?skip_ii=true``. Has ``shell.execute`` because the founder is an
      admin (``Operations.ALL``), not because SHELL_EXECUTE is a superuser
      bit on verbs inside the REPL.

  --nonadmin-index 1 → z32zf-ic72u-…  Identity 2. Used for the deny case.
      Stock MEMBER does not include ``shell.execute``; if this principal
      cannot enter ``__shell__``, that deny *is* the Candid deny for
      ``__shell__`` (documented, not papered over). The script does not
      grant permissions or mutate membership.

Read-only: no leftover-free, no deploy, no sandbox_config writes, no
``in_process`` / ``sandbox_exemptions`` changes.

Cases (locked 2026-08-25 for #313):
  1. Member ``api.call`` matches the same Candid method (allow / result shape).
  2. Non-admin gets the same no as Candid (same exception class / denial).
  3. ``ext.call`` matches ``extension_sync_call`` / ``gate_extension_call``
     on a sandboxed extension (default: department_docs). Fail if the
     resolved mode is ``in_process``.

Exit non-zero on any FAIL.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
ROSTER_PATH = REPO_ROOT / "config" / "deterministic-test-identity-principals.json"

DEFAULT_CANISTER = "wtn66-6qaaa-aaaae-agz6a-cai"
DEFAULT_FRONTEND = "wumyk-tiaaa-aaaae-agz6q-cai"
DEFAULT_PORTAL = "https://test.gos.earth/r/realmtest6"
DEFAULT_MEMBER_INDEX = 0
DEFAULT_NONADMIN_INDEX = 1
DEFAULT_EXTENSION = "department_docs"
DEFAULT_EXT_FN = "list_departments"
DEFAULT_EXT_ARGS: dict[str, Any] = {}

# dfx "test" / "staging" / "demo" / "ic" all talk to the same public replica.
REPLICA_URL = "https://icp0.io"
ROOT_KEY = "mainnet"

FORBIDDEN_IDENTITY_NAMES = frozenset(
    {"deployer", "my_dev_identity_1", "default"}
)
CONTROLLER_PRINCIPALS = frozenset(
    {
        "ah6ac-cc73l-bb2zc-ni7bh-jov4q-roeyj-6k2ob-mkg5j-pequi-vuaa6-2ae",
    }
)

IDENTITY_PREFIX = "realms-e2e-ii"
ADMIN_DENY_METHOD = "crypto_get_envelopes"
ADMIN_DENY_ARG = "e2e-no-such-scope"
ADMIN_DENY_OP = "realm.admin"
SHELL_OP = "shell.execute"
MEMBER_ALLOW_METHOD = "get_my_principal"

E2E_JSON_MARK = "E2E_JSON:"
E2E_ERR_MARK = "E2E_ERROR:"

PASS_N = 0
FAIL_N = 0


def info(msg: str) -> None:
    print(msg)


def pass_(name: str, detail: str = "") -> None:
    global PASS_N
    PASS_N += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  PASS  {name}{suffix}")


def fail_(name: str, detail: str) -> None:
    global FAIL_N
    FAIL_N += 1
    print(f"  FAIL  {name} — {detail}")


# ---------------------------------------------------------------------------
# II-bypass identities
# ---------------------------------------------------------------------------


def load_roster() -> dict[int, dict[str, Any]]:
    data = json.loads(ROSTER_PATH.read_text())
    return {int(row["index"]): row for row in data["identities"]}


def test_identity_seed(index: int) -> bytes:
    """Same 32-byte seed as ``testIdentitySeed`` in test-identities.js."""
    if index < 0 or index > 0xFFFFFFFF:
        raise ValueError(f"identity index out of range: {index}")
    seed = bytearray(32)
    seed[0] = 0xED
    seed[1] = 0x57
    seed[2] = index & 0xFF
    seed[3] = (index >> 8) & 0xFF
    seed[4] = (index >> 16) & 0xFF
    seed[5] = (index >> 24) & 0xFF
    return bytes(seed)


def ed25519_seed_to_pkcs8_pem(seed: bytes) -> str:
    """PKCS#8 PEM for an Ed25519 seed (RFC 8410). icp ``--assert-key-type ed25519``."""
    if len(seed) != 32:
        raise ValueError("Ed25519 seed must be 32 bytes")
    der = bytes.fromhex("302e020100300506032b657004220420") + seed
    b64 = base64.b64encode(der).decode("ascii")
    lines = [b64[i : i + 64] for i in range(0, len(b64), 64)]
    return "-----BEGIN PRIVATE KEY-----\n" + "\n".join(lines) + "\n-----END PRIVATE KEY-----\n"


def identity_name(index: int) -> str:
    return f"{IDENTITY_PREFIX}-{index}"


# ---------------------------------------------------------------------------
# icp
# ---------------------------------------------------------------------------


def resolve_network(network: str) -> tuple[str, str]:
    name = (network or "test").strip()
    if name.startswith("http://") or name.startswith("https://"):
        return name, ROOT_KEY
    aliases = {"test", "staging", "demo", "ic", "mainnet"}
    if name in aliases:
        return REPLICA_URL, ROOT_KEY
    raise SystemExit(
        f"Unknown --network {network!r}. Use test/staging/demo/ic or a replica URL."
    )


def find_icp() -> str:
    path = shutil.which("icp")
    if not path:
        raise SystemExit(
            "icp not found on PATH. Install with: npm i -g @icp-sdk/icp-cli"
        )
    return path


def run_icp(
    icp: str,
    args: list[str],
    *,
    check: bool = False,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("NO_COLOR", None)
    env.pop("FORCE_COLOR", None)
    env["TERM"] = env.get("TERM") or "xterm-256color"
    cmd = [icp, *args]
    proc = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        timeout=timeout,
        env=env,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"icp {' '.join(args)} failed ({proc.returncode}):\n"
            f"{proc.stdout}\n{proc.stderr}"
        )
    return proc


def import_ii_identity(
    icp: str, index: int, expected_principal: str, pem_dir: Path
) -> str:
    name = identity_name(index)
    if name in FORBIDDEN_IDENTITY_NAMES:
        raise SystemExit(f"refusing to use forbidden identity name {name!r}")

    pem_path = pem_dir / f"{name}.pem"
    pem_path.write_text(ed25519_seed_to_pkcs8_pem(test_identity_seed(index)))
    os.chmod(pem_path, 0o600)

    # Re-import so a leftover identity with the same name cannot be the wrong key.
    run_icp(icp, ["identity", "delete", name, "--yes"], check=False)
    run_icp(icp, ["identity", "delete", name], check=False)
    proc = run_icp(
        icp,
        [
            "identity",
            "import",
            name,
            "--from-pem",
            str(pem_path),
            "--storage",
            "plaintext",
            "--assert-key-type",
            "ed25519",
        ],
    )
    if proc.returncode != 0:
        # Older icp-cli: positional PEM + -f
        proc = run_icp(
            icp,
            [
                "identity",
                "import",
                name,
                str(pem_path),
                "--storage",
                "plaintext",
                "-f",
            ],
        )
    if proc.returncode != 0:
        raise SystemExit(
            f"icp identity import {name} failed:\n{proc.stdout}\n{proc.stderr}"
        )

    got = principal_of(icp, name)
    if got != expected_principal:
        raise SystemExit(
            f"Identity {index} principal {got} does not match roster {expected_principal}"
        )
    if got in CONTROLLER_PRINCIPALS:
        raise SystemExit(
            f"Identity {index} resolved to controller principal {got}; refusing to run"
        )
    return name


def principal_of(icp: str, name: str) -> str:
    proc = run_icp(icp, ["identity", "principal", "--identity", name], check=True)
    text = (proc.stdout or "").strip().splitlines()
    if not text:
        raise RuntimeError(f"icp identity principal --identity {name} printed nothing")
    return text[-1].strip()


def canister_call(
    icp: str,
    canister: str,
    method: str,
    candid_args: str,
    identity: str,
    replica: str,
    root_key: str,
    *,
    query: bool = False,
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    if identity in FORBIDDEN_IDENTITY_NAMES:
        raise SystemExit(f"refusing canister call as {identity!r}")
    args = [
        "canister",
        "call",
        canister,
        method,
        candid_args,
        "-n",
        replica,
        "--root-key",
        root_key,
        "--identity",
        identity,
    ]
    if query:
        args.append("--query")
    return run_icp(icp, args, timeout=timeout)


# ---------------------------------------------------------------------------
# Candid / denial parsing
# ---------------------------------------------------------------------------


def combined_output(proc: subprocess.CompletedProcess[str]) -> str:
    return f"{proc.stdout or ''}\n{proc.stderr or ''}"


def unescape_candid_text(s: str) -> str:
    out = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt == "t":
                out.append("\t")
            elif nxt in '"\\':
                out.append(nxt)
            else:
                out.append(nxt)
            i += 2
            continue
        out.append(s[i])
        i += 1
    return "".join(out)


def extract_candid_text(blob: str) -> Optional[str]:
    """Best-effort unwrap of a Candid ``( "…" )`` / ``"…"`` result."""
    m = re.search(r'\(\s*"(.*)"\s*\)\s*$', blob, re.S)
    if m:
        return unescape_candid_text(m.group(1))
    m = re.search(r'^\s*"(.*)"\s*$', blob.strip(), re.S)
    if m:
        return unescape_candid_text(m.group(1))
    # Some icp versions print the text without wrapping parens on the last line.
    lines = [ln for ln in blob.splitlines() if ln.strip()]
    if lines and lines[-1].startswith('"') and lines[-1].endswith('"'):
        return unescape_candid_text(lines[-1][1:-1])
    return None


def _read_candid_string(blob: str, start: int) -> Optional[str]:
    """Read a Candid ``"…"`` string starting at ``start`` (the opening quote)."""
    if start >= len(blob) or blob[start] != '"':
        return None
    i = start + 1
    out = []
    while i < len(blob):
        ch = blob[i]
        if ch == "\\" and i + 1 < len(blob):
            nxt = blob[i + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt == "t":
                out.append("\t")
            elif nxt in '"\\':
                out.append(nxt)
            else:
                out.append(nxt)
            i += 2
            continue
        if ch == '"':
            return "".join(out)
        out.append(ch)
        i += 1
    return None


def extract_extension_record(blob: str) -> Optional[dict[str, Any]]:
    """Parse ``record { success = …; response = "…" }`` from Candid text."""
    success_m = re.search(r"\bsuccess\s*=\s*(true|false)\b", blob)
    if not success_m:
        return None
    resp_key = re.search(r"\bresponse\s*=\s*", blob)
    response = ""
    if resp_key:
        q = blob.find('"', resp_key.end())
        parsed = _read_candid_string(blob, q) if q >= 0 else None
        if parsed is not None:
            response = parsed
    return {"success": success_m.group(1) == "true", "response": response}


def parse_json_loose(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Shell may print a Python dict.
    if (text.startswith("{") and text.endswith("}")) or (
        text.startswith("[") and text.endswith("]")
    ):
        try:
            return json.loads(text.replace("True", "true").replace("False", "false").replace("None", "null"))
        except json.JSONDecodeError:
            return None
    return None


def extract_marked_json(text: str, mark: str = E2E_JSON_MARK) -> Any:
    for line in (text or "").splitlines():
        if mark in line:
            payload = line.split(mark, 1)[1].strip()
            return parse_json_loose(payload)
    if mark in (text or ""):
        payload = text.split(mark, 1)[1].strip()
        return parse_json_loose(payload.splitlines()[0] if payload else "")
    return None


def denial_info(text: str) -> dict[str, Any]:
    """Classify a Candid reject or REPL traceback as an AccessDenied-shaped no."""
    blob = text or ""
    op = None
    m = re.search(r"lacks permission '([^']+)'", blob)
    if m:
        op = m.group(1)
    if not op:
        m = re.search(r"denied_operation['\"]?\s*[:=]\s*['\"]([^'\"]+)", blob)
        if m:
            op = m.group(1)
    is_access = (
        "AccessDenied" in blob
        or "Access denied" in blob
        or "access denied" in blob.lower()
    )
    is_perm = "PermissionError" in blob or is_access
    return {
        "access_denied": is_access,
        "permission_error": is_perm,
        "operation": op,
        "text": blob,
    }


def same_denial(a: dict[str, Any], b: dict[str, Any]) -> tuple[bool, str]:
    """Same exception class (AccessDenied / PermissionError) and same op if both known."""
    if not (a["permission_error"] and b["permission_error"]):
        return False, "one side is not a PermissionError/AccessDenied"
    if a["access_denied"] != b["access_denied"] and not (
        a["permission_error"] and b["permission_error"]
    ):
        return False, "exception class mismatch"
    if a["operation"] and b["operation"] and a["operation"] != b["operation"]:
        return False, f"denied_operation {a['operation']!r} vs {b['operation']!r}"
    return True, (
        f"AccessDenied/PermissionError"
        + (f" ({a['operation'] or b['operation']})" if (a["operation"] or b["operation"]) else "")
    )


def shape_of(value: Any) -> Any:
    """Compare Candid vs REPL on structure, not pretty-print."""
    if isinstance(value, dict):
        return {k: shape_of(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        return [shape_of(v) for v in value]
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    return value


def normalize_ext_result(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        success = value.get("success")
        response = value.get("response", value)
        if isinstance(response, str):
            parsed = parse_json_loose(response)
            response_obj = parsed if parsed is not None else response
        else:
            response_obj = response
        return {"success": bool(success) if success is not None else None, "response": response_obj}
    if isinstance(value, str):
        parsed = parse_json_loose(value)
        if isinstance(parsed, dict):
            return normalize_ext_result(parsed)
    return {"success": None, "response": value}


# ---------------------------------------------------------------------------
# Shell snippets (print a marker; never mutate)
# ---------------------------------------------------------------------------


def shell_eval_snippet(expr: str) -> str:
    """Run ``expr`` inside __shell__ and print JSON / error markers."""
    return (
        "import json\n"
        "def _dump(x):\n"
        "    try:\n"
        "        print(%r + json.dumps(x, default=str))\n"
        "    except Exception:\n"
        "        print(%r + json.dumps({'repr': repr(x)}))\n"
        "try:\n"
        f"    _dump({expr})\n"
        "except Exception as e:\n"
        "    print(%r + type(e).__name__ + ':' + str(e))\n"
        "    raise\n"
        % (E2E_JSON_MARK, E2E_JSON_MARK, E2E_ERR_MARK)
    )


def candid_text_arg(code: str) -> str:
    escaped = code.replace("\\", "\\\\").replace('"', '\\"')
    return f'("{escaped}")'


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------


def call_as(
    icp: str,
    canister: str,
    method: str,
    candid_args: str,
    identity: str,
    replica: str,
    root_key: str,
    *,
    query: bool = False,
) -> subprocess.CompletedProcess[str]:
    return canister_call(
        icp, canister, method, candid_args, identity, replica, root_key, query=query
    )


def probe_user(icp, canister, identity, replica, root_key) -> dict[str, Any]:
    """Read-only: principal + get_my_user_status + can they open __shell__?"""
    principal = principal_of(icp, identity)
    status_proc = call_as(
        icp,
        canister,
        "get_my_user_status",
        "()",
        identity,
        replica,
        root_key,
        query=True,
    )
    status_out = combined_output(status_proc)
    profiles = re.findall(r'vec\s*\{([^}]*)\}', status_out)
    profile_names = []
    if profiles:
        profile_names = re.findall(r'"([^"]+)"', profiles[0])
    registered = status_proc.returncode == 0 and "success = true" in status_out.replace(
        "\n", " "
    )

    shell_proc = call_as(
        icp,
        canister,
        "__shell__",
        candid_text_arg('print("E2E_SHELL_OK")'),
        identity,
        replica,
        root_key,
    )
    shell_out = combined_output(shell_proc)
    can_shell = shell_proc.returncode == 0 and "E2E_SHELL_OK" in shell_out
    shell_deny = denial_info(shell_out) if not can_shell else None
    return {
        "principal": principal,
        "registered": registered,
        "profiles": profile_names,
        "can_shell": can_shell,
        "shell_deny": shell_deny,
        "shell_out": shell_out,
        "status_out": status_out,
        "looks_admin": any(p in {"admin", "operator"} for p in profile_names),
    }


def case1_member_api_call_matches_candid(
    icp, canister, member_id, replica, root_key
) -> None:
    name = "1. member api.call matches Candid get_my_principal"
    candid = call_as(
        icp,
        canister,
        MEMBER_ALLOW_METHOD,
        "()",
        member_id,
        replica,
        root_key,
        query=True,
    )
    if candid.returncode != 0:
        fail_(name, f"Candid {MEMBER_ALLOW_METHOD} rejected:\n{combined_output(candid)}")
        return
    candid_text = extract_candid_text(candid.stdout or "") or (candid.stdout or "").strip()
    candid_principal = candid_text.strip().strip('"')

    shell = call_as(
        icp,
        canister,
        "__shell__",
        candid_text_arg(shell_eval_snippet("api.call('get_my_principal')")),
        member_id,
        replica,
        root_key,
    )
    if shell.returncode != 0:
        fail_(name, f"__shell__ rejected (member should have shell.execute):\n{combined_output(shell)}")
        return
    shell_body = extract_candid_text(combined_output(shell)) or combined_output(shell)
    marked = extract_marked_json(shell_body)
    err = None
    for line in shell_body.splitlines():
        if E2E_ERR_MARK in line:
            err = line.split(E2E_ERR_MARK, 1)[1].strip()
    if err:
        fail_(name, f"api.call raised {err}")
        return
    via_shell = marked if isinstance(marked, str) else (
        marked.get("repr") if isinstance(marked, dict) else marked
    )
    if via_shell is None:
        # Last resort: the REPL printed the principal somewhere.
        via_shell = shell_body
    if candid_principal not in str(via_shell) and str(via_shell) != candid_principal:
        fail_(
            name,
            f"result shape mismatch: Candid={candid_principal!r} shell={via_shell!r}",
        )
        return
    if candid_principal != principal_of(icp, member_id):
        fail_(name, f"Candid principal {candid_principal} != identity {principal_of(icp, member_id)}")
        return
    pass_(name, f"both returned {candid_principal}")


def case2_nonadmin_same_no(
    icp, canister, nonadmin_id, nonadmin_probe, replica, root_key
) -> None:
    """Non-admin deny matches Candid. SHELL_EXECUTE is not a verb bypass."""
    name = "2. non-admin same no as Candid"

    candid_admin = call_as(
        icp,
        canister,
        ADMIN_DENY_METHOD,
        candid_text_arg(ADMIN_DENY_ARG),
        nonadmin_id,
        replica,
        root_key,
        query=True,
    )
    candid_deny = denial_info(combined_output(candid_admin))
    if candid_admin.returncode == 0 and not candid_deny["permission_error"]:
        # Query returned a value — unexpected allow. Do not continue (would
        # still be read-only, but the case is about a no).
        fail_(
            name,
            f"Candid {ADMIN_DENY_METHOD} allowed for non-admin "
            f"(profiles={nonadmin_probe.get('profiles')}):\n{combined_output(candid_admin)}",
        )
        return
    if not candid_deny["permission_error"]:
        fail_(
            name,
            f"Candid {ADMIN_DENY_METHOD} did not look like AccessDenied:\n"
            f"{combined_output(candid_admin)}",
        )
        return

    if not nonadmin_probe["can_shell"]:
        # Documented path: stock members cannot open the REPL. The deny of
        # __shell__ itself must match Candid (it *is* the Candid method).
        shell_deny = nonadmin_probe["shell_deny"] or denial_info(
            nonadmin_probe["shell_out"]
        )
        if not shell_deny["permission_error"]:
            fail_(
                name,
                "non-admin cannot enter __shell__, but the reject was not "
                f"AccessDenied/PermissionError:\n{nonadmin_probe['shell_out']}",
            )
            return
        if shell_deny["operation"] and shell_deny["operation"] != SHELL_OP:
            fail_(
                name,
                f"__shell__ denied as {shell_deny['operation']!r}, expected {SHELL_OP!r}",
            )
            return
        info(
            "    note: non-admin cannot enter __shell__ — that deny is the Candid "
            f"__shell__ @{SHELL_OP} gate (SHELL_EXECUTE is not granted; not a "
            "superuser bit). Candid admin verb deny is separate:"
        )
        info(
            f"      __shell__ → AccessDenied ({shell_deny['operation'] or SHELL_OP})"
        )
        info(
            f"      {ADMIN_DENY_METHOD} → AccessDenied "
            f"({candid_deny['operation'] or ADMIN_DENY_OP})"
        )
        if candid_deny["operation"] and candid_deny["operation"] != ADMIN_DENY_OP:
            fail_(
                name,
                f"admin Candid deny op {candid_deny['operation']!r} != {ADMIN_DENY_OP!r}",
            )
            return
        pass_(
            name,
            f"__shell__ AccessDenied({SHELL_OP}); "
            f"{ADMIN_DENY_METHOD} AccessDenied({candid_deny['operation'] or ADMIN_DENY_OP})",
        )
        return

    # They can open the REPL. SHELL_EXECUTE must not succeed the admin verb.
    if nonadmin_probe.get("looks_admin"):
        fail_(
            name,
            "chosen --nonadmin-index has an admin/operator profile on this realm; "
            "pick another index (do not grant permissions to make this green)",
        )
        return

    shell = call_as(
        icp,
        canister,
        "__shell__",
        candid_text_arg(
            shell_eval_snippet(f"api.call({ADMIN_DENY_METHOD!r}, {ADMIN_DENY_ARG!r})")
        ),
        nonadmin_id,
        replica,
        root_key,
    )
    shell_out = combined_output(shell)
    shell_body = extract_candid_text(shell_out) or shell_out
    # Either the canister rejected (shouldn't — they have SHELL_EXECUTE) or
    # api.call raised AccessDenied inside the REPL (expected).
    if shell.returncode != 0:
        fail_(
            name,
            f"__shell__ itself rejected even though probe said can_shell:\n{shell_out}",
        )
        return
    err_line = None
    for line in shell_body.splitlines():
        if E2E_ERR_MARK in line:
            err_line = line.split(E2E_ERR_MARK, 1)[1].strip()
    shell_deny = denial_info(err_line or shell_body)
    ok, why = same_denial(candid_deny, shell_deny)
    if not ok:
        fail_(
            name,
            f"{why}. Candid={candid_deny} shell={shell_deny}\n{shell_body}",
        )
        return
    if shell_deny["operation"] and shell_deny["operation"] != (
        candid_deny["operation"] or ADMIN_DENY_OP
    ):
        fail_(name, f"api.call op {shell_deny['operation']} != Candid {candid_deny['operation']}")
        return
    pass_(name, why)


def case3_ext_call_matches_sync_and_sandbox(
    icp,
    canister,
    member_id,
    replica,
    root_key,
    extension: str,
    ext_fn: str,
    ext_args: dict[str, Any],
) -> None:
    name_parity = f"3a. ext.call matches extension_sync_call ({extension}.{ext_fn})"
    name_sandbox = f"3b. {extension} sandbox still on (not in_process)"

    args_json = json.dumps(ext_args)
    candid_args = f'("{extension}", "{ext_fn}", {json.dumps(args_json)})'
    candid = call_as(
        icp,
        canister,
        "extension_sync_call",
        candid_args,
        member_id,
        replica,
        root_key,
    )
    if candid.returncode != 0:
        fail_(name_parity, f"Candid extension_sync_call rejected:\n{combined_output(candid)}")
        fail_(name_sandbox, "skipped; extension_sync_call did not run")
        return
    candid_rec = extract_extension_record(candid.stdout or combined_output(candid))
    if candid_rec is None:
        fail_(name_parity, f"could not parse ExtensionCallResponse:\n{candid.stdout}")
        fail_(name_sandbox, "skipped")
        return
    candid_norm = normalize_ext_result(candid_rec)

    expr = (
        f"ext.call({extension!r}, {ext_fn!r}, {ext_args!r})"
    )
    shell = call_as(
        icp,
        canister,
        "__shell__",
        candid_text_arg(shell_eval_snippet(expr)),
        member_id,
        replica,
        root_key,
    )
    if shell.returncode != 0:
        fail_(name_parity, f"__shell__ ext.call rejected:\n{combined_output(shell)}")
        fail_(name_sandbox, "skipped")
        return
    shell_body = extract_candid_text(combined_output(shell)) or combined_output(shell)
    err = None
    for line in shell_body.splitlines():
        if E2E_ERR_MARK in line:
            err = line.split(E2E_ERR_MARK, 1)[1].strip()
    if err:
        # A PermissionError from ext.call should still match the Candid
        # *result* if the host wraps it; if Candid returned a payload
        # instead of raising, this is a mismatch.
        if candid_norm.get("success") is False:
            shell_deny = denial_info(err)
            candid_blob = json.dumps(candid_norm, default=str)
            if shell_deny["permission_error"] and (
                "permission_denied" in candid_blob
                or "Access denied" in candid_blob
                or "permission" in candid_blob
            ):
                pass_(name_parity, f"both denied ({err})")
            else:
                fail_(name_parity, f"ext.call raised {err}; Candid={candid_norm}")
        else:
            fail_(name_parity, f"ext.call raised {err}; Candid allowed {candid_norm}")
    else:
        marked = extract_marked_json(shell_body)
        shell_norm = normalize_ext_result(marked)
        if shape_of(candid_norm) != shape_of(shell_norm):
            # Allow success+response string vs already-parsed JSON.
            c_resp = candid_norm.get("response")
            s_resp = shell_norm.get("response")
            if candid_norm.get("success") == shell_norm.get("success") and shape_of(
                c_resp
            ) == shape_of(s_resp):
                pass_(name_parity, f"success={candid_norm.get('success')}")
            else:
                fail_(
                    name_parity,
                    f"shape mismatch\n  Candid={candid_norm}\n  shell={shell_norm}",
                )
        else:
            pass_(name_parity, f"success={candid_norm.get('success')}")

    # Sandbox mode — read-only get_sandbox_config (realm.configure).
    cfg = call_as(
        icp,
        canister,
        "get_sandbox_config",
        "()",
        member_id,
        replica,
        root_key,
        query=True,
    )
    cfg_text = extract_candid_text(combined_output(cfg)) or combined_output(cfg)
    cfg_json = parse_json_loose(cfg_text)
    if cfg_json is None:
        # Candid may leave the JSON inside a quoted blob with extra wrapping.
        m = re.search(r'\{.*\}', cfg_text, re.S)
        if m:
            cfg_json = parse_json_loose(m.group(0))
    if not isinstance(cfg_json, dict) or not cfg_json.get("success"):
        # Try via api.call in case the query decode was ugly but the member
        # can configure.
        shell_cfg = call_as(
            icp,
            canister,
            "__shell__",
            candid_text_arg(shell_eval_snippet("api.call('get_sandbox_config')")),
            member_id,
            replica,
            root_key,
        )
        body = extract_candid_text(combined_output(shell_cfg)) or combined_output(shell_cfg)
        marked = extract_marked_json(body)
        if isinstance(marked, str):
            cfg_json = parse_json_loose(marked)
        elif isinstance(marked, dict):
            cfg_json = marked if "data" in marked or "success" in marked else None
            if cfg_json is None:
                cfg_json = parse_json_loose(json.dumps(marked))

    if not isinstance(cfg_json, dict):
        fail_(name_sandbox, f"could not read get_sandbox_config:\n{cfg_text[:800]}")
        return
    if cfg_json.get("success") is False:
        fail_(
            name_sandbox,
            "get_sandbox_config denied — cannot prove sandbox is on without "
            f"mutating membership. payload={cfg_json}",
        )
        return

    data = cfg_json.get("data") or {}
    extensions = data.get("extensions") or []
    resolved = data.get("resolved_modes") or {}
    row = next((e for e in extensions if e.get("id") == extension), None)
    mode = None
    reason = ""
    if row:
        mode = row.get("resolved_mode")
        reason = row.get("reason") or ""
    elif extension in resolved:
        raw = resolved[extension]
        mode = str(raw).split()[0]
        reason = str(raw)
    if mode is None:
        fail_(
            name_sandbox,
            f"{extension} not in sandbox status (is it installed?). "
            f"resolved_modes={resolved}",
        )
        return
    if mode == "in_process":
        fail_(
            name_sandbox,
            f"resolved_mode=in_process ({reason}). Sandbox must still be on.",
        )
        return
    if mode != "sandbox":
        fail_(name_sandbox, f"resolved_mode={mode!r} reason={reason!r}")
        return
    pass_(name_sandbox, f"resolved_mode=sandbox ({reason or 'default'})")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__.split("How to run")[0].strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--canister", default=DEFAULT_CANISTER, help="realm backend canister id")
    p.add_argument(
        "--frontend",
        default=DEFAULT_FRONTEND,
        help="realm frontend canister id (printed only)",
    )
    p.add_argument(
        "--network",
        default="test",
        help="dfx-style name (test/staging/demo/ic) or replica URL",
    )
    p.add_argument("--member-index", type=int, default=DEFAULT_MEMBER_INDEX)
    p.add_argument("--nonadmin-index", type=int, default=DEFAULT_NONADMIN_INDEX)
    p.add_argument("--extension", default=DEFAULT_EXTENSION)
    p.add_argument("--ext-fn", default=DEFAULT_EXT_FN)
    p.add_argument(
        "--scan-shell",
        action="store_true",
        help="probe indices 0–9 for shell.execute (read-only __shell__ print)",
    )
    p.add_argument(
        "--self-check",
        action="store_true",
        help="import II-bypass identities and verify principals; do not call IC",
    )
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.member_index == args.nonadmin_index:
        raise SystemExit("--member-index and --nonadmin-index must differ")

    roster = load_roster()
    for idx, label in (
        (args.member_index, "member"),
        (args.nonadmin_index, "non-admin"),
    ):
        if idx not in roster:
            raise SystemExit(
                f"{label} index {idx} is not in {ROSTER_PATH} (known 0–9)"
            )

    icp = find_icp()
    replica, root_key = resolve_network(args.network)

    info("realmtest6 __shell__ permission E2E (realms#313)")
    info(f"  portal     {DEFAULT_PORTAL}")
    info(f"  backend    {args.canister}")
    info(f"  frontend   {args.frontend}")
    info(f"  network    {args.network} → {replica} ({root_key})")
    info(f"  icp        {icp}")
    info(
        "  identities II-bypass Ed25519 (NOT deployer / my_dev_identity_1)"
    )

    pem_dir = Path(tempfile.mkdtemp(prefix="realms-e2e-ii-"))
    try:
        member_row = roster[args.member_index]
        nonadmin_row = roster[args.nonadmin_index]
        member_id = import_ii_identity(
            icp, args.member_index, member_row["principal"], pem_dir
        )
        nonadmin_id = import_ii_identity(
            icp, args.nonadmin_index, nonadmin_row["principal"], pem_dir
        )
        info(
            f"  member     index {args.member_index} {member_row['label']} "
            f"{member_row['principal']}  (icp {member_id})"
        )
        info(
            f"  non-admin  index {args.nonadmin_index} {nonadmin_row['label']} "
            f"{nonadmin_row['principal']}  (icp {nonadmin_id})"
        )

        if args.self_check:
            pass_("self-check principals match roster", "no IC calls")
            print(f"\n{PASS_N} passed, {FAIL_N} failed")
            return 0 if FAIL_N == 0 else 1

        info("\nProbe (read-only)")
        member_probe = probe_user(icp, args.canister, member_id, replica, root_key)
        nonadmin_probe = probe_user(
            icp, args.canister, nonadmin_id, replica, root_key
        )
        info(
            f"  member    registered={member_probe['registered']} "
            f"profiles={member_probe['profiles'] or '—'} "
            f"shell.execute={member_probe['can_shell']}"
        )
        info(
            f"  non-admin registered={nonadmin_probe['registered']} "
            f"profiles={nonadmin_probe['profiles'] or '—'} "
            f"shell.execute={nonadmin_probe['can_shell']}"
        )
        if member_probe["principal"] in CONTROLLER_PRINCIPALS:
            raise SystemExit("member identity is a known controller; refusing")
        if not member_probe["can_shell"]:
            fail_(
                "probe: member can enter __shell__",
                "index 0 should have shell.execute on realmtest6 (founder). "
                f"{member_probe['shell_out'][:500]}",
            )
        else:
            pass_("probe: member can enter __shell__", member_probe["principal"])

        if args.scan_shell:
            info("\nScan indices 0–9 for shell.execute")
            for idx, row in sorted(roster.items()):
                name = import_ii_identity(icp, idx, row["principal"], pem_dir)
                probe = probe_user(icp, args.canister, name, replica, root_key)
                info(
                    f"  [{idx}] {row['principal'][:16]}… "
                    f"registered={probe['registered']} "
                    f"profiles={probe['profiles'] or '—'} "
                    f"shell={probe['can_shell']}"
                )

        info("\nCases")
        case1_member_api_call_matches_candid(
            icp, args.canister, member_id, replica, root_key
        )
        case2_nonadmin_same_no(
            icp, args.canister, nonadmin_id, nonadmin_probe, replica, root_key
        )
        case3_ext_call_matches_sync_and_sandbox(
            icp,
            args.canister,
            member_id,
            replica,
            root_key,
            args.extension,
            args.ext_fn,
            DEFAULT_EXT_ARGS,
        )
    finally:
        shutil.rmtree(pem_dir, ignore_errors=True)

    print(f"\n{PASS_N} passed, {FAIL_N} failed")
    return 0 if FAIL_N == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
