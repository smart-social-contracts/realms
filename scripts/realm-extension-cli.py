#!/usr/bin/env python3
"""
Extension CLI for Smart Social Contracts Platform

This tool provides a unified interface for managing extensions:
- Package extensions into distributable zip files
- Install packaged extensions into the Realm project

Usage:
  python realm-extension-cli.py package --dir=path/to/extension
  python realm-extension-cli.py install --package=path/to/extension.zip

"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile
import datetime
from pathlib import Path

# Add utils module to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils"))
try:
    from colors import Colors, print_colored
except ImportError:
    # Fallback if colors module is not available
    class Colors:
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        RESET = '\033[0m'
        BOLD = '\033[1m'

    def print_colored(color, text):
        print(f"{color}{text}{Colors.RESET}")

# Get project root directory (assuming script is in scripts/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "src/realm_backend")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "src/realm_frontend")

def log_info(message):
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {message}")

def log_success(message):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {message}")

def log_warning(message):
    print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {message}")

def log_error(message):
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {message}")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Manage extensions for the Smart Social Contracts platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Package an extension:
    python realm-extension-cli.py package vault-extension

  Install an extension:
    python realm-extension-cli.py install /path/to/extension.zip
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Package command
    package_parser = subparsers.add_parser("package", help="Package an extension into a zip file")
    package_parser.add_argument("name", help="Name of the extension to package")
    package_parser.add_argument("--output", help="Output directory for the package (default: realms directory)")
    
    # Install command
    install_parser = subparsers.add_parser("install", help="Install an extension package")
    install_parser.add_argument("package", help="Path to the extension package (zip file)")
    install_parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    install_parser.add_argument("--skip-register", action="store_true", help="Skip code registration steps (manual registration required)")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List installed extensions")
    list_parser.add_argument("--format", choices=["table", "json"], default="table", help="Output format")
    
    # Uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall an extension")
    uninstall_parser.add_argument("name", help="Name of the extension to uninstall, or 'all' to uninstall all extensions")
    uninstall_parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    return parser.parse_args()

#
# PACKAGING FUNCTIONALITY
#

def package_extension(extension_name, output_dir=None):
    """Package an extension into a zip file"""
    # Set extension vault directory
    ext_dir = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "realm-extension-vault"))
    
    if not os.path.isdir(ext_dir):
        log_error(f"Extension vault directory {ext_dir} not found")
        return False
    
    # Read manifest to get extension info
    manifest_path = os.path.join(ext_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        log_error(f"manifest.json not found in {ext_dir}")
        return False
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except Exception as e:
        log_error(f"Failed to parse manifest.json: {str(e)}")
        return False
    
    extension_id = manifest.get("id")
    extension_name_in_manifest = manifest.get("name")
    version = manifest.get("version", "1.0.0")
    
    if not extension_id:
        log_error("Extension ID not found in manifest.json")
        return False
    
    # Normalize extension name for comparison (support different formats)
    normalized_input = extension_name.lower().replace('_', '-').replace(' ', '-')
    normalized_id = extension_id.lower().replace('_', '-').replace(' ', '-')
    normalized_name = extension_name_in_manifest.lower().replace('_', '-').replace(' ', '-') if extension_name_in_manifest else ''
    
    # Accept the input if it matches either the ID or the name
    if normalized_input != normalized_id and normalized_input != normalized_name:
        log_info(f"Note: Using ID '{extension_id}' from manifest.json")
        # We'll continue anyway, just showing an informational message
    
    # Set output directory
    if not output_dir:
        output_dir = PROJECT_ROOT  # This is the realms directory
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Use a simple version-based filename without timestamp
    zip_filename = f"{extension_id}-{version}.zip"
    zip_path = os.path.join(output_dir, zip_filename)
    
    # Collect files to package
    log_info(f"Packaging extension {extension_id} v{version}")
    
    # Create the zip file
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Always add manifest.json to the root
        zipf.write(manifest_path, "manifest.json")
        log_info(f"Added manifest.json to package")
        
        # Add backend files if they exist
        backend_dir = os.path.join(ext_dir, "backend")
        if os.path.exists(backend_dir):
            for root, _, files in os.walk(backend_dir):
                for item in files:
                    if item.endswith('.py'):
                        file_path = os.path.join(root, item)
                        relative_path = os.path.relpath(file_path, ext_dir)
                        zipf.write(file_path, relative_path)
                        log_info(f"Added {relative_path} to package")
        
        # Add frontend files if they exist
        frontend_dir = os.path.join(ext_dir, "frontend")
        if os.path.exists(frontend_dir):
            for root, _, files in os.walk(frontend_dir):
                for item in files:
                    if item.endswith(('.svelte', '.js', '.ts', '.css')):
                        file_path = os.path.join(root, item)
                        relative_path = os.path.relpath(file_path, ext_dir)
                        zipf.write(file_path, relative_path)
                        log_info(f"Added {relative_path} to package")
    
    log_success(f"Extension packaged successfully: {zip_path}")
    return True

#
# INSTALLATION FUNCTIONALITY
#

def extract_package(package_path, temp_dir):
    """Extract the extension package to a temporary directory"""
    log_info(f"Extracting {package_path} to temporary directory")
    
    try:
        with zipfile.ZipFile(package_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        return True
    except Exception as e:
        log_error(f"Failed to extract package: {str(e)}")
        return False

def read_manifest(temp_dir):
    """Read the extension manifest.json file"""
    manifest_path = os.path.join(temp_dir, "manifest.json")
    
    if not os.path.exists(manifest_path):
        log_error("manifest.json not found in the package")
        return None
        
    try:
        with open(manifest_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        log_error(f"Failed to parse manifest.json: {str(e)}")
        return None

def install_backend(temp_dir, manifest, dry_run=False):
    """Install the backend part of the extension"""
    extension_id = manifest["id"]
    backend_config = manifest.get("backendConfig", {})
    
    if not backend_config:
        log_warning("No backend configuration found in manifest, skipping backend installation")
        return True
    
    # Convert extension ID to appropriate format for Python modules
    # e.g., "vault-extension" -> "vault_extension"
    module_name = extension_id.replace("-", "_")
    
    # Get init function name
    init_function = backend_config.get("init_function", f"init_{module_name}")
    
    # Path to main.py
    main_py_path = os.path.join(BACKEND_DIR, "main.py")
    
    if not os.path.exists(main_py_path):
        log_error(f"main.py not found at {main_py_path}")
        return False
    
    log_info(f"Registering backend extension in {main_py_path}")
    
    if dry_run:
        log_info(f"[DRY RUN] Would add import and init call for {module_name}")
        return True
    
    # Read the current content of main.py
    with open(main_py_path, 'r') as f:
        lines = f.readlines()
    
    # Look for the extension imports section
    import_section_start = None
    import_section_end = None
    init_section_start = None
    init_section_end = None
    
    # Find the import and init sections
    for i, line in enumerate(lines):
        if "# START EXTENSION IMPORTS" in line:
            import_section_start = i
        elif "# END EXTENSION IMPORTS" in line:
            import_section_end = i
        elif "# START EXTENSION INITIALIZATION" in line:
            init_section_start = i
        elif "# END EXTENSION INITIALIZATION" in line:
            init_section_end = i
    
    if not all([import_section_start, import_section_end, init_section_start, init_section_end]):
        log_error("Could not find extension sections in main.py. Make sure it has the proper markers")
        return False
    
    # Check if the extension is already imported
    import_line = f"from extensions.{module_name} import {init_function}\n"
    init_line = f"    {init_function}()\n"
    
    already_imported = any(import_line == line for line in lines[import_section_start:import_section_end+1])
    already_initialized = any(init_line == line for line in lines[init_section_start:init_section_end+1])
    
    # Add the import if needed
    if not already_imported:
        lines.insert(import_section_end, import_line)
        log_info(f"Added import for {module_name}")
        
        # If we added an import, we need to update the indices
        if init_section_start > import_section_end:
            init_section_start += 1
        if init_section_end > import_section_end:
            init_section_end += 1
    
    # Add the init call if needed
    if not already_initialized:
        lines.insert(init_section_end, init_line)
        log_info(f"Added initialization call for {module_name}")
    
    # Write the updated content back to main.py
    with open(main_py_path, 'w') as f:
        f.writelines(lines)
    
    log_success(f"Backend extension registered in main.py")
    return True

def install_frontend(temp_dir, manifest, dry_run=False):
    """Install the frontend part of the extension"""
    extension_id = manifest["id"]
    frontend_config = manifest.get("frontendConfig", {})
    
    # Convert extension ID to appropriate format for JavaScript/Svelte modules
    # e.g., "vault-extension" stays as "vault-extension"
    module_name = extension_id
    
    # Define paths
    frontend_src_dir = os.path.join(temp_dir, "frontend")
    frontend_dest_dir = os.path.join(FRONTEND_DIR, "src/lib/extensions", module_name)
    
    if not os.path.exists(frontend_src_dir):
        log_warning("No frontend directory found in package, skipping frontend installation")
        return True
    
    log_info(f"Installing frontend extension to {frontend_dest_dir}")
    
    if dry_run:
        log_info("[DRY RUN] Would create directory and copy files")
        return True
    
    # Create the extension directory
    os.makedirs(frontend_dest_dir, exist_ok=True)
    
    # Copy all frontend files
    files_copied = 0
    for root, _, files in os.walk(frontend_src_dir):
        for item in files:
            if item.endswith(('.svelte', '.js', '.ts', '.css')):
                src_file = os.path.join(root, item)
                rel_path = os.path.relpath(src_file, frontend_src_dir)
                dest_file = os.path.join(frontend_dest_dir, rel_path)
                
                # Create subdirectories if needed
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                
                shutil.copy2(src_file, dest_file)
                files_copied += 1
                log_info(f"Copied {rel_path} to {frontend_dest_dir}")
    
    # Ensure the index.js file exists
    index_file = os.path.join(frontend_dest_dir, "index.js")
    if not os.path.exists(index_file):
        log_warning("No index.js found, trying to create a minimal one")
        
        # Find the main component file from config or guess based on naming convention
        main_component_path = frontend_config.get("main_component", "")
        if main_component_path:
            main_component = os.path.basename(main_component_path).replace(".svelte", "")
        else:
            # Try to guess the main component
            for item in os.listdir(frontend_dest_dir):
                if item.lower() == f"{module_name}.svelte".lower() or item.endswith("Extension.svelte"):
                    main_component = item.replace(".svelte", "")
                    break
            else:
                main_component = None
        
        if main_component:
            # Create basic index.js with extension metadata
            index_content = f"""import {main_component} from './{main_component}.svelte';

export const metadata = {{
  id: '{module_name}',
  name: '{manifest.get("name", module_name)}',
  description: '{manifest.get("description", "")}',
  version: '{manifest.get("version", "1.0.0")}',
  icon: '{manifest.get("icon", "app")}',
  author: '{manifest.get("author", "")}',
  category: '{manifest.get("category", "Other")}'
}};

export const ExtensionComponent = {main_component};
"""
            with open(index_file, 'w') as f:
                f.write(index_content)
            log_info(f"Created index.js for {module_name}")
        else:
            log_warning("Could not determine main component, index.js not created")
    
    log_success(f"Frontend installation complete: {files_copied} files copied")
    
    if not files_copied:
        log_warning("No frontend files were found")
    
    return True

def register_backend_extension(manifest, dry_run=False):
    """Register the extension in the backend main.py file"""
    extension_id = manifest["id"]
    backend_config = manifest.get("backendConfig", {})
    
    if not backend_config:
        log_warning("No backend configuration found in manifest, skipping backend registration")
        return True
    
    # Convert extension ID to appropriate format for Python modules
    module_name = extension_id.replace("-", "_")
    
    # Get init function name
    init_function = backend_config.get("init_function", f"init_{module_name}")
    
    # Path to main.py
    main_py_path = os.path.join(BACKEND_DIR, "main.py")
    
    if not os.path.exists(main_py_path):
        log_error(f"main.py not found at {main_py_path}")
        return False
    
    log_info(f"Registering backend extension in {main_py_path}")
    
    if dry_run:
        log_info(f"[DRY RUN] Would add import and init call for {module_name}")
        return True
    
    # Read the current content of main.py
    with open(main_py_path, 'r') as f:
        lines = f.readlines()
    
    # Look for the extension imports section
    import_section_start = None
    import_section_end = None
    init_section_start = None
    init_section_end = None
    
    # Find the import and init sections
    for i, line in enumerate(lines):
        if "# START EXTENSION IMPORTS" in line:
            import_section_start = i
        elif "# END EXTENSION IMPORTS" in line:
            import_section_end = i
        elif "# START EXTENSION INITIALIZATION" in line:
            init_section_start = i
        elif "# END EXTENSION INITIALIZATION" in line:
            init_section_end = i
    
    if not all([import_section_start, import_section_end, init_section_start, init_section_end]):
        log_error("Could not find extension sections in main.py. Make sure it has the proper markers")
        return False
    
    # Check if the extension is already imported
    import_line = f"from extensions.{module_name} import {init_function}\n"
    init_line = f"    {init_function}()\n"
    
    already_imported = any(import_line == line for line in lines[import_section_start:import_section_end+1])
    already_initialized = any(init_line == line for line in lines[init_section_start:init_section_end+1])
    
    # Add the import if needed
    if not already_imported:
        lines.insert(import_section_end, import_line)
        log_info(f"Added import for {module_name}")
        
        # If we added an import, we need to update the indices
        if init_section_start > import_section_end:
            init_section_start += 1
        if init_section_end > import_section_end:
            init_section_end += 1
    
    # Add the init call if needed
    if not already_initialized:
        lines.insert(init_section_end, init_line)
        log_info(f"Added initialization call for {module_name}")
    
    # Write the updated content back to main.py
    with open(main_py_path, 'w') as f:
        f.writelines(lines)
    
    log_success(f"Backend extension registered in main.py")
    return True

def register_frontend_extension(manifest, dry_run=False):
    """Register the extension in the frontend extensions registry"""
    extension_id = manifest["id"]
    
    # Path to frontend extensions registry
    registry_path = os.path.join(FRONTEND_DIR, "src/lib/extensions/registry.js")
    
    if not os.path.exists(registry_path):
        log_error(f"Frontend extensions registry not found at {registry_path}")
        return False
    
    log_info(f"Registering frontend extension in {registry_path}")
    
    if dry_run:
        log_info(f"[DRY RUN] Would add {extension_id} to frontend registry")
        return True
    
    # Read the current content of registry.js
    with open(registry_path, 'r') as f:
        lines = f.readlines()
    
    # Look for the extensions array
    extensions_start = None
    extensions_end = None
    
    for i, line in enumerate(lines):
        if "const extensions = [" in line:
            extensions_start = i
        elif extensions_start is not None and "];" in line:
            extensions_end = i
            break
    
    if not all([extensions_start, extensions_end]):
        log_error("Could not find extensions array in registry.js")
        return False
    
    # Check if the extension is already registered
    extension_import = f"import * as {extension_id.replace('-', '_')} from './{extension_id}';\n"
    extension_entry = f"  {extension_id.replace('-', '_')},\n"
    
    # Find the last import line
    last_import_line = 0
    for i, line in enumerate(lines):
        if line.startswith('import '):
            last_import_line = i
    
    # Check if already imported
    already_imported = any(extension_import == line for line in lines)
    already_registered = any(extension_entry == line for line in lines[extensions_start:extensions_end+1])
    
    # Add the import if needed
    if not already_imported:
        lines.insert(last_import_line + 1, extension_import)
        log_info(f"Added import for {extension_id}")
        
        # If we added an import, we need to update the indices
        if extensions_start > last_import_line:
            extensions_start += 1
        if extensions_end > last_import_line:
            extensions_end += 1
    
    # Add the extension to the array if needed
    if not already_registered:
        lines.insert(extensions_end, extension_entry)
        log_info(f"Added {extension_id} to extensions array")
    
    # Write the updated content back to registry.js
    with open(registry_path, 'w') as f:
        f.writelines(lines)
    
    log_success(f"Frontend extension registered in registry.js")
    return True

def list_extensions(format="table"):
    """List all installed extensions in a parseable table format"""
    backend_ext_dir = os.path.join(BACKEND_DIR, "extensions")
    frontend_ext_dir = os.path.join(FRONTEND_DIR, "src/lib/extensions")
    default_ext_dir = os.path.join(PROJECT_ROOT, "extensions")
    
    # Collect extension data
    extensions = {}
    
    # Check default bundled extensions
    if os.path.exists(default_ext_dir):
        for item in os.listdir(default_ext_dir):
            ext_dir = os.path.join(default_ext_dir, item)
            if os.path.isdir(ext_dir) and not item.startswith('__'):
                manifest_path = os.path.join(ext_dir, "manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                        
                        ext_id = manifest.get('id', item)
                        extensions[ext_id] = {
                            'id': ext_id,
                            'name': manifest.get('name', ext_id),
                            'version': manifest.get('version', 'unknown'),
                            'description': manifest.get('description', ''),
                            'backend': False,
                            'frontend': False,
                            'bundled': True,  # Mark as bundled/default extension
                            'installed': False
                        }
                    except Exception as e:
                        log_warning(f"Failed to parse manifest for bundled extension {item}: {str(e)}")
    
    # Check backend extensions
    if os.path.exists(backend_ext_dir):
        for item in os.listdir(backend_ext_dir):
            # Skip __pycache__ and other non-directory items
            if item.startswith('__') or not os.path.isdir(os.path.join(backend_ext_dir, item)):
                continue
            
            # Read the manifest file
            manifest_path = os.path.join(backend_ext_dir, item, "manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                    
                    ext_id = manifest.get('id', item)
                    if ext_id in extensions:
                        # Update existing entry
                        extensions[ext_id]['backend'] = True
                        extensions[ext_id]['installed'] = True
                    else:
                        # Create new entry
                        extensions[ext_id] = {
                            'id': ext_id,
                            'name': manifest.get('name', ext_id),
                            'version': manifest.get('version', 'unknown'),
                            'description': manifest.get('description', ''),
                            'backend': True,
                            'frontend': False,
                            'bundled': False,
                            'installed': True
                        }
                except Exception as e:
                    log_warning(f"Failed to parse manifest for backend extension {item}: {str(e)}")
    
    # Check frontend extensions
    if os.path.exists(frontend_ext_dir):
        for item in os.listdir(frontend_ext_dir):
            # Skip special directories and files
            if item.startswith('__') or item == 'registry.js' or not os.path.isdir(os.path.join(frontend_ext_dir, item)):
                continue
            
            # Try to get info from backend manifest if available
            ext_id = item
            # Check if it matches an existing backend extension
            if ext_id.replace('-', '_') in [k.replace('-', '_') for k in extensions.keys()]:
                # Find the matching key with normalized comparison
                for k in extensions.keys():
                    if k.replace('-', '_') == ext_id.replace('-', '_'):
                        extensions[k]['frontend'] = True
                        extensions[k]['installed'] = True
                        break
            else:
                # Check if the frontend directory has a manifest
                manifest_path = os.path.join(frontend_ext_dir, ext_id, "manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                        
                        ext_id = manifest.get('id', ext_id)
                        extensions[ext_id] = {
                            'id': ext_id,
                            'name': manifest.get('name', ext_id),
                            'version': manifest.get('version', 'unknown'),
                            'description': manifest.get('description', ''),
                            'backend': False,
                            'frontend': True,
                            'bundled': False,
                            'installed': True
                        }
                    except Exception:
                        # If we can't read the manifest, just add with basic info
                        extensions[ext_id] = {
                            'id': ext_id,
                            'name': ext_id,
                            'version': 'unknown',
                            'description': '',
                            'backend': False,
                            'frontend': True,
                            'bundled': False,
                            'installed': True
                        }
    
    # Print the output
    if format == "table":
        print(f"{'ID':<20} {'NAME':<30} {'VERSION':<15} {'COMPONENTS':<15} {'STATUS':<10}")
        print(f"{'-'*20} {'-'*30} {'-'*15} {'-'*15} {'-'*10}")
        
        # Print extension data
        if extensions:
            for ext_id in sorted(extensions.keys()):
                ext = extensions[ext_id]
                components = []
                if ext.get('backend'):
                    components.append('backend')
                if ext.get('frontend'):
                    components.append('frontend')
                components_str = ', '.join(components) if components else 'none'
                
                status = []
                if ext.get('bundled'):
                    status.append('bundled')
                if ext.get('installed'):
                    status.append('installed')
                status_str = ', '.join(status)
                
                print(f"{ext['id']:<20} {ext['name']:<30} {ext['version']:<15} {components_str:<15} {status_str:<10}")
        else:
            print("No extensions found")
    elif format == "json":
        print(json.dumps(list(extensions.values()), indent=2))
        
    return True

def uninstall_extension(extension_id, dry_run=False):
    """Uninstall an extension"""
    if extension_id.lower() == 'all':
        log_info("Uninstalling all extensions")
        extensions = list_extensions(format="json")
        for ext_id in extensions:
            uninstall_extension(ext_id, dry_run)
        return True
    
    log_info(f"Uninstalling extension {extension_id}")
    
    # Remove backend extension
    backend_ext_dir = os.path.join(BACKEND_DIR, "extensions", extension_id.replace('-', '_'))
    if os.path.exists(backend_ext_dir):
        if dry_run:
            log_info(f"[DRY RUN] Would remove {backend_ext_dir}")
        else:
            shutil.rmtree(backend_ext_dir)
            log_success(f"Removed backend extension {extension_id}")
    
    # Remove frontend extension
    frontend_ext_dir = os.path.join(FRONTEND_DIR, "src/lib/extensions", extension_id)
    if os.path.exists(frontend_ext_dir):
        if dry_run:
            log_info(f"[DRY RUN] Would remove {frontend_ext_dir}")
        else:
            shutil.rmtree(frontend_ext_dir)
            log_success(f"Removed frontend extension {extension_id}")
    
    # Unregister extension
    if not dry_run:
        # Unregister from backend
        main_py_path = os.path.join(BACKEND_DIR, "main.py")
        if os.path.exists(main_py_path):
            with open(main_py_path, 'r') as f:
                lines = f.readlines()
            
            # Remove import and init lines
            import_section_start = None
            import_section_end = None
            init_section_start = None
            init_section_end = None
            
            for i, line in enumerate(lines):
                if "# START EXTENSION IMPORTS" in line:
                    import_section_start = i
                elif "# END EXTENSION IMPORTS" in line:
                    import_section_end = i
                elif "# START EXTENSION INITIALIZATION" in line:
                    init_section_start = i
                elif "# END EXTENSION INITIALIZATION" in line:
                    init_section_end = i
            
            if all([import_section_start, import_section_end, init_section_start, init_section_end]):
                import_line = f"from extensions.{extension_id.replace('-', '_')} import init_{extension_id.replace('-', '_')}\n"
                init_line = f"    init_{extension_id.replace('-', '_')}()\n"
                
                lines = [line for line in lines if line != import_line and line != init_line]
                
                with open(main_py_path, 'w') as f:
                    f.writelines(lines)
                log_success(f"Unregistered extension {extension_id} from backend")
        
        # Unregister from frontend
        registry_path = os.path.join(FRONTEND_DIR, "src/lib/extensions/registry.js")
        if os.path.exists(registry_path):
            with open(registry_path, 'r') as f:
                lines = f.readlines()
            
            # Remove import and registry lines
            extension_import = f"import * as {extension_id.replace('-', '_')} from './{extension_id}';\n"
            extension_entry = f"  {extension_id.replace('-', '_')},\n"
            
            lines = [line for line in lines if line != extension_import and line != extension_entry]
            
            with open(registry_path, 'w') as f:
                f.writelines(lines)
            log_success(f"Unregistered extension {extension_id} from frontend")
    
    return True

def install_extension(package_path, dry_run=False, skip_register=False):
    """Install an extension package"""
    if not os.path.exists(package_path):
        log_error(f"Package not found: {package_path}")
        return False
    
    # Create a temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the package
        if not extract_package(package_path, temp_dir):
            return False
        
        # Read the manifest
        manifest = read_manifest(temp_dir)
        if not manifest:
            return False
        
        log_info(f"Installing extension: {manifest.get('name', manifest.get('id'))}")
        
        # Install backend and frontend components
        backend_success = install_backend(temp_dir, manifest, dry_run)
        frontend_success = install_frontend(temp_dir, manifest, dry_run)
        
        if not backend_success or not frontend_success:
            log_error("Installation failed")
            return False
        
        # Register the extension (unless --skip-register is specified)
        if not skip_register and not dry_run:
            register_backend_extension(manifest, dry_run)
            register_frontend_extension(manifest, dry_run)
    
    log_success(f"Extension installation complete: {os.path.basename(package_path)}")
    return True

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Realm Extension CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List installed extensions")
    list_parser.add_argument("--format", choices=["table", "json"], default="table", help="Output format")
    
    # Package command
    package_parser = subparsers.add_parser("package", help="Package an extension into a zip file")
    package_parser.add_argument("name", help="Name of the extension to package")
    package_parser.add_argument("--output", help="Output directory for the package (default: realms directory)")
    
    # Install command
    install_parser = subparsers.add_parser("install", help="Install an extension package")
    install_parser.add_argument("package", help="Path to the extension package")
    install_parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    install_parser.add_argument("--skip-register", action="store_true", help="Skip code registration steps (manual registration required)")
    
    # Uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall an extension")
    uninstall_parser.add_argument("name", help="Name of the extension to uninstall, or 'all' to uninstall all extensions")
    uninstall_parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 1
    
    if args.command == "list":
        list_extensions(args.format)
    elif args.command == "package":
        if not package_extension(args.name, args.output):
            return 1
    elif args.command == "install":
        if not install_extension(args.package, args.dry_run, args.skip_register):
            return 1
    elif args.command == "uninstall":
        if not uninstall_extension(args.name, args.dry_run):
            return 1
    else:
        parser.print_help()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
