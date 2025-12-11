"""Shell command for interactive Python console in realm backend canister."""

import ast
import platform
import re
import subprocess
import sys
from typing import Optional

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from ..utils import is_repo_mode, get_effective_cwd

console = Console()


class RealmsShell:
    """Interactive Python shell for Realms backend canister."""

    def __init__(
        self, canister_name: str = "realm_backend", network: Optional[str] = None, cwd: Optional[str] = None
    ):
        self.canister_name = canister_name
        self.network = network
        self.cwd = cwd
        self.globals_dict = {}

    def execute(self, code: str) -> str:
        """
        Sends Python code to the canister's execute_code method and returns the result.
        """
        # Escape double quotes in the code
        escaped_code = code.replace('"', '\\"')

        # Prepare the dfx command
        cmd = ["dfx", "canister", "call"]

        # Add network parameter if provided
        if self.network:
            cmd.extend(["--network", self.network])

        # Add the rest of the command
        cmd.extend([self.canister_name, "execute_code_shell", f'("{escaped_code}")'])

        try:
            # Execute the dfx command from the realm folder if specified
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=self.cwd)

            # Parse the output
            output = result.stdout.strip()

            # First, check if the output is from a Python collection function like dir()
            # These typically return a tuple with a string representation of a list
            # Example: ("['item1', 'item2']\n",)

            # Remove trailing commas and parentheses that might cause parsing issues
            cleaned_output = output.strip().rstrip(",)").lstrip("(")

            # Check if it looks like a string representation of a list
            if cleaned_output.strip().startswith('"[') and (
                "\n" in cleaned_output or ']"' in cleaned_output
            ):
                # Extract just the list string (between quotes)
                list_str_match = re.search(r'"(.*)"', cleaned_output, re.DOTALL)
                if list_str_match:
                    list_str = list_str_match.group(1)
                    try:
                        # First unescape the string
                        unescaped_str = ast.literal_eval(f'"{list_str}"')
                        # Then try to evaluate it as a Python literal (list)
                        try:
                            result = ast.literal_eval(unescaped_str)
                            return str(result)
                        except (SyntaxError, ValueError):
                            # If it can't be parsed as a list, return the unescaped string
                            return unescaped_str
                    except (SyntaxError, ValueError):
                        # Basic fallback
                        return list_str.replace("\\n", "\n").replace('\\"', '"')

            # General tuple pattern: (  "content"  )
            tuple_match = re.search(r'\(\s*"(.*)"\s*\)', output, re.DOTALL)
            if tuple_match:
                tuple_content = tuple_match.group(1)
                try:
                    # Properly unescape the string content inside the tuple
                    unescaped_content = ast.literal_eval(f'"{tuple_content}"')
                    # If it's a list representation, evaluate it as such
                    if unescaped_content.startswith("[") and unescaped_content.endswith(
                        "]"
                    ):
                        try:
                            # Try to parse it as a list if it looks like one
                            list_content = ast.literal_eval(unescaped_content)
                            return str(list_content)
                        except (SyntaxError, ValueError):
                            # If it can't be parsed as a list, return as string
                            return unescaped_content
                    return unescaped_content
                except (SyntaxError, ValueError):
                    # Fallback to basic unescaping
                    unescaped_content = tuple_content.replace("\\n", "\n").replace(
                        '\\"', '"'
                    )
                    return unescaped_content

            # If not a tuple, try the standard pattern: ("content")
            standard_match = re.search(r'\("(.*)"\)', output)
            if standard_match:
                # Extract the content between quotes, preserving escaped characters
                response = standard_match.group(1)

                # Properly unescape all escape sequences using ast.literal_eval
                try:
                    # Add quotes around the string and use ast.literal_eval to handle all escape sequences
                    unescaped_response = ast.literal_eval(f'"{response}"')
                    return unescaped_response
                except (SyntaxError, ValueError):
                    # Fallback to the basic unescaping if ast.literal_eval fails
                    response = response.replace("\\n", "\n").replace('\\"', '"')
                    return response

            # If no patterns matched, return the raw output
            return output
        except subprocess.CalledProcessError as e:
            return f"Error calling canister: {e.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

    def get_dfx_version(self) -> str:
        """Get the installed dfx version."""
        try:
            result = subprocess.run(
                ["dfx", "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return "dfx not found or error getting version"
        except Exception:
            return "dfx not found or error getting version"

    def show_help(self) -> None:
        """Show help information."""
        console.print("\n[bold blue]Realms Shell Help:[/bold blue]")
        console.print("  [cyan]:q[/cyan]           - Quit the shell")
        console.print("  [cyan]:help[/cyan]        - Show this help message")
        console.print("  [cyan]:status[/cyan]      - Check canister status")
        console.print("\n[bold]Navigation:[/bold]")
        console.print("  Up Arrow     - Go to previous command in history")
        console.print("  Down Arrow   - Go to next command in history")
        console.print("\n[dim]You can execute Python code directly in this shell.")
        console.print(
            "The code will be sent to your Realms backend canister for execution."
        )
        console.print("Example: print('Hello from Realms!')")
        console.print("Example: from ggg_entities import User; User.list_all()[/dim]")
        console.print()

    def check_canister_status(self) -> None:
        """Check if the canister is responding."""
        try:
            cmd = ["dfx", "canister", "call"]
            if self.network:
                cmd.extend(["--network", self.network])
            cmd.extend([self.canister_name, "status"])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, cwd=self.cwd)
            if result.returncode == 0:
                console.print("[green]✅ Backend canister is responding[/green]")
                if "success = true" in result.stdout:
                    console.print("[green]✅ Backend status: healthy[/green]")
            else:
                console.print("[red]❌ Backend canister not responding[/red]")
                if result.stderr:
                    console.print(f"[red]Error: {result.stderr.strip()}[/red]")
        except subprocess.TimeoutExpired:
            console.print("[red]❌ Canister call timed out[/red]")
        except Exception as e:
            console.print(f"[red]❌ Could not check canister status: {e}[/red]")

    def run_shell(self) -> None:
        """Run an interactive shell for executing Python code on the canister."""
        # Get version information
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        python_implementation = platform.python_implementation()
        dfx_version = self.get_dfx_version()

        # Display welcome message with version info
        console.print("[bold blue]🏛️  Realms Interactive Shell[/bold blue]")
        console.print(
            f"[dim]Python {python_version} ({python_implementation}) on {platform.system()}[/dim]"
        )
        console.print(f"[dim]DFX: {dfx_version}[/dim]")
        console.print(f"[bold]Canister:[/bold] [cyan]{self.canister_name}[/cyan]")
        console.print(
            f"[bold]Network:[/bold] [cyan]{self.network if self.network else 'local'}[/cyan]"
        )
        console.print("[dim]Type ':q' to quit, ':help' for help[/dim]")
        console.print(
            "[dim]Arrow keys ↑↓ can be used to navigate command history[/dim]"
        )
        console.print()

        # Check canister status on startup
        self.check_canister_status()
        console.print()

        # Create a prompt session with history
        history = InMemoryHistory()
        session = PromptSession(history=history)

        while True:
            try:
                # Get user input with prompt_toolkit (supports arrow key navigation)
                user_input = session.prompt("realms>>> ")

                # Check for shell commands
                if user_input.strip() == ":q":
                    break
                elif user_input.strip() == ":help":
                    self.show_help()
                elif user_input.strip() == ":status":
                    self.check_canister_status()
                # If not a shell command, send to canister
                elif user_input.strip():
                    result = self.execute(user_input)
                    if result:
                        console.print(result, end="")

            except KeyboardInterrupt:
                console.print("\n[dim]Use ':q' to quit[/dim]")
            except EOFError:
                break
            except Exception as e:
                console.print(f"[red]Shell error: {str(e)}[/red]")

        console.print("[bold blue]Goodbye![/bold blue]")


def shell_command(
    network: Optional[str],
    canister: str,
    file: Optional[str],
    cwd: Optional[str] = None,
) -> None:
    """Start an interactive Python shell connected to the Realms backend canister or execute a Python file."""
    # If file is provided, execute it instead of interactive shell
    if file:
        console.print(f"[bold blue]📄 Executing Python file: {file}[/bold blue]\n")
        execute_python_file(file, canister, network, cwd)
        return

    console.print("[bold blue]🚀 Starting Realms Shell[/bold blue]\n")

    # Check if dfx is available (only in repo mode - in Docker mode it's in the container)
    if is_repo_mode():
        try:
            subprocess.run(["dfx", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print(
                "[red]❌ dfx not found. Please install dfx and ensure it's in your PATH.[/red]"
            )
            raise typer.Exit(1)

    # Check if dfx replica is running (for local network)
    if not network or network == "local":
        try:
            result = subprocess.run(
                ["dfx", "ping"], capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                console.print(
                    "[yellow]⚠️  dfx replica doesn't seem to be running. You may need to run 'dfx start'.[/yellow]"
                )
        except Exception:
            console.print("[yellow]⚠️  Could not check dfx replica status.[/yellow]")

    # Create and run the shell
    shell = RealmsShell(canister_name=canister, network=network, cwd=cwd)
    shell.run_shell()


def execute_python_file(file_path: str, canister: str, network: Optional[str], cwd: Optional[str] = None) -> None:
    """Execute a Python file on the Realms backend canister."""
    import os
    from pathlib import Path

    # Check if file exists
    if not os.path.exists(file_path):
        console.print(f"[red]❌ File not found: {file_path}[/red]")
        raise typer.Exit(1)

    # Read the file content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code_content = f.read()
    except Exception as e:
        console.print(f"[red]❌ Error reading file: {e}[/red]")
        raise typer.Exit(1)

    if not code_content.strip():
        console.print(f"[yellow]⚠️  File is empty: {file_path}[/yellow]")
        return

    console.print(
        f"[dim]Executing {len(code_content)} characters of Python code...[/dim]"
    )

    # Create shell instance and execute the code
    shell = RealmsShell(canister_name=canister, network=network, cwd=cwd)

    try:
        result = shell.execute(code_content)
        if result:
            console.print(result)
        console.print(f"[green]✅ Successfully executed {Path(file_path).name}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Error executing file: {e}[/red]")
        raise typer.Exit(1)