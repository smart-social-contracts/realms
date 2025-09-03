"""
Extension command for managing Realm extensions.

Provides functionality for packaging, installing, and managing extensions
in the Smart Social Contracts platform.
"""

import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def validate_extension_id(extension_id):
    """Validate extension ID (no hyphens allowed)"""
    if "-" in extension_id:
        raise ValueError(
            f"Extension ID '{extension_id}' contains hyphens. Only underscores are allowed."
        )
    return True


def get_project_paths():
    """Get standard project paths for extension management"""
    # Navigate up from cli/realms_cli/commands to project root
    current_dir = Path(__file__).parent.parent.parent.parent
    project_root = current_dir.resolve()

    return {
        "project_root": str(project_root),
        "backend_dir": str(project_root / "src" / "realm_backend"),
        "frontend_dir": str(project_root / "src" / "realm_frontend"),
        "extensions_dir": str(project_root / "extensions"),
    }


def get_extension_paths(extension_id):
    """Get all paths for an extension"""
    validate_extension_id(extension_id)
    paths = get_project_paths()

    return {
        "backend": os.path.join(
            paths["backend_dir"], "extension_packages", extension_id
        ),
        "frontend_lib": os.path.join(
            paths["frontend_dir"], "src/lib/extensions", extension_id
        ),
        "frontend_route": os.path.join(
            paths["frontend_dir"], "src/routes/(sidebar)/extensions", extension_id
        ),
        "i18n": os.path.join(
            paths["frontend_dir"], "src/lib/i18n/locales/extensions", extension_id
        ),
        "source": os.path.join(paths["extensions_dir"], extension_id),
    }


def find_extension_locations(extension_id):
    """Find where an extension is located"""
    paths = get_extension_paths(extension_id)
    locations = {}

    # Check each location
    for location_type, path in paths.items():
        if os.path.exists(path) and os.listdir(path):
            locations[location_type] = path

    return locations


def list_extensions_command():
    """List all installed extensions"""
    paths = get_project_paths()
    backend_ext_dir = os.path.join(paths["backend_dir"], "extension_packages")
    frontend_ext_dir = os.path.join(paths["frontend_dir"], "src/lib/extensions")

    extensions = {}

    # Check backend extensions
    if os.path.exists(backend_ext_dir):
        for item in os.listdir(backend_ext_dir):
            if os.path.isdir(
                os.path.join(backend_ext_dir, item)
            ) and not item.startswith("__"):
                try:
                    validate_extension_id(item)
                    manifest_path = os.path.join(backend_ext_dir, item, "manifest.json")

                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, "r") as f:
                                manifest = json.load(f)
                            extensions[item] = {
                                "id": item,
                                "version": manifest.get("version", "unknown"),
                                "description": manifest.get("description", ""),
                                "has_backend": True,
                                "has_frontend": False,
                            }
                        except Exception:
                            extensions[item] = {
                                "id": item,
                                "version": "unknown",
                                "description": "",
                                "has_backend": True,
                                "has_frontend": False,
                            }
                except ValueError:
                    console.print(
                        f"[yellow]Skipping extension with invalid ID: {item}[/yellow]"
                    )

    # Check frontend extensions
    if os.path.exists(frontend_ext_dir):
        for item in os.listdir(frontend_ext_dir):
            if os.path.isdir(
                os.path.join(frontend_ext_dir, item)
            ) and not item.startswith("__"):
                try:
                    validate_extension_id(item)

                    if item in extensions:
                        extensions[item]["has_frontend"] = True
                    else:
                        extensions[item] = {
                            "id": item,
                            "version": "unknown",
                            "description": "",
                            "has_backend": False,
                            "has_frontend": True,
                        }
                except ValueError:
                    console.print(
                        f"[yellow]Skipping extension with invalid ID: {item}[/yellow]"
                    )

    if not extensions:
        console.print("[yellow]No extensions installed[/yellow]")
        return

    # Create table
    table = Table(title="Installed Extensions")
    table.add_column("ID", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Components", style="magenta")
    table.add_column("Description", style="white")

    for ext_id, ext in extensions.items():
        components = []
        if ext["has_backend"]:
            components.append("backend")
        if ext["has_frontend"]:
            components.append("frontend")

        table.add_row(
            ext_id,
            ext["version"],
            ", ".join(components),
            (
                ext["description"][:50] + "..."
                if len(ext["description"]) > 50
                else ext["description"]
            ),
        )

    console.print(table)


def install_from_source_command(source_dir: str = "extensions"):
    """Package all extensions from source and install them"""
    paths = get_project_paths()
    extensions_source_dir = os.path.join(paths["project_root"], source_dir)

    if not os.path.exists(extensions_source_dir):
        console.print(
            f"[red]Extensions source directory not found: {extensions_source_dir}[/red]"
        )
        return False

    console.print(
        f"[green]Installing extensions from source directory: {extensions_source_dir}[/green]"
    )

    # Find all extension directories
    extension_dirs = []
    for item in os.listdir(extensions_source_dir):
        item_path = os.path.join(extensions_source_dir, item)
        if os.path.isdir(item_path) and not item.startswith("."):
            try:
                validate_extension_id(item)
                extension_dirs.append(item)
            except ValueError:
                console.print(
                    f"[yellow]Skipping directory with invalid extension ID: {item}[/yellow]"
                )

    if not extension_dirs:
        console.print(
            "[red]No valid extension directories found in source directory[/red]"
        )
        return False

    console.print(f"[blue]Found {len(extension_dirs)} extensions to install[/blue]")

    # Install each extension (simplified version - just copy files)
    success_count = 0
    for ext_id in extension_dirs:
        try:
            console.print(f"[blue]Installing {ext_id}...[/blue]")

            source_path = os.path.join(extensions_source_dir, ext_id)
            paths = get_extension_paths(ext_id)

            # Copy backend files if they exist
            backend_source = os.path.join(source_path, "backend")
            if os.path.exists(backend_source):
                os.makedirs(paths["backend"], exist_ok=True)
                shutil.copytree(backend_source, paths["backend"], dirs_exist_ok=True)
                console.print("  [green]✓[/green] Backend files copied")

            # Copy frontend files if they exist
            frontend_source = os.path.join(source_path, "frontend")
            if os.path.exists(frontend_source):
                # Copy lib files
                lib_source = os.path.join(frontend_source, "lib", "extensions", ext_id)
                if os.path.exists(lib_source):
                    os.makedirs(paths["frontend_lib"], exist_ok=True)
                    shutil.copytree(
                        lib_source, paths["frontend_lib"], dirs_exist_ok=True
                    )
                    console.print("  [green]✓[/green] Frontend lib files copied")

                # Copy route files
                route_source = os.path.join(
                    frontend_source, "routes", "(sidebar)", "extensions", ext_id
                )
                if os.path.exists(route_source):
                    os.makedirs(paths["frontend_route"], exist_ok=True)
                    shutil.copytree(
                        route_source, paths["frontend_route"], dirs_exist_ok=True
                    )
                    console.print("  [green]✓[/green] Frontend route files copied")

                # Copy i18n files
                i18n_source = os.path.join(
                    frontend_source, "i18n", "locales", "extensions", ext_id
                )
                if os.path.exists(i18n_source):
                    os.makedirs(paths["i18n"], exist_ok=True)
                    shutil.copytree(i18n_source, paths["i18n"], dirs_exist_ok=True)
                    console.print("  [green]✓[/green] i18n files copied")

            console.print(f"[green]✓ {ext_id} installed successfully[/green]")
            success_count += 1

        except Exception as e:
            console.print(f"[red]✗ Failed to install {ext_id}: {str(e)}[/red]")

    console.print(
        f"\n[green]Installation complete: {success_count}/{len(extension_dirs)} extensions installed[/green]"
    )
    return success_count == len(extension_dirs)


def extension_command(
    action: str = typer.Argument(
        ..., help="Action to perform: list, install-from-source"
    ),
    source_dir: str = typer.Option(
        "extensions", "--source-dir", help="Source directory for extensions"
    ),
) -> None:
    """Manage Realm extensions."""

    if action == "list":
        list_extensions_command()
    elif action == "install-from-source":
        install_from_source_command(source_dir)
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("[yellow]Available actions: list, install-from-source[/yellow]")
        raise typer.Exit(1)
