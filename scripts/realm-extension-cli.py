#!/usr/bin/env python3
"""
Realm Extension CLI - A simple tool for managing extensions in the Smart Social Contracts platform.

Usage:
  python realm-extension-cli.py list                        # List all installed extensions
  python realm-extension-cli.py package EXTENSION_ID        # Package a specific extension
  python realm-extension-cli.py package --all               # Package all extensions
  python realm-extension-cli.py install PACKAGE_PATH        # Install an extension from package
  python realm-extension-cli.py install --all               # Install all .zip packages in current dir
  python realm-extension-cli.py uninstall EXTENSION_ID      # Uninstall a specific extension
  python realm-extension-cli.py uninstall --all             # Uninstall all extensions

- `manifest.json` format:
{
    "name": "<extension_name>",
    "version": "x.y.z",
    "description": "<extension_description>",
    "author": "<author>",
    "permissions": [
        "<permission_1>",
        "<permission_2>"
    ]
}


- Files in the repo:
src/realm_backend/extensions/<extension_name>/manifest.json
src/realm_backend/extensions/<extension_name>/*.py
src/realm_frontend/src/lib/extensions/<extension_name>/index.ts
src/realm_frontend/src/lib/extensions/<extension_name>/*.svelte
src/realm_frontend/src/routes/(sidebar)/extensions/+page.svelte
src/realm_frontend/src/routes/(sidebar)/extensions/<extension_name>/+page-svelte

- Files in the zip:
manifest.json
backend/*.py
frontend/lib/extensions/<extension_name>/index.ts
frontend/lib/extensions/<extension_name>/*.svelte
frontend/routes/(sidebar)/extensions/+page.svelte
frontend/routes/(sidebar)/extensions/<extension_name>/+page.svelte
"""


import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

# ANSI colors for better CLI output
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

def log_info(message): print(f"{Colors.BLUE}[INFO]{Colors.RESET} {message}")
def log_success(message): print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {message}")
def log_warning(message): print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {message}")
def log_error(message): print(f"{Colors.RED}[ERROR]{Colors.RESET} {message}")

def validate_extension_id(extension_id):
    """Validate extension ID (no hyphens allowed)"""
    if "-" in extension_id:
        raise ValueError(f"Extension ID '{extension_id}' contains hyphens. Only underscores are allowed.")
    return True

def get_project_paths():
    """Get standard project paths for extension management"""
    project_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    return {
        "project_root": project_root,
        "backend_dir": os.path.join(project_root, "src/realm_backend"),
        "frontend_dir": os.path.join(project_root, "src/realm_frontend")
    }

def get_extension_paths(extension_id):
    """Get all paths for an extension"""
    validate_extension_id(extension_id)
    paths = get_project_paths()
    
    if not paths:
        return None
    
    return {
        "backend": os.path.join(paths["backend_dir"], "extension_packages", extension_id),
        "frontend_lib": os.path.join(paths["frontend_dir"], "src/lib/extensions", extension_id),
        "frontend_route": os.path.join(paths["frontend_dir"], "src/routes/(sidebar)/extensions", extension_id),
        "i18n": os.path.join(paths["frontend_dir"], "src/lib/i18n/locales/extensions", extension_id),
        "frontend_custom_routes": os.path.join(paths["frontend_dir"], "src/routes"),
        "frontend_static": os.path.join(paths["frontend_dir"], "static")
    }

def find_extension_locations(extension_id):
    """Find where an extension is located"""
    paths = get_extension_paths(extension_id)
    
    if not paths:
        return {}
    
    locations = {}
    
    # Check backend location
    if os.path.exists(paths["backend"]) and os.listdir(paths["backend"]):
        locations["backend"] = paths["backend"]
    
    # Check frontend lib location
    if os.path.exists(paths["frontend_lib"]) and os.listdir(paths["frontend_lib"]):
        locations["frontend_lib"] = paths["frontend_lib"]
    
    # Check frontend route location
    if os.path.exists(paths["frontend_route"]) and os.listdir(paths["frontend_route"]):
        locations["frontend_route"] = paths["frontend_route"]
    
    # Check extension i18n location
    if os.path.exists(paths["i18n"]) and os.listdir(paths["i18n"]):
        locations["i18n"] = paths["i18n"]
    
    # Check for custom routes
    custom_route_path = os.path.join(paths["frontend_custom_routes"], extension_id)
    if os.path.exists(custom_route_path) and os.listdir(custom_route_path):
        locations["frontend_custom_routes"] = custom_route_path
    
    project_paths = get_project_paths()
    locations["frontend_static"] = os.path.join(project_paths["frontend_dir"], "static")
    
    return locations

def get_extension_manifest(extension_id):
    """Get extension manifest"""
    validate_extension_id(extension_id)
    locations = find_extension_locations(extension_id)
    
    if "backend" in locations:
        manifest_path = os.path.join(locations["backend"], "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                return json.load(f)
    
    return None

def package_extension(extension_id, output_dir=None):
    """Package an extension into a zip file"""
    validate_extension_id(extension_id)
    locations = find_extension_locations(extension_id)
    
    paths = get_project_paths()
    if not output_dir:
        output_dir = paths["project_root"]
    
    zip_filename = f"{extension_id}.zip"
    zip_path = os.path.join(output_dir, zip_filename)
    
    log_info(f"Packaging extension {extension_id}")
    
    # Ensure custom routes are properly detected
    custom_route_path = os.path.join(paths["frontend_dir"], "src/routes", extension_id)
    if os.path.exists(custom_route_path):
        locations["frontend_custom_routes"] = paths["frontend_dir"]
        log_info(f"Detected custom route: {custom_route_path}")
    
    # Check if we found any extension components
    if not locations:
        log_error(f"Extension '{extension_id}' not found or has no components")
        return False
    
    # Check for manifest
    manifest = None
    manifest_path = None
    if "backend" in locations:
        manifest_path = os.path.join(locations["backend"], "manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
            except Exception as e:
                log_error(f"Failed to load manifest: {e}")
                return False
    
    # If no manifest found, create a basic one
    if not manifest:
        manifest = {
            "name": extension_id,
            "version": "1.0.0",
            "description": f"{extension_id} extension",
            "author": "Smart Social Contracts",
            "permissions": []
        }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add manifest
            if manifest_path and os.path.exists(manifest_path):
                zipf.write(manifest_path, "manifest.json")
                log_info(f"Added manifest.json")
            else:
                # Create temporary manifest file
                temp_manifest_path = os.path.join(temp_dir, "manifest.json")
                with open(temp_manifest_path, 'w') as f:
                    json.dump(manifest, f, indent=2)
                zipf.write(temp_manifest_path, "manifest.json")
                log_info(f"Added generated manifest.json")
            
            # Package backend files
            if "backend" in locations:
                backend_src = locations["backend"]
                for root, _, files in os.walk(backend_src):
                    for file in files:
                        if file.endswith('.py') or file == "manifest.json":
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, backend_src)
                            zipf.write(file_path, os.path.join("backend", rel_path))
                            log_info(f"Added backend/{rel_path}")
            
            # Package frontend lib files
            if "frontend_lib" in locations:
                frontend_lib_src = locations["frontend_lib"]
                for root, _, files in os.walk(frontend_lib_src):
                    for file in files:
                        if file.endswith(('.svelte', '.ts', '.js')):
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, frontend_lib_src)
                            zipf.write(file_path, os.path.join("frontend/lib/extensions", extension_id, rel_path))
                            log_info(f"Added frontend/lib/extensions/{extension_id}/{rel_path}")
            
            # Package i18n translation files
            if "i18n" in locations:
                i18n_src = locations["i18n"]
                for root, _, files in os.walk(i18n_src):
                    for file in files:
                        if file.endswith(('.json')):
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, i18n_src)
                            zipf.write(file_path, os.path.join("frontend/i18n/locales/extensions", extension_id, rel_path))
                            log_info(f"Added frontend/i18n/locales/extensions/{extension_id}/{rel_path}")
            
            # Package frontend route files
            if "frontend_route" in locations:
                frontend_route_src = locations["frontend_route"]
                for root, _, files in os.walk(frontend_route_src):
                    for file in files:
                        if file.endswith(('.svelte', '.ts', '.js')):
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, frontend_route_src)
                            zipf.write(file_path, os.path.join("frontend/routes/(sidebar)/extensions", extension_id, rel_path))
                            log_info(f"Added frontend/routes/(sidebar)/extensions/{extension_id}/{rel_path}")
            
            # Package custom route files
            if "frontend_custom_routes" in locations:
                custom_route_src = os.path.join(paths["frontend_dir"], "src/routes", extension_id)
                if os.path.exists(custom_route_src):
                    for root, _, files in os.walk(custom_route_src):
                        for file in files:
                            if file.endswith(('.svelte', '.ts', '.js')):
                                file_path = os.path.join(root, file)
                                rel_path = os.path.relpath(file_path, custom_route_src)
                                zipf.write(file_path, os.path.join(f"frontend/routes/{extension_id}", rel_path))
                                log_info(f"Added frontend/routes/{extension_id}/{rel_path}")
            
            # Package static assets related to this extension
            static_path = os.path.join(paths["frontend_dir"], "static")
            
            # Define the media types to include
            media_extensions = {
                "videos": ['.mp4', '.webm', '.ogg'],
                "images": ['.png', '.jpg', '.jpeg', '.gif', '.svg'],
                "fonts": ['.ttf', '.woff', '.woff2']
            }
            
            # For video files, include all videos since there's no easy way to determine which ones are used by the extension
            videos_path = os.path.join(static_path, "videos")
            if os.path.exists(videos_path):
                for file in os.listdir(videos_path):
                    if any(file.endswith(ext) for ext in media_extensions["videos"]):
                        file_path = os.path.join(videos_path, file)
                        zipf.write(file_path, os.path.join("frontend/static/videos", file))
                        log_info(f"Added frontend/static/videos/{file}")
            
            # For other media files, try to be smarter about which ones to include
            for static_dir in ["images", "fonts", extension_id]:
                static_dir_path = os.path.join(static_path, static_dir)
                if not os.path.exists(static_dir_path):
                    continue
                
                # Get the list of allowed extensions for this directory type
                allowed_extensions = []
                if static_dir == "images":
                    allowed_extensions = media_extensions["images"]
                elif static_dir == "fonts":
                    allowed_extensions = media_extensions["fonts"]
                else:
                    # For extension-specific folders, include all media types
                    for exts in media_extensions.values():
                        allowed_extensions.extend(exts)
                
                # Walk through directory and include matching files
                for root, _, files in os.walk(static_dir_path):
                    for file in files:
                        # Check if the file has the right extension
                        if any(file.endswith(ext) for ext in allowed_extensions):
                            # If it's an extension-specific folder, include everything
                            # Otherwise only include files that are likely related to this extension
                            if static_dir == extension_id or extension_id in file.lower():
                                file_path = os.path.join(root, file)
                                rel_path = os.path.relpath(file_path, static_dir_path)
                                zipf.write(file_path, os.path.join(f"frontend/static/{static_dir}", rel_path))
                                log_info(f"Added frontend/static/{static_dir}/{rel_path}")
    
    log_success(f"Extension packaged successfully: {zip_path}")
    return True

def install_extension(package_path):
    """Install an extension from a package"""
    paths = get_project_paths()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(package_path, 'r') as zipf:
            zipf.extractall(temp_dir)
        log_info(f"Extracted package to temporary directory")
        
        manifest_path = os.path.join(temp_dir, "manifest.json")
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        extension_id = manifest.get("name", "")
        if not extension_id:
            log_error("No extension ID found in manifest")
            return False
        
        try:
            validate_extension_id(extension_id)
        except ValueError as e:
            log_error(str(e))
            return False
        
        backend_source = os.path.join(temp_dir, "backend")
        if os.path.exists(backend_source) and os.listdir(backend_source):
            backend_target = os.path.join(paths["backend_dir"], "extension_packages", extension_id)
            
            if os.path.exists(backend_target):
                shutil.rmtree(backend_target)
            
            os.makedirs(backend_target, exist_ok=True)
            
            shutil.copy2(manifest_path, os.path.join(backend_target, "manifest.json"))
            
            for root, _, files in os.walk(backend_source):
                for file in files:
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, backend_source)
                    dst_file = os.path.join(backend_target, rel_path)
                    
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    log_info(f"Installed backend file: {rel_path}")
            
            init_file = os.path.join(backend_target, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, 'w') as f:
                    f.write(f'"""\n{extension_id} extension package.\n"""\n')
                log_info(f"Created __init__.py file for {extension_id}")
            
            update_extension_imports(extension_id, "add")
            
            log_success(f"Installed backend files for {extension_id}")
        
        frontend_lib_source = os.path.join(temp_dir, "frontend/lib/extensions", extension_id)
        if os.path.exists(frontend_lib_source) and os.listdir(frontend_lib_source):
            frontend_lib_target = os.path.join(paths["frontend_dir"], "src/lib/extensions", extension_id)
            
            if os.path.exists(frontend_lib_target):
                shutil.rmtree(frontend_lib_target)
            
            os.makedirs(frontend_lib_target, exist_ok=True)
            
            for root, _, files in os.walk(frontend_lib_source):
                for file in files:
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, frontend_lib_source)
                    dst_file = os.path.join(frontend_lib_target, rel_path)
                    
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    log_info(f"Installed frontend lib file: {rel_path}")
            
            log_success(f"Installed frontend lib files for {extension_id}")
        else:
            log_info("No frontend lib files found in package")
        
        frontend_route_source = os.path.join(temp_dir, "frontend/routes/(sidebar)/extensions", extension_id)
        if os.path.exists(frontend_route_source) and os.listdir(frontend_route_source):
            frontend_route_target = os.path.join(paths["frontend_dir"], "src/routes/(sidebar)/extensions", extension_id)
            
            if os.path.exists(frontend_route_target):
                shutil.rmtree(frontend_route_target)
            
            os.makedirs(frontend_route_target, exist_ok=True)
            
            for root, _, files in os.walk(frontend_route_source):
                for file in files:
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, frontend_route_source)
                    dst_file = os.path.join(frontend_route_target, rel_path)
                    
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    log_info(f"Installed frontend route file: {rel_path}")
            
            log_success(f"Installed frontend route files for {extension_id}")
        else:
            log_info("No frontend route files found in package")
        
        # Install i18n translation files
        i18n_source = os.path.join(temp_dir, f"frontend/i18n/locales/extensions/{extension_id}")
        if os.path.exists(i18n_source) and os.listdir(i18n_source):
            i18n_target = os.path.join(paths["frontend_dir"], f"src/lib/i18n/locales/extensions/{extension_id}")
            
            if os.path.exists(i18n_target):
                shutil.rmtree(i18n_target)
            
            os.makedirs(i18n_target, exist_ok=True)
            
            for root, _, files in os.walk(i18n_source):
                for file in files:
                    if file.endswith('.json'):
                        src_file = os.path.join(root, file)
                        rel_path = os.path.relpath(src_file, i18n_source)
                        dst_file = os.path.join(i18n_target, rel_path)
                        
                        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                        log_info(f"Installed i18n translation file: {rel_path}")
            
            log_success(f"Installed i18n translation files for {extension_id}")
        else:
            log_info("No i18n translation files found in package")
            
        custom_route_source = os.path.join(temp_dir, f"frontend/routes/{extension_id}")
        if os.path.exists(custom_route_source) and os.listdir(custom_route_source):
            custom_route_target = os.path.join(paths["frontend_dir"], f"src/routes/{extension_id}")
            
            if os.path.exists(custom_route_target):
                shutil.rmtree(custom_route_target)
            
            os.makedirs(custom_route_target, exist_ok=True)
            
            for root, _, files in os.walk(custom_route_source):
                for file in files:
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, custom_route_source)
                    dst_file = os.path.join(custom_route_target, rel_path)
                    
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    log_info(f"Installed custom route file: {rel_path}")
            
            log_success(f"Installed custom route files for {extension_id}")
        else:
            log_info("No custom route files found in package")
            
        for static_dir in ["videos", "images", "fonts", extension_id]:
            static_source = os.path.join(temp_dir, f"frontend/static/{static_dir}")
            if os.path.exists(static_source) and os.listdir(static_source):
                static_target = os.path.join(paths["frontend_dir"], f"static/{static_dir}")
                
                os.makedirs(static_target, exist_ok=True)
                
                for root, _, files in os.walk(static_source):
                    for file in files:
                        src_file = os.path.join(root, file)
                        rel_path = os.path.relpath(src_file, static_source)
                        dst_file = os.path.join(static_target, rel_path)
                        
                        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                        log_info(f"Installed static asset: {static_dir}/{rel_path}")
                
                log_success(f"Installed static assets for {static_dir}")
    
    log_success(f"Extension {extension_id} installed successfully")
    return True

def uninstall_extension(extension_id):
    """Uninstall an extension"""
    try:
        validate_extension_id(extension_id)
    except ValueError as e:
        log_error(str(e))
        return False
    
    locations = find_extension_locations(extension_id)
    
    if not locations:
        log_error(f"Extension {extension_id} not found or already uninstalled")
        return False
    
    if "backend" in locations:
        try:
            shutil.rmtree(locations["backend"])
            log_success(f"Removed backend files for {extension_id}")
            
            update_extension_imports(extension_id, "remove")
        except Exception as e:
            log_error(f"Failed to remove backend files: {e}")
    
    if "frontend_lib" in locations:
        try:
            shutil.rmtree(locations["frontend_lib"])
            log_success(f"Removed frontend library files for {extension_id}")
        except Exception as e:
            log_error(f"Failed to remove frontend library files: {e}")
    
    if "frontend_route" in locations:
        try:
            shutil.rmtree(locations["frontend_route"])
            log_success(f"Removed frontend route files for {extension_id}")
        except Exception as e:
            log_error(f"Failed to remove frontend route files: {e}")
    
    if "frontend_custom_routes" in locations:
        try:
            shutil.rmtree(locations["frontend_custom_routes"])
            log_success(f"Removed custom route files for {extension_id}")
        except Exception as e:
            log_error(f"Failed to remove custom route files: {e}")
    
    log_success(f"Extension {extension_id} uninstalled successfully")
    return True

def update_extension_imports(extension_id, action="add"):
    """Update the extension_imports.py file"""
    paths = get_project_paths()
    imports_file = os.path.join(paths["backend_dir"], "extension_packages", "extension_imports.py")
    
    if not os.path.exists(imports_file):
        log_error(f"Extension imports file not found: {imports_file}")
        return False
    
    with open(imports_file, "r") as f:
        content = f.read()
    
    import_line = f"import extension_packages.{extension_id}.entry"
    
    if action == "add":
        if import_line in content:
            log_info(f"Import for {extension_id} already exists in extension_imports.py")
            return True
        
        if content and not content.endswith('\n'):
            import_line = '\n' + import_line
        
        if content:
            import_line += '\n'
        
        with open(imports_file, "a") as f:
            f.write(import_line)
        log_success(f"Added import for {extension_id} to extension_imports.py")
    
    elif action == "remove":
        if import_line not in content:
            log_info(f"No import for {extension_id} found in extension_imports.py")
            return True
        
        lines = content.splitlines()
        new_lines = [line for line in lines if line.strip() != import_line]
        new_content = '\n'.join(new_lines)
        
        if new_content and not new_content.endswith('\n'):
            new_content += '\n'
        
        with open(imports_file, "w") as f:
            f.write(new_content)
        log_success(f"Removed import for {extension_id} from extension_imports.py")
    
    return True

def package_all_extensions(output_dir=None):
    """Package all extensions into zip files"""
    log_info("Packaging all extensions")
    paths = get_project_paths()
    backend_ext_dir = os.path.join(paths["backend_dir"], "extension_packages")
    frontend_ext_dir = os.path.join(paths["frontend_dir"], "src/lib/extensions")
    
    # Collect all unique extension IDs
    all_extensions = set()
    if os.path.exists(backend_ext_dir):
        for item in os.listdir(backend_ext_dir):
            if os.path.isdir(os.path.join(backend_ext_dir, item)) and not item.startswith('__'):
                try:
                    validate_extension_id(item)
                    all_extensions.add(item)
                except ValueError:
                    log_warning(f"Skipping extension with invalid ID: {item}")
    
    if os.path.exists(frontend_ext_dir):
        for item in os.listdir(frontend_ext_dir):
            if os.path.isdir(os.path.join(frontend_ext_dir, item)) and not item.startswith('__'):
                try:
                    validate_extension_id(item)
                    all_extensions.add(item)
                except ValueError:
                    log_warning(f"Skipping extension with invalid ID: {item}")
    
    if not all_extensions:
        log_error("No extensions found to package")
        return False
    
    success = True
    for ext_id in all_extensions:
        log_info(f"Packaging extension: {ext_id}")
        if not package_extension(ext_id, output_dir):
            success = False
            log_error(f"Failed to package extension: {ext_id}")
    
    return success

def install_all_packages():
    """Install all extension packages in the current directory"""
    log_info("Installing all extension packages in the current directory")
    current_dir = os.getcwd()
    success = True
    packages_found = False
    
    for item in os.listdir(current_dir):
        if item.endswith('.zip'):
            packages_found = True
            log_info(f"Found package: {item}")
            if not install_extension(os.path.join(current_dir, item)):
                success = False
                log_error(f"Failed to install package: {item}")
    
    if not packages_found:
        log_error("No extension packages (.zip files) found in the current directory")
        return False
    
    return success

def uninstall_all_extensions():
    """Uninstall all extensions"""
    log_info("Uninstalling all extensions")
    paths = get_project_paths()
    backend_ext_dir = os.path.join(paths["backend_dir"], "extension_packages")
    frontend_ext_dir = os.path.join(paths["frontend_dir"], "src/lib/extensions")
    
    # Collect all unique extension IDs
    all_extensions = set()
    if os.path.exists(backend_ext_dir):
        for item in os.listdir(backend_ext_dir):
            if os.path.isdir(os.path.join(backend_ext_dir, item)) and not item.startswith('__'):
                try:
                    validate_extension_id(item)
                    all_extensions.add(item)
                except ValueError:
                    log_warning(f"Skipping extension with invalid ID: {item}")
    
    if os.path.exists(frontend_ext_dir):
        for item in os.listdir(frontend_ext_dir):
            if os.path.isdir(os.path.join(frontend_ext_dir, item)) and not item.startswith('__'):
                try:
                    validate_extension_id(item)
                    all_extensions.add(item)
                except ValueError:
                    log_warning(f"Skipping extension with invalid ID: {item}")
    
    if not all_extensions:
        log_error("No extensions found to uninstall")
        return False
    
    success = True
    for ext_id in all_extensions:
        log_info(f"Uninstalling extension: {ext_id}")
        if not uninstall_extension(ext_id):
            success = False
            log_error(f"Failed to uninstall extension: {ext_id}")
    
    return success

def list_extensions():
    """List all installed extensions"""
    paths = get_project_paths()
    backend_ext_dir = os.path.join(paths["backend_dir"], "extension_packages")
    frontend_ext_dir = os.path.join(paths["frontend_dir"], "src/lib/extensions")
    
    extensions = {}
    
    if os.path.exists(backend_ext_dir):
        for item in os.listdir(backend_ext_dir):
            if os.path.isdir(os.path.join(backend_ext_dir, item)) and not item.startswith('__'):
                try:
                    validate_extension_id(item)
                    manifest_path = os.path.join(backend_ext_dir, item, "manifest.json")
                    
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, 'r') as f:
                                manifest = json.load(f)
                            extensions[item] = {
                                'id': item,
                                'version': manifest.get('version', 'unknown'),
                                'description': manifest.get('description', ''),
                                'has_backend': True,
                                'has_frontend': False
                            }
                        except Exception:
                            extensions[item] = {
                                'id': item, 
                                'version': 'unknown',
                                'description': '',
                                'has_backend': True,
                                'has_frontend': False
                            }
                except ValueError:
                    log_warning(f"Skipping extension with invalid ID: {item}")
    
    if os.path.exists(frontend_ext_dir):
        for item in os.listdir(frontend_ext_dir):
            if os.path.isdir(os.path.join(frontend_ext_dir, item)) and not item.startswith('__'):
                try:
                    validate_extension_id(item)
                    
                    if item in extensions:
                        extensions[item]['has_frontend'] = True
                    else:
                        manifest_path = os.path.join(frontend_ext_dir, item, "manifest.json")
                        if os.path.exists(manifest_path):
                            try:
                                with open(manifest_path, 'r') as f:
                                    manifest = json.load(f)
                                extensions[item] = {
                                    'id': item,
                                    'version': manifest.get('version', 'unknown'),
                                    'description': manifest.get('description', ''),
                                    'has_backend': False,
                                    'has_frontend': True
                                }
                            except Exception:
                                extensions[item] = {
                                    'id': item,
                                    'version': 'unknown',
                                    'description': '',
                                    'has_backend': False,
                                    'has_frontend': True
                                }
                except ValueError:
                    log_warning(f"Skipping extension with invalid ID: {item}")
    
    if not extensions:
        log_info("No extensions installed")
        return []
    
    print("{:<20} {:<15} {:<15}".format("ID", "VERSION", "COMPONENTS"))
    print("{:<20} {:<15} {:<15}".format("-" * 20, "-" * 15, "-" * 15))
    for ext_id, ext in extensions.items():
        components = []
        if ext['has_backend']:
            components.append('backend')
        if ext['has_frontend']:
            components.append('frontend')
        print("{:<20} {:<15} {:<15}".format(
            ext_id,
            ext['version'],
            ", ".join(components)
        ))
    
    return list(extensions.values())

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Realm Extension CLI - Manage extensions for the Smart Social Contracts platform"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    list_parser = subparsers.add_parser("list", help="List installed extensions")
    
    package_parser = subparsers.add_parser("package", help="Package an extension into a zip file")
    package_group = package_parser.add_mutually_exclusive_group(required=True)
    package_group.add_argument("--extension-id", dest="extension_id", help="ID of the extension to package")
    package_group.add_argument("--all", action="store_true", help="Package all extensions")
    package_parser.add_argument("--output-dir", help="Directory to save the package", default=None)
    
    install_parser = subparsers.add_parser("install", help="Install an extension package")
    install_group = install_parser.add_mutually_exclusive_group(required=True)
    install_group.add_argument("--package-path", dest="package_path", help="Path to the extension package (.zip)")
    install_group.add_argument("--all", action="store_true", help="Install all packages in the current directory")
    
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall an extension")
    uninstall_group = uninstall_parser.add_mutually_exclusive_group(required=True)
    uninstall_group.add_argument("--extension-id", dest="extension_id", help="ID of the extension to uninstall")
    uninstall_group.add_argument("--all", action="store_true", help="Uninstall all extensions")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == "list":
        list_extensions()
    elif args.command == "package":
        if args.all:
            if not package_all_extensions(args.output_dir):
                return 1
        else:
            if not package_extension(args.extension_id, args.output_dir):
                return 1
    elif args.command == "install":
        if args.all:
            if not install_all_packages():
                return 1
        else:
            if not install_extension(args.package_path):
                return 1
    elif args.command == "uninstall":
        if args.all:
            if not uninstall_all_extensions():
                return 1
        else:
            if not uninstall_extension(args.extension_id):
                return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())