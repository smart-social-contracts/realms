#!/usr/bin/env python3
"""
Realm Extension CLI - A simple tool for managing extensions in the Smart Social Contracts platform.
"""



'''

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


- In the repo:
src/realm_backend/extensions/<extension_name>/manifest.json
src/realm_backend/extensions/<extension_name>/*.py
src/realm_frontend/src/lib/extensions/<extension_name>/index.ts
src/realm_frontend/src/lib/extensions/<extension_name>/*.svelte
src/realm_frontend/src/routes/(sidebar)/extensions/+page.svelte
src/realm_frontend/src/routes/(sidebar)/extensions/<extension_name>/+page-svelte

- In the zip:
manifest.json
backend/*.py
frontend/lib/extensions/<extension_name>/index.ts
frontend/lib/extensions/<extension_name>/*.svelte
frontend/routes/(sidebar)/extensions/+page.svelte
frontend/routes/(sidebar)/extensions/<extension_name>/+page.svelte

'''

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

def get_project_paths():
    """Get standard project paths for extension management"""
    project_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    return {
        "project_root": project_root,
        "backend_dir": os.path.join(project_root, "src/realm_backend"),
        "frontend_dir": os.path.join(project_root, "src/realm_frontend")
    }

def normalize_extension_id(extension_id):
    """Normalize extension ID for consistent handling"""
    return extension_id.lower().replace('_', '-').replace(' ', '-')

def get_extension_paths(extension_id):
    """Get all paths for an extension"""
    paths = get_project_paths()
    normalized_id = normalize_extension_id(extension_id)
    backend_id = normalized_id.replace('-', '_')
    
    return {
        "backend": os.path.join(paths["backend_dir"], "extensions", backend_id),
        "frontend_lib": os.path.join(paths["frontend_dir"], "src/lib/extensions", normalized_id),
        "frontend_route": os.path.join(paths["frontend_dir"], "src/routes/(sidebar)/extensions", normalized_id)
    }

def find_extension_locations(extension_id):
    """Find where an extension is located"""
    paths = get_project_paths()
    locations = {}
    
    # Handle both kebab-case and snake_case for extensions
    normalized_id = normalize_extension_id(extension_id)
    snake_id = normalized_id.replace('-', '_')
    
    # Check backend (always uses snake_case)
    backend_path = os.path.join(paths["backend_dir"], "extensions", snake_id)
    if os.path.isdir(backend_path): 
        locations["backend"] = backend_path
    
    # Check frontend lib paths (could be either format)
    frontend_lib_kebab = os.path.join(paths["frontend_dir"], "src/lib/extensions", normalized_id)
    frontend_lib_snake = os.path.join(paths["frontend_dir"], "src/lib/extensions", snake_id)
    
    if os.path.isdir(frontend_lib_kebab):
        locations["frontend_lib"] = frontend_lib_kebab
    elif os.path.isdir(frontend_lib_snake):
        locations["frontend_lib"] = frontend_lib_snake
    
    # Check frontend route paths (could be either format)
    frontend_route_kebab = os.path.join(paths["frontend_dir"], "src/routes/(sidebar)/extensions", normalized_id)
    frontend_route_snake = os.path.join(paths["frontend_dir"], "src/routes/(sidebar)/extensions", snake_id)
    
    if os.path.isdir(frontend_route_kebab):
        locations["frontend_route"] = frontend_route_kebab
    elif os.path.isdir(frontend_route_snake):
        locations["frontend_route"] = frontend_route_snake
    
    return locations

def get_extension_manifest(extension_id):
    """Find and load an extension's manifest file"""
    locations = find_extension_locations(extension_id)
    
    # First check backend, then frontend locations
    for loc_type in ["backend", "frontend_lib"]:
        if loc_type in locations:
            manifest_path = os.path.join(locations[loc_type], "manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, 'r') as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    log_error(f"Invalid JSON in manifest file: {manifest_path}")
    
    return None

def package_extension(extension_id, output_dir=None):
    """Package an extension into a zip file"""
    # Get extension locations (handles both kebab-case and snake_case)
    locations = find_extension_locations(extension_id)
    if not locations:
        log_error(f"Extension '{extension_id}' not found")
        return False
    
    # Get manifest
    manifest = get_extension_manifest(extension_id)
    if not manifest:
        log_error(f"No manifest.json found for extension '{extension_id}'")
        return False
    
    # Ensure we have a normalized extension ID for the package
    extension_id = normalize_extension_id(manifest.get("id", extension_id))
    
    # Set output directory and filename
    paths = get_project_paths()
    if not output_dir:
        output_dir = paths["project_root"]
    
    version = manifest.get("version", "1.0.0")
    zip_filename = f"{extension_id}-{version}.zip"
    zip_path = os.path.join(output_dir, zip_filename)
    
    log_info(f"Packaging extension {manifest.get('name', extension_id)} (v{version})")
    
    # Create the package
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy manifest
        if "backend" in locations and os.path.exists(os.path.join(locations["backend"], "manifest.json")):
            manifest_path = os.path.join(locations["backend"], "manifest.json")
        elif "frontend_lib" in locations and os.path.exists(os.path.join(locations["frontend_lib"], "manifest.json")):
            manifest_path = os.path.join(locations["frontend_lib"], "manifest.json")
        else:
            # Create a new manifest if none exists
            manifest_path = os.path.join(temp_dir, "manifest.json")
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
        
        # Create the zip file
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add manifest.json to the root
            if os.path.exists(manifest_path):
                zipf.write(manifest_path, "manifest.json")
                log_info(f"Added manifest.json")
            
            # Add backend files
            if "backend" in locations:
                backend_src = locations["backend"]
                for root, _, files in os.walk(backend_src):
                    for file in files:
                        if file.endswith('.py') or file == "manifest.json":
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, backend_src)
                            zipf.write(file_path, os.path.join("backend", rel_path))
                            log_info(f"Added backend/{rel_path}")
            
            # Add frontend lib files
            if "frontend_lib" in locations:
                frontend_lib_src = locations["frontend_lib"]
                for root, _, files in os.walk(frontend_lib_src):
                    for file in files:
                        if file.endswith(('.svelte', '.ts', '.js')):
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, frontend_lib_src)
                            zipf.write(file_path, os.path.join("frontend/lib/extensions", extension_id, rel_path))
                            log_info(f"Added frontend/lib/extensions/{extension_id}/{rel_path}")
            
            # Add frontend route files
            if "frontend_route" in locations:
                frontend_route_src = locations["frontend_route"]
                for root, _, files in os.walk(frontend_route_src):
                    for file in files:
                        if file.endswith(('.svelte', '.ts', '.js')):
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, frontend_route_src)
                            zipf.write(file_path, os.path.join("frontend/routes/(sidebar)/extensions", extension_id, rel_path))
                            log_info(f"Added frontend/routes/(sidebar)/extensions/{extension_id}/{rel_path}")
    
    log_success(f"Extension packaged successfully: {zip_path}")
    return True

def install_extension(package_path):
    """Install an extension from a package"""
    if not os.path.exists(package_path):
        log_error(f"Package file not found: {package_path}")
        return False
    
    paths = get_project_paths()
    
    # Extract and process the package
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the package
        try:
            with zipfile.ZipFile(package_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            log_info(f"Extracted package to temporary directory")
        except Exception as e:
            log_error(f"Failed to extract package: {e}")
            return False
        
        # Read the manifest
        manifest_path = os.path.join(temp_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            log_error("No manifest.json found in package")
            return False
        
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        except json.JSONDecodeError:
            log_error("Invalid JSON in manifest.json")
            return False
        
        # Get extension ID from manifest
        extension_id = manifest.get("id") or normalize_extension_id(manifest.get("name", ""))
        if not extension_id:
            log_error("No extension ID or name found in manifest")
            return False
        
        # Normalize IDs for different parts
        normalized_id = normalize_extension_id(extension_id)
        snake_id = normalized_id.replace('-', '_')
        
        # Install backend files
        backend_source = os.path.join(temp_dir, "backend")
        if os.path.exists(backend_source) and os.listdir(backend_source):
            # Backend always uses snake_case
            backend_target = os.path.join(paths["backend_dir"], "extensions", snake_id)
            
            # Remove existing files if needed
            if os.path.exists(backend_target):
                shutil.rmtree(backend_target)
            
            # Create target directory and copy files
            os.makedirs(backend_target, exist_ok=True)
            
            # Copy manifest
            shutil.copy2(manifest_path, os.path.join(backend_target, "manifest.json"))
            
            # Copy Python files
            for root, _, files in os.walk(backend_source):
                for file in files:
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, backend_source)
                    dst_file = os.path.join(backend_target, rel_path)
                    
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    log_info(f"Installed backend file: {rel_path}")
            
            log_success(f"Installed backend files for {extension_id}")
        
        # Install frontend lib files
        frontend_lib_source = os.path.join(temp_dir, "frontend/lib/extensions", normalized_id)
        if not os.path.exists(frontend_lib_source):
            # Try with snake_case if kebab-case didn't work
            frontend_lib_source = os.path.join(temp_dir, "frontend/lib/extensions", snake_id)
            
        if os.path.exists(frontend_lib_source) and os.listdir(frontend_lib_source):
            # For consistency, use the same ID format that's used in the source files
            ext_id_format = os.path.basename(frontend_lib_source)
            frontend_lib_target = os.path.join(paths["frontend_dir"], "src/lib/extensions", ext_id_format)
            
            # Remove existing files if needed
            if os.path.exists(frontend_lib_target):
                shutil.rmtree(frontend_lib_target)
            
            # Create target directory and copy files
            os.makedirs(frontend_lib_target, exist_ok=True)
            
            # Copy files
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
        
        # Install frontend route files
        frontend_route_source = os.path.join(temp_dir, "frontend/routes/(sidebar)/extensions", normalized_id)
        if not os.path.exists(frontend_route_source):
            # Try with snake_case if kebab-case didn't work
            frontend_route_source = os.path.join(temp_dir, "frontend/routes/(sidebar)/extensions", snake_id)
            
        if os.path.exists(frontend_route_source) and os.listdir(frontend_route_source):
            # For consistency, use the same ID format that's used in the source files
            ext_id_format = os.path.basename(frontend_route_source)
            frontend_route_target = os.path.join(paths["frontend_dir"], "src/routes/(sidebar)/extensions", ext_id_format)
            
            # Remove existing files if needed
            if os.path.exists(frontend_route_target):
                shutil.rmtree(frontend_route_target)
            
            # Create target directory and copy files
            os.makedirs(frontend_route_target, exist_ok=True)
            
            # Copy files
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
    
    log_success(f"Extension {extension_id} installed successfully")
    return True

def list_extensions():
    """List all installed extensions"""
    paths = get_project_paths()
    backend_ext_dir = os.path.join(paths["backend_dir"], "extensions")
    frontend_ext_dir = os.path.join(paths["frontend_dir"], "src/lib/extensions")
    
    # Find all extensions
    extensions = {}
    
    # Check backend extensions
    if os.path.exists(backend_ext_dir):
        for item in os.listdir(backend_ext_dir):
            if os.path.isdir(os.path.join(backend_ext_dir, item)) and not item.startswith('__'):
                ext_id = normalize_extension_id(item)
                manifest_path = os.path.join(backend_ext_dir, item, "manifest.json")
                
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                        extensions[ext_id] = {
                            'id': ext_id,
                            'name': manifest.get('name', ext_id),
                            'version': manifest.get('version', 'unknown'),
                            'description': manifest.get('description', ''),
                            'has_backend': True,
                            'has_frontend': False
                        }
                    except Exception:
                        # If manifest can't be read, use basic info
                        extensions[ext_id] = {
                            'id': ext_id, 
                            'name': item,
                            'version': 'unknown',
                            'description': '',
                            'has_backend': True,
                            'has_frontend': False
                        }
    
    # Check frontend extensions
    if os.path.exists(frontend_ext_dir):
        for item in os.listdir(frontend_ext_dir):
            if os.path.isdir(os.path.join(frontend_ext_dir, item)) and not item.startswith('__'):
                ext_id = normalize_extension_id(item)
                if ext_id in extensions:
                    extensions[ext_id]['has_frontend'] = True
                else:
                    manifest_path = os.path.join(frontend_ext_dir, item, "manifest.json")
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, 'r') as f:
                                manifest = json.load(f)
                            extensions[ext_id] = {
                                'id': ext_id,
                                'name': manifest.get('name', ext_id),
                                'version': manifest.get('version', 'unknown'),
                                'description': manifest.get('description', ''),
                                'has_backend': False,
                                'has_frontend': True
                            }
                        except Exception:
                            # If manifest can't be read, use basic info
                            extensions[ext_id] = {
                                'id': ext_id, 
                                'name': item,
                                'version': 'unknown',
                                'description': '',
                                'has_backend': False,
                                'has_frontend': True
                            }
    
    # Print results
    if not extensions:
        print("No extensions installed")
        return True
    
    # Print table header
    print(f"{'ID':<20} {'NAME':<30} {'VERSION':<15} {'COMPONENTS':<15}")
    print(f"{'-'*20} {'-'*30} {'-'*15} {'-'*15}")
    
    # Print extension data
    for ext_id in sorted(extensions.keys()):
        ext = extensions[ext_id]
        components = []
        if ext.get('has_backend'):
            components.append('backend')
        if ext.get('has_frontend'):
            components.append('frontend')
        components_str = ', '.join(components) if components else 'none'
        
        print(f"{ext['id']:<20} {ext['name']:<30} {ext['version']:<15} {components_str:<15}")
    
    return True

def uninstall_extension(extension_id):
    """Uninstall an extension"""
    extension_id = normalize_extension_id(extension_id)
    paths = get_extension_paths(extension_id)
    
    removed = False
    
    # Remove backend files
    backend_path = paths["backend"]
    if os.path.exists(backend_path):
        try:
            shutil.rmtree(backend_path)
            log_success(f"Removed backend files from {backend_path}")
            removed = True
        except Exception as e:
            log_error(f"Failed to remove backend files: {e}")
    
    # Remove frontend lib files
    frontend_lib_path = paths["frontend_lib"]
    if os.path.exists(frontend_lib_path):
        try:
            shutil.rmtree(frontend_lib_path)
            log_success(f"Removed frontend lib files from {frontend_lib_path}")
            removed = True
        except Exception as e:
            log_error(f"Failed to remove frontend lib files: {e}")
    
    # Remove frontend route files
    frontend_route_path = paths["frontend_route"]
    if os.path.exists(frontend_route_path):
        try:
            shutil.rmtree(frontend_route_path)
            log_success(f"Removed frontend route files from {frontend_route_path}")
            removed = True
        except Exception as e:
            log_error(f"Failed to remove frontend route files: {e}")
    
    if removed:
        log_success(f"Extension {extension_id} uninstalled successfully")
        return True
    else:
        log_error(f"Extension {extension_id} not found or already uninstalled")
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Realm Extension CLI - Manage extensions for the Smart Social Contracts platform")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List command
    subparsers.add_parser("list", help="List installed extensions")
    
    # Package command
    package_parser = subparsers.add_parser("package", help="Package an extension into a zip file")
    package_parser.add_argument("name", help="Name of the extension to package")
    package_parser.add_argument("--output", help="Output directory for the package")
    
    # Install command
    install_parser = subparsers.add_parser("install", help="Install an extension package")
    install_parser.add_argument("package", help="Path to the extension package")
    
    # Uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall an extension")
    uninstall_parser.add_argument("name", help="Name of the extension to uninstall")
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 1
    
    if args.command == "list":
        list_extensions()
    elif args.command == "package":
        if not package_extension(args.name, args.output):
            return 1
    elif args.command == "install":
        if not install_extension(args.package):
            return 1
    elif args.command == "uninstall":
        if not uninstall_extension(args.name):
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())