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
import os
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
    
    # Create src directory for all canisters
    src_dir = mundus_dir / "src"
    src_dir.mkdir(exist_ok=True)
    
    # Copy extensions once to mundus root (shared by all realms)
    extensions_src = repo_root / "extensions"
    extensions_dest = mundus_dir / "extensions"
    
    if extensions_src.exists():
        shutil.copytree(extensions_src, extensions_dest, dirs_exist_ok=True)
        print(f"\n📁 Copied extensions source to mundus/extensions/")
    
    # Copy source code for each realm to flattened structure
    for realm_id in realms:
        print(f"\n  📦 Creating {realm_id}...")
        
        # Copy backend source
        backend_src = repo_root / "src" / "realm_backend"
        backend_dest = src_dir / f"{realm_id}_backend"
        
        if backend_src.exists():
            shutil.copytree(backend_src, backend_dest, dirs_exist_ok=True)
            print(f"     ✅ Copied backend to src/{realm_id}_backend/")
        
        # Copy frontend source
        frontend_src = repo_root / "src" / "realm_frontend"
        frontend_dest = src_dir / f"{realm_id}_frontend"
        
        if frontend_src.exists():
            shutil.copytree(frontend_src, frontend_dest, dirs_exist_ok=True)
            print(f"     ✅ Copied frontend to src/{realm_id}_frontend/")
        
        # Install extensions for this realm
        if extensions_dest.exists():
            print(f"     🔌 Installing extensions for {realm_id}...")
            
            # Create a temporary realm structure for extension installation
            # The extension installer expects src/ to be in the current directory
            realm_temp_dir = mundus_dir / f"_temp_{realm_id}"
            realm_temp_dir.mkdir(exist_ok=True)
            
            # Create src symlinks
            realm_temp_src = realm_temp_dir / "src"
            realm_temp_src.mkdir(exist_ok=True)
            
            # Symlink backend and frontend into temp src/
            temp_backend = realm_temp_src / "realm_backend"
            temp_frontend = realm_temp_src / "realm_frontend"
            
            if not temp_backend.exists():
                os.symlink(backend_dest, temp_backend)
            if not temp_frontend.exists():
                os.symlink(frontend_dest, temp_frontend)
            
            install_cmd = [
                "realms", "extension", "install-from-source",
                "--source-dir", str(extensions_dest)
            ]
            
            try:
                result = subprocess.run(install_cmd, check=True, capture_output=True, cwd=realm_temp_dir, text=True)
                print(f"     ✅ Extensions installed for {realm_id}")
            except subprocess.CalledProcessError as e:
                print(f"     ⚠️  Warning: Extension installation failed for {realm_id}")
                if e.stderr:
                    print(f"        {e.stderr.strip()}")
            finally:
                # Clean up temp directory
                if realm_temp_dir.exists():
                    shutil.rmtree(realm_temp_dir)
        
        print(f"     ✅ {realm_id} created")
    
    # Create registry in flattened structure
    print(f"\n  📦 Creating registry...")
    
    # Copy registry backend
    registry_backend_src = repo_root / "src" / "realm_registry_backend"
    registry_backend_dest = src_dir / "realm_registry_backend"
    
    if registry_backend_src.exists():
        shutil.copytree(registry_backend_src, registry_backend_dest, dirs_exist_ok=True)
        print(f"     ✅ Copied backend to src/realm_registry_backend/")
    
    # Copy registry frontend
    registry_frontend_src = repo_root / "src" / "realm_registry_frontend"
    registry_frontend_dest = src_dir / "realm_registry_frontend"
    
    if registry_frontend_src.exists():
        shutil.copytree(registry_frontend_src, registry_frontend_dest, dirs_exist_ok=True)
        print(f"     ✅ Copied frontend to src/realm_registry_frontend/")
    
    print(f"     ✅ Registry created")
    
    print(f"\n✅ Mundus '{mundus_name}' created successfully at: {mundus_dir}\n")
    print(f"📊 Structure:")
    print(f"  - extensions/ (shared by all realms)")
    print(f"  - src/realm1_backend/ (with installed extensions)")
    print(f"  - src/realm1_frontend/ (with installed extensions)")
    print(f"  - src/realm2_backend/ (with installed extensions)")
    print(f"  - src/realm2_frontend/ (with installed extensions)")
    print(f"  - src/realm3_backend/ (with installed extensions)")
    print(f"  - src/realm3_frontend/ (with installed extensions)")
    print(f"  - src/realm_registry_backend/")
    print(f"  - src/realm_registry_frontend/")
    print(f"  - dfx.json (unified for all canisters)")


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
            "build": f"python -m kybra {realm_id}_backend src/{realm_id}_backend/main.py",
            "candid": f"src/{realm_id}_backend/realm_backend.did",
            "declarations": {
                "output": f"src/{realm_id}_frontend/src/declarations",
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
            "source": [f"src/{realm_id}_frontend/dist"],
            "type": "assets",
            "workspace": "realm_frontend"
        }
    
    # Add registry backend and frontend
    new_config["canisters"]["realm_registry_backend"] = {
        "build": "python -m kybra realm_registry_backend src/realm_registry_backend/main.py",
        "candid": "src/realm_registry_backend/realm_registry_backend.did",
        "declarations": {
            "output": "src/realm_registry_frontend/src/declarations",
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
        "source": ["src/realm_registry_frontend/dist"],
        "type": "assets",
        "workspace": "realm_registry_frontend"
    }
    
    # Add networks if they exist in template
    if "networks" in dfx_config:
        new_config["networks"] = dfx_config["networks"]
    
    # Write unified dfx.json to mundus directory
    with open(mundus_dir / "dfx.json", 'w') as f:
        json.dump(new_config, f, indent=2)




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
