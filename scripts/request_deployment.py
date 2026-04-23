#!/usr/bin/env python3
"""Request realm deployment via the queue-based architecture.

Reads a mundus descriptor file and submits deployment requests for
each realm via realm_registry_backend.request_deployment().

"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


REGISTRY_CANISTER_IDS = {
    "staging": "7wzxh-wyaaa-aaaau-aggyq-cai",
    "demo": "rhw4p-gqaaa-aaaac-qbw7q-cai",
}


def dfx_call(canister_id: str, method: str, arg: str, network: str) -> str:
    env = {
        "DFX_WARNING": "-mainnet_plaintext_identity",
        "NO_COLOR": "1",
    }
    import os
    run_env = os.environ.copy()
    run_env.update(env)
    if run_env.get("TERM", "dumb") == "dumb":
        run_env["TERM"] = "xterm-256color"

    result = subprocess.run(
        ["dfx", "canister", "call", canister_id, method, arg,
         "--network", network],
        capture_output=True, text=True, env=run_env,
    )
    if result.returncode != 0:
        print(f"  ERROR: dfx call failed: {result.stderr}", file=sys.stderr)
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def request_one(realm_config: dict, network: str, registry_id: str) -> str | None:
    """Submit a deployment request for one realm. Returns the job_id."""
    manifest = {
        "realm": {
            "name": realm_config.get("name", ""),
            "display_name": realm_config.get("display_name", ""),
            "description": realm_config.get("description", ""),
            "welcome_message": realm_config.get("welcome_message", ""),
            "branding": realm_config.get("branding", {}),
            "codex": realm_config.get("codex", {}),
            "extensions": realm_config.get("extensions", ["all"]),
        },
        "network": network,
    }

    manifest_json = json.dumps(manifest)
    candid_arg = f'("{manifest_json}")'

    print(f"  Calling request_deployment for '{manifest['realm']['name']}'...")
    raw = dfx_call(registry_id, "request_deployment", candid_arg, network)

    # Parse response
    json_str = raw
    if json_str.startswith("("):
        json_str = json_str.strip("()")
    if json_str.startswith('"') and json_str.endswith('"'):
        json_str = json_str[1:-1]
        json_str = json_str.replace('\\"', '"')

    result = json.loads(json_str)
    if result.get("success"):
        job_id = result.get("job_id", "?")
        print(f"  Enqueued: job_id={job_id}")
        return job_id
    else:
        print(f"  FAILED: {result.get('error', 'unknown')}")
        return None


def poll_jobs(job_ids: list[str], network: str, installer_id: str,
              timeout: int = 1800) -> bool:
    """Poll installer for job completion. Returns True if all succeeded."""
    start = time.time()
    pending = set(job_ids)

    while pending and (time.time() - start) < timeout:
        time.sleep(15)
        for job_id in list(pending):
            try:
                raw = dfx_call(
                    installer_id, "get_deployment_job_status",
                    f'("{job_id}")', network,
                )
                json_str = raw.strip("()").strip('"').replace('\\"', '"')
                result = json.loads(json_str)
                status = result.get("status", "?")
                print(f"  Job {job_id}: {status}")
                if status in ("completed", "failed", "failed_verification", "cancelled"):
                    pending.discard(job_id)
            except Exception as e:
                print(f"  Error polling {job_id}: {e}")

    if pending:
        print(f"\n  TIMEOUT: {len(pending)} job(s) still pending after {timeout}s")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="Mundus descriptor YAML")
    parser.add_argument("--network", help="Override network from descriptor")
    parser.add_argument("--no-poll", action="store_true", help="Don't wait for completion")
    args = parser.parse_args()

    if yaml is None:
        print("ERROR: pyyaml is required. pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    desc_path = Path(args.file)
    if not desc_path.exists():
        print(f"ERROR: {desc_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(desc_path) as f:
        desc = yaml.safe_load(f)

    network = args.network or desc.get("network", "staging")
    registry_id = REGISTRY_CANISTER_IDS.get(network)
    if not registry_id:
        print(f"ERROR: no registry canister ID for network '{network}'", file=sys.stderr)
        sys.exit(1)

    realms = desc.get("mundus", [])
    print(f"Submitting {len(realms)} realm deployment(s) to {network}")

    job_ids = []
    for realm in realms:
        if realm.get("type") in ("dashboard", "registry"):
            continue
        job_id = request_one(realm, network, registry_id)
        if job_id:
            job_ids.append(job_id)

    if not job_ids:
        print("No jobs submitted.")
        return

    print(f"\nSubmitted {len(job_ids)} job(s): {', '.join(job_ids)}")

    if args.no_poll:
        print("Skipping polling (--no-poll).")
        return

    installer_ids = {
        "staging": "lusjm-wqaaa-aaaau-ago7q-cai",
        "demo": "2s4td-daaaa-aaaao-bazmq-cai",
    }
    installer_id = installer_ids.get(network)
    if not installer_id:
        print(f"No installer ID for {network}, skipping polling.")
        return

    print(f"\nPolling for completion...")
    success = poll_jobs(job_ids, network, installer_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
