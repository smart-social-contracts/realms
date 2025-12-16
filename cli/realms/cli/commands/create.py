"""Create command for generating new realms with demo data and deployment scripts."""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..constants import REALM_FOLDER
from ..generator import RealmGenerator
from ..utils import get_scripts_path, is_repo_mode
from .deploy import _deploy_realm_internal

console = Console()


def _replace_timestamp_placeholders(extensions_dir: Path) -> None:
    """Replace timestamp placeholders in extension data JSON files.
    
    Placeholders:
    - __REALM_CREATION_TIME__: Current timestamp in format "YYYY-MM-DD HH:MM:SS.000"
    - __VOTING_DEADLINE_24H__: 24 hours from now in ISO format
    """
    now = datetime.utcnow()
    creation_time = now.strftime("%Y-%m-%d %H:%M:%S.000")
    voting_deadline = (now + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Find all JSON files in extensions/*/data/ directories
    for data_dir in extensions_dir.glob("*/data"):
        if data_dir.is_dir():
            for json_file in data_dir.glob("*.json"):
                try:
                    content = json_file.read_text(encoding="utf-8")
                    
                    # Check if file contains any placeholders
                    if "__REALM_CREATION_TIME__" in content or "__VOTING_DEADLINE_24H__" in content:
                        content = content.replace("__REALM_CREATION_TIME__", creation_time)
                        content = content.replace("__VOTING_DEADLINE_24H__", voting_deadline)
                        json_file.write_text(content, encoding="utf-8")
                except Exception as e:
                    console.print(f"   ⚠️  Warning: Could not process {json_file}: {e}")


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
        
        # Copy logo file if specified in manifest
        logo_filename = manifest_data.get("logo", "")
        if logo_filename:
            logo_source = demo_realm_dir / logo_filename
            if logo_source.exists():
                shutil.copy2(logo_source, realm_output / logo_filename)
                console.print(f"     ✅ Copied logo: {logo_filename}")
            else:
                console.print(f"     ⚠️  Warning: Logo file not found: {logo_source}")
    else:
        console.print(f"     ⚠️  Warning: No manifest found in {demo_realm_dir}")
    
    if random:
        # Generate random data for this realm using bundled generator
        try:
            generator = RealmGenerator(seed) if seed else RealmGenerator()
            
            realm_data = generator.generate_realm_data(
                members=members,
                organizations=organizations,
                transactions=transactions,
                disputes=disputes,
                realm_name=realm_name
            )
            
            # Save realm data JSON
            json_file = realm_output / "realm_data.json"
            realm_data_serialized = [obj.serialize() for obj in realm_data]
            with open(json_file, 'w') as f:
                json.dump(realm_data_serialized, f, indent=2)
            
            # Generate codex files
            generator.generate_codex_files(realm_output)
            
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
    bare: bool = False,
) -> None:
    """Create a new single realm. Flags override manifest values.
    
    Args:
        bare: If True, skip data generation and only deploy canisters (no extensions/data)
    """
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
    
    # Check if we're in repo mode or pip-installed mode
    in_repo_mode = is_repo_mode()
    if not in_repo_mode:
        # In pip-installed mode - use bundled files from package
        # The package includes src, extensions, scripts via symlinks at realms/ level
        # dfx.template.json and requirements.txt are in cli/ directory
        package_root = Path(__file__).parent.parent.parent  # cli/commands -> cli -> realms
        repo_root = package_root
        console.print("[dim]Running in pip-installed mode (using bundled files)...[/dim]")
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
            
            # Copy manifest to output directory
            dest_manifest = output_path / "manifest.json"
            with open(dest_manifest, 'w') as f:
                realm_manifest["name"] = realm_name  # Update name
                json.dump(realm_manifest, f, indent=2)
            console.print(f"✅ Copied manifest from {manifest_path.parent}")
            
            # Copy logo file if specified in manifest
            logo_filename = realm_manifest.get("logo", "")
            if logo_filename:
                logo_source = manifest_path.parent / logo_filename
                if logo_source.exists():
                    shutil.copy2(logo_source, output_path / logo_filename)
                    console.print(f"✅ Copied logo: {logo_filename}")
                else:
                    console.print(f"[yellow]⚠️  Logo file not found: {logo_source}[/yellow]")
    
    # Use bundled RealmGenerator directly
    try:
        # Determine parameters from flags or manifest
        gen_members = members if members is not None else realm_options.get("members", 50)
        gen_organizations = organizations if organizations is not None else realm_options.get("organizations", 5)
        gen_transactions = transactions if transactions is not None else realm_options.get("transactions", 100)
        gen_disputes = disputes if disputes is not None else realm_options.get("disputes", 10)
        gen_seed = seed if seed is not None else realm_options.get("seed")
        
        # Create generator
        generator = RealmGenerator(gen_seed) if gen_seed else RealmGenerator()
        
        # Generate realm data
        console.print("[dim]Generating realm data...[/dim]")
        realm_data = generator.generate_realm_data(
            members=gen_members,
            organizations=gen_organizations,
            transactions=gen_transactions,
            disputes=gen_disputes,
            realm_name=realm_name
        )
        
        # Save realm data JSON
        json_file = output_path / "realm_data.json"
        realm_data_serialized = [obj.serialize() for obj in realm_data]
        with open(json_file, 'w') as f:
            json.dump(realm_data_serialized, f, indent=2)
        console.print(f"[dim]Generated realm data saved to: {json_file}[/dim]")
        
        # Generate codex files
        codex_files = generator.generate_codex_files(output_path)
        console.print(f"[dim]Generated {len(codex_files)} codex files[/dim]")
        
        console.print(f"[dim]Seed used: {generator.seed}[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ Error creating realm: {e}[/red]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/red]")
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
    # Check if we can generate scripts - look in cli directory first (pip-installed), then repo root
    cli_dir = Path(__file__).parent.parent  # cli/commands -> cli
    can_generate_scripts = (cli_dir / "dfx.template.json").exists() or (repo_root / "dfx.template.json").exists()
    
    if can_generate_scripts:
        _generate_deployment_scripts(output_path, network, realm_name, random, repo_root, deploy, identity, mode, bare, in_repo_mode=in_repo_mode)
    else:
        console.print(f"\n[yellow]⚠️  Deployment scripts not generated (bundled files not found)[/yellow]")
        console.print(f"[dim]Searched: {cli_dir / 'dfx.template.json'}, {repo_root / 'dfx.template.json'}[/dim]")
    
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
    bare: bool,
    in_repo_mode: bool = True
):
    """Generate deployment scripts and dfx.json for independent realm.
    
    Args:
        bare: If True, skip extensions and data upload during deployment
    """
    console.print("\n🔧 Generating deployment configuration...")

    # 1. Generate dfx.json for this independent realm
    console.print("\n📝 Creating dfx.json...")
    
    # Load template dfx.json - check cli directory first (pip-installed), then repo root
    cli_dir = Path(__file__).parent.parent  # cli/commands -> cli
    template_dfx = cli_dir / "dfx.template.json"
    if not template_dfx.exists():
        template_dfx = repo_root / "dfx.template.json"
    if not template_dfx.exists():
        console.print(f"[red]❌ Template dfx.template.json not found[/red]")
        console.print(f"[dim]Searched: {cli_dir / 'dfx.template.json'}, {repo_root / 'dfx.template.json'}[/dim]")
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
    
    # Get the deploying user's principal for local ledger initialization
    deployer_principal = None
    if is_local_network:
        try:
            result = subprocess.run(
                ["dfx", "identity", "get-principal"],
                capture_output=True, text=True, check=True
            )
            deployer_principal = result.stdout.strip()
            console.print(f"   ✅ Deployer principal: {deployer_principal}")
        except Exception as e:
            console.print(f"   ⚠️  Could not get deployer principal: {e}")
    
    if is_local_network:
        # Include Internet Identity for local development (shared across realms)
        if "internet_identity" in dfx_config["canisters"]:
            realm_canisters["internet_identity"] = dfx_config["canisters"]["internet_identity"]
        
        # Include any ICRC-1 ledger canisters if they exist
        for canister_name, canister_config in dfx_config["canisters"].items():
            if any(keyword in canister_name.lower() for keyword in ["icrc1", "ledger", "indexer"]) and canister_name not in realm_canisters:
                # Use standard name if canister_ids exists, otherwise unique name
                if canister_ids_file.exists():
                    ledger_name = canister_name
                else:
                    sanitized_realm_name = realm_name.lower().replace(" ", "_").replace("-", "_")
                    ledger_name = f"{sanitized_realm_name}_{canister_name}"
                
                # Deep copy the config to avoid modifying the template
                ledger_config = copy.deepcopy(canister_config)
                
                # Update init_arg for ckbtc_ledger to include initial balance for deployer
                if "ckbtc" in canister_name.lower() and "ledger" in canister_name.lower() and deployer_principal:
                    if "init_arg" in ledger_config:
                        # Replace minting_account and initial_balances in existing init_arg
                        init_arg = ledger_config["init_arg"]
                        init_arg = init_arg.replace('principal "aaaaa-aa"', f'principal "{deployer_principal}"')
                        init_arg = init_arg.replace('initial_balances = vec {}', f'initial_balances = vec {{ record {{ record {{ owner = principal "{deployer_principal}"; subaccount = null }}; 100_000_000_000 }} }}')
                        ledger_config["init_arg"] = init_arg
                        console.print(f"   ✅ Configured {ledger_name} with 1000 ckBTC initial balance for deployer")
                
                realm_canisters[ledger_name] = ledger_config
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
            # Also exclude monitor route which depends on task_monitor extension
            ignore_patterns = shutil.ignore_patterns(
                'node_modules', '__pycache__', '.kybra', '*.pyc', '.svelte-kit',
                'build', 'dist', '.env', '.env.*', '*.log', 'monitor'
            )
            shutil.copytree(src_source, src_dest, ignore=ignore_patterns)
            console.print(f"   ✅ Copied src/ directory")
        else:
            console.print(f"   ⚠️  Warning: Could not find src directory at {src_source}")
    
    # Copy requirements.txt for venv creation during deployment
    # Check cli directory first (pip-installed), then repo root
    requirements_source = cli_dir / "requirements.txt"
    if not requirements_source.exists():
        requirements_source = repo_root / "requirements.txt"
    requirements_dest = output_path / "requirements.txt"
    if requirements_source.exists() and not requirements_dest.exists():
        shutil.copy2(requirements_source, requirements_dest)
        console.print(f"   ✅ Copied requirements.txt")
    
    # Copy extensions/ directory for extension data files (voting_data.json, etc.)
    # Also replace timestamp placeholders with actual values
    extensions_dest = output_path / "extensions"
    extensions_source = repo_root / "extensions"
    if extensions_source.exists():
        if not extensions_dest.exists():
            ignore_patterns = shutil.ignore_patterns(
                '__pycache__', '*.pyc', 'venv', '.venv', 'node_modules'
            )
            shutil.copytree(extensions_source, extensions_dest, ignore=ignore_patterns)
            console.print(f"   ✅ Copied extensions/ directory")
        
        # Always replace timestamp placeholders in extension data files
        _replace_timestamp_placeholders(extensions_dest)
        console.print(f"   ✅ Replaced timestamp placeholders in extension data")
    else:
        console.print(f"   ⚠️  Warning: Could not find extensions directory at {extensions_source}")
    
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
    
    # 5. Copy additional required scripts for deployment
    additional_scripts = [
        "download_wasms.sh",
        "set_canister_config.py",
        "clean_dfx.sh",
    ]
    for script_name in additional_scripts:
        source_script = scripts_path / script_name
        target_script = scripts_dir / script_name
        if source_script.exists():
            shutil.copy2(source_script, target_script)
            target_script.chmod(0o755)
            console.print(f"   ✅ {script_name}")
    
    # Copy utils directory if it exists (needed by some scripts)
    utils_source = scripts_path / "utils"
    utils_dest = scripts_dir / "utils"
    if utils_source.exists() and not utils_dest.exists():
        shutil.copytree(utils_source, utils_dest)
        console.print(f"   ✅ utils/")

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
                mode=mode,
                bare=bare,
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
