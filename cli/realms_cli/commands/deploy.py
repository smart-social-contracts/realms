"""Deploy command for deploying Realms projects."""

import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from ..models import RealmConfig, PostDeploymentAction
from ..utils import (
    console, 
    run_command, 
    load_config, 
    check_dependencies,
    get_project_root,
    get_current_branch,
    generate_port_from_branch,
    wait_for_canister_ready,
    display_success_panel,
    display_error_panel,
    display_info_panel
)


def deploy_command(
    config_file: str = typer.Option("realm_config.json", "--file", "-f", help="Path to realm configuration file"),
    network: Optional[str] = typer.Option(None, "--network", "-n", help="Override network from config"),
    skip_extensions: bool = typer.Option(False, "--skip-extensions", help="Skip extension deployment"),
    skip_post_deployment: bool = typer.Option(False, "--skip-post-deployment", help="Skip post-deployment actions"),
    phases: Optional[List[str]] = typer.Option(None, "--phases", help="Deploy specific extension phases only"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deployed without executing"),
    identity_file: Optional[str] = typer.Option(None, "--identity", help="Path to identity file for authentication")
) -> None:
    """Deploy a Realms project based on configuration file."""
    
    console.print("[bold blue]🚀 Realms Deployment[/bold blue]\n")
    
    # Check dependencies
    if not dry_run and not check_dependencies():
        raise typer.Exit(1)
    
    # Load and validate configuration
    try:
        config_data = load_config(config_file)
        config = RealmConfig(**config_data)
    except Exception as e:
        display_error_panel("Configuration Error", str(e))
        raise typer.Exit(1)
    
    # Override network if specified
    if network:
        config.deployment.network = network
    
    # Override identity file if specified
    if identity_file:
        config.deployment.identity_file = identity_file
    
    # Set port for local deployment
    if config.deployment.network in ["local", "local2"]:
        if not config.deployment.port:
            branch_name = get_current_branch()
            config.deployment.port = generate_port_from_branch(branch_name)
        
        console.print(f"[dim]Deploying to {config.deployment.network} network on port {config.deployment.port}[/dim]")
    
    if dry_run:
        _show_deployment_plan(config, phases, skip_extensions, skip_post_deployment)
        return
    
    project_root = get_project_root()
    
    try:
        # Phase 1: Setup environment and identity
        _setup_deployment_environment(config, project_root)
        
        # Phase 2: Deploy core canisters
        _deploy_core_canisters(config, project_root)
        
        # Phase 3: Deploy extensions
        if not skip_extensions:
            _deploy_extensions(config, project_root, phases)
        
        # Phase 4: Post-deployment actions
        if not skip_post_deployment and config.post_deployment:
            _execute_post_deployment_actions(config, project_root)
        
        # Success message
        _show_deployment_success(config)
        
    except Exception as e:
        display_error_panel("Deployment Failed", str(e))
        raise typer.Exit(1)


def _show_deployment_plan(
    config: RealmConfig, 
    phases: Optional[List[str]], 
    skip_extensions: bool, 
    skip_post_deployment: bool
) -> None:
    """Show what would be deployed in dry-run mode."""
    
    console.print("[bold yellow]📋 Deployment Plan (Dry Run)[/bold yellow]\n")
    
    console.print(f"[bold]Realm:[/bold] {config.realm.name} ({config.realm.id})")
    console.print(f"[bold]Network:[/bold] {config.deployment.network}")
    console.print(f"[bold]Admin:[/bold] {config.realm.admin_principal}\n")
    
    console.print("[bold]Core Canisters:[/bold]")
    console.print("  • realm_backend (Python/Kybra)")
    console.print("  • realm_frontend (SvelteKit/Assets)")
    
    if not skip_extensions and config.extensions:
        console.print(f"\n[bold]Extensions ({len(_get_extensions_to_deploy(config, phases))} total):[/bold]")
        for phase, extensions in config.extensions.items():
            if not phases or phase in phases:
                console.print(f"  [cyan]{phase}:[/cyan]")
                for ext in extensions:
                    status = "✓" if ext.enabled else "✗"
                    console.print(f"    {status} {ext.name}")
    
    if not skip_post_deployment and config.post_deployment:
        console.print(f"\n[bold]Post-deployment Actions ({len(config.post_deployment.actions)}):[/bold]")
        for i, action in enumerate(config.post_deployment.actions, 1):
            console.print(f"  {i}. {action.name or action.type}")


def _setup_deployment_environment(config: RealmConfig, project_root: Path) -> None:
    """Setup deployment environment and identity."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Setup identity if provided
        if config.deployment.identity_file:
            task = progress.add_task("Setting up identity...", total=None)
            run_command([
                "dfx", "identity", "import", "--force", "--storage-mode", "plaintext",
                "deployment", config.deployment.identity_file
            ], cwd=project_root)
            run_command(["dfx", "identity", "use", "deployment"], cwd=project_root)
            progress.update(task, description="[green]Identity configured[/green]")
        
        # Setup virtual environment
        task = progress.add_task("Setting up Python environment...", total=None)
        venv_path = project_root / "venv"
        if not venv_path.exists():
            run_command(["python3", "-m", "venv", "venv"], cwd=project_root)
        
        # Install Python dependencies
        pip_path = venv_path / "bin" / "pip"
        if (project_root / "requirements.txt").exists():
            run_command([str(pip_path), "install", "-r", "requirements.txt"], cwd=project_root)
        
        progress.update(task, description="[green]Python environment ready[/green]")
        
        # Stop and start dfx
        task = progress.add_task("Starting dfx replica...", total=None)
        run_command(["dfx", "stop"], cwd=project_root, check=False)
        
        dfx_args = ["dfx", "start", "--background"]
        if config.deployment.clean_deploy:
            dfx_args.append("--clean")
        
        if config.deployment.network == "local" and config.deployment.port:
            dfx_args.extend(["--host", f"127.0.0.1:{config.deployment.port}"])
        
        run_command(dfx_args, cwd=project_root)
        progress.update(task, description="[green]dfx replica started[/green]")


def _deploy_core_canisters(config: RealmConfig, project_root: Path) -> None:
    """Deploy core backend and frontend canisters."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Deploying backend canister...", total=3)
        
        # Deploy backend
        run_command([
            "dfx", "deploy", "realm_backend", "--yes",
            "--network", config.deployment.network
        ], cwd=project_root)
        progress.advance(task)
        
        # Generate declarations
        run_command([
            "dfx", "generate", "realm_backend",
            "--network", config.deployment.network
        ], cwd=project_root)
        progress.advance(task)
        progress.update(task, description="[green]Backend deployed[/green]")
        
        # Deploy frontend
        task2 = progress.add_task("Building and deploying frontend...", total=4)
        
        # Install npm dependencies
        run_command(["npm", "install", "--legacy-peer-deps"], cwd=project_root)
        progress.advance(task2)
        
        # Build frontend
        if (project_root / "src" / "realm_frontend").exists():
            run_command(["npm", "run", "build", "--workspace", "realm_frontend"], cwd=project_root)
        progress.advance(task2)
        
        # Update config if script exists
        update_config_script = project_root / "scripts" / "update_config.sh"
        if update_config_script.exists():
            run_command(["sh", str(update_config_script)], cwd=project_root)
        progress.advance(task2)
        
        # Deploy frontend canister
        run_command([
            "dfx", "deploy", "realm_frontend",
            "--network", config.deployment.network
        ], cwd=project_root)
        progress.advance(task2)
        progress.update(task2, description="[green]Frontend deployed[/green]")


def _deploy_extensions(config: RealmConfig, project_root: Path, phases: Optional[List[str]]) -> None:
    """Deploy extensions based on configuration."""
    
    extensions_to_deploy = _get_extensions_to_deploy(config, phases)
    
    if not extensions_to_deploy:
        console.print("[yellow]No extensions to deploy[/yellow]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task("Installing extensions...", total=None)
        
        # Check if install script exists
        install_script = project_root / "scripts" / "install_extensions.sh"
        if install_script.exists():
            run_command([str(install_script)], cwd=project_root)
        else:
            # Fallback: use extension CLI if available
            cli_script = project_root / "scripts" / "realm-extension-cli.py"
            if cli_script.exists():
                run_command(["python", str(cli_script), "install", "--all"], cwd=project_root)
        
        progress.update(task, description=f"[green]{len(extensions_to_deploy)} extensions installed[/green]")


def _execute_post_deployment_actions(config: RealmConfig, project_root: Path) -> None:
    """Execute post-deployment actions."""
    
    if not config.post_deployment or not config.post_deployment.actions:
        return
    
    actions = config.post_deployment.actions
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Executing post-deployment actions...", total=len(actions))
        
        for i, action in enumerate(actions, 1):
            action_name = action.name or f"{action.type} action {i}"
            progress.update(task, description=f"Running: {action_name}")
            
            try:
                _execute_single_action(action, config, project_root)
                progress.advance(task)
            except Exception as e:
                if action.ignore_failure:
                    console.print(f"[yellow]Action '{action_name}' failed but continuing: {e}[/yellow]")
                    progress.advance(task)
                else:
                    console.print(f"[red]Action '{action_name}' failed: {e}[/red]")
                    raise
        
        progress.update(task, description="[green]All post-deployment actions completed[/green]")


def _execute_single_action(action: PostDeploymentAction, config: RealmConfig, project_root: Path) -> None:
    """Execute a single post-deployment action."""
    
    retry_count = 0
    max_retries = action.retry_count
    
    while retry_count <= max_retries:
        try:
            if action.type == "wait":
                if action.duration:
                    time.sleep(action.duration)
                return
            
            elif action.type == "extension_call":
                if not action.extension_name or not action.function_name:
                    raise ValueError("extension_call requires extension_name and function_name")
                
                args_json = json.dumps(action.args) if action.args else "{}"
                
                run_command([
                    "dfx", "canister", "call", "realm_backend", "extension_sync_call",
                    f'(record {{ extension_name = "{action.extension_name}"; function_name = "{action.function_name}"; args = "{args_json}"; }})',
                    "--network", config.deployment.network
                ], cwd=project_root)
                return
            
            elif action.type == "script":
                if not action.script_path:
                    raise ValueError("script action requires script_path")
                
                script_path = project_root / action.script_path
                if not script_path.exists():
                    raise FileNotFoundError(f"Script not found: {script_path}")
                
                run_command([str(script_path)], cwd=project_root)
                return
            
            else:
                raise ValueError(f"Unknown action type: {action.type}")
        
        except Exception as e:
            retry_count += 1
            if retry_count <= max_retries:
                console.print(f"[yellow]Action failed, retrying ({retry_count}/{max_retries}): {e}[/yellow]")
                time.sleep(2)
            else:
                raise


def _get_extensions_to_deploy(config: RealmConfig, phases: Optional[List[str]]) -> List[Dict[str, Any]]:
    """Get list of extensions to deploy based on phases filter."""
    
    extensions = []
    
    for phase, phase_extensions in config.extensions.items():
        if phases and phase not in phases:
            continue
        
        for ext in phase_extensions:
            if ext.enabled:
                extensions.append({
                    "name": ext.name,
                    "phase": phase,
                    "source": ext.source
                })
    
    return extensions


def _show_deployment_success(config: RealmConfig) -> None:
    """Show deployment success message."""
    
    if config.deployment.network == "local":
        port = config.deployment.port or 8000
        url = f"http://localhost:{port}"
    else:
        url = f"Deployed to {config.deployment.network} network"
    
    display_success_panel(
        "Deployment Successful! 🎉",
        f"Realm '{config.realm.name}' has been deployed successfully.\n\n"
        f"🆔 Realm ID: {config.realm.id}\n"
        f"🌐 Network: {config.deployment.network}\n"
        f"🔗 URL: {url}\n"
        f"👤 Admin: {config.realm.admin_principal}\n\n"
        "Your Realms platform is now ready to use!"
    )
