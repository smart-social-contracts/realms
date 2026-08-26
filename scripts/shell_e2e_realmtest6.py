#!/usr/bin/env python3
"""One-off read-only e2e checks for realmtest6 (Xiao).

Not CI. Not leftover-free. Does not deploy, grant permissions, or mutate state.

Run from the realms repo root:

    python3 scripts/shell_e2e_realmtest6.py
    python3 scripts/shell_e2e_realmtest6.py --backend <canister> --network test

Requires ``icp`` (>= 1.3.0): ``npm i -g @icp-sdk/icp-cli``

Default target
    backend   wtn66-6qaaa-aaaae-agz6a-cai   (realmtest6 on test)
    network   test  →  icp -n https://icp0.io --root-key mainnet
    candid    src/realm_backend/realm_backend.did

Identity (NEVER deployer / controller PEM)
    Test-mode II-bypass index 0 = Identity 1 (Creator).
    Seed: [0xED, 0x57, index as 4-byte little-endian, rest 0]
    Principal: 2eqns-rmzes-7npxw-dxpw2-qdy2s-mw6ix-svdo2-oya7o-a6ldc-sqgwh-bqe
    See src/realm_frontend/src/lib/test-identities.js

    The script writes a throwaway PKCS#8 PEM from that seed, imports it as a
    plaintext icp identity, confirms whoami is 2eqns-…, then deletes it.

Overrides
    --backend / REALMTEST6_BACKEND
    --network / REALMTEST6_NETWORK   (test|demo|staging|ic|URL)

Cases (same host verbs as the REPL product surface)
    1. api.call("get_sandbox_config")
       Candid get_sandbox_config — sandbox must be available.
    2. ext.call("department_docs", "list_documents", {})
       Candid extension_sync_call — same path as the Docs button.
       Sandbox must stay on (department_docs still sandbox).
    3. api.call("__shell__", "1")
       Enter __shell__ and run that expression — must deny.

Prints PASS/FAIL and raw icp output. Exits non-zero on any fail.
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

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BACKEND = "wtn66-6qaaa-aaaae-agz6a-cai"
DEFAULT_NETWORK = "test"
EXPECTED_PRINCIPAL = (
    "2eqns-rmzes-7npxw-dxpw2-qdy2s-mw6ix-svdo2-oya7o-a6ldc-sqgwh-bqe"
)
IDENTITY_NAME = "realmtest6-ii-bypass-0"
FORBIDDEN_IDENTITY_SUBSTR = ("deployer", "controller", "my_dev_identity")

# II-bypass seed: [0xED, 0x57, index₀..₃ LE, 0, …] — index 0.
TEST_IDENTITY_MAGIC = (0xED, 0x57)

# PKCS#8 prefix for a raw 32-byte Ed25519 seed (RFC 8410).
_ED25519_PKCS8_PREFIX = bytes.fromhex("302e020100300506032b657004220420")

_NAMED_NETWORKS = {
    "test": ("https://icp0.io", "mainnet"),
    "demo": ("https://icp0.io", "mainnet"),
    "staging": ("https://icp0.io", "mainnet"),
    "ic": ("https://icp0.io", "mainnet"),
}

_DENY_MARKERS = (
    "access denied",
    "not callable from the repl",
    "permissionerror",
    "lacks permission",
    "denied_operation",
)


def test_identity_seed(index: int = 0) -> bytes:
    seed = bytearray(32)
    seed[0], seed[1] = TEST_IDENTITY_MAGIC
    seed[2] = index & 0xFF
    seed[3] = (index >> 8) & 0xFF
    seed[4] = (index >> 16) & 0xFF
    seed[5] = (index >> 24) & 0xFF
    return bytes(seed)


def ed25519_seed_pem(seed: bytes) -> bytes:
    if len(seed) != 32:
        raise ValueError("Ed25519 seed must be 32 bytes")
    der = _ED25519_PKCS8_PREFIX + seed
    b64 = base64.b64encode(der).decode("ascii")
    lines = [b64[i : i + 64] for i in range(0, len(b64), 64)]
    body = "\n".join(lines)
    return f"-----BEGIN PRIVATE KEY-----\n{body}\n-----END PRIVATE KEY-----\n".encode()


def candid_text(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'("{escaped}")'


def parse_candid_text(raw: str) -> str:
    """Unwrap a Candid text reply: ( \"…\" )."""
    match = re.search(r'"((?:\\.|[^"\\])*)"', raw, re.DOTALL)
    if not match:
        return raw.strip()
    return bytes(match.group(1), "utf-8").decode("unicode_escape")


def parse_json_payload(raw: str):
    text = parse_candid_text(raw)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        return None


def parse_extension_record(raw: str) -> tuple[bool | None, str]:
    success = None
    match = re.search(r"success\s*=\s*(true|false)", raw, re.IGNORECASE)
    if match:
        success = match.group(1).lower() == "true"
    response = ""
    resp = re.search(r'response\s*=\s*"((?:\\.|[^"\\])*)"', raw, re.DOTALL)
    if resp:
        response = bytes(resp.group(1), "utf-8").decode("unicode_escape")
    return success, response


def sandbox_status(payload) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "unparseable"
    if payload.get("success") is False:
        return False, str(payload.get("error") or "success=false")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    available = bool(data.get("available"))
    modes = data.get("resolved_modes") or {}
    docs_mode = str(modes.get("department_docs") or "")
    return available, docs_mode


def looks_denied(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _DENY_MARKERS)


def looks_shell_eval_success(text: str) -> bool:
    stripped = parse_candid_text(text).strip()
    return stripped in {"1", "1\n"} or stripped == '"1"'


def icp_bin() -> str:
    found = shutil.which("icp")
    if found:
        return found
    extra = Path.home() / ".local/npm-global/bin/icp"
    if extra.is_file():
        return str(extra)
    sys.exit(
        "icp not found. Install with: npm i -g @icp-sdk/icp-cli  (need >= 1.3.0)"
    )


def network_flags(network: str) -> list[str]:
    key = network.strip()
    if key in _NAMED_NETWORKS:
        url, root = _NAMED_NETWORKS[key]
        return ["-n", url, "--root-key", root]
    if key.startswith("http://") or key.startswith("https://"):
        return ["-n", key, "--root-key", "mainnet"]
    sys.exit(f"Unknown network {network!r}. Use test|demo|staging|ic or a replica URL.")


def run_icp(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("DO_NOT_TRACK", "1")
    return subprocess.run(
        args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
    )


def refuse_controller_identity(name: str) -> None:
    lowered = name.lower()
    if any(part in lowered for part in FORBIDDEN_IDENTITY_SUBSTR):
        sys.exit(
            f"Refusing identity {name!r}: this script never uses deployer/controller PEM."
        )


def import_throwaway_identity(icp: str, pem_path: Path, name: str) -> str:
    refuse_controller_identity(name)
    existing = run_icp([icp, "identity", "list"])
    if name in existing.stdout:
        run_icp([icp, "identity", "delete", name])
    imported = run_icp(
        [
            icp,
            "identity",
            "import",
            name,
            "--from-pem",
            str(pem_path),
            "--storage",
            "plaintext",
            "--assert-key-type",
            "ed25519",
        ]
    )
    if imported.returncode != 0:
        sys.exit(f"icp identity import failed:\n{imported.stdout}")
    who = run_icp([icp, "identity", "principal", "--identity", name])
    principal = who.stdout.strip().splitlines()[-1].strip() if who.stdout.strip() else ""
    if who.returncode != 0 or principal != EXPECTED_PRINCIPAL:
        run_icp([icp, "identity", "delete", name])
        sys.exit(
            f"whoami mismatch: got {principal!r}, expected {EXPECTED_PRINCIPAL}\n"
            f"{who.stdout}"
        )
    return principal


def canister_call(
    icp: str,
    *,
    backend: str,
    network: str,
    identity: str,
    did: Path,
    method: str,
    args: str,
    query: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        icp,
        "canister",
        "call",
        backend,
        method,
        args,
        *network_flags(network),
        "--identity",
        identity,
        "--candid",
        str(did),
        "--output",
        "candid",
    ]
    if query:
        cmd.append("--query")
    return run_icp(cmd)


def report(name: str, ok: bool, raw: str) -> bool:
    status = "PASS" if ok else "FAIL"
    print(f"\n=== {status}  {name} ===")
    print(raw.rstrip() or "(no output)")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only realmtest6 sandbox / Docs / __shell__ deny checks."
    )
    parser.add_argument(
        "--backend",
        default=os.environ.get("REALMTEST6_BACKEND", DEFAULT_BACKEND),
        help=f"Realm backend canister (default {DEFAULT_BACKEND})",
    )
    parser.add_argument(
        "--network",
        default=os.environ.get("REALMTEST6_NETWORK", DEFAULT_NETWORK),
        help="Named network or replica URL (default test)",
    )
    args = parser.parse_args()

    refuse_controller_identity(IDENTITY_NAME)
    icp = icp_bin()
    did = REPO_ROOT / "src" / "realm_backend" / "realm_backend.did"
    if not did.is_file():
        sys.exit(f"Candid file not found: {did}")

    print("realmtest6 one-off e2e (read-only, not leftover-free, not CI)")
    print(f"backend  {args.backend}")
    print(f"network   {args.network}")
    print(f"identity  II-bypass index 0 → {EXPECTED_PRINCIPAL}")

    tmpdir = tempfile.TemporaryDirectory(prefix="realmtest6-ii-bypass-")
    pem_path = Path(tmpdir.name) / "identity.pem"
    pem_path.write_bytes(ed25519_seed_pem(test_identity_seed(0)))
    pem_path.chmod(0o600)

    imported = False
    failed = 0
    try:
        principal = import_throwaway_identity(icp, pem_path, IDENTITY_NAME)
        imported = True
        print(f"whoami    {principal}  (throwaway identity {IDENTITY_NAME})")

        # 1. api.call("get_sandbox_config") — Candid host verb
        r1 = canister_call(
            icp,
            backend=args.backend,
            network=args.network,
            identity=IDENTITY_NAME,
            did=did,
            method="get_sandbox_config",
            args="()",
            query=True,
        )
        payload1 = parse_json_payload(r1.stdout)
        available, docs_mode = sandbox_status(payload1)
        ok1 = r1.returncode == 0 and available
        if not report('api.call("get_sandbox_config")  — sandbox available', ok1, r1.stdout):
            failed += 1

        # 2. ext.call("department_docs", "list_documents", {}) — Docs button path
        r2 = canister_call(
            icp,
            backend=args.backend,
            network=args.network,
            identity=IDENTITY_NAME,
            did=did,
            method="extension_sync_call",
            args='("department_docs", "list_documents", "{}")',
        )
        ext_ok, ext_body = parse_extension_record(r2.stdout)
        ext_payload = None
        if ext_body:
            try:
                ext_payload = json.loads(ext_body)
            except json.JSONDecodeError:
                ext_payload = None
        list_ok = (
            r2.returncode == 0
            and ext_ok is True
            and (not isinstance(ext_payload, dict) or ext_payload.get("success", True))
        )

        r2b = canister_call(
            icp,
            backend=args.backend,
            network=args.network,
            identity=IDENTITY_NAME,
            did=did,
            method="get_sandbox_config",
            args="()",
            query=True,
        )
        payload2 = parse_json_payload(r2b.stdout)
        still_available, docs_mode_after = sandbox_status(payload2)
        sandbox_stays = still_available and (
            docs_mode_after.startswith("sandbox") or not docs_mode_after
        )
        ok2 = list_ok and r2b.returncode == 0 and sandbox_stays
        raw2 = (
            r2.stdout.rstrip()
            + "\n--- get_sandbox_config after list_documents ---\n"
            + r2b.stdout
            + f"\n(department_docs mode before={docs_mode!r} after={docs_mode_after!r})"
        )
        if not report(
            'ext.call("department_docs", "list_documents", {})  — Docs button; sandbox stays on',
            ok2,
            raw2,
        ):
            failed += 1

        # 3. api.call("__shell__", "1") must deny (REPL host block)
        r3 = canister_call(
            icp,
            backend=args.backend,
            network=args.network,
            identity=IDENTITY_NAME,
            did=did,
            method="__shell__",
            args=candid_text('api.call("__shell__", "1")'),
        )
        raw3 = r3.stdout
        denied = looks_denied(raw3) and not looks_shell_eval_success(raw3)
        ok3 = denied
        if not report('api.call("__shell__", "1")  — must deny', ok3, raw3):
            failed += 1

    finally:
        if imported:
            run_icp([icp, "identity", "delete", IDENTITY_NAME])
        tmpdir.cleanup()

    print(f"\n{3 - failed}/3 passed" if failed else "\n3/3 passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
