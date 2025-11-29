"""Mundus creation and management commands."""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from .create import create_command
from .registry import registry_create_command
from ..utils import console, generate_output_dir_name, get_project_root


def mundus_create_command(
    output_dir: str,
    mundus_name: str,
    manifest: Optional[str],
    network: str,
    deploy: bool,
    identity: Optional[str],
    mode: str,
) -> None:
    """Create a new multi-realm mundus by calling realm and registry commands."""
    
    console.print(Panel.fit(
        "[bold cyan]🌍 Creating Mundus (Multi-Realm Universe)[/bold cyan]",
        border_style="cyan"
    ))
    
    project_root = get_project_root()
    
    # Load manifest
    if manifest:
        manifest_path = Path(manifest)
    else:
        # Use default demo mundus manifest
        manifest_path = project_root / "examples" / "demo" / "manifest.json"
    
    if not manifest_path.exists():
        console.print(f"[red]❌ Manifest not found: {manifest_path}[/red]")
        raise typer.Exit(1)
    
    with open(manifest_path, 'r') as f:
        mundus_config = json.load(f)
    
    # Generate mundus directory with timestamp
    dir_name = generate_output_dir_name("mundus", mundus_name)
    base_dir = Path(output_dir)
    mundus_dir = base_dir / dir_name
    
    mundus_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"📁 Mundus directory: {mundus_dir}\n")
    
    # Save mundus manifest
    mundus_manifest_path = mundus_dir / "manifest.json"
    with open(mundus_manifest_path, 'w') as f:
        json.dump(mundus_config, f, indent=2)
    console.print(f"📄 Saved mundus manifest\n")
    
    # Get realms from manifest
    realms = mundus_config.get("realms", [])
    console.print(f"🌍 Creating {len(realms)} realm(s) + 1 registry...\n")
    
    created_realms = []
    
    # Create each realm
    for i, realm_config in enumerate(realms, 1):
        realm_name = realm_config.get("name", f"Realm{i}")
        console.print(f"  📦 Creating realm: {realm_name}...")
        
        # Call create_command for each realm (it will create timestamped directory)
        # We pass the mundus directory as the base output_dir
        try:
            # Temporarily change to project root for realm creation
            orig_dir = os.getcwd()
            os.chdir(project_root)
            
            create_command(
                output_dir=str(mundus_dir),
                realm_name=realm_name,
                manifest=None,  # Use realm config from mundus manifest
                random=realm_config.get("random", False),
                members=realm_config.get("members"),
                organizations=realm_config.get("organizations"),
                transactions=realm_config.get("transactions"),
                disputes=realm_config.get("disputes"),
                seed=realm_config.get("seed"),
                network=network,
                deploy=False,  # Don't deploy individual realms yet
            )
            
            # Find the created realm directory (most recent realm_* directory)
            realm_dirs = sorted(mundus_dir.glob("realm_*"), key=lambda p: p.stat().st_mtime)
            if realm_dirs:
                created_realms.append(realm_dirs[-1])
                console.print(f"     ✅ {realm_name} created\n")
            
        finally:
            os.chdir(orig_dir)
    
    # Create registry
    console.print(f"  📋 Creating registry...")
    try:
        orig_dir = os.getcwd()
        os.chdir(project_root)
        
        registry_dir = registry_create_command(
            registry_name=mundus_config.get("registry", {}).get("name", "MainRegistry"),
            output_dir=str(mundus_dir),
            network=network,
        )
        console.print(f"     ✅ Registry created\n")
        
    finally:
        os.chdir(orig_dir)
    
    # Create mundus deployment orchestration script
    _create_mundus_deploy_script(mundus_dir, created_realms, registry_dir, network)
    
    console.print(f"\n[green]✅ Mundus '{mundus_name}' created successfully at:[/green] [cyan]{mundus_dir}[/cyan]\n")
    console.print(f"[yellow]📝 Next steps:[/yellow]")
    console.print(f"   1. Deploy: realms mundus deploy --mundus-dir {mundus_dir}")
    console.print(f"   2. Or run: cd {mundus_dir} && bash scripts/deploy-all.sh\n")
    
    if deploy:
        console.print("\n[bold yellow]🚀 Starting deployment...[/bold yellow]\n")
        mundus_deploy_command(str(mundus_dir), network, identity, mode)


def _create_mundus_deploy_script(
    mundus_dir: Path,
    realm_dirs: list,
    registry_dir: Path,
    network: str
) -> None:
    """Create orchestration script to deploy all realms and registry."""
    
    scripts_dir = mundus_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    
    script_content = f"""#!/bin/bash
# Mundus deployment orchestration script
# Deploys all realms and registry in sequence

set -e

NETWORK="${{1:-{network}}}"
MODE="${{2:-upgrade}}"

echo "╭────────────────────────────────────────╮"
echo "│ 🌍 Deploying Mundus                    │"
echo "╰────────────────────────────────────────╯"
echo "📡 Network: $NETWORK"
echo "🔄 Mode: $MODE"
echo ""

# Get the mundus directory
MUNDUS_DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )/.." && pwd )"

# Deploy registry first
echo "📋 Deploying registry..."
REGISTRY_DIR=$(find "$MUNDUS_DIR" -maxdepth 1 -type d -name "registry_*" | head -1)
if [ -n "$REGISTRY_DIR" ]; then
    echo "   Directory: $REGISTRY_DIR"
    if [ -f "$REGISTRY_DIR/scripts/2-deploy-canisters.sh" ]; then
        bash "$REGISTRY_DIR/scripts/2-deploy-canisters.sh" "$NETWORK" "$MODE"
        echo "   ✅ Registry deployed"
    else
        echo "   ⚠️  Registry deployment script not found"
    fi
else
    echo "   ⚠️  No registry directory found"
fi

echo ""

# Deploy all realms
echo "🏛️  Deploying realms..."
REALM_COUNT=0
for REALM_DIR in "$MUNDUS_DIR"/realm_*/; do
    if [ -d "$REALM_DIR" ]; then
        REALM_NAME=$(basename "$REALM_DIR")
        echo "   📦 Deploying $REALM_NAME..."
        
        # Run realm deployment scripts
        if [ -f "$REALM_DIR/scripts/1-install-extensions.sh" ]; then
            bash "$REALM_DIR/scripts/1-install-extensions.sh" || echo "      ⚠️  Extension installation failed"
        fi
        
        if [ -f "$REALM_DIR/scripts/2-deploy-canisters.sh" ]; then
            bash "$REALM_DIR/scripts/2-deploy-canisters.sh" "$NETWORK" "$MODE"
            echo "      ✅ $REALM_NAME deployed"
            REALM_COUNT=$((REALM_COUNT + 1))
        else
            echo "      ⚠️  Deployment script not found"
        fi
        
        echo ""
    fi
done

echo "╭────────────────────────────────────────╮"
echo "│ ✅ Mundus Deployment Complete          │"
echo "╰────────────────────────────────────────╯"
echo "📊 Deployed: $REALM_COUNT realm(s) + 1 registry"
echo ""
"""
    
    deploy_script = scripts_dir / "deploy-all.sh"
    deploy_script.write_text(script_content)
    deploy_script.chmod(0o755)
    console.print(f"   ✅ Created orchestration script: scripts/deploy-all.sh")


def mundus_deploy_command(
    mundus_dir: str,
    network: str,
    identity: Optional[str],
    mode: str,
) -> None:
    """Deploy all realms and registry in a mundus by calling individual deploy commands."""
    
    console.print(Panel.fit(
        f"[bold cyan]🚀 Deploying Mundus to {network}[/bold cyan]",
        border_style="cyan"
    ))
    
    mundus_path = Path(mundus_dir).absolute()
    if not mundus_path.exists():
        console.print(f"[red]❌ Mundus directory not found: {mundus_dir}[/red]")
        raise typer.Exit(1)
    
    console.print(f"📁 Mundus: {mundus_path}")
    console.print(f"📡 Network: {network}")
    console.print(f"🔄 Mode: {mode}\n")
    
    # Start dfx once for local network (shared by all deployments)
    if network == "local":
        import subprocess
        from ..utils import get_project_root
        
        # Start dfx from repo root so all deployments can share it
        repo_root = get_project_root()
        
        # Determine port based on branch
        port = 8006  # Default port for mundus
        try:
            branch_name = subprocess.check_output(
                ["git", "branch", "--show-current"],
                cwd=repo_root,
                text=True
            ).strip()
            if branch_name == "main":
                port = 8000
            else:
                # Hash branch name to get consistent port
                import hashlib
                hash_val = int(hashlib.md5(branch_name.encode()).hexdigest(), 16)
                port = 8001 + (hash_val % 99)
        except:
            pass
        
        # Check if dfx is already running and responsive
        dfx_running = False
        try:
            # First check if port is occupied
            subprocess.run(["lsof", "-ti:" + str(port)], check=True, capture_output=True)
            # Then verify dfx is actually responsive
            result = subprocess.run(
                ["dfx", "ping", "--network", "local"],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                dfx_running = True
                console.print(f"🌐 dfx already running on port {port}\n")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
        
        if not dfx_running:
            console.print(f"🌐 Starting shared dfx instance on port {port}...\n")
            # Activate venv and start dfx from repo root
            venv_activate = repo_root / "venv" / "bin" / "activate"
            
            # Stop any existing dfx
            if venv_activate.exists():
                subprocess.run(
                    ["bash", "-c", f"source {venv_activate} && dfx stop"],
                    cwd=repo_root,
                    capture_output=True
                )
            else:
                subprocess.run(["dfx", "stop"], cwd=repo_root, capture_output=True)
            
            # Start dfx with venv activated
            if venv_activate.exists():
                subprocess.Popen(
                    ["bash", "-c", f"source {venv_activate} && dfx start --clean --background --host 127.0.0.1:{port}"],
                    cwd=repo_root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                subprocess.Popen(
                    ["dfx", "start", "--clean", "--background", "--host", f"127.0.0.1:{port}"],
                    cwd=repo_root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            import time
            time.sleep(5)  # Wait for dfx to initialize
    
    # Set environment variable to skip dfx start in individual deployments
    # since we're managing a shared instance
    import os
    os.environ['SKIP_DFX_START'] = 'true'
    
    # Create symlinks to shared .dfx directory from repo root
    from ..utils import get_project_root
    repo_root = get_project_root()
    shared_dfx = repo_root / ".dfx"
    
    # Symlink .dfx to all deployment directories so they can find the running dfx
    all_deploy_dirs = list(mundus_path.glob("registry_*")) + list(mundus_path.glob("realm_*"))
    for deploy_dir in all_deploy_dirs:
        dfx_link = deploy_dir / ".dfx"
        if not dfx_link.exists():
            try:
                dfx_link.symlink_to(shared_dfx, target_is_directory=True)
            except:
                pass  # Ignore if symlink fails
    
    # Import deploy commands
    from .deploy import deploy_command as realm_deploy_command
    from .registry import registry_deploy_command
    
    # Deploy registry first
    registry_dirs = sorted(mundus_path.glob("registry_*"))
    if registry_dirs:
        console.print("📋 Deploying registry...")
        for registry_dir in registry_dirs:
            try:
                registry_deploy_command(
                    folder=str(registry_dir),
                    network=network,
                    mode=mode,
                    identity=identity
                )
                console.print(f"   ✅ {registry_dir.name} deployed\n")
            except Exception as e:
                console.print(f"[red]   ❌ Failed to deploy {registry_dir.name}: {e}[/red]")
                raise typer.Exit(1)
    
    # Deploy all realms
    realm_dirs = sorted(mundus_path.glob("realm_*"))
    if not realm_dirs:
        console.print("[yellow]⚠️  No realms found in mundus directory[/yellow]")
        return
    
    console.print(f"🏛️  Deploying {len(realm_dirs)} realm(s)...\n")
    
    for realm_dir in realm_dirs:
        console.print(f"   📦 Deploying {realm_dir.name}...")
        try:
            realm_deploy_command(
                folder=str(realm_dir),
                network=network,
                mode=mode,
                identity=identity
            )
            console.print(f"   ✅ {realm_dir.name} deployed\n")
        except Exception as e:
            console.print(f"[red]   ❌ Failed to deploy {realm_dir.name}: {e}[/red]")
            raise typer.Exit(1)
    
    # Clean up environment variable
    if 'SKIP_DFX_START' in os.environ:
        del os.environ['SKIP_DFX_START']
    
    console.print(Panel.fit(
        "[bold green]✅ Mundus Deployment Complete[/bold green]",
        border_style="green"
    ))
    console.print(f"📊 Deployed: {len(realm_dirs)} realm(s) + {len(registry_dirs)} registry\n")


def _deploy_canister(realm_dir: Path, canister_name: str, network: str, identity: Optional[str], mode: str) -> None:
    """Deploy a single canister from a realm directory."""
    
    # If deploying frontend, generate declarations and rebuild
    if "frontend" in canister_name:
        backend_name = canister_name.replace("_frontend", "_backend")
        _generate_declarations(realm_dir, backend_name, network)
        _build_frontend(realm_dir)
    
    cmd = ["dfx", "deploy", canister_name, "--network", network]
    
    if mode == "reinstall":
        cmd.append("--mode=reinstall")
    
    if identity:
        # Handle identity (PEM file or dfx identity name)
        if Path(identity).exists():
            # TODO: Import identity from PEM file
            pass
        else:
            cmd.extend(["--identity", identity])
    
    try:
        subprocess.run(
            cmd,
            cwd=realm_dir,
            check=True,
            capture_output=False,  # Show output in real-time
            text=True
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error deploying {canister_name}[/red]")
        raise typer.Exit(1)


def _generate_declarations(realm_dir: Path, backend_name: str, network: str) -> None:
    """Generate TypeScript declarations for a backend canister."""
    
    cmd = ["dfx", "generate", backend_name, "--network", network]
    
    try:
        subprocess.run(
            cmd,
            cwd=realm_dir,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Create symlink from realm_backend to realm{N}_backend for frontend compatibility
        declarations_dir = realm_dir / "src" / "declarations"
        if declarations_dir.exists():
            backend_decl = declarations_dir / backend_name
            symlink_target = declarations_dir / "realm_backend"
            
            if backend_decl.exists() and not symlink_target.exists():
                import os
                os.symlink(backend_name, symlink_target)
                
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]⚠️  Warning: Could not generate declarations for {backend_name}[/yellow]")
        console.print(f"[dim]{e.stderr}[/dim]")


def _build_frontend(realm_dir: Path) -> None:
    """Build the frontend for a realm."""
    
    frontend_dir = realm_dir / "src" / "realm_frontend"
    
    if not frontend_dir.exists():
        frontend_dir = realm_dir / "src" / "realm_registry_frontend"
    
    if not frontend_dir.exists():
        console.print(f"[yellow]⚠️  Warning: Frontend directory not found in {realm_dir}[/yellow]")
        return
    
    console.print(f"[dim]     Building frontend...[/dim]")
    try:
        subprocess.run(
            ["npm", "run", "build"],
            cwd=frontend_dir,
            check=True,
            capture_output=True,  # Keep this quiet unless it fails
            text=True
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error building frontend:[/red]")
        console.print(f"[red]{e.stderr}[/red]")
        raise typer.Exit(1)


def _build_all_frontends(mundus_path: Path) -> None:
    """Build all frontend applications in the mundus."""
    
    # Build realm frontends
    for realm_num in [1, 2, 3]:
        realm_id = f"realm{realm_num}"
        frontend_dir = mundus_path / realm_id / "src" / "realm_frontend"
        
        if frontend_dir.exists():
            console.print(f"[dim]  Building {realm_id} frontend...[/dim]")
            try:
                subprocess.run(
                    ["npm", "run", "build"],
                    cwd=frontend_dir,
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                console.print(f"[red]❌ Error building {realm_id} frontend:[/red]")
                console.print(f"[red]{e.stderr}[/red]")
                raise typer.Exit(1)
    
    # Build registry frontend
    registry_frontend_dir = mundus_path / "registry" / "src" / "realm_registry_frontend"
    if registry_frontend_dir.exists():
        console.print(f"[dim]  Building registry frontend...[/dim]")
        try:
            subprocess.run(
                ["npm", "run", "build"],
                cwd=registry_frontend_dir,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Error building registry frontend:[/red]")
            console.print(f"[red]{e.stderr}[/red]")
            raise typer.Exit(1)


def _deploy_all_canisters(mundus_path: Path, network: str, identity: Optional[str], mode: str) -> None:
    """Deploy all canisters using the unified dfx.json."""
    
    cmd = ["dfx", "deploy", "--network", network]
    
    if mode == "reinstall":
        cmd.append("--mode=reinstall")
    
    if identity:
        if not Path(identity).exists():
            cmd.extend(["--identity", identity])
    
    try:
        subprocess.run(
            cmd,
            cwd=mundus_path,
            check=True,
            capture_output=False,  # Show output in real-time
            text=True
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Deployment failed[/red]")
        raise typer.Exit(1)


def _ensure_dfx_running(cwd: Optional[Path] = None) -> None:
    """Ensure dfx is running on local network, start if not."""
    
    # Check if dfx is running
    try:
        result = subprocess.run(
            ["dfx", "ping", "local"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd
        )
        if result.returncode == 0:
            console.print("[dim]✅ dfx is already running[/dim]\n")
            return
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Start dfx
    console.print("[yellow]🚀 Starting dfx local replica...[/yellow]")
    try:
        subprocess.run(
            ["dfx", "start", "--background"],
            check=True,
            capture_output=False,  # Show output in real-time
            text=True,
            cwd=cwd
        )
        console.print("[green]✅ dfx started successfully[/green]\n")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Failed to start dfx[/red]")
        raise typer.Exit(1)
