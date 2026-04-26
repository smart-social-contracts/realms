#!/usr/bin/env python3
"""Build WASM and frontend artifacts for a mundus deployment.

Reads a mundus descriptor and produces the artifacts that the off-chain
deploy service needs:
  - realm_backend.wasm.gz  (compiled via basilisk)
  - realm_frontend dist/   (built via npm with correct per-env canister IDs)

Designed to run inside the deploy-mundus GitHub Actions workflow before
queue submission, so the upload_ci_artifacts.py step has real files to
upload.
"""

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run(cmd, **kwargs):
    kwargs.setdefault("cwd", str(REPO_ROOT))
    kwargs.setdefault("check", True)
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, **kwargs)


def build_backend_wasm(skip: bool = False) -> bool:
    """Build realm_backend WASM via basilisk. Returns True on success."""
    if skip:
        print("Skipping backend WASM build (--skip-base-wasm)")
        return True

    print("\n── Building realm_backend WASM ──")
    wasm_raw = REPO_ROOT / ".basilisk" / "realm_backend" / "realm_backend.wasm"
    wasm_gz = wasm_raw.with_suffix(".wasm.gz")

    env = os.environ.copy()
    env["CANISTER_CANDID_PATH"] = str(
        REPO_ROOT / "src" / "realm_backend" / "realm_backend.did"
    )

    _run(
        [sys.executable, "-m", "basilisk",
         "realm_backend", "src/realm_backend/main.py"],
        env=env,
    )

    if wasm_raw.exists() and not wasm_gz.exists():
        print(f"  gzipping {wasm_raw.name}")
        with open(wasm_raw, "rb") as f_in:
            with gzip.open(wasm_gz, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

    if wasm_gz.exists():
        print(f"  ✓ {wasm_gz} ({wasm_gz.stat().st_size:,} bytes)")
        return True
    if wasm_raw.exists():
        print(f"  ✓ {wasm_raw} ({wasm_raw.stat().st_size:,} bytes)")
        return True

    print("  ✗ WASM build failed — no output artifact")
    return False


def build_realm_frontend(
    network: str,
    backend_id: str,
    frontend_id: str,
    descriptor: dict,
) -> bool:
    """Build realm_frontend with environment-correct canister IDs."""
    print(f"\n── Building realm_frontend (network={network}) ──")

    fe_dir = REPO_ROOT / "src" / "realm_frontend"
    src_decls = REPO_ROOT / "src" / "declarations"
    lib_decls = fe_dir / "src" / "lib" / "declarations"
    ids_file = REPO_ROOT / "canister_ids.json"

    ids_data = json.loads(ids_file.read_text()) if ids_file.exists() else {}
    ids_data.setdefault("realm_backend", {})[network] = backend_id
    ids_data.setdefault("realm_frontend", {})[network] = frontend_id

    infra = descriptor.get("infrastructure_overrides", {})
    for key in ("file_registry", "file_registry_frontend",
                "realm_installer", "realm_registry_backend",
                "realm_registry_frontend"):
        cid = (infra.get(key, {}).get("canister_id") or "").strip()
        if cid:
            ids_data.setdefault(key, {})[network] = cid
    ids_file.write_text(json.dumps(ids_data, indent=2) + "\n")

    did_path = REPO_ROOT / "src" / "realm_backend" / "realm_backend.did"
    if did_path.exists():
        _run(["dfx", "generate", "realm_backend", "--network", network],
             check=False)

    if src_decls.exists() and (src_decls / "realm_backend").exists():
        lib_decls.mkdir(parents=True, exist_ok=True)
        target = lib_decls / "realm_backend"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src_decls / "realm_backend", target)

        idx = target / "index.js"
        if idx.exists():
            text = idx.read_text()
            text = text.replace(
                "process.env.CANISTER_ID_REALM_BACKEND",
                f'"{backend_id}"',
            )
            text = text.replace("@icp-sdk/core/agent", "@dfinity/agent")
            text = text.replace("@icp-sdk/core/candid", "@dfinity/candid")
            idx.write_text(text)

    env = os.environ.copy()
    env["DFX_NETWORK"] = network
    file_reg = (infra.get("file_registry", {}).get("canister_id") or "").strip()
    if file_reg:
        env["CANISTER_ID_FILE_REGISTRY"] = file_reg
        env["VITE_FILE_REGISTRY_CANISTER_ID"] = file_reg

    _run(["npm", "run", "build", "--workspace=realm_frontend"], env=env)

    dist = fe_dir / "dist"
    if dist.is_dir() and any(dist.iterdir()):
        meta = {"build_backend_canister_id": backend_id}
        (dist / "_build_meta.json").write_text(json.dumps(meta))
        print(f"  ✓ {dist}")
        return True

    print("  ✗ realm_frontend build produced no dist/")
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="Mundus descriptor YAML")
    parser.add_argument(
        "--skip-base-wasm", action="store_true",
        help="Skip WASM compilation (use pre-built artifact)",
    )
    args = parser.parse_args()

    if yaml is None:
        print("ERROR: pyyaml is required. pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    desc_path = Path(args.file)
    if not desc_path.is_absolute():
        desc_path = REPO_ROOT / desc_path
    with open(desc_path) as f:
        desc = yaml.safe_load(f)

    network = desc.get("network", "staging")

    ok = build_backend_wasm(skip=args.skip_base_wasm)
    if not ok:
        sys.exit(1)

    first_realm = next(
        (m for m in desc.get("mundus", [])
         if (m.get("type") or "realm") == "realm"),
        None,
    )
    if first_realm:
        backend_id = first_realm.get("canister_id", "")
        frontend_id = first_realm.get("frontend_canister_id", "")
        ok = build_realm_frontend(network, backend_id, frontend_id, desc)
        if not ok:
            sys.exit(1)
    else:
        print("No realm-type member found in descriptor, skipping frontend build")


if __name__ == "__main__":
    main()
