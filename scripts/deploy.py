#!/usr/bin/env python3
"""Unified deployment script for Realms.

Reads a deployment descriptor YAML and executes the appropriate deployment.
Supports targeted deploys (backend-only, frontend-only) and multiple codebase
sources (local path, git ref, version tag).

Usage:
    python scripts/deploy.py --file deployments/staging-realm2-backend.yml
    python scripts/deploy.py --file deployments/staging-mundus.yml --subtypes backend
    realms deploy --file deployments/staging-realm2-backend.yml

See: https://github.com/smart-social-contracts/realms/issues/160
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


def _detect_icp_cli() -> str:
    """Detect the icp CLI on PATH."""
    if shutil.which("icp"):
        return "icp"
    print("❌ 'icp' CLI not found on PATH. Install with: npm install -g @icp-sdk/icp-cli")
    sys.exit(1)


ICP_CLI = _detect_icp_cli()


# ── Constants ──────────────────────────────────────────────────────────────────

VALID_TYPES = ("realm", "registry", "mundus")
VALID_SUBTYPES = ("backend", "frontend", "token", "nft", "marketplace", "all")
VALID_MODES = ("upgrade", "reinstall", "install", "auto")
VALID_NETWORKS = ("local", "staging", "demo", "ic")

VITE_PARAM_MAP = {
    "TEST_MODE": "VITE_TEST_MODE",
    "TEST_MODE_II_BYPASS": "VITE_TEST_MODE_II_BYPASS",
    "TEST_MODE_ADMIN_SELF_REGISTRATION": "VITE_TEST_MODE_ADMIN_SELF_REGISTRATION",
    "TEST_MODE_DEMO_DATA": "VITE_TEST_MODE_DEMO_DATA",
    "TEST_MODE_SKIP_TERMS": "VITE_TEST_MODE_SKIP_TERMS",
}


# ── YAML Parsing ──────────────────────────────────────────────────────────────

def load_descriptor(file_path: str) -> dict:
    """Load and validate a deployment descriptor YAML file."""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ Deployment descriptor not found: {file_path}")
        sys.exit(1)

    with open(path) as f:
        data = yaml.safe_load(f)

    if not data or "object" not in data:
        print(f"❌ Invalid deployment descriptor: missing 'object' key")
        sys.exit(1)

    obj = data["object"]

    # Validate type
    obj_type = obj.get("type", "").strip()
    if obj_type not in VALID_TYPES:
        print(f"❌ Invalid object.type: '{obj_type}'. Valid: {VALID_TYPES}")
        sys.exit(1)

    # Parse subtypes
    subtypes_raw = obj.get("subtypes", "all")
    if isinstance(subtypes_raw, str):
        subtypes = [s.strip() for s in subtypes_raw.split(",")]
    elif isinstance(subtypes_raw, list):
        subtypes = [s.strip() for s in subtypes_raw]
    else:
        subtypes = ["all"]

    for st in subtypes:
        if st not in VALID_SUBTYPES:
            print(f"❌ Invalid subtype: '{st}'. Valid: {VALID_SUBTYPES}")
            sys.exit(1)

    # Validate network
    network = obj.get("network", "local").strip()
    if network not in VALID_NETWORKS:
        print(f"❌ Invalid network: '{network}'. Valid: {VALID_NETWORKS}")
        sys.exit(1)

    # Validate mode
    mode = obj.get("mode", "upgrade").strip()
    if mode not in VALID_MODES:
        print(f"❌ Invalid mode: '{mode}'. Valid: {VALID_MODES}")
        sys.exit(1)

    return {
        "version": data.get("version", 1),
        "type": obj_type,
        "subtypes": subtypes,
        "quarters": int(obj.get("quarters", 1)),
        "manifest": obj.get("manifest", ""),
        "core_codebase": obj.get("core_codebase", {}).get("path", "./src"),
        "extensions_codebase": obj.get("extensions_codebase", {}).get("path", "bundled"),
        "codices_codebase": obj.get("codices_codebase", {}).get("path", "bundled"),
        "network": network,
        "id_in_registry": obj.get("id_in_registry"),
        "mode": mode,
        "parameters": obj.get("parameters", {}),
    }


# ── Codebase Resolution ──────────────────────────────────────────────────────

def is_local_path(path: str) -> bool:
    """Check if a codebase path is a local filesystem path."""
    return path.startswith("./") or path.startswith("/") or path == "."


def is_git_ref(path: str) -> bool:
    """Check if a codebase path is a git reference."""
    return path.startswith("git@") or path.startswith("https://github.com")


def is_version_tag(path: str) -> bool:
    """Check if a codebase path is a version tag (semver-like)."""
    return bool(re.match(r"^\d+\.\d+\.\d+", path))


def resolve_codebase(path: str, label: str, temp_dir: str) -> str:
    """Resolve a codebase path to a local directory.

    Returns the local directory path where the code is available.
    """
    if path in ("bundled", "none", ""):
        return path

    if is_local_path(path):
        resolved = Path(path).resolve()
        if not resolved.exists():
            print(f"❌ {label} local path not found: {path}")
            sys.exit(1)
        print(f"   📁 {label}: using local path {resolved}")
        return str(resolved)

    if is_git_ref(path):
        # Parse git@github.com:org/repo.git@ref
        match = re.match(r"(.+?)@([^@]+)$", path)
        if not match:
            print(f"❌ {label}: invalid git ref format: {path}")
            sys.exit(1)
        repo_url = match.group(1)
        ref = match.group(2)
        clone_dir = os.path.join(temp_dir, label.replace(" ", "_"))
        print(f"   📥 {label}: cloning {repo_url} at {ref}...")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", ref, repo_url, clone_dir],
                check=True, capture_output=True, text=True, timeout=120,
            )
        except subprocess.CalledProcessError as e:
            # --branch may not work for commit SHAs; fall back to full clone + checkout
            print(f"   ⚠️  Shallow clone failed, trying full clone + checkout...")
            subprocess.run(
                ["git", "clone", repo_url, clone_dir],
                check=True, capture_output=True, text=True, timeout=300,
            )
            subprocess.run(
                ["git", "checkout", ref],
                check=True, capture_output=True, text=True, cwd=clone_dir,
            )
        print(f"   ✅ {label}: cloned to {clone_dir}")
        return clone_dir

    if is_version_tag(path):
        print(f"   📦 {label}: version {path} (will use Docker image or pip package)")
        # For version tags, we'd pull the Docker image or install via pip
        # For now, return the version string; the deploy functions handle it
        return f"version:{path}"

    print(f"❌ {label}: unrecognized codebase format: {path}")
    sys.exit(1)


# ── Registry Resolution ──────────────────────────────────────────────────────

def resolve_canister_ids_from_registry(
    id_in_registry, network: str, registry_canister_id: str = None
) -> dict:
    """Query the registry to resolve canister IDs for a realm.

    Args:
        id_in_registry: Integer index or canister ID string.
        network: Target network.
        registry_canister_id: Override registry canister ID.

    Returns:
        Dict with canister name -> canister ID mappings.
    """
    if id_in_registry is None:
        return {}

    # Determine registry canister ID
    if not registry_canister_id:
        registry_canister_id = "realm_registry_backend"

    print(f"   🔍 Querying registry ({registry_canister_id}) on {network}...")

    try:
        result = subprocess.run(
            [ICP_CLI, "canister", "call", "-e", network,
             registry_canister_id, "list_realms", "--query"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"   ⚠️  Registry query failed: {result.stderr.strip()}")
            return {}

        output = result.stdout.strip()

        # Parse realm records from Candid output
        # Each record has: id (= backend canister ID), frontend_canister_id, etc.
        canister_ids = {}

        if isinstance(id_in_registry, int):
            # Extract the Nth realm's canister IDs from the registry output
            # Look for record patterns with id field
            id_matches = re.findall(r'id\s*=\s*"([^"]+)"', output)
            frontend_matches = re.findall(r'frontend_canister_id\s*=\s*"([^"]*)"', output)
            token_matches = re.findall(r'token_canister_id\s*=\s*"([^"]*)"', output)
            nft_matches = re.findall(r'nft_canister_id\s*=\s*"([^"]*)"', output)

            idx = id_in_registry - 1  # Convert to 0-based
            if idx < len(id_matches):
                canister_ids["realm_backend"] = id_matches[idx]
                if idx < len(frontend_matches) and frontend_matches[idx]:
                    canister_ids["realm_frontend"] = frontend_matches[idx]
                if idx < len(token_matches) and token_matches[idx]:
                    canister_ids["token_backend"] = token_matches[idx]
                if idx < len(nft_matches) and nft_matches[idx]:
                    canister_ids["nft_backend"] = nft_matches[idx]
                print(f"   ✅ Resolved realm #{id_in_registry}: backend={canister_ids.get('realm_backend', 'N/A')}")
            else:
                print(f"   ⚠️  Registry has {len(id_matches)} realms, index {id_in_registry} out of range")

        elif isinstance(id_in_registry, str):
            # Use the string directly as the backend canister ID
            canister_ids["realm_backend"] = id_in_registry
            print(f"   ✅ Using canister ID directly: {id_in_registry}")

        return canister_ids

    except subprocess.TimeoutExpired:
        print(f"   ⚠️  Registry query timed out")
        return {}
    except Exception as e:
        print(f"   ⚠️  Registry query error: {e}")
        return {}


def resolve_canister_ids_from_files(network: str, manifest_path: str) -> dict:
    """Fall back to resolving canister IDs from canister_ids.json files."""
    canister_ids = {}
    manifest_dir = Path(manifest_path).parent if manifest_path else Path(".")

    # Try manifest directory's canister_ids.json
    ids_file = manifest_dir / "canister_ids.json"
    if ids_file.exists():
        with open(ids_file) as f:
            data = json.load(f)
        for canister_name, networks in data.items():
            if isinstance(networks, dict) and network in networks:
                canister_ids[canister_name] = networks[network]

    # Also try root canister_ids.json
    root_ids = Path("canister_ids.json")
    if root_ids.exists():
        with open(root_ids) as f:
            data = json.load(f)
        for canister_name, networks in data.items():
            if isinstance(networks, dict) and network in networks:
                if canister_name not in canister_ids:
                    canister_ids[canister_name] = networks[network]

    return canister_ids


# ── Deploy Functions ──────────────────────────────────────────────────────────

def set_vite_env_vars(parameters: dict) -> dict:
    """Convert deployment parameters to VITE_* environment variables."""
    env = os.environ.copy()

    for param_name, value in parameters.items():
        vite_key = VITE_PARAM_MAP.get(param_name)
        if vite_key:
            env[vite_key] = str(value).lower()
        # Also set NO_DEMO_DATA if TEST_MODE_DEMO_DATA is false
        if param_name == "TEST_MODE_DEMO_DATA" and not value:
            env["NO_DEMO_DATA"] = "1"

    return env


def deploy_backend(
    network: str,
    mode: str,
    canister_ids: dict,
    core_path: str,
    extensions_path: str,
    quarters: int,
    env: dict,
) -> None:
    """Deploy backend canister(s) only."""
    backend_id = canister_ids.get("realm_backend")
    if not backend_id:
        print("❌ No realm_backend canister ID resolved. Cannot deploy backend.")
        print("   Provide id_in_registry or ensure canister_ids.json has the mapping.")
        sys.exit(1)

    print(f"\n⚡ Deploying backend to {backend_id} on {network} (mode={mode})")

    # Install backend dependencies
    print("   📦 Installing backend dependencies...")
    for backend_dir in Path("src").glob("*_backend"):
        req = backend_dir / "requirements.txt"
        if req.exists():
            subprocess.run(
                ["pip3", "install", "-q", "-r", str(req)],
                env=env, check=False,
            )

    # Clear build cache
    basilisk_cache = Path(".basilisk/realm_backend")
    if basilisk_cache.exists():
        shutil.rmtree(basilisk_cache)
        print("   🧹 Cleared Basilisk build cache")

    # Build backend WASM
    # Set CANISTER_CANDID_PATH — required by Basilisk.
    # icp sets this automatically; we must do it manually for direct builds.
    candid_path = Path("src/realm_backend/realm_backend.did")
    if candid_path.exists():
        env["CANISTER_CANDID_PATH"] = str(candid_path.resolve())
    else:
        # Try icp.yaml / dfx.json to find the candid path
        for config_file in ("icp.yaml", "dfx.json"):
            config_path = Path(config_file)
            if config_path.exists():
                with open(config_path) as f:
                    if config_file.endswith(".yaml"):
                        config = yaml.safe_load(f)
                    else:
                        config = json.load(f)
                cp = config.get("canisters", {}).get("realm_backend", {}).get("candid", "")
                if cp and Path(cp).exists():
                    env["CANISTER_CANDID_PATH"] = str(Path(cp).resolve())
                    break

    print("   🔨 Building backend WASM...")
    result = subprocess.run(
        ["python", "-m", "basilisk", "realm_backend", "src/realm_backend/main.py"],
        env=env,
    )
    if result.returncode != 0:
        print("❌ Backend build failed")
        sys.exit(1)

    wasm_path = ".basilisk/realm_backend/realm_backend.wasm"
    if not Path(wasm_path).exists():
        print(f"❌ WASM not found at {wasm_path}")
        sys.exit(1)

    # Deploy
    print(f"   📦 Installing WASM to {backend_id}...")

    # Top up cycles first
    subprocess.run(
        [ICP_CLI, "canister", "top-up", backend_id, "--amount", "1000000000000", "-e", network],
        env=env, capture_output=True,
    )

    result = subprocess.run(
        [ICP_CLI, "canister", "install", backend_id,
         "--wasm", wasm_path,
         "-e", network,
         "--mode", mode,
         "--yes"],
        env=env,
    )
    if result.returncode != 0:
        print("❌ Backend deploy failed")
        sys.exit(1)

    print(f"   ✅ Backend deployed to {backend_id}")

    # Deploy quarter backends if quarters > 1
    for q in range(1, quarters):
        quarter_name = f"quarter_{q}_backend"
        quarter_id = canister_ids.get(quarter_name)
        if quarter_id:
            print(f"\n   🔨 Building {quarter_name}...")
            # Quarter backends use the same source but different canister name
            cache_dir = Path(f".basilisk/{quarter_name}")
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
            result = subprocess.run(
                ["python", "-m", "basilisk", quarter_name, "src/realm_backend/main.py"],
                env=env,
            )
            if result.returncode != 0:
                print(f"   ⚠️  {quarter_name} build failed, skipping")
                continue
            quarter_wasm = f".basilisk/{quarter_name}/{quarter_name}.wasm"
            if Path(quarter_wasm).exists():
                subprocess.run(
                    [ICP_CLI, "canister", "top-up", quarter_id, "--amount", "1000000000000", "-e", network],
                    env=env, capture_output=True,
                )
                result = subprocess.run(
                    [ICP_CLI, "canister", "install", quarter_id,
                     "--wasm", quarter_wasm,
                     "-e", network,
                     "--mode", mode,
                     "--yes"],
                    env=env,
                )
                if result.returncode == 0:
                    print(f"   ✅ {quarter_name} deployed to {quarter_id}")
                else:
                    print(f"   ⚠️  {quarter_name} deploy failed")


def deploy_frontend(
    network: str,
    mode: str,
    canister_ids: dict,
    core_path: str,
    manifest_path: str,
    env: dict,
) -> None:
    """Deploy frontend canister only."""
    frontend_id = canister_ids.get("realm_frontend")
    if not frontend_id:
        print("❌ No realm_frontend canister ID resolved. Cannot deploy frontend.")
        sys.exit(1)

    print(f"\n⚡ Deploying frontend to {frontend_id} on {network} (mode={mode})")

    frontend_dir = Path("src/realm_frontend")
    if not frontend_dir.exists():
        print(f"❌ Frontend source not found: {frontend_dir}")
        sys.exit(1)

    # Copy realm assets from manifest directory
    if manifest_path:
        manifest_dir = Path(manifest_path).parent
        static_images = frontend_dir / "static" / "images"
        static_images.mkdir(parents=True, exist_ok=True)

        for img_name in ("emblem.png", "logo.svg", "logo.png"):
            src = manifest_dir / img_name
            if src.exists():
                dest = static_images / ("realm_logo" + src.suffix)
                shutil.copy2(src, dest)
                print(f"   🖼️  Copied {img_name} → {dest}")

        for img_name in ("background.png", "welcome.png", "background.jpg"):
            src = manifest_dir / img_name
            if src.exists():
                dest = static_images / ("welcome" + src.suffix)
                shutil.copy2(src, dest)
                print(f"   🖼️  Copied {img_name} → {dest}")

    # Ensure declarations/realm_backend exists (normally created during full deploy)
    decl_dir = frontend_dir / "src" / "lib" / "declarations" / "realm_backend"
    if not decl_dir.exists():
        print("   📋 Generating declarations for realm_backend...")
        backend_id = canister_ids.get("realm_backend", "")

        # Find the JS IDL factory from a previous deploy in .realms/
        did_js_src = None
        realms_dir = Path(".realms")
        if realms_dir.exists():
            import glob
            candidates = sorted(
                glob.glob(str(realms_dir / "**/declarations/realm_backend/realm_backend.did.js"), recursive=True),
                key=os.path.getmtime, reverse=True,
            )
            if candidates:
                did_js_src = candidates[0]

        if did_js_src:
            decl_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(did_js_src, decl_dir / "realm_backend.did.js")

            index_js = (
                'import { Actor, HttpAgent } from "@dfinity/agent";\n'
                'import { idlFactory } from "./realm_backend.did.js";\n'
                'export { idlFactory } from "./realm_backend.did.js";\n'
                f'export const canisterId = "{backend_id}";\n'
                'export const createActor = (canisterId, options = {}) => {\n'
                '  const agent = options.agent || new HttpAgent({ ...options.agentOptions });\n'
                '  if (options.agent && options.agentOptions) {\n'
                '    console.warn("Detected both agent and agentOptions passed to createActor. Ignoring agentOptions and proceeding with the provided agent.");\n'
                '  }\n'
                '  if (process.env.DFX_NETWORK !== "ic") {\n'
                '    agent.fetchRootKey().catch((err) => {\n'
                '      console.warn("Unable to fetch root key. Check to ensure that your local replica is running");\n'
                '      console.error(err);\n'
                '    });\n'
                '  }\n'
                '  return Actor.createActor(idlFactory, { agent, canisterId, ...options.actorOptions });\n'
                '};\n'
            )
            (decl_dir / "index.js").write_text(index_js)
            print(f"   ✅ Declarations generated (canisterId={backend_id})")
        else:
            print("   ⚠️  No previous declarations found in .realms/. Run a full deploy first.")

    # Install npm deps and build
    print("   📥 Installing npm dependencies...")
    subprocess.run(
        ["npm", "install", "--legacy-peer-deps"],
        cwd=str(frontend_dir), env=env, check=True,
    )

    print("   🔨 Building frontend...")
    subprocess.run(
        ["npm", "run", "build"],
        cwd=str(frontend_dir), env=env, check=True,
    )

    # Deploy frontend assets
    print(f"   📦 Deploying to {frontend_id}...")
    subprocess.run(
        [ICP_CLI, "canister", "top-up", frontend_id, "--amount", "500000000000", "-e", network],
        env=env, capture_output=True,
    )

    result = subprocess.run(
        [ICP_CLI, "deploy", "realm_frontend",
         "-e", network,
         "--mode", mode,
         "--yes"],
        env=env,
    )
    if result.returncode != 0:
        print("❌ Frontend deploy failed")
        sys.exit(1)

    print(f"   ✅ Frontend deployed to {frontend_id}")


def deploy_full(
    descriptor: dict,
    env: dict,
) -> None:
    """Deploy using the existing realms CLI (full pipeline)."""
    obj_type = descriptor["type"]
    network = descriptor["network"]
    mode = descriptor["mode"]
    manifest = descriptor["manifest"]
    parameters = descriptor["parameters"]

    demo_flag = ""
    if parameters.get("TEST_MODE_DEMO_DATA") is False or parameters.get("NO_DEMO_DATA"):
        demo_flag = "--no-demo-data"

    if obj_type == "mundus":
        print(f"\n🌍 Deploying full mundus to {network}...")
        cmd = [
            "realms", "mundus", "create",
            "--manifest", manifest,
            "--network", network,
            "--deploy",
            "--mode", mode,
        ]
        if demo_flag:
            cmd.append(demo_flag)

    elif obj_type == "realm":
        print(f"\n🏛️  Deploying realm to {network}...")
        cmd = [
            "realms", "realm", "create",
            "--manifest", manifest,
            "--network", network,
            "--deploy",
            "--mode", mode,
        ]
        if mode == "reinstall":
            cmd.append("--random")
        if demo_flag:
            cmd.append(demo_flag)

    elif obj_type == "registry":
        print(f"\n📋 Deploying registry to {network}...")
        cmd = [
            "realms", "registry", "create",
            "--network", network,
            "--deploy",
            "--mode", mode,
        ]
        if demo_flag:
            cmd.append(demo_flag)

    else:
        print(f"❌ Unknown type: {obj_type}")
        sys.exit(1)

    print(f"   Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        print(f"❌ Deployment failed with exit code {result.returncode}")
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Unified deployment for Realms (issue #160)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backend hotfix from local source
  python scripts/deploy.py --file deployments/staging-realm2-backend.yml

  # Override subtypes to deploy only backend from a mundus descriptor
  python scripts/deploy.py --file deployments/staging-mundus.yml --subtypes backend

  # Override network
  python scripts/deploy.py --file deployments/staging-realm1-backend.yml --network demo
        """,
    )
    parser.add_argument(
        "--file", "-f", required=True,
        help="Path to deployment descriptor YAML",
    )
    parser.add_argument(
        "--subtypes", "-s",
        help="Override subtypes (comma-separated: backend,frontend,all)",
    )
    parser.add_argument(
        "--network", "-n",
        help="Override network",
    )
    parser.add_argument(
        "--mode", "-m",
        help="Override mode (upgrade, reinstall)",
    )
    parser.add_argument(
        "--identity",
        help="Identity PEM file or identity name",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be done without actually deploying",
    )

    args = parser.parse_args()

    # Load descriptor
    descriptor = load_descriptor(args.file)

    # Apply overrides
    if args.subtypes:
        descriptor["subtypes"] = [s.strip() for s in args.subtypes.split(",")]
    if args.network:
        descriptor["network"] = args.network
    if args.mode:
        descriptor["mode"] = args.mode

    # Print deployment plan
    print("╭────────────────────────────────────────╮")
    print("│ 🚀 Unified Deployment (issue #160)     │")
    print("╰────────────────────────────────────────╯")
    print(f"📄 Descriptor:  {args.file}")
    print(f"🎯 Type:        {descriptor['type']}")
    print(f"🔧 Subtypes:    {', '.join(descriptor['subtypes'])}")
    print(f"🏛️  Quarters:    {descriptor['quarters']}")
    print(f"📝 Manifest:    {descriptor['manifest']}")
    print(f"📡 Network:     {descriptor['network']}")
    print(f"🔄 Mode:        {descriptor['mode']}")
    print(f"💻 Core:        {descriptor['core_codebase']}")
    print(f"🧩 Extensions:  {descriptor['extensions_codebase']}")
    print(f"📜 Codices:     {descriptor['codices_codebase']}")
    if descriptor["id_in_registry"]:
        print(f"🔢 Registry ID: {descriptor['id_in_registry']}")
    if descriptor["parameters"]:
        print(f"⚙️  Parameters:  {descriptor['parameters']}")
    print()

    if args.dry_run:
        print("🏁 Dry run — no changes made.")
        return

    # Set up environment variables from parameters
    env = set_vite_env_vars(descriptor["parameters"])

    # Handle identity
    if args.identity:
        if Path(args.identity).exists():
            # PEM file — import it
            print(f"🔐 Importing identity from {args.identity}...")
            subprocess.run(
                [ICP_CLI, "identity", "import", "--from-pem", args.identity,
                 "--storage", "plaintext", "deploy_identity"],
                env=env, check=True,
            )
            subprocess.run(
                [ICP_CLI, "identity", "default", "deploy_identity"],
                env=env, check=True,
            )
        else:
            # Identity name
            subprocess.run(
                [ICP_CLI, "identity", "default", args.identity],
                env=env, check=True,
            )

    # Resolve codebases
    temp_dir = tempfile.mkdtemp(prefix="realms_deploy_")
    try:
        core_path = resolve_codebase(descriptor["core_codebase"], "core", temp_dir)
        extensions_path = resolve_codebase(descriptor["extensions_codebase"], "extensions", temp_dir)
        codices_path = resolve_codebase(descriptor["codices_codebase"], "codices", temp_dir)

        subtypes = descriptor["subtypes"]
        is_targeted = subtypes != ["all"] and descriptor["type"] != "mundus"

        if is_targeted:
            # Targeted deployment: deploy specific canister types directly
            # Resolve canister IDs
            canister_ids = {}
            if descriptor["id_in_registry"]:
                canister_ids = resolve_canister_ids_from_registry(
                    descriptor["id_in_registry"],
                    descriptor["network"],
                )
            if not canister_ids:
                canister_ids = resolve_canister_ids_from_files(
                    descriptor["network"],
                    descriptor["manifest"],
                )

            if not canister_ids:
                print("❌ Could not resolve canister IDs. Provide id_in_registry or canister_ids.json.")
                sys.exit(1)

            print(f"\n📋 Resolved canister IDs:")
            for name, cid in canister_ids.items():
                print(f"   {name}: {cid}")

            if "backend" in subtypes:
                deploy_backend(
                    network=descriptor["network"],
                    mode=descriptor["mode"],
                    canister_ids=canister_ids,
                    core_path=core_path,
                    extensions_path=extensions_path,
                    quarters=descriptor["quarters"],
                    env=env,
                )

            if "frontend" in subtypes:
                deploy_frontend(
                    network=descriptor["network"],
                    mode=descriptor["mode"],
                    canister_ids=canister_ids,
                    core_path=core_path,
                    manifest_path=descriptor["manifest"],
                    env=env,
                )

            # Token and NFT subtypes would follow the same pattern
            if "token" in subtypes:
                token_id = canister_ids.get("token_backend")
                if token_id:
                    print(f"\n⚡ Token backend deploy not yet implemented (canister: {token_id})")
                else:
                    print("   ⚠️  No token_backend canister ID found, skipping")

            if "nft" in subtypes:
                nft_id = canister_ids.get("nft_backend")
                if nft_id:
                    print(f"\n⚡ NFT backend deploy not yet implemented (canister: {nft_id})")
                else:
                    print("   ⚠️  No nft_backend canister ID found, skipping")

        else:
            # Full deployment: use the existing realms CLI pipeline
            deploy_full(descriptor, env)

    finally:
        # Clean up temp directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n✅ Deployment completed!")


if __name__ == "__main__":
    main()
