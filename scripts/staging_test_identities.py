#!/usr/bin/env python3
"""Build /canister_ids.js snippets and patch staging realm frontends with test identities."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "staging-test-identities.json"
PEM_DIR = REPO_ROOT / "config" / "staging-test-identities"

STAGING_REALM_FRONTENDS = {
    "dominion": "iocgc-oaaaa-aaaac-beh2q-cai",
    "agora": "iaalk-vqaaa-aaaac-beh3q-cai",
    "syntropia": "jkpjq-xaaaa-aaaac-beh4q-cai",
}
STAGING_REGISTRY_FRONTEND = "77243-aqaaa-aaaau-aggza-cai"


def _load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _load_pem(index: int) -> str:
    """Load PEM for identity number (1-based). Env wins over file."""
    env_key = f"STAGING_TEST_IDENTITY_PEM_{index}"
    env_val = os.environ.get(env_key, "").strip()
    if env_val:
        if "BEGIN" in env_val:
            return env_val
        try:
            return base64.b64decode(env_val).decode("utf-8")
        except Exception:
            return env_val
    pem_path = PEM_DIR / f"identity-{index}.pem"
    if pem_path.is_file():
        return pem_path.read_text(encoding="utf-8").strip()
    return ""


def _verify_pem_principal(pem: str, expected: str) -> None:
    """Verify PEM derives expected principal via node + @dfinity/identity."""
    if not pem or not expected:
        return
    script = REPO_ROOT / "src" / "realm_frontend"
    if not (script / "node_modules" / "@dfinity" / "identity").is_dir():
        raise RuntimeError(
            "Cannot verify PEM principal: run npm install in src/realm_frontend first"
        )
    code = f"""
const {{ Ed25519KeyIdentity, Secp256k1KeyIdentity }} = require('@dfinity/identity');
const pem = {json.dumps(pem)};
let id;
try {{ id = Secp256k1KeyIdentity.fromPem(pem); }} catch {{
  try {{ id = Ed25519KeyIdentity.fromPem(pem); }} catch (e) {{ console.error('PEM_PARSE_FAIL'); process.exit(2); }}
}}
console.log(id.getPrincipal().toText());
"""
    out = subprocess.check_output(["node", "-e", code], cwd=script, text=True).strip()
    if out != expected:
        raise ValueError(f"PEM principal mismatch: got {out}, expected {expected}")


def build_test_identity_js(config: dict | None = None, config_path: Path = DEFAULT_CONFIG) -> str:
    """Return JS assignments for globalThis.__TEST_IDENTITY_* arrays."""
    cfg = config or _load_config(config_path)
    identities = cfg.get("identities") or []
    principals: list[str] = []
    pems: list[str] = []
    for entry in identities:
        principals.append(str(entry.get("principal") or ""))
        num = int(entry.get("number") or len(pems) + 1)
        pem = _load_pem(num)
        if pem:
            _verify_pem_principal(pem, principals[-1])
        pems.append(pem)

    parts = [
        f"globalThis.__TEST_IDENTITY_PRINCIPALS={json.dumps(principals)};",
    ]
    if any(pems):
        # JSON.parse keeps escaping safe for multiline PEM strings in JS.
        parts.append(
            f"globalThis.__TEST_IDENTITY_PEms=JSON.parse({json.dumps(json.dumps(pems))});"
        )
    return "".join(parts)


def build_canister_ids_js(
    *,
    backend_id: str,
    file_registry_id: str = "",
    derivation_origin: str = "",
    portal_url: str = "",
    test_identity_config: dict | None = None,
    test_identity_config_path: Path = DEFAULT_CONFIG,
) -> str:
    fields = {
        "realm_backend": backend_id,
        "internet_identity": "https://identity.ic0.app",
    }
    if file_registry_id:
        fields["file_registry"] = file_registry_id
    if derivation_origin:
        fields["derivation_origin"] = derivation_origin
    if portal_url:
        fields["portal_url"] = portal_url
    body = ",".join(f'{k}:"{v}"' for k, v in fields.items())
    js = "globalThis.__CANISTER_IDS={" + body + "};"
    if test_identity_config is not None or test_identity_config_path.is_file():
        js += build_test_identity_js(test_identity_config, test_identity_config_path)
    return js


def _candid_store_arg(js: str) -> str:
    escaped = js.replace("\\", "\\\\").replace('"', '\\"')
    return (
        '(record { key = "/canister_ids.js"; content_type = "application/javascript"; '
        'content_encoding = "identity"; content = blob "' + escaped + '"; sha256 = null })'
    )


def store_canister_ids_js(frontend_id: str, js: str, network: str, identity: str = "deployer") -> None:
    arg = _candid_store_arg(js)
    subprocess.run(
        [
            "dfx",
            "canister",
            "call",
            frontend_id,
            "store",
            arg,
            "--network",
            network,
            "--identity",
            identity,
        ],
        cwd=REPO_ROOT,
        check=True,
    )


def patch_staging_realm(
    name: str,
    frontend_id: str,
    backend_id: str,
    *,
    network: str = "staging",
    identity: str = "deployer",
    file_registry_id: str = "iebdk-kqaaa-aaaau-agoxq-cai",
    derivation_origin: str = "https://staging.realmsgos.org",
    portal_url: str = "",
) -> None:
    js = build_canister_ids_js(
        backend_id=backend_id,
        file_registry_id=file_registry_id,
        derivation_origin=derivation_origin,
        portal_url=portal_url,
    )
    print(f"Patching {name} frontend {frontend_id} …")
    store_canister_ids_js(frontend_id, js, network, identity)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", default="staging")
    parser.add_argument("--identity", default=os.environ.get("DFX_IDENTITY", "deployer"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--print-js", action="store_true", help="Print JS only, do not store")
    parser.add_argument(
        "--frontend",
        action="append",
        help="frontend_canister_id:backend_id[:name] (repeatable)",
    )
    parser.add_argument("--all-staging-realms", action="store_true")
    parser.add_argument("--registry", action="store_true", help="Also patch registry frontend")
    args = parser.parse_args(argv)

    if args.print_js:
        print(build_test_identity_js(config_path=args.config))
        return 0

    if args.all_staging_realms:
        backends = {
            "dominion": "ijdaw-dyaaa-aaaac-beh2a-cai",
            "agora": "ihbn6-yiaaa-aaaac-beh3a-cai",
            "syntropia": "jnope-2yaaa-aaaac-beh4a-cai",
        }
        for name, frontend_id in STAGING_REALM_FRONTENDS.items():
            patch_staging_realm(
                name,
                frontend_id,
                backends[name],
                network=args.network,
                identity=args.identity,
            )
    elif args.frontend:
        for spec in args.frontend:
            parts = spec.split(":")
            if len(parts) < 2:
                parser.error(f"Invalid --frontend spec: {spec}")
            frontend_id, backend_id = parts[0], parts[1]
            name = parts[2] if len(parts) > 2 else frontend_id
            patch_staging_realm(
                name,
                frontend_id,
                backend_id,
                network=args.network,
                identity=args.identity,
            )
    elif not args.registry:
        parser.error("Specify --all-staging-realms, --frontend, or --registry")

    if args.registry:
        js = build_test_identity_js(config_path=args.config)
        # Registry frontend only needs test identity globals (no realm_backend).
        store_canister_ids_js(STAGING_REGISTRY_FRONTEND, js, args.network, args.identity)
        print(f"Patched registry frontend {STAGING_REGISTRY_FRONTEND}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
