#!/usr/bin/env python3
"""
Mundus Generator - Creates independent multi-realm deployments

This script creates a mundus (multi-realm universe) with:
- 3 independent realms (realm1, realm2, realm3)
- 1 central registry
- Each realm has complete independent source code
"""

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def create_mundus(
    mundus_name: str,
    output_dir: Path,
    manifest_path: "Path | None" = None
):
    """Create a new mundus using a manifest template."""
    
    print(f"\n🌍 Creating Mundus: {mundus_name}\n")
    
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    # Create mundus structure
    mundus_dir = output_dir
    mundus_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Mundus directory: {mundus_dir}")
    
    # Use demo manifest as default if not specified
    if manifest_path is None:
        manifest_path = repo_root / "examples" / "demo" / "manifest.json"
    
    if not manifest_path.exists():
        print(f"❌ Manifest not found: {manifest_path}")
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    
    # Load the manifest
    with open(manifest_path, 'r') as f:
        mundus_manifest = json.load(f)
    
    # Override name if provided
    if mundus_name:
        mundus_manifest["name"] = mundus_name
    
    # Ensure type is set
    mundus_manifest["type"] = "mundus"
    
    # Copy manifest to mundus directory
    mundus_manifest_path = mundus_dir / "manifest.json"
    with open(mundus_manifest_path, 'w') as f:
        json.dump(mundus_manifest, f, indent=2)
    print(f"📄 Copied mundus manifest: {mundus_manifest_path}")
    
    realms = mundus_manifest.get("realms", [])
    registries = mundus_manifest.get("registries", [])
    
    print(f"📁 Creating {len(realms)} realms + {len(registries)} registries...\n")
    
    # Create unified dfx.json for the mundus
    create_mundus_dfx_json(mundus_dir, repo_root, realms, registries)
    print(f"📄 Created unified dfx.json")
    
    # Create each realm using the existing CLI command
    for realm_id in realms:
        realm_dir = mundus_dir / realm_id
        
        print(f"\n  📦 Creating {realm_id}...")
        
        # Read realm manifest to get options
        realm_manifest_path = repo_root / "examples" / "demo" / realm_id / "manifest.json"
        realm_options = {}
        if realm_manifest_path.exists():
            with open(realm_manifest_path, 'r') as f:
                realm_manifest = json.load(f)
                realm_options = realm_manifest.get("options", {}).get("random", {})
        
        # Build realms realm create command with manifest
        cmd = [
            "realms", "realm", "create",
            "--output-dir", str(realm_dir),
            "--realm-name", realm_id.replace("_", " ").title(),
            "--manifest", str(realm_manifest_path)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, cwd=repo_root)
        except subprocess.CalledProcessError as e:
            print(f"     ❌ Error creating {realm_id}: {e}")
            raise
        
        print(f"     ✅ {realm_id} created")
    
    # Create registry
    print(f"\n  📦 Creating registry...")
    create_registry(mundus_dir, repo_root)
    print(f"     ✅ Registry created")
    
    print(f"\n✅ Mundus '{mundus_name}' created successfully at: {mundus_dir}\n")
    print(f"📊 Structure:")
    print(f"  - realm1/ (independent realm)")
    print(f"  - realm2/ (independent realm)")
    print(f"  - realm3/ (independent realm)")
    print(f"  - registry/ (central registry)")


def create_mundus_dfx_json(mundus_dir: Path, repo_root: Path, realms: list, registries: list):
    """Create a unified dfx.json file for the entire mundus."""
    
    # Read the template dfx.json from repo root
    template_dfx = repo_root / "dfx.json"
    
    with open(template_dfx, 'r') as f:
        dfx_config = json.load(f)
    
    # Create new config with all mundus canisters
    new_config = {
        "dfx": dfx_config.get("dfx", "0.29.0"),
        "canisters": {}
    }
    
    # Add each realm's backend and frontend from the manifest
    for realm_id in realms:
        
        # Backend
        new_config["canisters"][f"{realm_id}_backend"] = {
            "build": f"python -m kybra {realm_id}_backend {realm_id}/src/realm_backend/main.py",
            "candid": f"{realm_id}/src/realm_backend/realm_backend.did",
            "declarations": {
                "output": f"{realm_id}/src/realm_frontend/src/declarations",
                "node_compatibility": True
            },
            "gzip": True,
            "metadata": [{"name": "candid:service"}],
            "tech_stack": {
                "cdk": {"kybra": {}},
                "language": {"python": {}}
            },
            "type": "custom",
            "wasm": f".kybra/{realm_id}_backend/{realm_id}_backend.wasm"
        }
        
        # Frontend
        new_config["canisters"][f"{realm_id}_frontend"] = {
            "source": [f"{realm_id}/src/realm_frontend/dist"],
            "type": "assets",
            "workspace": "realm_frontend"
        }
    
    # Add registry backend and frontend
    new_config["canisters"]["realm_registry_backend"] = {
        "build": "python -m kybra realm_registry_backend registry/src/realm_registry_backend/main.py",
        "candid": "registry/src/realm_registry_backend/realm_registry_backend.did",
        "declarations": {
            "output": "registry/src/realm_registry_frontend/src/declarations",
            "node_compatibility": True
        },
        "gzip": True,
        "metadata": [{"name": "candid:service"}],
        "tech_stack": {
            "cdk": {"kybra": {}},
            "language": {"python": {}}
        },
        "type": "custom",
        "wasm": ".kybra/realm_registry_backend/realm_registry_backend.wasm"
    }
    
    new_config["canisters"]["realm_registry_frontend"] = {
        "source": ["registry/src/realm_registry_frontend/dist"],
        "type": "assets",
        "workspace": "realm_registry_frontend"
    }
    
    # Add networks if they exist in template
    if "networks" in dfx_config:
        new_config["networks"] = dfx_config["networks"]
    
    # Write unified dfx.json to mundus directory
    with open(mundus_dir / "dfx.json", 'w') as f:
        json.dump(new_config, f, indent=2)




def create_registry(mundus_dir: Path, repo_root: Path):
    """Create the central registry by copying source code."""
    
    registry_dir = mundus_dir / "registry"
    registry_dir.mkdir(exist_ok=True)
    (registry_dir / "src").mkdir(exist_ok=True)
    
    # Copy registry source code
    registry_backend_src = repo_root / "src" / "realm_registry_backend"
    registry_frontend_src = repo_root / "src" / "realm_registry_frontend"
    
    if registry_backend_src.exists():
        shutil.copytree(
            registry_backend_src,
            registry_dir / "src" / "realm_registry_backend",
            dirs_exist_ok=True
        )
    
    if registry_frontend_src.exists():
        shutil.copytree(
            registry_frontend_src,
            registry_dir / "src" / "realm_registry_frontend",
            dirs_exist_ok=True
        )
    
    # No separate dfx.json needed - using unified dfx.json at mundus level


def generate_realm_data(
    realm_dir: Path,
    realm_id: str,
    realm_name: str,
    members: int,
    organizations: int,
    transactions: int,
    disputes: int,
    seed: int,
    repo_root: Path
):
    """Generate random data for a realm using the existing generator."""
    
    # Call the existing realm_generator.py script
    cmd = [
        "python",
        str(repo_root / "scripts" / "realm_generator.py"),
        "--output-dir", str(realm_dir),
        "--realm-name", realm_name,
        "--members", str(members),
        "--organizations", str(organizations),
        "--transactions", str(transactions),
        "--disputes", str(disputes),
        "--demo-folder", realm_id
    ]
    
    if seed is not None:
        cmd.extend(["--seed", str(seed)])
    
    subprocess.run(cmd, check=True, capture_output=True)


def main():
    parser = argparse.ArgumentParser(description="Generate a multi-realm mundus from manifest")
    parser.add_argument("--mundus-name", type=str, default="Demo Mundus", help="Name of the mundus")
    parser.add_argument("--output-dir", type=str, default=".realms/mundus", help="Output directory")
    parser.add_argument("--manifest", type=str, help="Path to mundus manifest.json (default: examples/demo/manifest.json)")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    manifest_path = Path(args.manifest) if args.manifest else None
    
    create_mundus(
        mundus_name=args.mundus_name,
        output_dir=output_dir,
        manifest_path=manifest_path
    )


if __name__ == "__main__":
    main()
