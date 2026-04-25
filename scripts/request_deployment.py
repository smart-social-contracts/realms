#!/usr/bin/env python3
"""Request realm deployment via the queue-based architecture.

Reads a mundus descriptor file and submits deployment requests for
each realm via realm_registry_backend.request_deployment().

"""

import argparse
import json
import os
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
    "test": "yhw3g-fyaaa-aaaas-qgorq-cai",
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
         "--network", network, "--output", "json"],
        capture_output=True, text=True, env=run_env,
    )
    if result.returncode != 0:
        print(f"  ERROR: dfx call failed: {result.stderr}", file=sys.stderr)
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


REALMS_RELEASE_BASE = (
    "https://github.com/smart-social-contracts/realms/releases/download"
)


def _fetch_release_checksums(tag: str) -> dict[str, str]:
    """Fetch checksums.txt from a GitHub release. Returns {filename: "sha256:hex"}."""
    import urllib.request
    url = f"{REALMS_RELEASE_BASE}/{tag}/checksums.txt"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        result = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                result[parts[1].strip()] = f"sha256:{parts[0]}"
        return result
    except Exception as e:
        print(f"  (checksums.txt not available for {tag}: {e})")
        return {}


def _build_artifact_refs(tag: str) -> dict:
    """Build canister_artifacts from a GitHub release tag with checksums."""
    cs = _fetch_release_checksums(tag)
    return {
        "realm": {
            "backend": {
                "wasm": {
                    "url": f"{REALMS_RELEASE_BASE}/{tag}/realm_backend.wasm.gz",
                    "checksum": cs.get("realm_backend.wasm.gz", ""),
                },
            },
            "frontend": {
                "url": f"{REALMS_RELEASE_BASE}/{tag}/realm_frontend.tar.gz",
                "checksum": cs.get("realm_frontend.tar.gz", ""),
            },
        },
    }


def request_one(
    realm_config: dict, network: str, registry_id: str, *, release_tag: str = "",
) -> str | None:
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
    if realm_config.get("canister_id"):
        manifest["backend_canister_id"] = realm_config["canister_id"]
    if realm_config.get("frontend_canister_id"):
        manifest["frontend_canister_id"] = realm_config["frontend_canister_id"]
    if release_tag:
        manifest["canister_artifacts"] = _build_artifact_refs(release_tag)

    manifest_json = json.dumps(manifest)
    escaped = manifest_json.replace('\\', '\\\\').replace('"', '\\"')
    candid_arg = f'("{escaped}")'

    print(f"  Calling request_deployment for '{manifest['realm']['name']}'...")
    raw = dfx_call(registry_id, "request_deployment", candid_arg, network)

    data = json.loads(raw)
    if isinstance(data, dict) and data.get("Err") is not None:
        err = data["Err"]
        if isinstance(err, dict):
            print(f"  FAILED: {err.get('message', str(err))}")
        else:
            print(f"  FAILED: {err}")
        return None
    payload = data.get("Ok", data) if isinstance(data, dict) else data
    if isinstance(payload, str):
        result = json.loads(payload)
    else:
        result = payload

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
                data = json.loads(raw)
                if isinstance(data, dict) and data.get("Err") is not None:
                    print(f"  Job {job_id}: error {data['Err']}")
                    continue
                result = data.get("Ok", data) if isinstance(data, dict) else data
                status = (result or {}).get("status", "?")
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
    parser.add_argument(
        "--release-tag",
        default=os.environ.get("DEPLOY_RELEASE_TAG", ""),
        help="GitHub release tag for WASM/frontend artifacts (e.g. v0.3.1)",
    )
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

    release_tag = (args.release_tag or "").strip()

    realms = desc.get("mundus", [])
    print(f"Submitting {len(realms)} realm deployment(s) to {network}")
    if release_tag:
        print(f"  release tag: {release_tag}")

    job_ids = []
    for realm in realms:
        if realm.get("type") in ("dashboard", "registry", "realm_registry", "marketplace", "token", "nft"):
            continue
        job_id = request_one(realm, network, registry_id, release_tag=release_tag)
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
        "test": "fltjm-tyaaa-aaaap-qunhq-cai",
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
