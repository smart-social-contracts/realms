#!/usr/bin/env python3
"""Bulk-approve first-party packages in a file registry (issue #267).

Realms refuse to install extensions and codices that carry no marketplace
approval. Everything already published predates the approval mechanism, so
without a one-off pass every deployment would fail on content we shipped
ourselves. This script records those approvals.

It only touches ``ext/`` and ``codex/`` namespaces — the installable packages
a realm gates on. Branding, WASM artifacts and frontend bundles are
infrastructure and are not part of the marketplace.

Approvals are bound to file hashes, so re-running after a republish is both
safe and necessary: an unchanged namespace is skipped, a changed one is
re-approved.

Usage:
    python3 scripts/approve_registry_content.py --network ic \\
        --registry iebdk-kqaaa-aaaau-agoxq-cai --dry-run
    python3 scripts/approve_registry_content.py --network ic \\
        --registry iebdk-kqaaa-aaaau-agoxq-cai --execute
"""

import argparse
import json
import os
import re
import subprocess
import sys

INSTALLABLE_PREFIXES = ("ext/", "codex/")
DEFAULT_NOTES = "First-party package, approved in bulk migration (issue #267)"


def dfx(args, network, timeout=120):
    """Run a dfx command and return stdout, raising on failure."""
    env = dict(os.environ)
    # dfx 0.30 panics on colour setup unless it gets a colour-capable terminal,
    # and refuses to run against mainnet with a plaintext identity unless the
    # warning is suppressed.
    env["TERM"] = "xterm-256color"
    env["DFX_WARNING"] = "-mainnet_plaintext_identity"
    env.pop("NO_COLOR", None)
    env.pop("FORCE_COLOR", None)

    result = subprocess.run(
        ["dfx"] + args + ["--network", network],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"dfx {' '.join(args)} failed ({result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout


def unwrap_candid_text(raw):
    """Pull the payload out of dfx's `("...")` rendering of a text return."""
    match = re.search(r'\(\s*"(.*)"\s*,?\s*\)\s*$', raw.strip(), re.DOTALL)
    if not match:
        raise ValueError(f"unexpected dfx output: {raw[:200]}")
    # dfx escapes the inner JSON; json.loads on the quoted form unescapes it.
    return json.loads('"' + match.group(1) + '"')


def call(registry, method, arg, network, query=False):
    args = ["canister", "call", registry, method, f'("{arg}")' if arg else "()"]
    if query:
        args.append("--query")
    return unwrap_candid_text(dfx(args, network))


def escaped(payload):
    """JSON payload escaped for embedding in a Candid text literal."""
    return json.dumps(payload).replace('\\', '\\\\').replace('"', '\\"')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, help="File registry canister id")
    parser.add_argument(
        "--via-marketplace",
        default="",
        help=(
            "Marketplace canister id to route approvals through. Defaults to "
            "the known marketplace for --network (test/staging/demo). Realms "
            "trust their configured marketplace by default, so an approval "
            "written directly by an operator key is one they will refuse "
            "(found the hard way: P18, 10k E2E). Pass --direct to override. "
            "Requires the marketplace to hold approver rights on the "
            "registry (grant_publish on the '_approvers' namespace)."
        ),
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Approve directly with the operator identity instead of routing "
        "through the marketplace (NOT recommended — realms will refuse).",
    )
    parser.add_argument("--network", default="ic")
    parser.add_argument("--notes", default=DEFAULT_NOTES)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually record approvals (default is a dry run)",
    )
    parser.add_argument(
        "--only",
        default="",
        help="Comma-separated substring filter, e.g. 'ext/voting,codex/syntropia'",
    )
    args = parser.parse_args()

    # Default to the network's marketplace so approvals are attributed to the
    # principal realms actually trust. --direct opts out (operator-attributed
    # approvals — realms refuse them).
    MARKETPLACE_BY_NETWORK = {
        "test": "2wldc-niaaa-aaaad-qlxga-cai",
        "staging": "jji3o-uyaaa-aaaah-qreja-cai",
        "demo": "ehyfg-wyaaa-aaaae-qg3qq-cai",
    }
    if args.direct:
        args.via_marketplace = ""
    elif not args.via_marketplace:
        args.via_marketplace = MARKETPLACE_BY_NETWORK.get(args.network, "")
        if not args.via_marketplace and args.execute:
            parser.error(
                f"no known marketplace for --network {args.network}; "
                "pass --via-marketplace explicitly or --direct to approve "
                "with the operator identity (realms will refuse those)"
            )

    print(f"Reading namespaces from {args.registry} on {args.network} ...")
    namespaces = json.loads(call(args.registry, "list_namespaces", "", args.network, query=True))

    installable = [
        entry
        for entry in namespaces
        if str(entry.get("namespace", "")).startswith(INSTALLABLE_PREFIXES)
    ]
    if args.only:
        wanted = [s.strip() for s in args.only.split(",") if s.strip()]
        installable = [
            e for e in installable if any(w in e["namespace"] for w in wanted)
        ]

    # "approved" in the listing only says a decision exists, not who made it.
    # Re-approving through the marketplace is how a migration fixes attribution,
    # so an explicit approver check decides what still needs doing.
    expected_approver = args.via_marketplace.strip()
    already, todo = [], []
    for entry in installable:
        if not entry.get("approved"):
            todo.append(entry)
            continue
        if not expected_approver:
            already.append(entry)
            continue
        record = json.loads(
            call(
                args.registry,
                "get_namespace_approval",
                escaped({"namespace": entry["namespace"]}),
                args.network,
                query=True,
            )
        )
        if record.get("approver") == expected_approver:
            already.append(entry)
        else:
            todo.append(entry)

    print(
        f"{len(namespaces)} namespaces total, {len(installable)} installable "
        f"({len(already)} already approved, {len(todo)} to approve)"
    )
    if not todo:
        print("Nothing to do.")
        return 0

    if not args.execute:
        for entry in todo[:20]:
            print(f"  would approve {entry['namespace']} ({entry.get('file_count', '?')} files)")
        if len(todo) > 20:
            print(f"  ... and {len(todo) - 20} more")
        print("\nDry run. Re-run with --execute to record these approvals.")
        return 0

    approved, failed = 0, []
    for index, entry in enumerate(todo, start=1):
        namespace = entry["namespace"]
        try:
            if expected_approver:
                raw = dfx(
                    [
                        "canister",
                        "call",
                        expected_approver,
                        "admin_approve_namespace",
                        f'("{namespace}", "{args.notes}")',
                    ],
                    args.network,
                )
                response = json.loads(unwrap_candid_text(raw))
            else:
                payload = escaped(
                    {"namespace": namespace, "status": "approved", "notes": args.notes}
                )
                response = json.loads(
                    call(args.registry, "set_namespace_approval", payload, args.network)
                )
        except Exception as e:
            failed.append((namespace, str(e)))
            print(f"[{index}/{len(todo)}] FAILED {namespace}: {e}")
            continue

        reason = response.get("error")
        if reason:
            failed.append((namespace, reason))
            print(f"[{index}/{len(todo)}] REFUSED {namespace}: {reason}")
        else:
            approved += 1
            print(f"[{index}/{len(todo)}] approved {namespace}")

    print(f"\nApproved {approved}, failed {len(failed)}.")
    for namespace, reason in failed:
        print(f"  {namespace}: {reason}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
