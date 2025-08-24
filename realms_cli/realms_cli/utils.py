"""Utility functions for Realms CLI."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text

console = Console()


def run_command(
    command: List[str],
    cwd: Optional[str] = None,
    capture_output: bool = False,
    check: bool = True,
    env: Optional[Dict[str, str]] = None
) -> subprocess.CompletedProcess:
    """Run a shell command with proper error handling."""
    try:
        console.print(f"[dim]Running: {' '.join(command)}[/dim]")
        
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=check,
            env=env
        )
        
        if capture_output and result.stdout:
            console.print(f"[dim]{result.stdout}[/dim]")
            
        return result
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Command failed: {' '.join(command)}[/red]")
        if e.stdout:
            console.print(f"[red]stdout: {e.stdout}[/red]")
        if e.stderr:
            console.print(f"[red]stderr: {e.stderr}[/red]")
        raise
    except FileNotFoundError:
        console.print(f"[red]Command not found: {command[0]}[/red]")
        console.print("[yellow]Make sure the required tools are installed and in your PATH[/yellow]")
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
        console.print("\n[yellow]Please install the missing tools and try again.[/yellow]")
        return False
    
    return True


def load_config(config_path: str) -> Dict[str, Any]:
    """Load and validate realm configuration."""
    try:
        with open(config_path, 'r') as f:
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
        with open(config_path, 'w') as f:
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
            check=True
        )
        return result.stdout.strip() or "main"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "main"


def wait_for_canister_ready(canister_name: str, network: str = "local", timeout: int = 60) -> bool:
    """Wait for a canister to be ready."""
    start_time = time.time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[progress.description]Waiting for {canister_name} to be ready..."),
        console=console
    ) as progress:
        task = progress.add_task("waiting", total=None)
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["dfx", "canister", "status", canister_name, "--network", network],
                    capture_output=True,
                    check=True
                )
                if "Status: Running" in result.stdout:
                    progress.update(task, description=f"[green]{canister_name} is ready![/green]")
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
                with open(path, 'w') as f:
                    f.write(content)


def display_success_panel(title: str, message: str) -> None:
    """Display a success panel."""
    console.print(Panel(
        Text(message, style="green"),
        title=f"[bold green]{title}[/bold green]",
        border_style="green"
    ))


def display_error_panel(title: str, message: str) -> None:
    """Display an error panel."""
    console.print(Panel(
        Text(message, style="red"),
        title=f"[bold red]{title}[/bold red]",
        border_style="red"
    ))


def display_info_panel(title: str, message: str) -> None:
    """Display an info panel."""
    console.print(Panel(
        Text(message, style="blue"),
        title=f"[bold blue]{title}[/bold blue]",
        border_style="blue"
    ))
