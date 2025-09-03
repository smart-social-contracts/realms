"""Deploy command for deploying Realms projects."""

import base64
import json
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from ..models import PostDeploymentAction, RealmConfig
from ..utils import (
    check_dependencies,
    console,
    display_error_panel,
    display_info_panel,
    display_success_panel,
    generate_port_from_branch,
    get_current_branch,
    get_project_root,
    load_config,
    run_command,
    wait_for_canister_ready,
)


def deploy_command(
    config_file: str = typer.Option(
        "realm_config.json", "--file", "-f", help="Path to realm configuration file"
    ),
    network: Optional[str] = typer.Option(
        None, "--network", "-n", help="Override network from config"
    ),
    skip_extensions: bool = typer.Option(
        False, "--skip-extensions", help="Skip extension deployment"
    ),
    skip_post_deployment: bool = typer.Option(
        False, "--skip-post-deployment", help="Skip post-deployment actions"
    ),
    phases: Optional[List[str]] = typer.Option(
        None, "--phases", help="Deploy specific extension phases only"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be deployed without executing"
    ),
    identity_file: Optional[str] = typer.Option(
        None, "--identity", help="Path to identity file for authentication"
    ),
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

    # Store config file path for relative path resolution
    config_file_path = Path(config_file) if config_file else None

    # Override network if specified
    if network:
        config.deployment.network = network

    # Override identity file if specified
    if identity_file:
        config.deployment.identity_file = identity_file

    if dry_run:
        _show_deployment_plan(config, phases, skip_extensions, skip_post_deployment)
        return

    project_root = get_project_root()

    try:
        # Delegate to appropriate deployment script
        if config.deployment.network in ["local", "local2"]:
            _deploy_local(project_root)
        else:
            _deploy_ic(config, project_root)

        # Post-deployment actions
        if not skip_post_deployment and config.post_deployment:
            _execute_post_deployment_actions(config, project_root, config_file_path)

        # Success message
        _show_deployment_success(config)

    except Exception as e:
        display_error_panel("Deployment Failed", str(e))
        raise typer.Exit(1)


def _deploy_local(project_root: Path) -> None:
    """Deploy to local network using deploy_local.sh script."""

    console.print("[bold]Deploying to local network...[/bold]")

    deploy_script = project_root / "scripts" / "deploy_local.sh"
    if not deploy_script.exists():
        raise FileNotFoundError(f"Local deployment script not found: {deploy_script}")

    run_command([str(deploy_script)], cwd=project_root)


def _deploy_ic(config: RealmConfig, project_root: Path) -> None:
    """Deploy to Internet Computer network using deploy_ic.sh script."""

    console.print(f"[bold]Deploying to {config.deployment.network} network...[/bold]")

    deploy_script = project_root / "scripts" / "deploy_ic.sh"
    if not deploy_script.exists():
        raise FileNotFoundError(f"IC deployment script not found: {deploy_script}")

    # Prepare arguments for deploy_ic.sh
    args = [str(deploy_script)]

    # Add identity file if specified
    if config.deployment.identity_file:
        args.append(config.deployment.identity_file)

    # Add network (defaults to staging in script if not provided)
    if config.deployment.network != "local":
        if config.deployment.identity_file:
            args.append(config.deployment.network)
        else:
            # If no identity file, we need to add empty string as first arg
            args.extend(["", config.deployment.network])

    run_command(args, cwd=project_root)


def _show_deployment_plan(
    config: RealmConfig,
    phases: Optional[List[str]],
    skip_extensions: bool,
    skip_post_deployment: bool,
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
        # Count enabled extensions
        total_extensions = sum(
            len([ext for ext in extensions if ext.enabled])
            for phase, extensions in config.extensions.items()
            if not phases or phase in phases
        )
        console.print(f"\n[bold]Extensions ({total_extensions} total):[/bold]")
        for phase, extensions in config.extensions.items():
            if not phases or phase in phases:
                console.print(f"  [cyan]{phase}:[/cyan]")
                for ext in extensions:
                    status = "✓" if ext.enabled else "✗"
                    console.print(f"    {status} {ext.name}")

    if not skip_post_deployment and config.post_deployment:
        if isinstance(config.post_deployment, list):
            console.print(
                f"\n[bold]Post-deployment Commands ({len(config.post_deployment)}):[/bold]"
            )
            for i, command in enumerate(config.post_deployment, 1):
                console.print(f"  {i}. {command}")
        else:
            console.print(
                f"\n[bold]Post-deployment Actions ({len(config.post_deployment.actions)}):[/bold]"
            )
            for i, action in enumerate(config.post_deployment.actions, 1):
                console.print(f"  {i}. {action.name or action.type}")


def _execute_post_deployment_actions(config: RealmConfig, project_root: Path, config_file_path: Path = None) -> None:
    """Execute post-deployment actions."""

    if not config.post_deployment:
        return

    # Handle both simple string array and complex action format
    if isinstance(config.post_deployment, list):
        # Simple string array format
        _execute_simple_post_deployment_commands(
            config.post_deployment, config, project_root
        )
        return

    # Complex action format
    if not config.post_deployment.actions:
        return

    actions = config.post_deployment.actions

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:

        task = progress.add_task(
            "Executing post-deployment actions...", total=len(actions)
        )

        for i, action in enumerate(actions, 1):
            action_name = action.name or f"{action.type} action {i}"
            progress.update(task, description=f"Running: {action_name}")

            try:
                config_file_dir = config_file_path.parent if config_file_path else None
                _execute_single_action(action, config, project_root, config_file_dir)
                progress.advance(task)
            except Exception as e:
                if action.ignore_failure:
                    console.print(
                        f"[yellow]Action '{action_name}' failed but continuing: {e}[/yellow]"
                    )
                    progress.advance(task)
                else:
                    console.print(f"[red]Action '{action_name}' failed: {e}[/red]")
                    raise

        progress.update(
            task, description="[green]All post-deployment actions completed[/green]"
        )


def _execute_simple_post_deployment_commands(
    commands: List[str], config: RealmConfig, project_root: Path
) -> None:
    """Execute simple post-deployment commands from string array."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:

        task = progress.add_task(
            "Executing post-deployment commands...", total=len(commands)
        )

        for i, command in enumerate(commands, 1):
            progress.update(task, description=f"Running: {command}")

            try:
                _execute_simple_command(command, config, project_root)
                progress.advance(task)
            except Exception as e:
                console.print(f"[red]Command '{command}' failed: {e}[/red]")
                raise

        progress.update(
            task, description="[green]All post-deployment commands completed[/green]"
        )


def _execute_simple_command(
    command: str, config: RealmConfig, project_root: Path
) -> None:
    """Execute a single simple post-deployment command."""

    # Handle shell scripts
    if command.endswith(".sh"):
        script_path = project_root / command
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        run_command([str(script_path)], cwd=project_root)
        return

    # Handle realms shell -f commands
    if command.startswith("realms shell -f "):
        python_file = command.replace("realms shell -f ", "").strip()
        python_path = project_root / python_file

        if not python_path.exists():
            raise FileNotFoundError(f"Python file not found: {python_path}")

        # Import the shell command function
        from .shell import execute_python_file

        # Execute the Python file using the shell command
        canister = "realm_backend"
        network = config.deployment.network
        execute_python_file(str(python_path), canister, network)
        return

    # Handle other command formats
    if command.startswith("realms "):
        # Parse realms CLI commands
        cmd_parts = command.split()
        run_command(cmd_parts, cwd=project_root)
        return

    # Default: treat as shell command
    run_command(command.split(), cwd=project_root)


def _execute_single_action(
    action: PostDeploymentAction, config: RealmConfig, project_root: Path, config_file_dir: Path = None
) -> None:
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
                    raise ValueError(
                        "extension_call requires extension_name and function_name"
                    )

                args = action.args.copy() if action.args else {}
                
                # Handle file content reading for import_data function
                if action.function_name == "import_data" and "file_path" in args:
                    file_path = args["file_path"]
                    # Resolve file path relative to config file directory if provided
                    if config_file_dir and not Path(file_path).is_absolute():
                        data_file_path = config_file_dir / file_path
                    else:
                        data_file_path = project_root / file_path
                    if data_file_path.exists():
                        with open(data_file_path, "r") as f:
                            file_data = json.load(f)
                        # Remove file_path and send actual data
                        del args["file_path"]
                        args["data"] = file_data  # Send as actual data, not JSON string
                    else:
                        raise FileNotFoundError(f"Data file not found: {data_file_path}")
                
                # Handle generic data_file parameter for other functions
                elif "data_file" in args:
                    data_file = args["data_file"]
                    # Resolve file path relative to config file directory if provided
                    if config_file_dir and not Path(data_file).is_absolute():
                        data_file_path = config_file_dir / data_file
                    else:
                        data_file_path = project_root / data_file
                    if data_file_path.exists():
                        with open(data_file_path, "r") as f:
                            file_data = json.load(f)
                        args["data"] = json.dumps(file_data)
                        del args["data_file"]

                args_json = json.dumps(args) if args else "{}"
                # Escape quotes properly for Candid
                escaped_args = args_json.replace('"', '\\"')
                
                run_command(
                    [
                        "dfx",
                        "canister",
                        "call",
                        "realm_backend",
                        "extension_sync_call",
                        f'(record {{ extension_name = "{action.extension_name}"; function_name = "{action.function_name}"; args = "{escaped_args}"; }})',
                        "--network",
                        config.deployment.network,
                    ],
                    cwd=project_root,
                )
                return

            elif action.type == "script":
                if not action.script_path:
                    raise ValueError("script action requires script_path")

                script_path = project_root / action.script_path
                if not script_path.exists():
                    raise FileNotFoundError(f"Script not found: {script_path}")

                run_command([str(script_path)], cwd=project_root)
                return

            elif action.type == "create_codex":
                if not action.codex_id:
                    raise ValueError("create_codex action requires codex_id")

                # Get codex configuration from config
                if action.codex_id not in config.codexes:
                    raise ValueError(
                        f"Codex '{action.codex_id}' not found in configuration"
                    )

                codex_config = config.codexes[action.codex_id]

                # Build function call based on codex configuration
                if hasattr(codex_config, "code") and codex_config.code:
                    # Inline code
                    escaped_code = codex_config.code.replace("\n", "\\n").replace(
                        '"', '\\"'
                    )
                    function_call = f'("{codex_config.name}", "{escaped_code}", "", "")'

                elif hasattr(codex_config, "url") and codex_config.url:
                    # Downloadable code
                    url = codex_config.url
                    checksum = getattr(codex_config, "checksum", "")
                    function_call = (
                        f'("{codex_config.name}", "", "{url}", "{checksum}")'
                    )
                else:
                    raise ValueError(
                        f"Codex '{action.codex_id}' must have either 'code' or 'url' specified"
                    )

                run_command(
                    [
                        "dfx",
                        "canister",
                        "call",
                        "realm_backend",
                        "create_codex",
                        function_call,
                        "--network",
                        config.deployment.network,
                    ],
                    cwd=project_root,
                )
                return

            elif action.type == "create_task":
                if not action.task_id:
                    raise ValueError("create_task action requires task_id")

                # Get task configuration from config
                if action.task_id not in config.tasks:
                    raise ValueError(
                        f"Task '{action.task_id}' not found in configuration"
                    )

                task_config = config.tasks[action.task_id]

                # Verify the referenced codex exists
                if task_config.codex not in config.codexes:
                    raise ValueError(
                        f"Task '{action.task_id}' references unknown codex '{task_config.codex}'"
                    )

                # Create task via backend API
                task_data = {
                    "name": task_config.name,
                    "codex": config.codexes[task_config.codex].name,
                    "metadata": task_config.metadata,
                }
                task_json = json.dumps(task_data).replace('"', '\\"')

                run_command(
                    [
                        "dfx",
                        "canister",
                        "call",
                        "realm_backend",
                        "create_task",
                        f'("{task_json}")',
                        "--network",
                        config.deployment.network,
                    ],
                    cwd=project_root,
                )
                return

            else:
                raise ValueError(f"Unknown action type: {action.type}")

        except Exception as e:
            retry_count += 1
            if retry_count <= max_retries:
                console.print(
                    f"[yellow]Action failed, retrying ({retry_count}/{max_retries}): {e}[/yellow]"
                )
                time.sleep(2)
            else:
                raise


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
        "Your Realms platform is now ready to use!",
    )
