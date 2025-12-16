"""Utility functions for Realms CLI."""

import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
import venv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

console = Console()
stderr_console = Console(stderr=True)  # For warnings/errors that shouldn't pollute JSON output


def generate_timestamp() -> str:
    """Generate timestamp string for directory naming.
    
    Returns:
        Timestamp string in format YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def sanitize_name(name: str) -> str:
    """Sanitize a name for use in directory/file names.
    
    Args:
        name: Name to sanitize
        
    Returns:
        Sanitized name with only alphanumeric and underscores
    """
    # Replace spaces and hyphens with underscores
    name = name.replace(" ", "_").replace("-", "_")
    # Remove any non-alphanumeric characters except underscores
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
    # Remove multiple consecutive underscores
    name = re.sub(r'_+', '_', name)
    # Remove leading/trailing underscores
    name = name.strip('_')
    return name


def generate_output_dir_name(prefix: str, name: Optional[str] = None) -> str:
    """Generate output directory name with timestamp.
    
    Args:
        prefix: Prefix (e.g., 'realm', 'registry', 'mundus')
        name: Optional name to include
        
    Returns:
        Directory name in format: prefix_Name_YYYYMMDD_HHMMSS or prefix_YYYYMMDD_HHMMSS
    """
    timestamp = generate_timestamp()
    if name:
        sanitized_name = sanitize_name(name)
        return f"{prefix}_{sanitized_name}_{timestamp}"
    return f"{prefix}_{timestamp}"


# Global log directory for the current session
_session_log_dir: Optional[Path] = None


def set_log_dir(log_dir: Path) -> None:
    """Set the log directory for the current session."""
    global _session_log_dir
    _session_log_dir = Path(log_dir)
    _session_log_dir.mkdir(parents=True, exist_ok=True)


def get_log_dir() -> Path:
    """Get the current log directory, defaulting to current working directory."""
    return _session_log_dir or Path.cwd()


def get_logger(name: str) -> logging.Logger:
    """Get a basic logger instance (no file output).
    
    Use this for module-level loggers that don't need file logging.
    For deployment logging, use get_realms_logger() instead.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        # No handlers = no output by default (can be configured externally)
    return logger


def get_realms_logger(log_dir: Path) -> logging.Logger:
    """Get a file logger for realms.log in the specified directory.
    
    Args:
        log_dir: Directory where realms.log will be created. REQUIRED.
    
    Returns:
        Logger that writes timestamped entries to realms.log
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "realms.log"
    
    # Use unique logger name per log path to support multiple deployments
    logger_name = f"realms_{log_path}"
    logger = logging.getLogger(logger_name)
    
    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)

    # File handler with timestamps
    file_handler = logging.FileHandler(log_path, mode='a')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


def truncate_command_for_logging(command: List[str], max_arg_length: int = 200) -> str:
    """Format command for logging, truncating very long arguments like base64 data.
    
    Args:
        command: Command as list of strings
        max_arg_length: Maximum length for each argument before truncation
    
    Returns:
        Formatted command string suitable for logging
    """
    formatted_parts = []
    for arg in command:
        if len(arg) > max_arg_length:
            # Truncate long arguments (like base64 data)
            truncated = arg[:max_arg_length] + f"...[truncated {len(arg) - max_arg_length} chars]"
            formatted_parts.append(truncated)
        elif " " in arg or '"' in arg or "'" in arg:
            # Quote arguments with special characters
            escaped_arg = arg.replace("'", "'\"'\"'")
            formatted_parts.append(f"'{escaped_arg}'")
        else:
            formatted_parts.append(arg)
    return ' '.join(formatted_parts)


def get_scripts_path() -> Path:
    """
    Get scripts path - auto-detect repo mode vs pip-installed mode.
    
    Priority:
    1. ./scripts (repo mode - local development)
    2. Package bundled scripts (pip-installed mode)
    3. /app/scripts (legacy Docker image mode)
    
    Returns:
        Path to scripts directory
    """
    # 1. Check for local repo scripts
    local_scripts = Path.cwd() / "scripts"
    if local_scripts.exists() and (local_scripts / "realm_generator.py").exists():
        return local_scripts
    
    # 2. Check for bundled scripts in pip package
    package_scripts = Path(__file__).parent.parent / "scripts"  # cli -> realms -> scripts
    if package_scripts.exists() and (package_scripts / "deploy_canisters.sh").exists():
        return package_scripts
    
    # 3. Fallback to Docker image path
    return Path("/app/scripts")


def is_repo_mode() -> bool:
    """Check if running in repo mode (local scripts exist)."""
    local_scripts = Path.cwd() / "scripts"
    return local_scripts.exists() and (local_scripts / "realm_generator.py").exists()


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
        # Format command for logging (with truncation of long args like base64)
        log_command = truncate_command_for_logging(command)

        if logger:
            logger.info(f"Running: {log_command}")
        else:
            console.print(f"[dim]Running: {log_command}[/dim]")

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
                    # Also print to stdout so CI can capture it
                    print(line, flush=True)
            
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

    # Look for dfx.template.json or pyproject.toml to identify project root
    while current_path != current_path.parent:
        if (current_path / "dfx.template.json").exists():
            return current_path
        if (current_path / "pyproject.toml").exists() and (current_path / "cli").exists():
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


def is_dfx_running(network: str = "local") -> bool:
    """Check if dfx replica is running."""
    try:
        result = subprocess.run(
            ["dfx", "ping", "--network", network],
            capture_output=True,
            timeout=2
        )
        return result.returncode == 0
    except Exception:
        return False


def ensure_dfx_running(
    log_dir: Path,
    network: str = "local",
    clean: bool = True,
    port: Optional[int] = None
) -> bool:
    """Ensure dfx replica is running for local network.
    
    Args:
        log_dir: Directory where dfx.log will be created
        network: Network name (only 'local' triggers dfx start)
        clean: Whether to start with --clean flag
        port: Optional port number. If None, uses branch-based port.
    
    Returns:
        True if dfx is running (either already was or just started)
    
    Side effects:
        - Sets SKIP_DFX_START=true env var to prevent deploy scripts from starting dfx
        - Creates dfx.log in log_dir
    """
    if network != "local":
        return True
    
    # Always set this so deploy scripts don't try to start dfx
    os.environ['SKIP_DFX_START'] = 'true'
    
    if is_dfx_running(network):
        console.print("🌐 dfx already running\n")
        return True
    
    console.print("🌐 Starting dfx...\n")
    
    # Stop any existing dfx
    subprocess.run(["dfx", "stop"], capture_output=True)
    
    # Determine port
    if port is None:
        branch = get_current_branch()
        port = generate_port_from_branch(branch)
    
    # Start dfx with logging
    # dfx.log = dfx CLI logs (via --logfile)
    # dfx2.log = canister/replica logs (via stderr - requires NOT using --background)
    dfx_log_path = Path(log_dir) / "dfx.log"
    dfx2_log_path = Path(log_dir) / "dfx2.log"
    
    # Run dfx WITHOUT --background to capture canister logs from stderr
    # Redirect all file descriptors to fully detach process
    # (required for docker exec to return properly when running in containers)
    cmd = f"dfx start {'--clean ' if clean else ''}--log file --logfile {dfx_log_path} --host 127.0.0.1:{port} </dev/null >/dev/null 2>{dfx2_log_path} &"
    
    subprocess.Popen(
        cmd,
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=log_dir,
        start_new_session=True
    )
    
    console.print(f"[dim]dfx CLI log: {dfx_log_path}[/dim]")
    console.print(f"[dim]dfx canister log: {dfx2_log_path}[/dim]")
    console.print(f"[dim]dfx port: {port}[/dim]\n")
    
    # Wait for dfx to be ready
    time.sleep(5)
    
    return is_dfx_running(network)


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
    """Get the Realms configuration directory (project-local)."""
    config_dir = Path.cwd() / ".realms"
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


def get_current_realm_folder(auto_select: bool = True) -> Optional[str]:
    """Get the current active realm folder path.
    
    Args:
        auto_select: If True, automatically select the first available realm
                     when none is set in context.
    
    Returns:
        Path to the current realm folder, or None if no realms available.
    """
    context = load_context()
    folder = context.get("current_realm_folder")
    
    # If folder is set and exists, use it
    if folder and Path(folder).exists():
        return folder
    
    # Fallback: pick the first available realm (prefer deployed)
    if auto_select:
        realms = list_realm_folders()
        if realms:
            # Prefer deployed realms over created-but-not-deployed
            deployed = [r for r in realms if r["status"] == "deployed"]
            first_realm = deployed[0] if deployed else realms[0]
            
            # Auto-save for convenience
            set_current_realm_folder(first_realm["path"])
            set_current_realm(first_realm["name"])
            if first_realm["network"] != "unknown":
                set_current_network(first_realm["network"])
            
            stderr_console.print(f"[dim]📁 Auto-selected realm: {first_realm['name']}[/dim]")
            return first_realm["path"]
    
    return None


def set_current_realm_folder(folder_path: str) -> None:
    """Set the current active realm folder."""
    context = load_context()
    context["current_realm_folder"] = folder_path
    save_context(context)


def unset_current_realm_folder() -> None:
    """Clear the current realm folder context."""
    context = load_context()
    context.pop("current_realm_folder", None)
    save_context(context)


def get_effective_cwd(folder: Optional[str] = None) -> Optional[str]:
    """Get the effective working directory for dfx commands.
    
    Priority:
    1. Explicit folder parameter
    2. Current working directory if it's a realm folder
    3. Current realm folder from context
    4. None (use current working directory)
    """
    if folder:
        folder_path = Path(folder).resolve()
        if folder_path.exists():
            return str(folder_path)
        stderr_console.print(f"[yellow]⚠️  Specified folder not found: {folder}[/yellow]")
    
    # Check if current working directory is a realm folder
    cwd = Path.cwd()
    if _is_realm_folder(cwd):
        return str(cwd)
    
    # Try current realm folder from context
    current_folder = get_current_realm_folder()
    if current_folder:
        folder_path = Path(current_folder).resolve()
        if folder_path.exists():
            return str(folder_path)
    
    return None


def _is_realm_folder(path: Path) -> bool:
    """Check if a path is a realm folder (in .realms/ and starts with realm_)."""
    # Check if it's in .realms/ directory and starts with realm_
    if ".realms" in str(path) and path.name.startswith("realm_"):
        return True
    return False


def list_realm_folders(base_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all realm folders with their status information.
    
    Args:
        base_dir: Base directory to search for realms (defaults to REALM_FOLDER constant)
        
    Returns:
        List of dicts with realm folder info: name, path, network, status, canister_count, created
    """
    from .constants import REALM_FOLDER
    
    base_path = Path(base_dir) if base_dir else Path(REALM_FOLDER)
    realms = []
    
    if not base_path.exists():
        return realms
    
    # Find all realm_* directories
    for realm_dir in sorted(base_path.iterdir()):
        if not realm_dir.is_dir() or not realm_dir.name.startswith("realm_"):
            continue
        
        realm_info = {
            "name": realm_dir.name,
            "path": str(realm_dir),
            "network": "unknown",
            "status": "created",
            "canister_count": 0,
            "created": None,
        }
        
        # Get creation time
        try:
            realm_info["created"] = datetime.fromtimestamp(realm_dir.stat().st_mtime)
        except Exception:
            pass
        
        # Check for dfx.json to determine network config
        dfx_json_path = realm_dir / "dfx.json"
        if dfx_json_path.exists():
            try:
                with open(dfx_json_path, "r") as f:
                    dfx_config = json.load(f)
                # Check networks config
                networks = dfx_config.get("networks", {})
                if "ic" in networks:
                    realm_info["network"] = "ic"
                elif "staging" in networks:
                    realm_info["network"] = "staging"
                else:
                    realm_info["network"] = "local"
            except Exception:
                pass
        
        # Check for .dfx folder to determine deployment status
        dfx_folder = realm_dir / ".dfx"
        if dfx_folder.exists():
            # Check for canister_ids.json in local or network folders
            for network_dir in dfx_folder.iterdir():
                if network_dir.is_dir():
                    canister_ids_file = network_dir / "canister_ids.json"
                    if canister_ids_file.exists():
                        realm_info["status"] = "deployed"
                        realm_info["network"] = network_dir.name
                        try:
                            with open(canister_ids_file, "r") as f:
                                canister_ids = json.load(f)
                                realm_info["canister_count"] = len(canister_ids)
                        except Exception:
                            pass
                        break
        
        realms.append(realm_info)
    
    return realms


def resolve_realm_by_id(realm_id: str, base_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Resolve a realm by ID (name or index number).
    
    Args:
        realm_id: Either a realm folder name or a 1-based index number
        base_dir: Base directory to search for realms
        
    Returns:
        Realm info dict if found, None otherwise
    """
    realms = list_realm_folders(base_dir)
    
    if not realms:
        return None
    
    # Try as index first (1-based)
    try:
        index = int(realm_id) - 1
        if 0 <= index < len(realms):
            return realms[index]
    except ValueError:
        pass
    
    # Try as name
    for realm in realms:
        if realm["name"] == realm_id:
            return realm
    
    # Try partial match
    for realm in realms:
        if realm_id in realm["name"]:
            return realm
    
    return None


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
            # Log to stderr so JSON output on stdout is not polluted
            logger = get_logger("utils")
            logger.warning(f"{e}")
            stderr_console.print(f"[yellow]Warning: {e}[/yellow]")
            stderr_console.print("[yellow]Falling back to network/default values[/yellow]")

    # Use network context or explicit network
    effective_network = explicit_network or get_current_network()
    effective_canister = explicit_canister or "realm_backend"

    return effective_network, effective_canister


def get_canister_urls(
    working_dir: Path,
    network: str = "local"
) -> Dict[str, Dict[str, str]]:
    """Extract canister IDs and URLs from a deployment directory.
    
    Args:
        working_dir: Directory containing dfx.json and .dfx directory
        network: Network name (local, staging, ic, etc.)
        
    Returns:
        Dictionary mapping canister names to their IDs and URLs
    """
    import subprocess
    
    canisters = {}
    working_dir = Path(working_dir).absolute()
    
    # Read dfx.json to get list of canisters
    dfx_json_path = working_dir / "dfx.json"
    if not dfx_json_path.exists():
        return canisters
    
    try:
        with open(dfx_json_path, 'r') as f:
            dfx_config = json.load(f)
        
        canister_names = dfx_config.get("canisters", {}).keys()
        
        # Determine port for local network (default 8000)
        port = 8000
        if network == "local":
            try:
                result = subprocess.run(
                    ["dfx", "info", "webserver-port"],
                    capture_output=True, text=True, timeout=5, cwd=working_dir
                )
                if result.returncode == 0 and result.stdout.strip():
                    port = int(result.stdout.strip())
            except:
                pass  # Use default 8000
        
        # Get canister IDs and construct URLs
        for canister_name in canister_names:
            try:
                id_result = subprocess.run(
                    ["dfx", "canister", "id", canister_name],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    cwd=working_dir
                )
                
                if id_result.returncode == 0:
                    canister_id = id_result.stdout.strip()
                    
                    # Determine URL based on network - prefer CANISTER_ID.localhost format
                    canister_info = {"id": canister_id}
                    
                    if network == "local":
                        # Use CANISTER_ID.localhost:PORT format for all canisters
                        canister_info["url"] = f"http://{canister_id}.localhost:{port}/"
                    elif network in ["staging", "ic", "mainnet"]:
                        if "frontend" in canister_name:
                            canister_info["url"] = f"https://{canister_id}.icp0.io/"
                        else:
                            # For backends on IC, use Candid UI
                            canister_info["url"] = f"https://a4gq6-oaaaa-aaaab-qaa4q-cai.raw.icp0.io/?id={canister_id}"
                    
                    canisters[canister_name] = canister_info
                    
            except Exception:
                # Skip canisters we can't get IDs for
                pass
    
    except Exception:
        pass
    
    return canisters


def display_canister_urls_json(
    working_dir: Path,
    network: str = "local",
    title: str = "Deployed Canisters"
) -> None:
    """Display canister URLs as formatted JSON.
    
    Args:
        working_dir: Directory containing the deployed canisters
        network: Network name
        title: Title to display above the JSON
    """
    canisters = get_canister_urls(working_dir, network)
    
    if canisters:
        console.print(f"\n[bold cyan]📋 {title}[/bold cyan]")
        console.print(json.dumps(canisters, indent=2))
        console.print("")
