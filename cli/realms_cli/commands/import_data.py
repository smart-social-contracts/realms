"""Import command for loading JSON data and codex files into Realms."""

import json
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


def import_data_command(
    file_path: str,
    entity_type: str,
    format: str = "json",
    batch_size: int = 100,
    dry_run: bool = False,
) -> None:
    """Import JSON data into the realm via admin_dashboard extension."""

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

        if dry_run:
            console.print("[yellow]🔍 Dry run mode - no data will be imported[/yellow]")
            display_success_panel(
                "Dry Run Complete",
                f"Would import {len(data)} {entity_type} records from {file_path}",
            )
            return

        project_root = get_project_root()

        args = {
            "entity_type": entity_type,
            "format": format,
            "data": data,
            "batch_size": batch_size,
        }

        args_json = json.dumps(args)
        escaped_args = args_json.replace('"', '\\"')

        run_command(
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
            cwd=project_root,
        )

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

    console.print(f"[bold blue]📥 Importing codex from {file_path}[/bold blue]\n")

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

        escaped_content = codex_content.replace('"', '\\"')
        run_command(
            [
                "dfx",
                "canister",
                "call",
                "realm_backend",
                "create_codex",
                f'(record {{ name = "{codex_name}"; code = "{escaped_content}"; }})',
                "--network",
                "local",
            ],
            cwd=project_root,
        )

        display_success_panel(
            "Codex Import Complete! 🎉",
            f"Successfully imported codex '{codex_name}' from {file_path}",
        )

    except Exception as e:
        display_error_panel("Codex Import Failed", str(e))
        raise typer.Exit(1)
