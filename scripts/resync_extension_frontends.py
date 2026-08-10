#!/usr/bin/env python3
"""Re-install extensions from file_registry to restore /ext/ frontend assets."""

from __future__ import annotations

import argparse
import json
import sys
import time

from ic.agent import Agent
from ic.candid import Types, encode
from ic.client import Client
from ic.identity import Identity

DEFAULT_REGISTRY = "iebdk-kqaaa-aaaau-agoxq-cai"
DEFAULT_FRONTEND = "fcm3z-5qaaa-aaaac-bfq4a-cai"
DEFAULT_PEM = "/root/.config/dfx/identity/deployer/identity.pem"
DEFAULT_HOST = "https://icp0.io"


def _text_arg(value: str) -> bytes:
    return encode([{"type": Types.Text, "value": value}])


def _decode_text(raw) -> str:
    if isinstance(raw, list) and raw:
        return raw[0].get("value", "")
    if isinstance(raw, str):
        return raw
    raise ValueError(f"Unexpected candid decode result: {raw!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", help="Realm backend canister id")
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--frontend", default=DEFAULT_FRONTEND)
    parser.add_argument("--identity-pem", default=DEFAULT_PEM)
    parser.add_argument("--ext", help="Single extension id (default: all installed)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ident = Identity.from_pem(open(args.identity_pem, encoding="utf-8").read())
    agent = Agent(ident, Client(DEFAULT_HOST))
    print(f"Caller:   {ident.sender()}")
    print(f"Backend:  {args.backend}")
    print(f"Registry: {args.registry}")
    print(f"Frontend: {args.frontend}")

    listed_raw = agent.query_raw(
        args.backend,
        "list_runtime_extensions",
        encode([]),
        [{"type": Types.Text}],
    )
    listed = json.loads(_decode_text(listed_raw))
    # list_runtime_extensions uses runtime_extensions; older payloads used installed.
    installed = listed.get("runtime_extensions") or listed.get("installed") or []
    manifests = listed.get("all_manifests") or {}
    ext_ids = [args.ext] if args.ext else installed

    if not ext_ids:
        print("No extensions installed.")
        return 0

    print(f"Resyncing {len(ext_ids)} extension(s)...")
    ok = fail = 0

    for ext_id in ext_ids:
        version = (manifests.get(ext_id) or {}).get("version", "?")
        print(f"\n→ {ext_id}@{version}")
        if args.dry_run:
            continue

        payload = json.dumps(
            {
                "registry_canister_id": args.registry,
                "ext_id": ext_id,
                "version": None,
                "frontend_canister_id": args.frontend,
            }
        )
        try:
            result_raw = agent.update_raw(
                args.backend,
                "install_extension_from_registry",
                _text_arg(payload),
                [{"type": Types.Text}],
                timeout=300,
            )
            result = json.loads(_decode_text(result_raw))
            if result.get("success"):
                copied = result.get("frontend_files_copied", "?")
                print(f"  ✓ synced v{result.get('version', version)} ({copied} frontend files)")
                ok += 1
            else:
                print(f"  ✗ {result.get('error', result)}")
                fail += 1
        except Exception as exc:
            print(f"  ✗ {exc}")
            fail += 1
        time.sleep(1)

    print(f"\nDone: {ok} ok, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
