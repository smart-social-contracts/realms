"""Run command for executing and scheduling tasks on realm backend canister."""

import json
import subprocess
from typing import Optional

import typer
from rich.console import Console

from ..utils import get_effective_cwd
from ._dfx_utils import build_dfx_call_cmd, parse_candid_string_output, parse_candid_json_response

console = Console()

class RealmsRunner:
    """Task runner for Realms backend canister."""

    def __init__(
        self, canister_name: str = "realm_backend", network: Optional[str] = None, cwd: Optional[str] = None
    ):
        self.canister_name = canister_name
        self.network = network
        self.cwd = cwd

    def execute(self, code: str) -> str:
        """
        Sends Python code to the canister's execute_code_shell method and returns the result.
        """
        escaped_code = code.replace('"', '\\"')
        cmd = build_dfx_call_cmd(
            self.canister_name, "execute_code_shell",
            f'("{escaped_code}")', self.network,
        )

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=self.cwd)
            return parse_candid_string_output(result.stdout)
        except subprocess.CalledProcessError as e:
            return f"Error calling canister: {e.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

    def poll_task_status(self, task_id: str) -> dict:
        """
        Poll the status of an async task using get_objects.
        Returns a dictionary with task status information.
        """
        cmd = build_dfx_call_cmd(
            self.canister_name, "get_objects",
            f'(vec {{ record {{ 0 = "Task"; 1 = "{task_id}" }}; }})',
            self.network, output_format="json",
        )

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=self.cwd)
            response = json.loads(result.stdout)
            
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
    cmd = build_dfx_call_cmd(
        canister, "create_multi_step_scheduled_task",
        f'("{task_name}", "{steps_json_escaped}", {repeat_every}, {run_after})',
        network,
    )
    
    try:
        console.print(f"[dim]Calling backend to create multi-step task...[/dim]")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30, cwd=cwd)
        data = parse_candid_json_response(result.stdout)
        
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
        raise typer.Exit(1)
    except typer.Exit:
        raise
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
    """Execute or schedule Python code on the Realms backend canister."""
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

    # No file/config: fall back to interactive shell (delegate to shell command)
    from .shell import shell_command
    shell_command(network=network, canister=canister, file=None, cwd=effective_cwd)


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

    # Create runner instance and execute the code
    runner = RealmsRunner(canister_name=canister, network=network, cwd=cwd)

    try:
        raw_result = runner.execute(code_content)
        if raw_result:
            console.print(raw_result)

        console.print(f"[green]✅ Successfully executed {Path(file_path).name}[/green]")
    except typer.Exit:
        raise
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

    # Wrap as single-step config for create_multi_step_scheduled_task
    steps_json = json.dumps([{"code": encoded_code}])
    steps_json_escaped = steps_json.replace('"', '\\"')

    cmd = build_dfx_call_cmd(
        canister, "create_multi_step_scheduled_task",
        f'("{file_name}", "{steps_json_escaped}", {interval}, {delay})',
        network,
    )
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30, cwd=cwd)
        data = parse_candid_json_response(result.stdout)
        
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
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]❌ Error scheduling task: {e}[/red]")
        raise typer.Exit(1)
