"""Utility functions for Realms CLI."""

import hashlib
import json
import logging
import os
import subprocess
import sys
import time
import venv
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from .constants import DOCKER_IMAGE

console = Console()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # save to file
    file_handler = logging.FileHandler("realms_cli.log")
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # # print warnings and errors to console
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.WARNING)
    # logger.addHandler(console_handler)

    return logger


def get_scripts_path() -> Path:
    """
    Get scripts path - auto-detect repo mode vs image mode.
    
    If ./scripts exists with expected files, use it (repo mode).
    Otherwise, assume Docker image mode (/app/scripts).
    
    Returns:
        Path to scripts directory
    """
    local_scripts = Path.cwd() / "scripts"
    if local_scripts.exists() and (local_scripts / "realm_generator.py").exists():
        return local_scripts
    return Path("/app/scripts")


def is_repo_mode() -> bool:
    """Check if running in repo mode (local scripts exist)."""
    local_scripts = Path.cwd() / "scripts"
    return local_scripts.exists() and (local_scripts / "realm_generator.py").exists()


def run_in_docker(
    cmd: List[str],
    working_dir: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    docker_image: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """
    Run a command inside a Docker container.
    
    Args:
        cmd: Command to run
        working_dir: Working directory (defaults to current directory)
        env: Environment variables to pass through
        docker_image: Docker image to use (defaults to DOCKER_IMAGE from constants)
    
    Returns:
        CompletedProcess result
    """
    if working_dir is None:
        working_dir = Path.cwd()
    
    if docker_image is None:
        docker_image = DOCKER_IMAGE
    
    # Build docker run command
    docker_cmd = [
        "docker", "run",
        "--rm",  # Remove container after run
        "-v", f"{working_dir}:/workspace",  # Mount working directory
        "-w", "/workspace",  # Set working directory in container
    ]
    
    # Mount home directory for dfx identity access
    home_dir = Path.home()
    docker_cmd.extend(["-v", f"{home_dir}/.config/dfx:/root/.config/dfx:ro"])
    
    # Pass through environment variables
    if env:
        for key, value in env.items():
            docker_cmd.extend(["-e", f"{key}={value}"])
    
    # Add the image
    docker_cmd.append(docker_image)
    
    # Add the command to run
    docker_cmd.extend(cmd)
    
    console.print(f"[dim]Running in Docker: {' '.join(docker_cmd)}[/dim]")
    
    return subprocess.run(docker_cmd, capture_output=True, text=True)


def find_python_310() -> Optional[str]:
    """Find Python 3.10 executable on the system."""
    # Common Python 3.10 executable names to try
    python_candidates = [
        "python3.10",
        "python3",
        "python",
    ]

    for candidate in python_candidates:
        try:
            result = subprocess.run(
                [
                    candidate,
                    "-c",
                    "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            version = result.stdout.strip()
            if version == "3.10":
                # Get full path to the executable
                which_result = subprocess.run(
                    ["which", candidate], capture_output=True, text=True, check=True
                )
                return which_result.stdout.strip()

        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    # Try pyenv if available
    try:
        result = subprocess.run(
            ["pyenv", "which", "python3.10"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None


def ensure_project_venv(project_dir: Path) -> Path:
    """Ensure a project-specific virtual environment exists with required dependencies."""
    venv_dir = project_dir / "venv"

    if not venv_dir.exists():
        console.print(
            f"[yellow]🔧 Creating project virtual environment at {venv_dir}[/yellow]"
        )

        # Check if Python 3.10 is available
        python_executable = find_python_310()
        if not python_executable:
            console.print("[red]❌ Python 3.10 is required but not found[/red]")
            console.print(
                "[yellow]💡 Please install Python 3.10 or use pyenv to manage Python versions[/yellow]"
            )
            raise RuntimeError(
                "Python 3.10 is required for project virtual environment"
            )

        console.print(f"[dim]Using Python: {python_executable}[/dim]")

        # Create virtual environment with specific Python version
        subprocess.run([python_executable, "-m", "venv", str(venv_dir)], check=True)

        # Install requirements if they exist
        requirements_file = project_dir / "requirements.txt"
        if requirements_file.exists():
            console.print("[yellow]📦 Installing project dependencies...[/yellow]")
            pip_path = venv_dir / "bin" / "pip"
            if sys.platform == "win32":
                pip_path = venv_dir / "Scripts" / "pip.exe"

            subprocess.run(
                [str(pip_path), "install", "-r", str(requirements_file)], check=True
            )

        # Install development requirements if they exist
        dev_requirements_file = project_dir / "requirements-dev.txt"
        if dev_requirements_file.exists():
            console.print("[yellow]📦 Installing development dependencies...[/yellow]")
            pip_path = venv_dir / "bin" / "pip"
            if sys.platform == "win32":
                pip_path = venv_dir / "Scripts" / "pip.exe"

            subprocess.run(
                [str(pip_path), "install", "-r", str(dev_requirements_file)], check=True
            )

    return venv_dir


def get_project_python_env(project_dir: Path) -> Dict[str, str]:
    """Get environment variables for subprocess execution with project venv."""
    venv_dir = ensure_project_venv(project_dir)

    # Get current environment
    env = os.environ.copy()

    # Update PATH to include venv binaries
    bin_dir = venv_dir / "bin"
    if sys.platform == "win32":
        bin_dir = venv_dir / "Scripts"

    current_path = env.get("PATH", "")
    env["PATH"] = f"{bin_dir}:{current_path}"
    env["VIRTUAL_ENV"] = str(venv_dir)

    # Remove any existing PYTHONPATH to avoid conflicts
    env.pop("PYTHONPATH", None)

    return env


def run_command(
    command: List[str],
    cwd: Optional[str] = None,
    capture_output: bool = False,
    check: bool = True,
    env: Optional[Dict[str, str]] = None,
    use_project_venv: bool = False,
    logger: Optional[logging.Logger] = None,
) -> subprocess.CompletedProcess:
    """Run a shell command with proper error handling.
    
    Args:
        logger: If provided, output will be written to the logger instead of console.
    """
    try:
        # Format command for copy-paste with proper quoting
        formatted_command = []
        for arg in command:
            if " " in arg or '"' in arg or "'" in arg:
                # Use single quotes and escape any single quotes inside
                escaped_arg = arg.replace("'", "'\"'\"'")
                formatted_command.append(f"'{escaped_arg}'")
            else:
                formatted_command.append(arg)

        if logger:
            logger.info(f"Running: {' '.join(formatted_command)}")
        else:
            console.print(f"[dim]Running: {' '.join(formatted_command)}[/dim]")

        # Use project venv environment if requested
        if use_project_venv and cwd:
            project_dir = Path(cwd)
            if not env:
                env = get_project_python_env(project_dir)
            else:
                # Merge with project env, giving priority to passed env
                project_env = get_project_python_env(project_dir)
                project_env.update(env)
                env = project_env

        # Stream output in real-time when logger is provided
        if logger:
            # Use Popen to stream output line by line
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                env=env,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            stdout_lines = []
            # Read and log output in real-time
            for line in process.stdout:
                line = line.rstrip()
                if line:
                    logger.info(line)
                    stdout_lines.append(line)
            
            # Wait for process to complete
            returncode = process.wait()
            
            # Create a CompletedProcess-like object
            result = subprocess.CompletedProcess(
                command,
                returncode,
                stdout='\n'.join(stdout_lines) if stdout_lines else '',
                stderr=''
            )
            
            if check and returncode != 0:
                raise subprocess.CalledProcessError(returncode, command, result.stdout, '')
            
            return result
        else:
            # Original behavior when no logger
            should_capture = capture_output
            
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=should_capture,
                text=True,
                check=check,
                env=env,
            )

            # Write output to console
            if should_capture and result.stdout:
                console.print(f"[dim]{result.stdout}[/dim]")

            return result

    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed: {' '.join(command)}"
        if logger:
            logger.error(error_msg)
            if e.stdout:
                logger.error(f"stdout: {e.stdout}")
            if e.stderr:
                logger.error(f"stderr: {e.stderr}")
        else:
            console.print(f"[red]{error_msg}[/red]")
            if e.stdout:
                console.print(f"[red]stdout: {e.stdout}[/red]")
            if e.stderr:
                console.print(f"[red]stderr: {e.stderr}[/red]")
        raise
    except FileNotFoundError:
        error_msg = f"Command not found: {command[0]}"
        info_msg = "Make sure the required tools are installed and in your PATH"
        if logger:
            logger.error(error_msg)
            logger.info(info_msg)
        else:
            console.print(f"[red]{error_msg}[/red]")
            console.print(f"[yellow]{info_msg}[/yellow]")
        raise


def check_dependencies() -> bool:
    """Check if required dependencies are available."""
    # In Docker mode, all dependencies are in the container
    if not is_repo_mode():
        console.print("  ℹ️  Running in Docker mode - dependencies available in container")
        return True
    
    # Only check dependencies in repo mode
    required_tools = ["dfx", "npm", "python3"]
    missing_tools = []

    for tool in required_tools:
        try:
            subprocess.run([tool, "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_tools.append(tool)

    if missing_tools:
        console.print("[red]Missing required dependencies:[/red]")
        for tool in missing_tools:
            console.print(f"  - {tool}")
        console.print(
            "\n[yellow]Please install the missing tools and try again.[/yellow]"
        )
        return False

    return True


def load_config(config_path: str) -> Dict[str, Any]:
    """Load and validate realm configuration."""
    try:
        with open(config_path, "r") as f:
            config_data = json.load(f)
        return config_data
    except FileNotFoundError:
        console.print(f"[red]Configuration file not found: {config_path}[/red]")
        raise
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON in configuration file: {e}[/red]")
        raise


def save_config(config_data: Dict[str, Any], config_path: str) -> None:
    """Save configuration to file."""
    try:
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
        console.print(f"[green]Configuration saved to {config_path}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to save configuration: {e}[/red]")
        raise


def get_project_root() -> Path:
    """Get the project root directory."""
    current_path = Path.cwd()

    # Look for dfx.json to identify project root
    while current_path != current_path.parent:
        if (current_path / "dfx.json").exists():
            return current_path
        current_path = current_path.parent

    # If not found, use current directory
    return Path.cwd()


def generate_port_from_branch(branch_name: str) -> int:
    """Generate a unique port number based on branch name."""
    if branch_name == "main":
        return 8000

    # Generate hash-based port
    hash_obj = hashlib.md5(branch_name.encode())
    hash_int = int(hash_obj.hexdigest()[:8], 16)
    return 8001 + (hash_int % 99)


def get_current_branch() -> str:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or "main"
    except Exception:
        return "main"


def wait_for_canister_ready(
    canister_name: str, network: str = "local", timeout: int = 60
) -> bool:
    """Wait for a canister to be ready."""
    start_time = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn(f"[progress.description]Waiting for {canister_name} to be ready..."),
        console=console,
    ) as progress:
        task = progress.add_task("waiting", total=None)

        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["dfx", "canister", "status", canister_name, "--network", network],
                    capture_output=True,
                    check=True,
                )
                if "Status: Running" in result.stdout:
                    progress.update(
                        task, description=f"[green]{canister_name} is ready![/green]"
                    )
                    return True
            except subprocess.CalledProcessError:
                pass

            time.sleep(2)

    console.print(f"[red]Timeout waiting for {canister_name} to be ready[/red]")
    return False


def create_directory_structure(base_path: Path, structure: Dict[str, Any]) -> None:
    """Create directory structure from nested dictionary."""
    for name, content in structure.items():
        path = base_path / name

        if isinstance(content, dict):
            path.mkdir(parents=True, exist_ok=True)
            create_directory_structure(path, content)
        else:
            # It's a file
            path.parent.mkdir(parents=True, exist_ok=True)
            if content is not None:
                with open(path, "w") as f:
                    f.write(content)


def display_success_panel(title: str, message: str) -> None:
    """Display a success panel."""
    console.print(
        Panel(
            Text(message, style="green"),
            title=f"[bold green]{title}[/bold green]",
            border_style="green",
        )
    )


def display_error_panel(title: str, message: str) -> None:
    """Display an error panel."""
    console.print(
        Panel(
            Text(message, style="red"),
            title=f"[bold red]{title}[/bold red]",
            border_style="red",
        )
    )


def display_info_panel(title: str, message: str) -> None:
    """Display an info panel."""
    console.print(
        Panel(
            Text(message, style="blue"),
            title=f"[bold blue]{title}[/bold blue]",
            border_style="blue",
        )
    )


# Realm Context Management


def get_realms_config_dir() -> Path:
    """Get the Realms configuration directory."""
    config_dir = Path.home() / ".realms"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def get_context_file() -> Path:
    """Get the path to the context configuration file."""
    return get_realms_config_dir() / "context.json"


def load_context() -> Dict[str, Any]:
    """Load the current realm context."""
    context_file = get_context_file()
    if not context_file.exists():
        return {}

    try:
        with open(context_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_context(context: Dict[str, Any]) -> None:
    """Save the realm context."""
    context_file = get_context_file()
    try:
        with open(context_file, "w") as f:
            json.dump(context, f, indent=2)
    except IOError as e:
        console.print(f"[red]Failed to save context: {e}[/red]")
        raise


def get_current_realm() -> Optional[str]:
    """Get the current active realm name."""
    context = load_context()
    return context.get("current_realm")


def set_current_realm(realm_name: str) -> None:
    """Set the current active realm."""
    context = load_context()
    context["current_realm"] = realm_name
    save_context(context)


def unset_current_realm() -> None:
    """Clear the current realm context."""
    context = load_context()
    context.pop("current_realm", None)
    save_context(context)


def get_current_network() -> str:
    """Get the current active network (defaults to 'local')."""
    context = load_context()
    return context.get("current_network", "local")


def set_current_network(network_name: str) -> None:
    """Set the current active network."""
    context = load_context()
    context["current_network"] = network_name
    save_context(context)


def unset_current_network() -> None:
    """Clear the current network context (reverts to 'local')."""
    context = load_context()
    context.pop("current_network", None)
    save_context(context)


def resolve_realm_details(
    realm_name: str,
    registry_network: Optional[str] = None,
    registry_canister: str = "realm_registry_backend",
) -> Tuple[str, str]:
    """Resolve realm name to network and canister ID via registry lookup.

    Returns:
        Tuple[str, str]: (network, canister_id)
    """
    # Use current network context if no registry network specified
    effective_registry_network = registry_network or get_current_network()

    try:
        # Call registry to get realm details
        cmd = [
            "dfx",
            "canister",
            "call",
            "--network",
            effective_registry_network,
            registry_canister,
            "get_realm",
            f'("{realm_name}")',
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=30
        )

        # Parse the Candid output
        output = result.stdout.strip()
        if "Ok" in output:
            # Extract realm details from Candid response
            # This is a simplified parser - in production you'd use proper Candid parsing
            if "url" in output:
                # Extract canister ID from URL field
                import re

                canister_match = re.search(r'url = "([^"]+)"', output)
                if canister_match:
                    canister_id = canister_match.group(1)
                    # For now, assume IC network if canister ID is provided
                    # This could be enhanced to store network info in registry
                    network = "ic" if len(canister_id) > 10 else "local"
                    return network, canister_id

            # Fallback: assume local network with realm name as canister
            return "local", f"{realm_name}_backend"
        else:
            raise ValueError(f"Realm '{realm_name}' not found in registry")

    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to lookup realm '{realm_name}': {e.stderr}")
    except subprocess.TimeoutExpired:
        raise ValueError(f"Timeout looking up realm '{realm_name}'")
    except Exception as e:
        raise ValueError(f"Error resolving realm '{realm_name}': {str(e)}")


def get_effective_network_and_canister(
    explicit_network: Optional[str] = None, explicit_canister: Optional[str] = None
) -> Tuple[str, str]:
    """Get the effective network and canister, considering realm and network context.

    Priority:
    1. Explicit parameters (if provided)
    2. Current realm context (if set) - overrides network context
    3. Current network context (if set)
    4. Default values (local, realm_backend)

    Returns:
        Tuple[str, str]: (network, canister_id)
    """
    # If both explicit parameters provided, use them
    if explicit_network and explicit_canister:
        return explicit_network, explicit_canister

    # Check for current realm context (highest priority)
    current_realm = get_current_realm()
    if current_realm:
        try:
            realm_network, realm_canister = resolve_realm_details(current_realm)
            # Override with explicit parameters if provided
            return (
                explicit_network or realm_network,
                explicit_canister or realm_canister,
            )
        except ValueError as e:
            console.print(f"[yellow]Warning: {e}[/yellow]")
            console.print("[yellow]Falling back to network/default values[/yellow]")

    # Use network context or explicit network
    effective_network = explicit_network or get_current_network()
    effective_canister = explicit_canister or "realm_backend"

    return effective_network, effective_canister
