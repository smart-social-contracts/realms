"""Run command for interactive Python console in realm backend canister."""

import ast
import json
import platform
import re
import subprocess
import sys
import time
from typing import Optional

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from ..utils import is_repo_mode, get_effective_cwd

console = Console()

# Configuration constants for async task polling
DEFAULT_TASK_TIMEOUT_SECONDS = 60
DEFAULT_POLL_INTERVAL_SECONDS = 2

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
        cmd.extend([self.canister_name, "execute_code", f'("{escaped_code}")'])

        try:
            # Execute the dfx command
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

    def poll_task_status(self, task_id: str) -> dict:
        """
        Poll the status of an async task using get_objects.
        Returns a dictionary with task status information.
        """
        # Prepare the dfx command using get_objects to query the Task entity
        cmd = [
            "dfx", "canister", "call",
            self.canister_name, "get_objects",
            f'(vec {{ record {{ 0 = "Task"; 1 = "{task_id}" }}; }})',
            "--output", "json"
        ]

        # Add network parameter if provided
        if self.network:
            cmd.insert(3, "--network")
            cmd.insert(4, self.network)

        try:
            # Execute the dfx command
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=self.cwd)

            # Parse the JSON response
            response = json.loads(result.stdout)
            
            # Extract task data from response
            if response.get('data', {}).get('objectsList', {}).get('objects'):
                objects = response['data']['objectsList']['objects']
                if objects and len(objects) > 0:
                    task_data = json.loads(objects[0])
                    return {
                        "task_id": task_id,
                        "status": task_data.get("status", "unknown"),
                        "name": task_data.get("name", "unknown")
                    }
                else:
                    return {"error": f"Task with ID '{task_id}' not found"}
            else:
                return {"error": "Failed to parse task status response"}
                
        except subprocess.CalledProcessError as e:
            return {"error": f"Error calling canister: {e.stderr}"}
        except json.JSONDecodeError as e:
            return {"error": f"JSON decode error: {str(e)}"}
        except Exception as e:
            return {"error": f"Error polling task status: {str(e)}"}

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


def schedule_multi_step_task_from_config(
    config_path: str, 
    canister: str, 
    network: Optional[str],
    cwd: Optional[str] = None
) -> None:
    """Schedule a multi-step task from a JSON config file."""
    import os
    import json
    import base64
    from pathlib import Path
    
    # Check if config file exists
    if not os.path.exists(config_path):
        console.print(f"[red]❌ Config file not found: {config_path}[/red]")
        raise typer.Exit(1)
    
    # Read and parse config
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ Invalid JSON in config file: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error reading config file: {e}[/red]")
        raise typer.Exit(1)
    
    # Validate required fields
    required = ['name', 'steps']
    for field in required:
        if field not in config:
            console.print(f"[red]❌ Missing required field in config: {field}[/red]")
            raise typer.Exit(1)
    
    if not config['steps'] or len(config['steps']) == 0:
        console.print(f"[red]❌ Config must contain at least one step[/red]")
        raise typer.Exit(1)
    
    # Process each step
    console.print(f"[bold blue]📋 Processing multi-step task: {config['name']}[/bold blue]")
    console.print(f"[cyan]Steps:[/cyan] {len(config['steps'])}\n")
    
    steps_config = []
    config_dir = Path(config_path).parent
    
    for idx, step in enumerate(config['steps']):
        if 'file' not in step:
            console.print(f"[red]❌ Step {idx} missing 'file' field[/red]")
            raise typer.Exit(1)
        
        # Resolve step file path (relative to config file)
        step_file = step['file']
        if not os.path.isabs(step_file):
            step_file = config_dir / step_file
        else:
            step_file = Path(step_file)
        
        if not step_file.exists():
            console.print(f"[red]❌ Step {idx} file not found: {step_file}[/red]")
            raise typer.Exit(1)
        
        # Read step code
        try:
            with open(step_file, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            console.print(f"[red]❌ Error reading step {idx} file: {e}[/red]")
            raise typer.Exit(1)
        
        if not code.strip():
            console.print(f"[yellow]⚠️  Step {idx} file is empty: {step_file}[/yellow]")
        
        # Base64 encode
        encoded_code = base64.b64encode(code.encode('utf-8')).decode('ascii')
        
        # Detect async (for display purposes only - backend will auto-detect)
        is_async = "yield" in code or "async_task" in code
        async_marker = "[async]" if is_async else "[sync]"
        
        # Get run_next_after delay
        run_next_after = step.get('run_next_after', 0)
        
        steps_config.append({
            'code': encoded_code,
            'run_next_after': run_next_after
        })
        
        console.print(f"  {idx + 1}. {step_file.name} {async_marker} → wait {run_next_after}s")
    
    console.print()
    
    # Prepare backend call parameters
    task_name = config['name']
    repeat_every = config.get('every', 0)
    run_after = config.get('after', 5)
    
    console.print(f"[cyan]First run:[/cyan] in {run_after} seconds")
    if repeat_every > 0:
        console.print(f"[cyan]Repeat every:[/cyan] {repeat_every} seconds ({repeat_every // 60}m {repeat_every % 60}s)")
    else:
        console.print(f"[cyan]Repeat:[/cyan] one-time execution")
    console.print()
    
    # Convert steps config to JSON string
    steps_json = json.dumps(steps_config)
    # Escape for shell
    steps_json_escaped = steps_json.replace('"', '\\"')
    
    # Call backend
    cmd = ["dfx", "canister", "call"]
    
    if network:
        cmd.extend(["--network", network])
    
    cmd.extend([
        canister,
        "create_multi_step_scheduled_task",
        f'("{task_name}", "{steps_json_escaped}", {repeat_every}, {run_after})'
    ])
    
    try:
        console.print(f"[dim]Calling backend to create multi-step task...[/dim]")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30, cwd=cwd)
        
        # Parse response
        output = result.stdout.strip()
        if output.startswith('(') and output.endswith(')'):
            inner = output[1:-1].strip()
            if inner.endswith(','):
                inner = inner[:-1].strip()
            if inner.startswith('"') and inner.endswith('"'):
                json_str = inner[1:-1]
                json_str = json_str.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                data = json.loads(json_str)
                
                if data.get('success'):
                    console.print(f"[green]✅ Multi-step task created successfully![/green]")
                    console.print(f"[dim]   Task ID: {data['task_id']}[/dim]")
                    console.print(f"[dim]   Task name: {data['task_name']}[/dim]")
                    console.print(f"[dim]   Schedule ID: {data['schedule_id']}[/dim]")
                    console.print(f"[dim]   Steps: {data['steps_count']}[/dim]")
                    console.print(f"[dim]   First run at: {data['run_at']}[/dim]")
                    console.print(f"[dim]   Repeat every: {data['repeat_every']}s[/dim]")
                    console.print(f"\n[dim]Use 'realms ps ls' to view scheduled tasks[/dim]")
                else:
                    console.print(f"[red]❌ Error: {data.get('error', 'Unknown error')}[/red]")
                    raise typer.Exit(1)
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error calling backend: {e.stderr}[/red]")
        raise typer.Exit(1)
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ Failed to parse response: {e}[/red]")
        console.print(f"[dim]Raw output: {output}[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error scheduling multi-step task: {e}[/red]")
        raise typer.Exit(1)


def run_command(
    network: Optional[str] = None,
    canister: str = "realm_backend",
    file: Optional[str] = None,
    wait: Optional[int] = None,
    every: Optional[int] = None,
    after: Optional[int] = None,
    config: Optional[str] = None,
    folder: Optional[str] = None,
) -> None:
    """Start an interactive Python shell connected to the Realms backend canister or execute a Python file."""
    # Get effective working directory from context
    effective_cwd = get_effective_cwd(folder)
    
    # If config is provided, create multi-step task from config file
    if config:
        schedule_multi_step_task_from_config(config, canister, network, effective_cwd)
        return
    
    # If file is provided, execute it instead of interactive shell
    if file:
        # If scheduling options are provided, schedule the task
        if every is not None or after is not None:
            console.print(f"[bold blue]📅 Scheduling Python file: {file}[/bold blue]\n")
            schedule_python_file(file, canister, network, every, after, effective_cwd)
            return
        
        console.print(f"[bold blue]📄 Executing Python file: {file}[/bold blue]\n")
        execute_python_file(file, canister, network, wait, effective_cwd)
        return

    console.print("[bold blue]🚀 Starting Realms Interactive Console[/bold blue]\n")

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
    shell = RealmsShell(canister_name=canister, network=network, cwd=effective_cwd)
    shell.run_shell()


def execute_python_file(file_path: str, canister: str, network: Optional[str], wait: Optional[int] = None, cwd: Optional[str] = None) -> None:
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
            
            # If wait flag is set, check if this is an async task and poll for completion
            if wait is not None:
                try:
                    # Extract JSON from tuple format if needed
                    json_str = result
                    # Check if result is in tuple format: ("json_content")
                    tuple_match = re.search(r'\(\s*"(.*)"\s*,?\s*\)', result, re.DOTALL)
                    if tuple_match:
                        json_str = tuple_match.group(1)
                        # Unescape the JSON string - handle both \n escape sequences
                        json_str = json_str.replace('\\n', '\n').replace('\\"', '"')
                    
                    # Try to parse the result as JSON to check if it's an async task
                    result_data = json.loads(json_str)
                    
                    if result_data.get("type") == "async" and "task_id" in result_data:
                        task_id = result_data["task_id"]
                        
                        # Use provided timeout or default
                        timeout_seconds = wait if wait > 0 else DEFAULT_TASK_TIMEOUT_SECONDS
                        console.print(f"\n[cyan]⏳ Waiting for async task {task_id} to complete (timeout: {timeout_seconds}s)...[/cyan]")
                        
                        # Poll the task status
                        poll_interval = DEFAULT_POLL_INTERVAL_SECONDS
                        max_polls = timeout_seconds // poll_interval
                        polls = 0
                        
                        while polls < max_polls:
                            time.sleep(poll_interval)
                            status_data = shell.poll_task_status(task_id)
                            
                            if "error" in status_data:
                                console.print(f"[red]❌ Error polling task: {status_data['error']}[/red]")
                                break
                            
                            status = status_data.get("status", "unknown")
                            console.print(f"[dim]Status: {status}[/dim]", end="\r")
                            
                            if status == "completed":
                                console.print(f"\n[green]✅ Task completed successfully[/green]")
                                if "result" in status_data:
                                    console.print(f"Result: {status_data['result']}")
                                break
                            elif status == "failed":
                                console.print(f"\n[red]❌ Task failed[/red]")
                                if "error" in status_data:
                                    console.print(f"Error: {status_data['error']}")
                                break
                            
                            polls += 1
                        
                        if polls >= max_polls:
                            console.print(f"\n[yellow]⚠️  Timeout waiting for task completion[/yellow]")
                    else:
                        # Sync task, nothing to wait for
                        console.print(f"[dim]Task completed synchronously (no waiting needed)[/dim]")
                        
                except json.JSONDecodeError:
                    # Not JSON, probably sync execution
                    console.print(f"[dim]Task completed synchronously (no waiting needed)[/dim]")
        
        console.print(f"[green]✅ Successfully executed {Path(file_path).name}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Error executing file: {e}[/red]")
        raise typer.Exit(1)


def schedule_python_file(file_path: str, canister: str, network: Optional[str], every: Optional[int], after: Optional[int], cwd: Optional[str] = None) -> None:
    """Schedule a Python file to run at intervals on the Realms backend canister."""
    import os
    import base64
    import json
    from pathlib import Path

    # Check if file exists
    if not os.path.exists(file_path):
        console.print(f"[red]❌ File not found: {file_path}[/red]")
        raise typer.Exit(1)

    # Read the file content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            codex_code = f.read()
    except Exception as e:
        console.print(f"[red]❌ Error reading file: {e}[/red]")
        raise typer.Exit(1)

    if not codex_code.strip():
        console.print(f"[yellow]⚠️  File is empty: {file_path}[/yellow]")
        return

    # Prepare parameters
    file_name = Path(file_path).stem
    delay = after if after is not None else 0
    interval = every if every is not None else 0
    
    # Base64 encode the code for safe transmission
    encoded_code = base64.b64encode(codex_code.encode('utf-8')).decode('ascii')

    console.print(f"[dim]Setting up scheduled task...[/dim]")
    console.print(f"[cyan]File:[/cyan] {file_path}")
    console.print(f"[cyan]First run:[/cyan] in {delay} seconds")
    if interval > 0:
        console.print(f"[cyan]Repeat every:[/cyan] {interval} seconds ({interval // 60}m {interval % 60}s)")
    else:
        console.print(f"[cyan]Repeat:[/cyan] one-time execution")
    console.print()

    # Call the backend API endpoint
    cmd = ["dfx", "canister", "call"]
    
    if network:
        cmd.extend(["--network", network])
    
    cmd.extend([
        canister,
        "create_scheduled_task",
        f'("{file_name}", "{encoded_code}", {interval}, {delay})'
    ])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30, cwd=cwd)
        
        # Parse response
        output = result.stdout.strip()
        if output.startswith('(') and output.endswith(')'):
            inner = output[1:-1].strip()
            if inner.endswith(','):
                inner = inner[:-1].strip()
            if inner.startswith('"') and inner.endswith('"'):
                json_str = inner[1:-1]
                json_str = json_str.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                data = json.loads(json_str)
                
                if data.get('success'):
                    console.print(f"[green]✅ Scheduled task: {data['task_id']}[/green]")
                    console.print(f"[dim]   Task name: {data['task_name']}[/dim]")
                    console.print(f"[dim]   Schedule ID: {data['schedule_id']}[/dim]")
                    console.print(f"[dim]   First run at: {data['run_at']}[/dim]")
                    console.print(f"[dim]   Repeat every: {data['repeat_every']}s[/dim]")
                    console.print(f"\n[dim]Use 'realms ps ls' to view scheduled tasks[/dim]")
                else:
                    console.print(f"[red]❌ Error: {data.get('error', 'Unknown error')}[/red]")
                    raise typer.Exit(1)
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error calling backend: {e.stderr}[/red]")
        raise typer.Exit(1)
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ Failed to parse response: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error scheduling task: {e}[/red]")
        raise typer.Exit(1)
