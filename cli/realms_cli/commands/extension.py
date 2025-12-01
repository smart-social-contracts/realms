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
from pprint import pformat

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
    # Use current working directory as project root
    # This allows the CLI to work from any Realms project directory
    project_root = Path.cwd()

    return {
        "project_root": str(project_root),
        "backend_dir": str(project_root / "src" / "realm_backend"),
        "frontend_dir": str(project_root / "src" / "realm_frontend"),
        "extensions_dir": str(project_root / "extensions"),
    }


def get_extension_paths(extension_id, source_dir=None):
    """Get all paths for an extension"""
    validate_extension_id(extension_id)
    paths = get_project_paths()
    
    if source_dir:
        # When packaging from source, use the source directory structure
        return {
            "backend": os.path.join(source_dir, "backend"),
            "frontend_lib": os.path.join(source_dir, "frontend/lib/extensions", extension_id),
            "frontend_route": os.path.join(source_dir, "frontend/routes/(sidebar)/extensions", extension_id),
            "i18n": os.path.join(source_dir, "frontend/i18n/locales/extensions", extension_id),
            "source": source_dir,
        }
    
    # Default paths in realm project structure
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


def find_extension_locations(extension_id, source_dir=None):
    """Find where an extension is located"""
    paths = get_extension_paths(extension_id, source_dir)
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

    # Check i18n-only extensions
    i18n_ext_dir = os.path.join(paths["frontend_dir"], "src/lib/i18n/locales/extensions")
    if os.path.exists(i18n_ext_dir):
        for item in os.listdir(i18n_ext_dir):
            if os.path.isdir(
                os.path.join(i18n_ext_dir, item)
            ) and not item.startswith("__"):
                try:
                    validate_extension_id(item)
                    
                    # Only add if not already discovered
                    if item not in extensions:
                        extensions[item] = {
                            "id": item,
                            "version": "unknown",
                            "description": "",
                            "has_backend": False,
                            "has_frontend": False,
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
        
        # If no backend or frontend, it's i18n-only
        if not components:
            components.append("i18n")

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


def update_extension_imports(extension_id, action="add"):
    """Update the extension_imports.py file"""
    paths = get_project_paths()
    imports_file = os.path.join(
        paths["backend_dir"], "extension_packages", "extension_imports.py"
    )

    if not os.path.exists(imports_file):
        os.makedirs(os.path.dirname(imports_file), exist_ok=True)
        with open(imports_file, "w") as f:
            f.write("")
        console.print(f"[blue]Created extension imports file: {imports_file}[/blue]")

    with open(imports_file, "r") as f:
        content = f.read()

    import_line = f"import extension_packages.{extension_id}.entry"

    if action == "add":
        if import_line in content:
            console.print(
                f"[yellow]Import for {extension_id} already exists in extension_imports.py[/yellow]"
            )
            return True

        if content and not content.endswith("\n"):
            import_line = "\n" + import_line

        if content:
            import_line += "\n"

        with open(imports_file, "a") as f:
            f.write(import_line)
        console.print(
            f"[green]Added import for {extension_id} to extension_imports.py[/green]"
        )

    elif action == "remove":
        if import_line not in content:
            console.print(
                f"[yellow]No import for {extension_id} found in extension_imports.py[/yellow]"
            )
            return True

        lines = content.splitlines()
        new_lines = [line for line in lines if line.strip() != import_line]
        new_content = "\n".join(new_lines)

        if new_content and not new_content.endswith("\n"):
            new_content += "\n"

        with open(imports_file, "w") as f:
            f.write(new_content)
        console.print(
            f"[green]Removed import for {extension_id} from extension_imports.py[/green]"
        )

    return True


def package_extension_command(extension_id: str, output_dir: Optional[str] = None, output_path: Optional[str] = None, source_dir: Optional[str] = None):
    """Package an extension into a zip file
    
    Args:
        extension_id: ID of the extension to package
        output_dir: Directory to save the zip file (used if output_path not specified)
        output_path: Full path for the output zip file (overrides output_dir)
        source_dir: Source directory containing the extension
    """
    try:
        validate_extension_id(extension_id)
    except ValueError as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return False

    locations = find_extension_locations(extension_id, source_dir)

    paths = get_project_paths()
    
    # Determine output path
    if output_path:
        zip_path = output_path
    else:
        if not output_dir:
            output_dir = paths["project_root"]
        zip_filename = f"{extension_id}.zip"
        zip_path = os.path.join(output_dir, zip_filename)

    console.print(f"[blue]Packaging extension {extension_id}[/blue]")

    custom_route_path = os.path.join(paths["frontend_dir"], "src/routes", extension_id)
    if os.path.exists(custom_route_path):
        locations["frontend_custom_routes"] = paths["frontend_dir"]
        console.print(f"[blue]Detected custom route: {custom_route_path}[/blue]")

    if not locations:
        console.print(
            f"[red]Extension '{extension_id}' not found or has no components[/red]"
        )
        return False

    manifest = None
    manifest_path = None
    
    # First try to load root manifest.json from source_dir
    if source_dir:
        root_manifest_path = os.path.join(source_dir, "manifest.json")
        if os.path.exists(root_manifest_path):
            manifest_path = root_manifest_path
            try:
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
            except Exception as e:
                console.print(f"[red]Failed to load manifest: {e}[/red]")
                return False
    
    # Fall back to backend manifest.json if root manifest not found
    if not manifest and "backend" in locations:
        backend_manifest_path = os.path.join(locations["backend"], "manifest.json")
        if os.path.exists(backend_manifest_path):
            manifest_path = backend_manifest_path
            try:
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
            except Exception as e:
                console.print(f"[red]Failed to load manifest: {e}[/red]")
                return False

    if not manifest:
        manifest = {
            "name": extension_id,
            "version": "1.0.0",
            "description": f"{extension_id} extension",
            "author": "Smart Social Contracts",
            "permissions": [],
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            if manifest_path and os.path.exists(manifest_path):
                zipf.write(manifest_path, "manifest.json")
                console.print("[blue]Added manifest.json[/blue]")
            else:
                temp_manifest_path = os.path.join(temp_dir, "manifest.json")
                with open(temp_manifest_path, "w") as f:
                    json.dump(manifest, f, indent=2)
                zipf.write(temp_manifest_path, "manifest.json")
                console.print("[blue]Added generated manifest.json[/blue]")

            if "backend" in locations:
                backend_src = locations["backend"]
                for root, _, files in os.walk(backend_src):
                    for file in files:
                        if file.endswith(".py") or file == "manifest.json":
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, backend_src)
                            zipf.write(file_path, os.path.join("backend", rel_path))
                            console.print(f"[blue]Added backend/{rel_path}[/blue]")

            if "frontend_lib" in locations:
                frontend_lib_src = locations["frontend_lib"]
                for root, _, files in os.walk(frontend_lib_src):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, frontend_lib_src)
                        zipf.write(
                            file_path,
                            os.path.join(
                                f"frontend/lib/extensions/{extension_id}", rel_path
                            ),
                        )
                        console.print(
                            f"[blue]Added frontend/lib/extensions/{extension_id}/{rel_path}[/blue]"
                        )

            # Package routes with flexible structure
            # Check for routes in the extension source
            if source_dir:
                routes_source = os.path.join(source_dir, "frontend", "routes")
            else:
                # Check default project structure for custom routes
                routes_source = os.path.join(paths["project_root"], "extensions", extension_id, "frontend", "routes")
            
            if os.path.exists(routes_source):
                for root, _, files in os.walk(routes_source):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Preserve the full directory structure from routes/
                        rel_path = os.path.relpath(file_path, routes_source)
                        zipf.write(
                            file_path,
                            os.path.join("frontend/routes", rel_path),
                        )
                        console.print(
                            f"[blue]Added frontend/routes/{rel_path}[/blue]"
                        )

            if "i18n" in locations:
                i18n_src = locations["i18n"]
                for root, _, files in os.walk(i18n_src):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, i18n_src)
                        zipf.write(
                            file_path,
                            os.path.join(
                                f"frontend/i18n/locales/extensions/{extension_id}",
                                rel_path,
                            ),
                        )
                        console.print(
                            f"[blue]Added frontend/i18n/locales/extensions/{extension_id}/{rel_path}[/blue]"
                        )

    console.print(f"[green]Extension packaged successfully: {zip_path}[/green]")
    return True


def install_extension_command(package_path: str):
    """Install an extension from a package"""
    paths = get_project_paths()

    if not os.path.exists(package_path):
        console.print(f"[red]Package file not found: {package_path}[/red]")
        return False

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(package_path, "r") as zipf:
                zipf.extractall(temp_dir)
            console.print("[blue]Extracted package to temporary directory[/blue]")
        except Exception as e:
            console.print(f"[red]Failed to extract package: {e}[/red]")
            return False

        manifest_path = os.path.join(temp_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            console.print("[red]No manifest.json found in package[/red]")
            return False

        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        except Exception as e:
            console.print(f"[red]Failed to read manifest: {e}[/red]")
            return False

        extension_id = manifest.get("name", "")
        if not extension_id:
            console.print("[red]No extension ID found in manifest[/red]")
            return False

        try:
            validate_extension_id(extension_id)
        except ValueError as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            return False

        backend_source = os.path.join(temp_dir, "backend")
        if os.path.exists(backend_source) and os.listdir(backend_source):
            backend_target = os.path.join(
                paths["backend_dir"], "extension_packages", extension_id
            )

            if os.path.exists(backend_target):
                shutil.rmtree(backend_target)

            # Ensure extension_packages directory exists and has __init__.py
            extension_packages_dir = os.path.join(paths["backend_dir"], "extension_packages")
            os.makedirs(extension_packages_dir, exist_ok=True)
            extension_packages_init = os.path.join(extension_packages_dir, "__init__.py")
            if not os.path.exists(extension_packages_init):
                with open(extension_packages_init, "w") as f:
                    f.write('"""Extension packages directory."""\n')

            os.makedirs(backend_target, exist_ok=True)

            shutil.copy2(manifest_path, os.path.join(backend_target, "manifest.json"))

            for root, _, files in os.walk(backend_source):
                for file in files:
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, backend_source)
                    dst_file = os.path.join(backend_target, rel_path)

                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    console.print(f"[blue]Installed backend file: {rel_path}[/blue]")

            init_file = os.path.join(backend_target, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, "w") as f:
                    f.write(f'"""\n{extension_id} extension package.\n"""\n')
                console.print(
                    f"[blue]Created __init__.py file for {extension_id}[/blue]"
                )

            update_extension_imports(extension_id, "add")
            console.print(f"[green]Installed backend files for {extension_id}[/green]")

        frontend_lib_source = os.path.join(
            temp_dir, "frontend/lib/extensions", extension_id
        )
        if os.path.exists(frontend_lib_source) and os.listdir(frontend_lib_source):
            frontend_lib_target = os.path.join(
                paths["frontend_dir"], "src/lib/extensions", extension_id
            )

            if os.path.exists(frontend_lib_target):
                shutil.rmtree(frontend_lib_target)

            os.makedirs(frontend_lib_target, exist_ok=True)

            shutil.copy2(
                manifest_path, os.path.join(frontend_lib_target, "manifest.json")
            )
            console.print(
                "[blue]Copied manifest.json to frontend extension directory[/blue]"
            )

            for root, _, files in os.walk(frontend_lib_source):
                for file in files:
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, frontend_lib_source)
                    dst_file = os.path.join(frontend_lib_target, rel_path)

                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    console.print(
                        f"[blue]Installed frontend lib file: {rel_path}[/blue]"
                    )

            console.print(
                f"[green]Installed frontend lib files for {extension_id}[/green]"
            )

        # Install routes with flexible structure
        # Copy all routes from frontend/routes/ to src/routes/ preserving structure
        routes_source = os.path.join(temp_dir, "frontend/routes")
        if os.path.exists(routes_source):
            routes_target = os.path.join(paths["frontend_dir"], "src/routes")
            
            for root, _, files in os.walk(routes_source):
                for file in files:
                    src_file = os.path.join(root, file)
                    # Get relative path from routes_source
                    rel_path = os.path.relpath(src_file, routes_source)
                    dst_file = os.path.join(routes_target, rel_path)
                    
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    console.print(
                        f"[blue]Installed frontend route file: {rel_path}[/blue]"
                    )
            
            console.print(
                f"[green]Installed frontend route files for {extension_id}[/green]"
            )

        i18n_source = os.path.join(
            temp_dir, "frontend/i18n/locales/extensions", extension_id
        )
        if os.path.exists(i18n_source) and os.listdir(i18n_source):
            i18n_target = os.path.join(
                paths["frontend_dir"], "src/lib/i18n/locales/extensions", extension_id
            )

            if os.path.exists(i18n_target):
                shutil.rmtree(i18n_target)

            os.makedirs(i18n_target, exist_ok=True)

            for root, _, files in os.walk(i18n_source):
                for file in files:
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, i18n_source)
                    dst_file = os.path.join(i18n_target, rel_path)

                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    console.print(f"[blue]Installed i18n file: {rel_path}[/blue]")

            console.print(f"[green]Installed i18n files for {extension_id}[/green]")

    # Regenerate manifests and registry after installation
    generate_extension_manifests()
    generate_extension_registry()

    console.print(f"[green]Extension {extension_id} installed successfully[/green]")
    return True


def uninstall_extension_command(extension_id: str):
    """Uninstall an extension"""
    try:
        validate_extension_id(extension_id)
    except ValueError as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return False

    locations = find_extension_locations(extension_id)
    paths = get_extension_paths(extension_id)

    if not locations and not any(os.path.exists(path) for path in paths.values()):
        console.print(
            f"[red]Extension {extension_id} not found or already uninstalled[/red]"
        )
        return False

    if "backend" in locations:
        try:
            shutil.rmtree(locations["backend"])
            console.print(f"[green]Removed backend files for {extension_id}[/green]")

            update_extension_imports(extension_id, "remove")
        except Exception as e:
            console.print(f"[red]Failed to remove backend files: {e}[/red]")

    if "frontend_lib" in locations or os.path.exists(paths["frontend_lib"]):
        try:
            if os.path.exists(paths["frontend_lib"]):
                shutil.rmtree(paths["frontend_lib"])
                console.print(
                    f"[green]Removed frontend library files for {extension_id}[/green]"
                )
        except Exception as e:
            console.print(f"[red]Failed to remove frontend library files: {e}[/red]")

    if "frontend_route" in locations or os.path.exists(paths["frontend_route"]):
        try:
            if os.path.exists(paths["frontend_route"]):
                shutil.rmtree(paths["frontend_route"])
                console.print(
                    f"[green]Removed frontend route files for {extension_id}[/green]"
                )
        except Exception as e:
            console.print(f"[red]Failed to remove frontend route files: {e}[/red]")

    if "i18n" in locations or os.path.exists(paths["i18n"]):
        try:
            if os.path.exists(paths["i18n"]):
                shutil.rmtree(paths["i18n"])
                console.print(f"[green]Removed i18n files for {extension_id}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to remove i18n files: {e}[/red]")

    if "frontend_custom_routes" in locations:
        try:
            shutil.rmtree(locations["frontend_custom_routes"])
            console.print(
                f"[green]Removed custom route files for {extension_id}[/green]"
            )
        except Exception as e:
            console.print(f"[red]Failed to remove custom route files: {e}[/red]")

    console.print(f"[green]Extension {extension_id} uninstalled successfully[/green]")
    return True


def uninstall_all_extensions_command():
    """Uninstall all installed extensions"""
    paths = get_project_paths()
    backend_ext_dir = os.path.join(paths["backend_dir"], "extension_packages")
    frontend_ext_dir = os.path.join(paths["frontend_dir"], "src/lib/extensions")

    extensions = set()

    # Find all backend extensions
    if os.path.exists(backend_ext_dir):
        for item in os.listdir(backend_ext_dir):
            if os.path.isdir(
                os.path.join(backend_ext_dir, item)
            ) and not item.startswith("__"):
                try:
                    validate_extension_id(item)
                    extensions.add(item)
                except ValueError:
                    pass

    # Find all frontend extensions
    if os.path.exists(frontend_ext_dir):
        for item in os.listdir(frontend_ext_dir):
            if os.path.isdir(
                os.path.join(frontend_ext_dir, item)
            ) and not item.startswith("__"):
                try:
                    validate_extension_id(item)
                    extensions.add(item)
                except ValueError:
                    pass

    if not extensions:
        console.print("[yellow]No extensions found to uninstall[/yellow]")
        return True

    console.print(f"[blue]Found {len(extensions)} extension(s) to uninstall[/blue]")
    
    success_count = 0
    failed_count = 0
    
    for ext_id in sorted(extensions):
        console.print(f"\n[blue]Uninstalling {ext_id}...[/blue]")
        if uninstall_extension_command(ext_id):
            success_count += 1
        else:
            failed_count += 1

    console.print(
        f"\n[green]Uninstallation complete: {success_count} succeeded, {failed_count} failed[/green]"
    )
    
    # Regenerate manifests and registry after uninstalling all
    if success_count > 0:
        generate_extension_manifests()
        generate_extension_registry()
    
    return failed_count == 0


def generate_extension_registry():
    """Generate registry.py that maps extension functions for the backend"""
    paths = get_project_paths()
    backend_ext_dir = os.path.join(paths["backend_dir"], "extension_packages")
    registry_file = os.path.join(backend_ext_dir, "registry.py")
    
    # Get list of installed extensions
    extensions = []
    if os.path.exists(backend_ext_dir):
        for item in os.listdir(backend_ext_dir):
            ext_path = os.path.join(backend_ext_dir, item)
            if os.path.isdir(ext_path) and not item.startswith("__"):
                entry_file = os.path.join(ext_path, "entry.py")
                if os.path.exists(entry_file):
                    extensions.append(item)
    
    # Generate the registry file
    content = '''"""
Extension Function Registry

This file provides a centralized registry for all extension functions.
It maps extension names and function names to their actual implementations.

Auto-generated by the realms CLI extension command.
DO NOT EDIT MANUALLY - your changes will be overwritten.
"""

from typing import Callable, Optional
from kybra_simple_logging import get_logger

logger = get_logger("extension_packages.registry")

'''
    
    # Import all extension entry modules
    for ext_id in extensions:
        content += f'import extension_packages.{ext_id}.entry as {ext_id}_entry\n'
    
    content += '''

def get_func(extension_name: str, function_name: str) -> Optional[Callable]:
    """
    Get a function from an extension by name.
    
    Args:
        extension_name: The ID of the extension
        function_name: The name of the function to retrieve
        
    Returns:
        The function object if found, None otherwise
    """
    logger.debug(f"Looking up function '{function_name}' in extension '{extension_name}'")
    
    # Map extension names to their entry modules
    extension_modules = {
'''
    
    for ext_id in extensions:
        content += f'        "{ext_id}": {ext_id}_entry,\n'
    
    content += '''    }
    
    # Get the extension module
    module = extension_modules.get(extension_name)
    if not module:
        logger.error(f"Extension '{extension_name}' not found in registry")
        raise ValueError(f"Extension '{extension_name}' not found")
    
    # Get the function from the module
    if not hasattr(module, function_name):
        logger.error(f"Function '{function_name}' not found in extension '{extension_name}'")
        raise AttributeError(f"Extension '{extension_name}' has no function '{function_name}'")
    
    func = getattr(module, function_name)
    logger.debug(f"Found function '{function_name}' in extension '{extension_name}'")
    return func
'''
    
    # Write the file
    os.makedirs(backend_ext_dir, exist_ok=True)
    with open(registry_file, "w") as f:
        f.write(content)
    
    console.print(f"[green]Generated registry.py with {len(extensions)} extensions[/green]")
    return True


def generate_extension_manifests():
    """Generate extension_manifests.py file from installed extension manifests"""
    paths = get_project_paths()
    backend_ext_dir = os.path.join(paths["backend_dir"], "extension_packages")
    manifests_file = os.path.join(backend_ext_dir, "extension_manifests.py")
    
    manifests = {}
    
    # Scan for installed extensions with manifests
    if os.path.exists(backend_ext_dir):
        for item in os.listdir(backend_ext_dir):
            ext_path = os.path.join(backend_ext_dir, item)
            if os.path.isdir(ext_path) and not item.startswith("__"):
                manifest_path = os.path.join(ext_path, "manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r") as f:
                            manifest_data = json.load(f)
                            manifests[item] = manifest_data
                    except Exception as e:
                        console.print(f"[yellow]Warning: Could not load manifest for {item}: {e}[/yellow]")
    
    # Generate the Python file
    content = '''"""
Static extension manifest registry for Kybra canister environment.
This file contains all extension manifests as Python dictionaries since
Kybra canisters don't have filesystem access.

This file is auto-generated by the realms CLI extension command.
DO NOT EDIT MANUALLY - your changes will be overwritten.
"""

# Extension manifests embedded as Python dictionaries
EXTENSION_MANIFESTS = {
'''
    
    for ext_id, manifest in manifests.items():
        # Use pformat for readable formatting, then indent properly
        formatted = pformat(manifest, width=100, compact=False)
        # Add proper indentation (4 spaces for extension level)
        indented = '\n'.join('    ' + line for line in formatted.split('\n'))
        content += f'    "{ext_id}": {indented},\n\n'
    
    content += '''}\n\n
def get_all_extension_manifests() -> dict:
    """Get all extension manifests"""
    return EXTENSION_MANIFESTS
'''
    
    # Write the file
    os.makedirs(backend_ext_dir, exist_ok=True)
    with open(manifests_file, "w") as f:
        f.write(content)
    
    console.print(f"[green]Generated extension_manifests.py with {len(manifests)} extensions[/green]")
    return True


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
            project_paths = get_project_paths()

            # Copy backend files if they exist
            backend_source = os.path.join(source_path, "backend")
            if os.path.exists(backend_source):
                # Ensure extension_packages directory exists and has __init__.py
                extension_packages_dir = os.path.join(project_paths["backend_dir"], "extension_packages")
                os.makedirs(extension_packages_dir, exist_ok=True)
                extension_packages_init = os.path.join(extension_packages_dir, "__init__.py")
                if not os.path.exists(extension_packages_init):
                    with open(extension_packages_init, "w") as f:
                        f.write('"""Extension packages directory."""\n')
                
                os.makedirs(paths["backend"], exist_ok=True)
                shutil.copytree(backend_source, paths["backend"], dirs_exist_ok=True)
                console.print("  [green]✓[/green] Backend files copied")
                update_extension_imports(ext_id, "add")
                console.print("  [green]✓[/green] Extension imports updated")
            
            # Copy root-level manifest.json to backend directory (always overwrite to get updates)
            root_manifest = os.path.join(source_path, "manifest.json")
            if os.path.exists(root_manifest):
                # Create backend dir if it doesn't exist (for frontend-only extensions)
                os.makedirs(paths["backend"], exist_ok=True)
                backend_manifest = os.path.join(paths["backend"], "manifest.json")
                shutil.copy2(root_manifest, backend_manifest)  # Always copy to get updates
                console.print("  [green]✓[/green] Manifest copied to backend")

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

                # Copy ALL routes preserving directory structure
                # This allows extensions to define routes at any location:
                # - frontend/routes/(sidebar)/admin/ → src/routes/(sidebar)/admin/
                # - frontend/routes/(sidebar)/extensions/{ext_id}/ → src/routes/(sidebar)/extensions/{ext_id}/
                # - frontend/routes/{ext_id}/ → src/routes/{ext_id}/
                # - Any other structure the extension needs
                routes_source = os.path.join(frontend_source, "routes")
                if os.path.exists(routes_source):
                    routes_target = os.path.join(
                        project_paths["frontend_dir"],
                        "src/routes"
                    )
                    # Walk through the routes directory and copy all files preserving structure
                    for root, dirs, files in os.walk(routes_source):
                        # Calculate relative path from routes_source
                        rel_path = os.path.relpath(root, routes_source)
                        
                        # Determine target directory
                        if rel_path == ".":
                            target_dir = routes_target
                        else:
                            target_dir = os.path.join(routes_target, rel_path)
                        
                        # Create target directory
                        os.makedirs(target_dir, exist_ok=True)
                        
                        # Copy all files in this directory
                        for file in files:
                            src_file = os.path.join(root, file)
                            dst_file = os.path.join(target_dir, file)
                            shutil.copy2(src_file, dst_file)
                    
                    console.print("  [green]✓[/green] Frontend route files copied")

                # Copy static files if they exist (e.g., photos, videos)
                static_source = os.path.join(frontend_source, "static")
                if os.path.exists(static_source):
                    static_target = os.path.join(
                        project_paths["frontend_dir"],
                        "static",
                        "extensions",
                        ext_id
                    )
                    os.makedirs(static_target, exist_ok=True)
                    shutil.copytree(
                        static_source, static_target, dirs_exist_ok=True
                    )
                    console.print("  [green]✓[/green] Static files copied")

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
    
    # Generate extension_manifests.py and registry.py files
    generate_extension_manifests()
    generate_extension_registry()
    
    return success_count == len(extension_dirs)


def extension_command(
    action: str = typer.Argument(
        ...,
        help="Action to perform: list, install-from-source, package, install, uninstall, generate-manifests",
    ),
    extension_id: Optional[str] = typer.Option(
        None, "--extension-id", help="Extension ID for package/uninstall operations"
    ),
    package_path: Optional[str] = typer.Option(
        None, "--package-path", help="Path for package file (full output path for package action, or package file to install for install action)"
    ),
    source_dir: str = typer.Option(
        "extensions", "--source-dir", help="Source directory for extensions"
    ),
    all_extensions: bool = typer.Option(
        False, "--all", help="Uninstall all extensions (only for uninstall action)"
    ),
) -> None:
    """Manage Realm extensions."""

    if action == "list":
        list_extensions_command()
    elif action == "install-from-source":
        install_from_source_command(source_dir)
    elif action == "generate-manifests":
        generate_extension_manifests()
        generate_extension_registry()
    elif action == "package":
        if not extension_id:
            console.print(
                "[red]Error: --extension-id is required for package action[/red]"
            )
            raise typer.Exit(1)
        package_extension_command(extension_id, output_path=package_path, source_dir=source_dir)
    elif action == "install":
        if not package_path:
            console.print(
                "[red]Error: --package-path is required for install action[/red]"
            )
            raise typer.Exit(1)
        install_extension_command(package_path)
    elif action == "uninstall":
        if all_extensions:
            uninstall_all_extensions_command()
        elif extension_id:
            uninstall_extension_command(extension_id)
        else:
            console.print(
                "[red]Error: Either --extension-id or --all is required for uninstall action[/red]"
            )
            raise typer.Exit(1)
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print(
            "[yellow]Available actions: list, install-from-source, generate-manifests, package, install, uninstall[/yellow]"
        )
        raise typer.Exit(1)
