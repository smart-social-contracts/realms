"""Create command for generating new realms with demo data and deployment scripts."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..constants import REALM_FOLDER
from ..utils import get_scripts_path, is_repo_mode, run_in_docker
from .deploy import _deploy_realm_internal

console = Console()


def _generate_single_realm(
    realm_name: str,
    realm_folder: str,
    output_path: Path,
    repo_root: Path,
    random: bool,
    members: int,
    organizations: int,
    transactions: int,
    disputes: int,
    seed: Optional[int],
) -> None:
    """Generate a single realm with its data and configuration."""
    console.print(f"\n[bold cyan]  📦 Generating {realm_name}...[/bold cyan]")
    
    # Create realm output directory
    realm_output = output_path / realm_folder
    realm_output.mkdir(parents=True, exist_ok=True)
    
    # Copy manifest from examples/demo/{realm_folder}/
    demo_realm_dir = repo_root / "examples" / "demo" / realm_folder
    demo_manifest = demo_realm_dir / "manifest.json"
    
    if demo_manifest.exists():
        # Copy manifest
        with open(demo_manifest, 'r') as f:
            manifest_data = json.load(f)
        
        # Optionally override name if different
        if "name" not in manifest_data or manifest_data["name"] != realm_name:
            manifest_data["name"] = realm_name
        
        manifest_path = realm_output / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2)
            f.write("\n")
        console.print(f"     ✅ Copied manifest from {demo_realm_dir}")
    else:
        console.print(f"     ⚠️  Warning: No manifest found in {demo_realm_dir}")
    
    if random:
        # Generate random data for this realm
        try:
            scripts_path = get_scripts_path()
            generator_script = scripts_path / "realm_generator.py"
            
            cmd = [
                "python3",
                str(generator_script),
                "--members",
                str(members),
                "--organizations",
                str(organizations),
                "--transactions",
                str(transactions),
                "--disputes",
                str(disputes),
                "--output-dir",
                str(realm_output),
                "--realm-name",
                realm_name,
            ]
            
            # Only pass --demo-folder if it exists (for multi-realm mundus with demo folders)
            demo_realm_dir = repo_root / "examples" / "demo" / realm_folder
            if demo_realm_dir.exists():
                cmd.extend(["--demo-folder", realm_folder])
            
            if seed:
                cmd.extend(["--seed", str(seed)])
            
            # Run in Docker if in image mode, otherwise run locally
            if is_repo_mode():
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
            else:
                result = run_in_docker(cmd, working_dir=Path.cwd())
            
            if result.returncode != 0:
                console.print(f"[red]     ❌ Error generating data for {realm_name}:[/red]")
                console.print(f"[red]{result.stderr}[/red]")
                raise typer.Exit(1)
            
            console.print(f"[green]     ✅ Generated random data for {realm_name}[/green]")
        
        except Exception as e:
            console.print(f"[red]     ❌ Error: {e}[/red]")
            raise typer.Exit(1)


def create_command(
    output_dir: str,
    realm_name: str,
    manifest: Optional[str],
    random: bool,
    members: Optional[int],
    organizations: Optional[int],
    transactions: Optional[int],
    disputes: Optional[int],
    seed: Optional[int],
    network: str,
    deploy: bool,
    identity: Optional[str] = None,
    mode: str = "upgrade",
) -> None:
    """Create a new single realm. Flags override manifest values."""
    from ..utils import generate_output_dir_name
    
    console.print(f"[bold blue]🏛️  Creating Realm: {realm_name}[/bold blue]\n")

    # Generate timestamped directory name
    dir_name = generate_output_dir_name("realm", realm_name)
    base_dir = Path(output_dir)
    output_path = base_dir / dir_name
    
    # Create base directory if it doesn't exist
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if generated directory already exists (unlikely with timestamps, but check anyway)
    if output_path.exists() and any(output_path.iterdir()):
        console.print(f"[red]❌ Error: Generated directory already exists and is not empty:[/red]")
        console.print(f"[red]   {output_path.absolute()}[/red]")
        raise typer.Exit(1)
    
    # Create output directory
    output_path.mkdir(exist_ok=True)
    console.print(f"📁 Realm directory: {output_path}\n")

    scripts_path = get_scripts_path()
    
    # Check if we're in repo mode or need to use Docker
    in_repo_mode = is_repo_mode()
    if not in_repo_mode:
        # In Docker/pip install mode - will use Docker container with full repo
        # repo_root should point to /app in the Docker image
        repo_root = Path("/app")
        console.print("[dim]Running in Docker mode (realm_generator will run in container)...[/dim]")
    else:
        repo_root = scripts_path.parent
        if not repo_root.exists() or not (repo_root / "scripts" / "realm_generator.py").exists():
            # In repo mode but scripts missing - error
            console.print("[red]❌ Error: Cannot locate realm_generator.py[/red]")
            console.print("[yellow]Repository structure is incomplete.[/yellow]")
            raise typer.Exit(1)
    
    # Determine if we should use manifest or flags
    has_flags = any([members is not None, organizations is not None, transactions is not None, disputes is not None, seed is not None])
    
    # Load manifest for defaults (if exists)
    realm_options = {}
    if not has_flags or manifest is not None:
        if manifest is None:
            manifest_path = repo_root / "examples" / "demo" / "realm1" / "manifest.json"
        else:
            manifest_path = Path(manifest)
        
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                realm_manifest = json.load(f)
            realm_options = realm_manifest.get("options", {}).get("random", {})
    
    # Call realm_generator.py
    # In Docker mode, paths need to be relative to /workspace mount point
    if in_repo_mode:
        generator_path = str(repo_root / "scripts" / "realm_generator.py")
        output_dir_arg = str(output_path)
    else:
        # In Docker, script is at /app/scripts/realm_generator.py
        # and output_path is mounted at /workspace, so use /workspace as output
        generator_path = "/app/scripts/realm_generator.py"
        output_dir_arg = "/workspace"
    
    cmd = [
        "python",
        generator_path,
        "--output-dir", output_dir_arg,
        "--realm-name", realm_name,
    ]
    
    # Use flags if provided, otherwise fall back to manifest
    if members is not None:
        cmd.extend(["--members", str(members)])
    elif "members" in realm_options:
        cmd.extend(["--members", str(realm_options["members"])])
    
    if organizations is not None:
        cmd.extend(["--organizations", str(organizations)])
    elif "organizations" in realm_options:
        cmd.extend(["--organizations", str(realm_options["organizations"])])
    
    if transactions is not None:
        cmd.extend(["--transactions", str(transactions)])
    elif "transactions" in realm_options:
        cmd.extend(["--transactions", str(realm_options["transactions"])])
    
    if disputes is not None:
        cmd.extend(["--disputes", str(disputes)])
    elif "disputes" in realm_options:
        cmd.extend(["--disputes", str(realm_options["disputes"])])
    
    if seed is not None:
        cmd.extend(["--seed", str(seed)])
    elif "seed" in realm_options:
        cmd.extend(["--seed", str(realm_options["seed"])])
    
    try:
        # Suppress debug output from realm_generator (ggg.user.User objects)
        if in_repo_mode:
            # Run locally in repo
            result = subprocess.run(cmd, check=True, cwd=repo_root, capture_output=True, text=True)
        else:
            # Run in Docker container (pip install mode)
            console.print("[dim]Running realm_generator in Docker container...[/dim]")
            result = run_in_docker(cmd, working_dir=output_path.absolute())
            if result.returncode != 0:
                console.print(f"[red]❌ realm_generator.py failed with exit code {result.returncode}[/red]")
                if result.stdout:
                    console.print("[yellow]stdout:[/yellow]")
                    console.print(result.stdout)
                if result.stderr:
                    console.print("[yellow]stderr:[/yellow]")
                    console.print(result.stderr)
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        
        # Only show important output (skip debug lines)
        for line in result.stdout.split('\n'):
            if line and not 'ggg.user.User object at' in line and not 'from_user' in line and not 'users [' in line:
                console.print(f"[dim]{line}[/dim]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error creating realm: {e}[/red]")
        if e.stderr:
            console.print(f"[red]{e.stderr}[/red]")
        raise typer.Exit(1)
    
    # Copy canister_ids.json from manifest's directory if a manifest was specified
    if manifest is not None:
        manifest_path = Path(manifest)
        if manifest_path.exists():
            canister_ids_source = manifest_path.parent / "canister_ids.json"
            if canister_ids_source.exists():
                canister_ids_dest = output_path / "canister_ids.json"
                shutil.copy2(canister_ids_source, canister_ids_dest)
                console.print(f"\n✅ Copied canister_ids.json from {canister_ids_source.parent}")
    
    # Generate deployment scripts after data generation
    # Check if we can generate scripts (either in repo mode or in Docker image with full repo)
    can_generate_scripts = in_repo_mode or (repo_root / "dfx.json").exists()
    
    if can_generate_scripts:
        _generate_deployment_scripts(output_path, network, realm_name, random, repo_root, deploy, identity, mode, in_repo_mode=in_repo_mode)
    else:
        console.print(f"\n[yellow]⚠️  Deployment scripts not generated (Docker mode without full repo)[/yellow]")
        console.print("[dim]To deploy this realm, you'll need to use the Realms Docker image or clone the full repository.[/dim]")
    
    console.print(f"\n[green]✅ Realm created successfully at: {output_path.absolute()}[/green]")


def _generate_deployment_scripts(
    output_path: Path,
    network: str,
    realm_name: str,
    has_random_data: bool,
    repo_root: Path,
    deploy: bool,
    identity: Optional[str],
    mode: str,
    in_repo_mode: bool = True
):
    """Generate deployment scripts and dfx.json for independent realm."""
    console.print("\n🔧 Generating deployment configuration...")

    # 1. Generate dfx.json for this independent realm
    console.print("\n📝 Creating dfx.json...")
    
    # Load template dfx.json from repo root
    template_dfx = repo_root / "dfx.json"
    if not template_dfx.exists():
        console.print(f"[red]❌ Template dfx.json not found at {template_dfx}[/red]")
        if not in_repo_mode:
            console.print("[yellow]Expected at /app/dfx.json in Docker image[/yellow]")
        raise typer.Exit(1)
    
    with open(template_dfx, 'r') as f:
        dfx_config = json.load(f)
    
    # Create realm-only dfx.json (realm_backend, realm_frontend, and optional local-only canisters)
    # Check if canister_ids.json exists - if so, use standard names to match existing canisters
    # Otherwise, use unique names to avoid conflicts in mundus deployments
    canister_ids_file = output_path / "canister_ids.json"
    
    if canister_ids_file.exists():
        # canister_ids.json exists (from manifest) - use standard names to match existing canisters
        backend_name = "realm_backend"
        frontend_name = "realm_frontend"
        console.print(f"   ✅ Using standard canister names from canister_ids.json")
    else:
        # No canister_ids.json - generate unique names for local/mundus deployments
        sanitized_realm_name = realm_name.lower().replace(" ", "_").replace("-", "_")
        backend_name = f"{sanitized_realm_name}_backend"
        frontend_name = f"{sanitized_realm_name}_frontend"
        console.print(f"   ✅ Using unique canister names: {backend_name}, {frontend_name}")
    
    # Deep copy and update canister configs to avoid reference issues
    import copy
    backend_config = copy.deepcopy(dfx_config["canisters"]["realm_backend"])
    frontend_config = copy.deepcopy(dfx_config["canisters"]["realm_frontend"])
    
    # IMPORTANT: Keep workspace as "realm_frontend" (not unique name)
    # because src/ directories are copied with standard names
    # The workspace field tells dfx where to find package.json, which is at src/realm_frontend/
    
    realm_canisters = {
        backend_name: backend_config,
        frontend_name: frontend_config,
    }
    
    # For local networks, include additional canisters (Internet Identity, ckBTC, etc.)
    is_local_network = network.startswith("local")
    
    if is_local_network:
        # Include Internet Identity for local development (shared across realms)
        if "internet_identity" in dfx_config["canisters"]:
            realm_canisters["internet_identity"] = dfx_config["canisters"]["internet_identity"]
        
        # Include any ICRC-1 ledger canisters if they exist
        for canister_name, canister_config in dfx_config["canisters"].items():
            if any(keyword in canister_name.lower() for keyword in ["icrc1", "ledger"]) and canister_name not in realm_canisters:
                # Use standard name if canister_ids exists, otherwise unique name
                if canister_ids_file.exists():
                    ledger_name = canister_name
                else:
                    sanitized_realm_name = realm_name.lower().replace(" ", "_").replace("-", "_")
                    ledger_name = f"{sanitized_realm_name}_{canister_name}"
                realm_canisters[ledger_name] = canister_config
                console.print(f"   ✅ Including {ledger_name} for local development")
    
    realm_dfx = {
        "canisters": realm_canisters,
        "defaults": dfx_config.get("defaults", {}),
        "networks": dfx_config.get("networks", {}),
        "output_env_file": ".env",
        "version": dfx_config.get("version", 1)
    }
    
    # Write dfx.json
    dfx_json_path = output_path / "dfx.json"
    with open(dfx_json_path, 'w') as f:
        json.dump(realm_dfx, f, indent=2)
    console.print(f"   ✅ dfx.json created")

    # Copy src directories so the realm is fully self-contained and portable
    # This is crucial: deploy_canisters.sh cd's into the realm directory and expects src/ there
    src_dest = output_path / "src"
    if not src_dest.exists():
        src_source = repo_root / "src"
        if src_source.exists():
            # Define patterns to ignore during copy (build artifacts, caches, etc.)
            ignore_patterns = shutil.ignore_patterns(
                'node_modules', '__pycache__', '.kybra', '*.pyc', '.svelte-kit',
                'build', 'dist', '.env', '.env.*', '*.log'
            )
            shutil.copytree(src_source, src_dest, ignore=ignore_patterns)
            console.print(f"   ✅ Copied src/ directory")
        else:
            console.print(f"   ⚠️  Warning: Could not find src directory at {src_source}")
    
    # Copy requirements.txt for venv creation during deployment
    requirements_source = repo_root / "requirements.txt"
    requirements_dest = output_path / "requirements.txt"
    if requirements_source.exists() and not requirements_dest.exists():
        shutil.copy2(requirements_source, requirements_dest)
        console.print(f"   ✅ Copied requirements.txt")
    
    # 2. Create scripts subdirectory
    console.print("\n🔧 Generating deployment scripts...")
    scripts_dir = output_path / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    # Get scripts path (auto-detects repo vs image mode)
    scripts_path = get_scripts_path()

    # 1. Create install_extensions.sh script
    target_install = scripts_dir / "1-install-extensions.sh"
    source_install = scripts_path / "install_extensions.sh"
    if source_install.exists():
        shutil.copy2(source_install, target_install)
        target_install.chmod(0o755)
        console.print(f"   ✅ {target_install.name}")
    else:
        console.print(f"   ❌ Source file not found: {source_install}")

    # 2. Copy deploy_canisters.sh script
    target_deploy = scripts_dir / "2-deploy-canisters.sh"
    source_deploy = scripts_path / "deploy_canisters.sh"
    if source_deploy.exists():
        shutil.copy2(source_deploy, target_deploy)
        target_deploy.chmod(0o755)
        console.print(f"   ✅ {target_deploy.name}")
    else:
        console.print(f"   ❌ Source file not found: {source_deploy}")

    # 3. Copy upload_data.sh script
    target_upload = scripts_dir / "3-upload-data.sh"
    source_upload = scripts_path / "upload_data.sh"
    if source_upload.exists():
        shutil.copy2(source_upload, target_upload)
        target_upload.chmod(0o755)
        console.print(f"   ✅ {target_upload.name}")
    else:
        console.print(f"   ❌ Source file not found: {source_upload}")

    # 4. Copy post_deploy.py script
    target_post_deploy = scripts_dir / "4-post-deploy.py"
    source_post_deploy = scripts_path / "post_deploy.py"
    if source_post_deploy.exists():
        shutil.copy2(source_post_deploy, target_post_deploy)
        target_post_deploy.chmod(0o755)
        console.print(f"   ✅ {target_post_deploy.name}")
    else:
        console.print(f"   ❌ Source file not found: {source_post_deploy}")
    
    # Note: canister_init.py is optional and realm-specific
    # It will be created by realm_generator.py if needed, or users can add it manually

    console.print(f"\n[green]🎉 Realm '{realm_name}' created successfully![/green]")
    
    if deploy:
        console.print("\n[yellow]🚀 Auto-deployment requested...[/yellow]")
        try:
            # Deploy the single realm using the internal deploy function
            _deploy_realm_internal(
                config_file=None, 
                folder=str(output_path),  # Use the generated realm directory
                network=network, 
                clean=False, 
                identity=identity, 
                mode=mode
            )
        except typer.Exit as e:
            console.print(
                f"[red]❌ Auto-deployment failed with exit code: {e.exit_code}[/red]"
            )
            raise
        except Exception as e:
            console.print(f"[red]❌ Auto-deployment failed: {e}[/red]")
            raise typer.Exit(1)
    else:
        console.print("\n[yellow]📝 Next steps:[/yellow]")
        console.print(f"   1. Deploy: realms realm deploy --folder {output_path}")
        console.print(f"   2. Or run: cd {output_path} && bash scripts/2-deploy-canisters.sh")
