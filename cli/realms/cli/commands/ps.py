"""PS command for listing, killing, and viewing logs of scheduled tasks."""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..utils import get_effective_cwd

console = Console()


def format_timestamp(ts: int) -> str:
    """Format a unix timestamp as a readable string."""
    if ts == 0 or ts is None:
        return "Never"
    try:
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return str(ts)


def format_interval(seconds: int) -> str:
    """Format interval in seconds to human-readable string."""
    if seconds == 0:
        return "once"
    
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m{secs}s" if secs > 0 else f"{minutes}m"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h{minutes}m" if minutes > 0 else f"{hours}h"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d{hours}h" if hours > 0 else f"{days}d"


def call_canister_endpoint(canister: str, method: str, args: str = "()", network: Optional[str] = None, cwd: Optional[str] = None) -> dict:
    """Helper to call a canister endpoint and parse JSON response."""
    cmd = ["dfx", "canister", "call"]
    
    if network:
        cmd.extend(["--network", network])
    
    cmd.extend([canister, method, args])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30, cwd=cwd)
        
        # Parse the output - extract JSON from tuple format
        output = result.stdout.strip()
        
        # Handle multi-line format: (\n  "...",\n) or (\n  "..."\n)
        # Remove outer parentheses and whitespace
        if output.startswith('(') and output.endswith(')'):
            # Remove outer parentheses
            inner = output[1:-1].strip()
            
            # Remove trailing comma if present
            if inner.endswith(','):
                inner = inner[:-1].strip()
            
            # Extract string content between quotes
            if inner.startswith('"') and inner.endswith('"'):
                # Use json.loads twice: once to unwrap the outer quotes,
                # and once to parse the actual JSON content
                json_string = json.loads(inner)  # Unwrap outer quotes
                return json.loads(json_string)    # Parse the JSON
        
        return {"error": "Failed to parse response"}
        
    except subprocess.CalledProcessError as e:
        return {"error": f"Command failed: {e.stderr}"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {e}"}
    except Exception as e:
        return {"error": str(e)}


def call_shell_json(canister: str, code: str, network: Optional[str] = None, cwd: Optional[str] = None) -> dict:
    """Execute Python code via execute_code_shell and parse JSON from stdout."""
    escaped = code.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    cmd = ["dfx", "canister", "call"]
    if network:
        cmd.extend(["--network", network])
    cmd.extend([canister, "execute_code_shell", f'("{escaped}")'])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30, cwd=cwd)
        output = result.stdout.strip()
        # Parse Candid string: ("content")
        if output.startswith('(') and output.endswith(')'):
            inner = output[1:-1].strip()
            if inner.endswith(','):
                inner = inner[:-1].strip()
            if inner.startswith('"') and inner.endswith('"'):
                text = json.loads(inner)
                # Find last JSON object line in output
                for line in reversed(text.strip().split('\n')):
                    line = line.strip()
                    if line.startswith('{'):
                        try:
                            return json.loads(line)
                        except json.JSONDecodeError:
                            continue
                return {"error": f"No JSON in response: {text[:200]}"}
        return {"error": f"Unexpected response format: {output[:200]}"}
    except subprocess.CalledProcessError as e:
        return {"error": f"Command failed: {e.stderr}"}
    except Exception as e:
        return {"error": str(e)}


def ps_ls_command(
    network: Optional[str] = None,
    canister: str = "realm_backend",
    verbose: bool = False,
    output_format: str = "table",
    folder: Optional[str] = None,
) -> None:
    """List all scheduled and running tasks."""
    if output_format != "json":
        console.print("[bold blue]📋 Scheduled Tasks & Schedules[/bold blue]\n")
    
    effective_cwd = get_effective_cwd(folder)
    
    try:
        # Query all Tasks using get_objects_paginated
        tasks_result = subprocess.run(
            [
                "dfx", "canister", "call", canister,
                "get_objects_paginated", '("Task", 0, 1000, "asc")',
                "--output", "json"
            ] + (["--network", network] if network else []),
            capture_output=True, text=True, check=False, cwd=effective_cwd
        )
        
        # Query all TaskSchedules using get_objects_paginated
        schedules_result = subprocess.run(
            [
                "dfx", "canister", "call", canister,
                "get_objects_paginated", '("TaskSchedule", 0, 1000, "asc")',
                "--output", "json"
            ] + (["--network", network] if network else []),
            capture_output=True, text=True, check=False, cwd=effective_cwd
        )
        
        if tasks_result.returncode != 0:
            error_msg = f"Error querying tasks: {tasks_result.stderr}"
            if output_format == "json":
                print(json.dumps({"error": error_msg}, indent=2))
            else:
                console.print(f"[red]❌ {error_msg}[/red]")
            raise typer.Exit(1)
        
        if schedules_result.returncode != 0:
            error_msg = f"Error querying schedules: {schedules_result.stderr}"
            if output_format == "json":
                print(json.dumps({"error": error_msg}, indent=2))
            else:
                console.print(f"[red]❌ {error_msg}[/red]")
            raise typer.Exit(1)
        
        # Parse responses
        tasks_response = json.loads(tasks_result.stdout)
        schedules_response = json.loads(schedules_result.stdout)
        
        # Extract objects from response structure
        tasks_objects = []
        if tasks_response.get('data', {}).get('objectsListPaginated', {}).get('objects'):
            for obj_str in tasks_response['data']['objectsListPaginated']['objects']:
                tasks_objects.append(json.loads(obj_str))
        
        schedules_objects = []
        if schedules_response.get('data', {}).get('objectsListPaginated', {}).get('objects'):
            for obj_str in schedules_response['data']['objectsListPaginated']['objects']:
                schedules_objects.append(json.loads(obj_str))
        
        # Build tasks list by matching schedules to tasks
        tasks = []
        current_time = int(time.time())
        
        for task in tasks_objects:
            task_id = task['_id']
            task_name = task.get('name', 'unknown')
            task_status = task.get('status', 'unknown')
            
            # Find schedules for this task
            task_schedules = [s for s in schedules_objects if str(s.get('task_id')) == str(task_id)]
            
            if not task_schedules:
                # Task without schedule
                tasks.append({
                    "task_id": task_id,
                    "name": task_name,
                    "status": task_status,
                    "last_run_at": 0,
                    "next_run": "N/A",
                    "repeat_every": 0,
                    "disabled": False,
                    "schedule_id": None,
                    "metadata": task.get('metadata', '')
                })
            else:
                for schedule in task_schedules:
                    run_at = int(schedule.get('run_at', 0))
                    repeat_every = int(schedule.get('repeat_every', 0))
                    last_run_at = int(schedule.get('last_run_at', 0))
                    disabled = bool(schedule.get('disabled', False))
                    
                    # Calculate next run
                    next_run = "N/A"
                    if disabled:
                        next_run = "Disabled"
                    elif repeat_every > 0 and last_run_at > 0:
                        next_run = last_run_at + repeat_every
                    elif run_at > current_time:
                        next_run = run_at
                    elif run_at <= current_time and last_run_at == 0:
                        next_run = "Pending"
                    elif repeat_every == 0 and last_run_at > 0:
                        next_run = "Completed"
                    
                    tasks.append({
                        "task_id": task_id,
                        "name": task_name,
                        "status": task_status,
                        "last_run_at": last_run_at,
                        "next_run": next_run,
                        "repeat_every": repeat_every,
                        "disabled": disabled,
                        "schedule_id": schedule.get('_id'),
                        "metadata": task.get('metadata', '')
                    })
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        if output_format == "json":
            print(json.dumps({"error": error_msg, "traceback": traceback.format_exc()}, indent=2))
        else:
            console.print(f"[red]❌ Error: {error_msg}[/red]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)
    
    if not tasks:
        if output_format == "json":
            print(json.dumps({"tasks": [], "total_tasks": 0, "total_schedules": 0}, indent=2))
        else:
            console.print("[yellow]No scheduled tasks found[/yellow]")
            console.print("[dim]Create tasks with: realms run --file <file> --every <seconds>[/dim]")
        return
    
    # Group tasks by task_id to show all schedules
    from collections import defaultdict
    tasks_by_id = defaultdict(list)
    for task in tasks:
        tasks_by_id[task["task_id"]].append(task)
    
    # If JSON output requested, print and return
    if output_format == "json":
        output_data = {
            "total_tasks": len(tasks_by_id),
            "total_schedules": len(tasks),
            "tasks": tasks
        }
        print(json.dumps(output_data, indent=2))
        return
    
    # Create table with more detailed information
    table = Table(title=f"Tasks: {len(tasks_by_id)} | Schedules: {len(tasks)}")
    table.add_column("Task ID", style="cyan", no_wrap=True, width=10)
    table.add_column("Task Name", style="green", width=20)
    table.add_column("Schedule ID", style="dim cyan", width=10)
    table.add_column("Status", style="yellow", width=10)
    table.add_column("Last Execution", style="blue", width=19)
    table.add_column("Next Execution", style="magenta", width=19)
    table.add_column("Interval", style="white", width=10)
    
    if verbose:
        table.add_column("Metadata", style="dim", width=30)
    
    # Sort by task ID
    for task_id in sorted(tasks_by_id.keys()):
        schedules = tasks_by_id[task_id]
        
        for idx, task in enumerate(schedules):
            # Only show task ID and name on first schedule
            if idx == 0:
                display_task_id = task["task_id"][:8]
                display_name = task["name"][:18]
            else:
                display_task_id = "↳"
                display_name = ""
            
            schedule_id = task.get("schedule_id", "")[:8] if task.get("schedule_id") else "N/A"
            status = task["status"]
            
            # Format last run
            last_run = task["last_run_at"]
            if last_run == 0:
                last_run_str = "[dim]Never[/dim]"
            else:
                last_run_str = format_timestamp(last_run)
            
            # Format next run
            next_run = task["next_run"]
            if isinstance(next_run, int):
                next_run_str = format_timestamp(next_run)
            elif next_run == "Disabled":
                next_run_str = "[dim]Disabled[/dim]"
            elif next_run == "Completed":
                next_run_str = "[dim]Completed[/dim]"
            elif next_run == "Pending":
                next_run_str = "[yellow]Pending[/yellow]"
            else:
                next_run_str = str(next_run)
            
            interval = format_interval(task["repeat_every"])
            
            # Style status
            if task["disabled"]:
                status_str = "[dim]disabled[/dim]"
            elif status == "running":
                status_str = "[green]●[/green] running"
            elif status == "pending":
                status_str = "[yellow]○[/yellow] pending"
            elif status == "failed":
                status_str = "[red]✗[/red] failed"
            elif status == "completed":
                status_str = "[blue]✓[/blue] completed"
            elif status == "cancelled":
                status_str = "[dim]✗ cancelled[/dim]"
            else:
                status_str = status
            
            if verbose:
                metadata = task.get("metadata", "")
                if metadata:
                    # Try to pretty print metadata
                    try:
                        meta_obj = json.loads(metadata) if isinstance(metadata, str) else metadata
                        metadata_str = f"created: {meta_obj.get('created_via', 'N/A')}"
                    except:
                        metadata_str = str(metadata)[:28]
                else:
                    metadata_str = ""
                
                table.add_row(
                    display_task_id, display_name, schedule_id, 
                    status_str, last_run_str, next_run_str, 
                    interval, metadata_str
                )
            else:
                table.add_row(
                    display_task_id, display_name, schedule_id,
                    status_str, last_run_str, next_run_str, interval
                )
    
    console.print(table)
    console.print(f"\n[dim]💡 Use 'realms ps kill <task_id>' to stop a task[/dim]")
    console.print(f"[dim]💡 Use 'realms ps logs <task_id>' to view execution history[/dim]")
    console.print(f"[dim]💡 Use '--verbose' flag for metadata details[/dim]")


def ps_start_command(
    task_id: str,
    network: Optional[str] = None,
    canister: str = "realm_backend",
    output_format: str = "table",
    folder: Optional[str] = None,
) -> None:
    """Start a scheduled task."""
    if output_format != "json":
        console.print(f"[bold blue]▶️ Starting Task: {task_id}[/bold blue]\n")
    
    effective_cwd = get_effective_cwd(folder)
    
    # Enable schedule via execute_code_shell
    code = (
        'import json\n'
        'from ggg import Task, TaskSchedule\n'
        'try:\n'
        '    task = Task.load(TASK_ID)\n'
        '    if task is None:\n'
        '        print(json.dumps({"success": False, "error": "Task not found"}))\n'
        '    else:\n'
        '        for s in TaskSchedule.all():\n'
        '            if hasattr(s, "task") and str(getattr(s.task, "_id", "")) == str(task._id):\n'
        '                s.disabled = False\n'
        '                break\n'
        '        print(json.dumps({"success": True, "task_id": str(task._id), "name": task.name}))\n'
        'except Exception as e:\n'
        '    print(json.dumps({"success": False, "error": str(e)}))'
    ).replace('TASK_ID', task_id)
    response = call_shell_json(canister, code, network=network, cwd=effective_cwd)
    
    if "error" in response or not response.get("success"):
        error_msg = response.get("error", "Unknown error")
        if output_format == "json":
            print(json.dumps({"success": False, "error": error_msg}, indent=2))
        else:
            console.print(f"[red]❌ Error: {error_msg}[/red]")
        raise typer.Exit(1)
    
    if output_format == "json":
        print(json.dumps({
            "success": True,
            "task_id": response['task_id'],
            "name": response['name'],
            "message": "Task started successfully"
        }, indent=2))
    else:
        console.print(f"[green]✅ Started task: {response['name']} ({response['task_id'][:8]})[/green]")
        console.print(f"\n[dim]💡 Use 'realms ps ls' to verify[/dim]")
        console.print(f"[dim]💡 Use 'realms ps logs {response['task_id'][:8]}' to view execution[/dim]")


def ps_kill_command(
    task_id: str,
    network: Optional[str] = None,
    canister: str = "realm_backend",
    output_format: str = "table",
    folder: Optional[str] = None,
) -> None:
    """Stop a scheduled task."""
    if output_format != "json":
        console.print(f"[bold blue]❌ Stopping Task: {task_id}[/bold blue]\n")
    
    effective_cwd = get_effective_cwd(folder)
    
    # Disable schedule via execute_code_shell
    code = (
        'import json\n'
        'from ggg import Task, TaskSchedule\n'
        'try:\n'
        '    task = Task.load(TASK_ID)\n'
        '    if task is None:\n'
        '        print(json.dumps({"success": False, "error": "Task not found"}))\n'
        '    else:\n'
        '        for s in TaskSchedule.all():\n'
        '            if hasattr(s, "task") and str(getattr(s.task, "_id", "")) == str(task._id):\n'
        '                s.disabled = True\n'
        '                break\n'
        '        print(json.dumps({"success": True, "task_id": str(task._id), "name": task.name}))\n'
        'except Exception as e:\n'
        '    print(json.dumps({"success": False, "error": str(e)}))'
    ).replace('TASK_ID', task_id)
    response = call_shell_json(canister, code, network=network, cwd=effective_cwd)
    
    if "error" in response or not response.get("success"):
        error_msg = response.get("error", "Unknown error")
        if output_format == "json":
            print(json.dumps({"success": False, "error": error_msg}, indent=2))
        else:
            console.print(f"[red]❌ Error: {error_msg}[/red]")
        raise typer.Exit(1)
    
    if output_format == "json":
        print(json.dumps({
            "success": True,
            "task_id": response['task_id'],
            "name": response['name'],
            "message": "Task stopped successfully"
        }, indent=2))
    else:
        console.print(f"[green]✅ Stopped task: {response['name']} ({response['task_id'][:8]})[/green]")
        console.print(f"\n[dim]💡 Use 'realms ps ls' to verify[/dim]")


def format_log_entry(log: dict) -> str:
    """Format a single log entry with human-readable timestamp.
    
    Args:
        log: Dict with 'timestamp' (nanoseconds), 'level', 'message'
    
    Returns:
        Formatted log line: "YYYY-MM-DD HH:MM:SS.XXX LEVEL    message"
    """
    from datetime import datetime
    
    # Convert nanosecond timestamp to datetime
    timestamp_ns = log['timestamp']
    timestamp_s = timestamp_ns / 1_000_000_000  # Convert to seconds
    dt = datetime.fromtimestamp(timestamp_s)
    formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Keep 3 decimal places (milliseconds)
    
    level = log['level']
    message = log['message']
    
    return f"{formatted_time} {level:8} {message}"


def ps_logs_continuous(
    task_id: str,
    network: Optional[str],
    canister: str,
    follow: bool,
    output_file: Optional[str],
    limit: int = 100,
    from_entry: int = 0,
    cwd: Optional[str] = None,
) -> None:
    """View continuous task logs via execute_code_shell."""
    # Query logs via shell code
    code = (
        'import json\n'
        'from ggg import Task, TaskExecution\n'
        'try:\n'
        '    logs = []\n'
        '    for e in TaskExecution.all():\n'
        '        if hasattr(e, "task") and str(getattr(e.task, "_id", "")).startswith("TASK_ID"):\n'
        '            logs.append({"timestamp": getattr(e, "started_at", 0) * 1000000000, "level": getattr(e, "status", "INFO"), "message": str(getattr(e, "result", ""))[:500]})\n'
        '    print(json.dumps(logs[-LIMIT:]))\n'
        'except Exception as ex:\n'
        '    print(json.dumps([]))'
    ).replace('TASK_ID', task_id).replace('LIMIT', str(limit))

    escaped = code.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    cmd = ["dfx", "canister", "call"]
    if network:
        cmd.extend(["--network", network])
    cmd.extend([canister, "execute_code_shell", f'("{escaped}")'])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30, cwd=cwd)
        output = result.stdout.strip()
        logs_data = []
        if output.startswith('(') and output.endswith(')'):
            inner = output[1:-1].strip()
            if inner.endswith(','):
                inner = inner[:-1].strip()
            if inner.startswith('"') and inner.endswith('"'):
                try:
                    text = json.loads(inner)
                    for line in text.strip().split('\n'):
                        if line.strip().startswith('['):
                            logs_data = json.loads(line.strip())
                            break
                except (json.JSONDecodeError, TypeError):
                    pass

        if not isinstance(logs_data, list):
            logs_data = []

        if output_file:
            with open(output_file, 'w' if not follow else 'a') as f:
                for log in logs_data:
                    formatted_line = format_log_entry(log)
                    f.write(formatted_line + '\n')
            console.print(f"[green]✅ Logs written to {output_file}[/green]")

        if not output_file or follow:
            console.print(f"[bold blue]📋 Task Logs: {task_id}[/bold blue]\n")
            if logs_data:
                for log in logs_data:
                    formatted_line = format_log_entry(log)
                    console.print(formatted_line)
            else:
                console.print("[dim]No logs found[/dim]")
            console.print()

        if follow:
            console.print("[dim]Following logs (Ctrl+C to stop)...[/dim]\n")
            try:
                while True:
                    time.sleep(2)
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30, cwd=cwd)
                    # Re-parse (simplified: just show any new output)
                    console.print("[dim].[/dim]", end="")
            except KeyboardInterrupt:
                console.print("\n[dim]Stopped following logs[/dim]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Error calling canister: {e.stderr}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error retrieving logs: {str(e)}[/red]")
        raise typer.Exit(1)


def ps_logs_command(
    task_id: str,
    network: Optional[str] = None,
    canister: str = "realm_backend",
    tail: int = 20,
    output_format: str = "table",
    follow: bool = False,
    output_file: Optional[str] = None,
    limit: int = 100,
    from_entry: int = 0,
    folder: Optional[str] = None,
) -> None:
    """View execution logs for a task."""
    
    effective_cwd = get_effective_cwd(folder)
    
    # Use continuous log viewer for --follow or --output-file
    if follow or output_file:
        return ps_logs_continuous(
            task_id, network, canister, follow, output_file, limit, from_entry, cwd=effective_cwd
        )
    
    if output_format != "json":
        console.print(f"[bold blue]📑 Task Execution History: {task_id}[/bold blue]\n")
    
    # Query task executions via execute_code_shell
    code = (
        'import json\n'
        'from ggg import Task, TaskExecution\n'
        'try:\n'
        '    task = None\n'
        '    for t in Task.all():\n'
        '        if str(t._id).startswith("TASK_ID") or getattr(t, "name", "").startswith("TASK_ID"):\n'
        '            task = t\n'
        '            break\n'
        '    if task is None:\n'
        '        print(json.dumps({"success": False, "error": "Task TASK_ID not found"}))\n'
        '    else:\n'
        '        execs = []\n'
        '        for e in TaskExecution.all():\n'
        '            if hasattr(e, "task") and str(getattr(e.task, "_id", "")) == str(task._id):\n'
        '                execs.append({"status": getattr(e, "status", "unknown"), "started_at": str(getattr(e, "started_at", 0)), "result": str(getattr(e, "result", ""))[:100], "logs": str(getattr(e, "logs", ""))[:300]})\n'
        '        execs = execs[-TAIL:]\n'
        '        print(json.dumps({"success": True, "task_id": str(task._id), "task_name": task.name, "status": getattr(task, "status", "unknown"), "total_executions": len(execs), "executions": execs}))\n'
        'except Exception as ex:\n'
        '    print(json.dumps({"success": False, "error": str(ex)}))'
    ).replace('TASK_ID', task_id).replace('TAIL', str(tail))
    response = call_shell_json(canister, code, network=network, cwd=effective_cwd)
    
    if "error" in response or not response.get("success"):
        error_msg = response.get("error", "Unknown error")
        if output_format == "json":
            print(json.dumps({"success": False, "error": error_msg}, indent=2))
        else:
            console.print(f"[red]❌ Error: {error_msg}[/red]")
        raise typer.Exit(1)
    
    if output_format == "json":
        print(json.dumps({
            "success": True,
            "task_id": response['task_id'],
            "task_name": response['task_name'],
            "status": response['status'],
            "total_executions": response['total_executions'],
            "executions": response.get("executions", [])
        }, indent=2))
        return
    
    console.print(f"[bold]Task:[/bold] {response['task_name']} ({response['task_id'][:8]})")
    console.print(f"[bold]Status:[/bold] {response['status']}")
    console.print(f"[bold]Total Executions:[/bold] {response['total_executions']}\n")
    
    executions = response.get("executions", [])
    
    if not executions:
        console.print("[yellow]No executions recorded yet[/yellow]")
        return
    
    console.print(f"[bold]Recent Executions (last {len(executions)}):[/bold]\n")
    
    for i, execution in enumerate(executions, 1):
        status = execution.get("status", "unknown")
        status_color = {
            "completed": "green",
            "failed": "red",
            "running": "yellow"
        }.get(status, "white")
        
        console.print(f"  [{i}] Started: [dim]{execution['started_at']}[/dim]")
        console.print(f"      Status: [{status_color}]{status}[/{status_color}]")
        
        if "result" in execution:
            result_str = str(execution['result'])[:100]
            console.print(f"      Result: {result_str}")
        
        if "logs" in execution and execution['logs']:
            logs_str = str(execution['logs'])[:300]
            if "Error:" in logs_str or "failed" in execution.get('status', ''):
                console.print(f"      [red]Logs: {logs_str}[/red]")
            else:
                console.print(f"      Logs: [dim]{logs_str}[/dim]")
        
        console.print()
    
    console.print(f"[dim]💡 Showing last {tail} executions. Use --tail to see more.[/dim]")
    console.print(f"[dim]💡 Use 'realms ps logs {task_id} --follow' for continuous task logs[/dim]")
