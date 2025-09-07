"""Import command for loading JSON data and codex files into Realms."""

import json
from pathlib import Path
from typing import Optional
import base64

import typer

from ..utils import (
    console,
    display_error_panel,
    display_success_panel,
    get_project_root,
    run_command,
)


def import_data_command(
    file_path: str,
    entity_type: str,
    format: str = "json",
    batch_size: int = 3,
    dry_run: bool = False,
) -> None:
    """Import data into the realm. Supports JSON data and Python codex files."""

    # Handle codex files separately
    if entity_type == "codex":
        return import_codex_command(file_path, dry_run=dry_run)

    console.print(
        f"[bold blue]📥 Importing {entity_type} data from {file_path}[/bold blue]\n"
    )

    try:
        data_file = Path(file_path)
        if not data_file.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")

        with open(data_file, "r") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("JSON data must be an array of objects")

        console.print(f"📊 Found {len(data)} {entity_type} records to import")

        # TODO:
        # if dry_run:
        #     console.print("[yellow]🔍 Dry run mode - no data will be imported[/yellow]")
        #     display_success_panel(
        #         "Dry Run Complete",
        #         f"Would import {len(data)} {entity_type} records from {file_path}",
        #     )
        #     return

        project_root = get_project_root()

        batch_size = 3
        for i in range(0, len(data), batch_size):
            chunk = data[i:i + batch_size]

            console.print(f"📊 Sending chunk {i // batch_size + 1}/{len(data) // batch_size}")

            args = {
                "format": format,
                "data": chunk,
            }

            args_json = json.dumps(args)
            escaped_args = args_json.replace('"', '\\"')

            result = run_command(
                [
                    "dfx",
                    "canister",
                    "call",
                    "realm_backend",
                    "extension_sync_call",
                    f'(record {{ extension_name = "admin_dashboard"; function_name = "import_data"; args = "{escaped_args}"; }})',
                    "--network",
                    "local",
                ],
                cwd=project_root
            )

            # Parse the dfx response to check for backend errors
            if result and result.stdout:
                try:
                    # Extract the response field from the dfx output
                    import re
                    import ast
                    
                    # Look for the response field in the dfx output
                    response_match = re.search(r'response = "(.+?)";', result.stdout, re.DOTALL)
                    if response_match:
                        response_str = response_match.group(1)
                        # Unescape the response string
                        response_str = response_str.replace("\\'", "'").replace('\\"', '"')
                        
                        # Parse the backend response safely
                        try:
                            backend_response = ast.literal_eval(response_str)
                        except (ValueError, SyntaxError):
                            # Fallback to eval if literal_eval fails
                            backend_response = eval(response_str)
                        
                        if isinstance(backend_response, dict):
                            # Check if the import actually failed by looking at the detailed results
                            if not backend_response.get('success', True):
                                error_msg = backend_response.get('error', 'Unknown backend error')
                                raise Exception(f"Backend import failed: {error_msg}")
                            
                            # Check if there were failed records even if top-level success is True
                            data = backend_response.get('data', {})
                            if isinstance(data, dict):
                                failed_count = data.get('failed', 0)
                                successful_count = data.get('successful', 0)
                                errors = data.get('errors', [])
                                
                                if failed_count > 0:
                                    error_details = '\n'.join(errors) if errors else f"{failed_count} records failed to import"
                                    raise Exception(f"Import partially failed: {successful_count} successful, {failed_count} failed.\nErrors:\n{error_details}")
                                
                except Exception as parse_error:
                    # If we can't parse the response, check if there's an obvious error
                    if "success': False" in result.stdout or "failed': 1" in result.stdout:
                        raise Exception("Backend import failed - check logs for details")

        display_success_panel(
            "Import Complete! 🎉",
            f"Successfully imported {len(data)} {entity_type} records from {file_path}",
        )

    except Exception as e:
        display_error_panel("Import Failed", str(e))
        raise typer.Exit(1)


def import_codex_command(
    file_path: str, codex_name: Optional[str] = None, dry_run: bool = False
) -> None:
    """Import Python codex file into the realm."""

    console.print(f"[bold blue]📜 Importing codex from {file_path}[/bold blue]\n")

    try:
        codex_file = Path(file_path)
        if not codex_file.exists():
            raise FileNotFoundError(f"Codex file not found: {file_path}")

        with open(codex_file, "r") as f:
            codex_content = f.read()

        if not codex_name:
            codex_name = codex_file.stem

        console.print(f"📜 Importing codex: {codex_name}")

        if dry_run:
            console.print(
                "[yellow]🔍 Dry run mode - no codex will be imported[/yellow]"
            )
            display_success_panel(
                "Dry Run Complete",
                f"Would import codex '{codex_name}' from {file_path}",
            )
            return

        project_root = get_project_root()
        base64_content = base64.b64encode(codex_content.encode()).decode()

        # run_command(
        #     [
        #         "dfx",
        #         "canister",
        #         "call",
        #         "realm_backend",
        #         "create_codex",
        #         f'(record {{ name = "{codex_name}"; code = "{base64_content}"; encoding = "base64"; }})',
        #         "--network",
        #         "local",
        #     ],
        #     cwd=project_root,
        # )

        args = {
            "entity_type": "Codex",
            "format": "json",
            "data": {
                "name": codex_name,
                "code": base64_content,
                "encoding": "base64",
            },
            "batch_size": 1,
        }

        args_json = json.dumps(args)
        escaped_args = args_json.replace('"', '\\"')

        result = run_command(
            [
                "dfx",
                "canister",
                "call",
                "realm_backend",
                "extension_sync_call",
                f'(record {{ extension_name = "admin_dashboard"; function_name = "import_data"; args = "{escaped_args}"; }})',
                "--network",
                "local",
            ],
            cwd=project_root
        )

        display_success_panel(
            "Codex Import Complete! 🎉",
            f"Successfully imported codex '{codex_name}' from {file_path}",
        )

    except Exception as e:
        display_error_panel("Codex Import Failed", str(e))
        raise typer.Exit(1)
