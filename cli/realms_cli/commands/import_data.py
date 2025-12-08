"""Import command for loading JSON data and codex files into Realms."""

import base64
import json
import tempfile
from pathlib import Path
from typing import Optional

import typer

from ..constants import MAX_BATCH_SIZE
from ..utils import (
    console,
    display_error_panel,
    display_success_panel,
    get_effective_cwd,
    get_project_root,
    run_command,
)


def import_data_command(
    file_path: str,
    entity_type: Optional[str] = None,
    format: str = "json",
    batch_size: int = MAX_BATCH_SIZE,
    dry_run: bool = False,
    network: str = "local",
    identity: Optional[str] = None,
    canister: str = "realm_backend",
    folder: Optional[str] = None,
) -> None:
    """Import data into the realm. Supports JSON data and Python codex files."""

    # Handle codex files separately
    if entity_type == "codex":
        return import_codex_command(file_path, dry_run=dry_run, network=network, identity=identity, canister=canister, folder=folder)

    console.print(
        f"[bold blue]📥 Importing data from {file_path}[/bold blue]\n"
    )

    try:
        data_file = Path(file_path)
        if not data_file.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")

        with open(data_file, "r") as f:
            data = json.load(f)

        console.print(type(data))

        if not isinstance(data, list):
            raise ValueError("JSON data must be an array of objects")

        console.print(f"📊 Found {len(data)} records to import")

        # TODO:
        # if dry_run:
        #     console.print("[yellow]🔍 Dry run mode - no data will be imported[/yellow]")
        #     display_success_panel(
        #         "Dry Run Complete",
        #         f"Would import {len(data)} {entity_type} records from {file_path}",
        #     )
        #     return

        project_root = get_project_root()

        for i in range(0, len(data), batch_size):
            chunk = data[i : i + batch_size]

            console.print(
                f"📊 Sending chunk {i // batch_size + 1}/{len(data) // batch_size}"
            )

            args = {
                "format": format,
                "data": chunk,
            }

            args_json = json.dumps(args)
            # Use base64 encoding to avoid shell escaping issues
            args_b64 = base64.b64encode(args_json.encode()).decode()

            cmd = [
                "dfx",
                "canister",
                "call",
                canister,
                "extension_sync_call",
                f'(record {{ extension_name = "admin_dashboard"; function_name = "import_data"; args = "base64:{args_b64}"; }})',
                "--network",
                network,
                "--output",
                "json",
            ]
            
            if identity:
                cmd.extend(["--identity", identity])
            
            console.print(f"Running: {' '.join(cmd[:6])}...")
            
            # Run from realm folder so dfx can find .dfx/local/canister_ids.json
            effective_cwd = get_effective_cwd(folder)
            result = run_command(
                cmd,
                cwd=effective_cwd,
                capture_output=True,
            )

            # Parse the dfx response to check for backend errors
            if result and result.stdout:
                # Check for success in response (handle both JSON double quotes and Python single quotes)
                if '"success": true' in result.stdout.lower() or "'success': True" in result.stdout:
                    display_success_panel("Import Chunk Complete! 🎉", result.stdout)
                else:
                    display_error_panel("Backend Import Chunk Failed", result.stdout)
                    raise typer.Exit(1)
     
            elif result and result.stderr:
                # dfx command had stderr output
                display_error_panel("Backend Import Chunk Failed", result.stderr)
                raise typer.Exit(1)
            else:
                # dfx command failed completely
                display_error_panel("Backend Import Data Failed", "dfx command failed with no output")
                raise typer.Exit(1)
                
        display_success_panel(
            "Import Data Complete! 🎉",
            f"Successfully imported {len(data)} records from {file_path}",
        )

    except Exception as e:
        display_error_panel("Backend Import Data Failed", str(e))
        raise typer.Exit(1)


def import_codex_command(
    file_path: str,
    codex_name: Optional[str] = None,
    dry_run: bool = False,
    network: str = "local",
    identity: Optional[str] = None,
    canister: str = "realm_backend",
    folder: Optional[str] = None,
) -> None:
    """Import Python codex file into the realm.

    We use base64 encoding for codexes because escaping Python code in JSON can be problematic.
    """

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
        base64_content = 'base64:' + base64.b64encode(codex_content.encode()).decode()

        args = {
            "format": "json",
            "data": [
                {
                    "_type": "Codex",
                    "name": codex_name,
                    "code": base64_content
                }
            ]
        }

        args_json = json.dumps(args)
        escaped_args = args_json.replace('"', '\\"')

        cmd = [
            "dfx",
            "canister",
            "call",
            canister,
            "extension_sync_call",
            f'(record {{ extension_name = "admin_dashboard"; function_name = "import_data"; args = "{escaped_args}"; }})',
            "--network",
            network,
        ]
        
        if identity:
            cmd.extend(["--identity", identity])
        
        # Run from realm folder so dfx can find .dfx/local/canister_ids.json
        effective_cwd = get_effective_cwd(folder)
        result = run_command(
            cmd,
            cwd=effective_cwd,
        )

        display_success_panel(
            "Codex Import Complete! 🎉",
            f"Successfully imported codex '{codex_name}' from {file_path}",
        )

    except Exception as e:
        display_error_panel("Codex Import Failed", str(e))
        raise typer.Exit(1)
