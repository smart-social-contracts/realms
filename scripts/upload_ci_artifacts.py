#!/usr/bin/env python3
"""Upload CI-built artifacts to the realms-canister-deploy-service cache.

After a successful build, this script uploads:
  - realm_backend.wasm.gz and realm_backend.did
  - realm_frontend dist/ as a tarball
  - (future) token and nft artifacts

The deploy service caches these so staging/demo deployments via the
queue-based flow can resolve artifacts without explicit URLs.
"""

import argparse
import hashlib
import os
import sys
import tarfile
import tempfile
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

DEFAULT_DEPLOY_SERVICE_URL = os.environ.get(
    "DEPLOY_SERVICE_URL", "https://deploy.realmsgos.dev"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def find_repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "dfx.json").exists():
            return p
        p = p.parent
    return Path.cwd()


def upload_realm_backend(repo: Path, network: str, base_url: str) -> bool:
    candidates = [
        repo / ".dfx" / network / "canisters" / "realm_backend" / "realm_backend.wasm.gz",
        repo / "build" / "realm_backend.wasm.gz",
    ]
    wasm_path = next((c for c in candidates if c.exists()), None)
    if not wasm_path:
        print("  [skip] realm_backend.wasm.gz not found")
        return False

    did_candidates = [
        repo / "src" / "realm_backend" / "realm_backend.did",
        repo / ".dfx" / network / "canisters" / "realm_backend" / "realm_backend.did",
    ]
    did_path = next((c for c in did_candidates if c.exists()), None)

    files = {"wasm": ("realm_backend.wasm.gz", open(wasm_path, "rb"), "application/gzip")}
    if did_path:
        files["did"] = ("realm_backend.did", open(did_path, "rb"), "text/plain")

    url = f"{base_url}/artifacts/{network}/realm/backend"
    print(f"  Uploading realm backend to {url}")
    print(f"    WASM: {wasm_path} ({wasm_path.stat().st_size} bytes)")

    if requests:
        resp = requests.post(url, files=files)
        print(f"    Response: {resp.status_code} {resp.text[:200]}")
        return resp.ok
    else:
        print("    [dry-run] requests module not available")
        return True


def upload_realm_frontend(repo: Path, network: str, base_url: str) -> bool:
    candidates = [
        repo / "src" / "realm_frontend" / "dist",
        repo / "dist" / "realm_frontend",
    ]
    dist_dir = next((c for c in candidates if c.exists() and c.is_dir()), None)
    if not dist_dir:
        print("  [skip] realm_frontend dist/ not found")
        return False

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tarball_path = tmp.name

    try:
        with tarfile.open(tarball_path, "w:gz") as tar:
            for f in sorted(dist_dir.rglob("*")):
                if f.is_file():
                    tar.add(str(f), arcname=str(f.relative_to(dist_dir)))

        size = os.path.getsize(tarball_path)
        url = f"{base_url}/artifacts/{network}/realm/frontend"
        print(f"  Uploading realm frontend to {url}")
        print(f"    Tarball: {size} bytes from {dist_dir}")

        if requests:
            with open(tarball_path, "rb") as f:
                resp = requests.post(url, files={
                    "tarball": ("realm_frontend.tar.gz", f, "application/gzip"),
                })
            print(f"    Response: {resp.status_code} {resp.text[:200]}")
            return resp.ok
        else:
            print("    [dry-run] requests module not available")
            return True
    finally:
        os.unlink(tarball_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", required=True, help="Target network (staging, demo)")
    parser.add_argument(
        "--deploy-service-url", default=DEFAULT_DEPLOY_SERVICE_URL,
        help=f"Deploy service URL (default: {DEFAULT_DEPLOY_SERVICE_URL})",
    )
    args = parser.parse_args()

    repo = find_repo_root()
    url = args.deploy_service_url
    print(f"Uploading CI artifacts for network '{args.network}' from {repo}")

    upload_realm_backend(repo, args.network, url)
    upload_realm_frontend(repo, args.network, url)
    print("Done.")


if __name__ == "__main__":
    main()
