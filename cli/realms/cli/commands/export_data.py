"""Export command for extracting data and codexes from Realms."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from ..utils import (
    console,
    display_error_panel,
    display_success_panel,
    get_project_root,
    run_command,
)


def export_data_command(
    output_dir: str = "exported_realm",
    entity_types: Optional[str] = None,
    network: str = "local",
    identity: Optional[str] = None,
    include_codexes: bool = True,
) -> None:
    """Export data from the realm. Saves JSON data and Python codex files."""

    console.print(
        f"[bold blue]📤 Exporting data to {output_dir}[/bold blue]\n"
    )

    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        project_root = get_project_root()

        # Prepare export arguments
        args = {
            "entity_types": entity_types.split(",") if entity_types else None,
            "include_codexes": include_codexes,
        }

        args_json = json.dumps(args)
        escaped_args = args_json.replace('"', '\\"')

        console.print("📊 Fetching data from backend...")

        cmd = [
            "dfx",
            "canister",
            "call",
            "realm_backend",
            "extension_sync_call",
            f'(record {{ extension_name = "admin_dashboard"; function_name = "export_data"; args = "{escaped_args}"; }})',
            "--network",
            network,
            "--output",
            "json",
        ]
        
        if identity:
            cmd.extend(["--identity", identity])
        
        result = run_command(
            cmd,
            cwd=project_root,
            capture_output=True,
        )

        # Parse the dfx response
        if result and result.stdout:
            # Parse the Candid response
            if "'success': True" not in result.stdout and "success = true" not in result.stdout.lower():
                display_error_panel("Backend Export Failed", result.stdout)
                raise typer.Exit(1)

            # Extract the JSON data from the Candid response
            # The response format is typically: (variant { Ok = record { success = true; data = ... } })
            try:
                # Try to extract JSON from the response
                import re
                
                # Look for the data field in the response
                # First, try to find the raw data section
                data_match = re.search(r'"data"\s*[:=]\s*"([^"]+)"', result.stdout, re.DOTALL)
                if not data_match:
                    data_match = re.search(r'data\s*=\s*"([^"]+)"', result.stdout, re.DOTALL)
                
                if not data_match:
                    console.print("[yellow]⚠️  Could not extract data from response[/yellow]")
                    console.print(f"[dim]Response: {result.stdout[:500]}...[/dim]")
                    raise typer.Exit(1)
                
                # The data is JSON-encoded as a string, so we need to parse it
                data_str = data_match.group(1)
                # Unescape the JSON string
                data_str = data_str.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                export_data = json.loads(data_str)
                
                # Separate entities and codexes
                entities = export_data.get("entities", [])
                codexes = export_data.get("codexes", [])
                
                console.print(f"[green]✓[/green] Retrieved {len(entities)} entities and {len(codexes)} codexes")
                
                # Save entities to JSON file
                if entities:
                    entities_file = output_path / "realm_data.json"
                    with open(entities_file, "w") as f:
                        json.dump(entities, f, indent=2)
                    console.print(f"[green]✓[/green] Saved entities to {entities_file}")
                
                # Save codexes to individual Python files
                if codexes and include_codexes:
                    codex_dir = output_path / "codexes"
                    codex_dir.mkdir(exist_ok=True)
                    
                    for codex in codexes:
                        codex_name = codex.get("name", "unnamed_codex")
                        codex_code = codex.get("code", "")
                        
                        # Sanitize filename
                        safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in codex_name)
                        codex_file = codex_dir / f"{safe_name}.py"
                        
                        with open(codex_file, "w") as f:
                            f.write(codex_code)
                        
                        console.print(f"[green]✓[/green] Saved codex '{codex_name}' to {codex_file}")
                
                # Create a summary file
                summary = {
                    "export_date": datetime.now().isoformat(),
                    "network": network,
                    "total_entities": len(entities),
                    "total_codexes": len(codexes),
                    "entity_types": {},
                }
                
                # Count entities by type
                for entity in entities:
                    entity_type = entity.get("_type", "Unknown")
                    summary["entity_types"][entity_type] = summary["entity_types"].get(entity_type, 0) + 1
                
                summary_file = output_path / "export_summary.json"
                with open(summary_file, "w") as f:
                    json.dump(summary, f, indent=2)
                
                console.print(f"[green]✓[/green] Saved export summary to {summary_file}")
                
                display_success_panel(
                    "Export Complete! 🎉",
                    f"Successfully exported {len(entities)} entities and {len(codexes)} codexes to {output_dir}",
                )
                
            except json.JSONDecodeError as e:
                display_error_panel("JSON Parse Error", f"Could not parse export data: {str(e)}")
                console.print(f"[dim]Response: {result.stdout[:500]}...[/dim]")
                raise typer.Exit(1)
            except Exception as e:
                display_error_panel("Export Processing Error", str(e))
                console.print(f"[dim]Response: {result.stdout[:500]}...[/dim]")
                raise typer.Exit(1)
        
        elif result and result.stderr:
            display_error_panel("Backend Export Failed", result.stderr)
            raise typer.Exit(1)
        else:
            display_error_panel("Backend Export Failed", "dfx command failed with no output")
            raise typer.Exit(1)

    except Exception as e:
        display_error_panel("Export Failed", str(e))
        raise typer.Exit(1)
