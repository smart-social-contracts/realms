#!/usr/bin/env python3
"""
Extension Installer for Smart Social Contracts Platform

This script installs extensions packaged in the standard format into the Realm project.
It handles both backend and frontend components automatically.

Usage:
  python scripts/install_extension.py --package=path/to/extension.zip
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile
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
    parser = argparse.ArgumentParser(description="Install extensions into the Realm project")
    parser.add_argument("--package", required=True, help="Path to the extension package (zip file)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--skip-register", action="store_true", help="Skip code registration steps (manual registration required)")
    return parser.parse_args()

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
    
    # Convert extension ID to appropriate format for Python modules
    # e.g., "vault-extension" -> "vault_extension"
    module_name = extension_id.replace("-", "_")
    
    # Define paths
    backend_src_dir = os.path.join(temp_dir, "backend")
    backend_dest_dir = os.path.join(BACKEND_DIR, "extensions", module_name)
    
    if not os.path.exists(backend_src_dir):
        log_warning("No backend directory found in package, skipping backend installation")
        return True
    
    log_info(f"Installing backend extension to {backend_dest_dir}")
    
    if dry_run:
        log_info("[DRY RUN] Would create directory and copy files")
        return True
    
    # Create the extension directory
    os.makedirs(backend_dest_dir, exist_ok=True)
    
    # Copy all Python files from the backend directory
    files_copied = 0
    for item in os.listdir(backend_src_dir):
        if item.endswith('.py'):
            src_file = os.path.join(backend_src_dir, item)
            dest_file = os.path.join(backend_dest_dir, item)
            shutil.copy2(src_file, dest_file)
            files_copied += 1
            log_info(f"Copied {item} to {backend_dest_dir}")
    
    # Create __init__.py file to expose the extension initialization function
    init_function = backend_config.get("init_function", f"init_{module_name}")
    class_name = backend_config.get("class_name")
    
    # Determine the correct import statement based on manifest
    if class_name:
        init_py_content = f"from extensions.{module_name}.{module_name} import {init_function}, {class_name}\n"
    else:
        init_py_content = f"from extensions.{module_name}.{module_name} import {init_function}\n"
    
    init_py_path = os.path.join(backend_dest_dir, "__init__.py")
    with open(init_py_path, 'w') as f:
        f.write(init_py_content)
    
    log_info(f"Created {init_py_path}")
    log_success(f"Backend installation complete: {files_copied} files copied")
    
    if not files_copied:
        log_warning("No Python files were found in the backend directory")
    
    return True

def install_frontend(temp_dir, manifest, dry_run=False):
    """Install the frontend part of the extension"""
    extension_id = manifest["id"]
    
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
    for item in os.listdir(frontend_src_dir):
        if item.endswith(('.svelte', '.js', '.ts', '.css')):
            src_file = os.path.join(frontend_src_dir, item)
            dest_file = os.path.join(frontend_dest_dir, item)
            shutil.copy2(src_file, dest_file)
            files_copied += 1
            log_info(f"Copied {item} to {frontend_dest_dir}")
    
    # Ensure the index.js file exists
    index_file = os.path.join(frontend_dest_dir, "index.js")
    if not os.path.exists(index_file):
        log_warning("No index.js found, trying to create a minimal one")
        
        # Find the main component file (assuming it's named like the extension or ends with Extension.svelte)
        main_component = None
        for item in os.listdir(frontend_dest_dir):
            if item.lower() == f"{module_name}.svelte".lower() or item.endswith("Extension.svelte"):
                main_component = item.replace(".svelte", "")
                break
        
        if main_component:
            index_content = f"""import {main_component} from './{main_component}.svelte';

export const metadata = {{
  id: '{module_name}',
  name: '{manifest.get("name", module_name)}',
  description: '{manifest.get("description", "")}',
  version: '{manifest.get("version", "1.0.0")}',
  icon: '{manifest.get("icon", "puzzle-piece")}',
  author: '{manifest.get("author", "")}',
  permissions: {json.dumps(manifest.get("backendConfig", {}).get("permissions", []))}
}};

export default {main_component};
"""
            with open(index_file, 'w') as f:
                f.write(index_content)
            
            log_info(f"Created {index_file}")
            files_copied += 1
        else:
            log_warning("Could not determine main component name, index.js creation skipped")
    
    log_success(f"Frontend installation complete: {files_copied} files copied")
    
    if not files_copied:
        log_warning("No frontend files were found or copied")
    
    return True

def register_backend_extension(manifest, dry_run=False):
    """Update main.py to register the extension"""
    if dry_run:
        log_info("[DRY RUN] Would update main.py to register the extension")
        return True
    
    extension_id = manifest["id"]
    module_name = extension_id.replace("-", "_")
    backend_config = manifest.get("backendConfig", {})
    init_function = backend_config.get("init_function", f"init_{module_name}")
    
    main_py_path = os.path.join(BACKEND_DIR, "main.py")
    
    if not os.path.exists(main_py_path):
        log_error(f"main.py not found at {main_py_path}")
        return False
    
    # Read existing main.py
    with open(main_py_path, 'r') as f:
        content = f.read()
    
    # Check if extension is already imported
    import_line = f"from extensions.{module_name} import {init_function}"
    if import_line in content:
        log_info("Extension already imported in main.py")
    else:
        # Find a good place to add the import
        import_section_end = content.find("\n\n", content.find("import "))
        if import_section_end == -1:
            import_section_end = content.find("def init")
        
        if import_section_end == -1:
            log_warning("Could not determine where to add import, you need to manually add:")
            log_warning(f"  {import_line}")
            return False
        
        # Insert the import line
        new_content = content[:import_section_end] + f"\n{import_line}" + content[import_section_end:]
        
        # Write back the updated content
        with open(main_py_path, 'w') as f:
            f.write(new_content)
        
        log_info(f"Added import to {main_py_path}")
    
    # Check if extension initialization is already in the init function
    init_call = f"{init_function}("
    
    if init_call in content:
        log_info("Extension initialization already in main.py")
    else:
        # Find the init function
        init_function_start = content.find("def init")
        if init_function_start == -1:
            log_warning("Could not find init function, you need to manually add:")
            log_warning(f"  {init_function}()")
            return False
        
        # Find a good place to add the initialization
        function_body_start = content.find(":", init_function_start) + 1
        next_return = content.find("return", function_body_start)
        
        if next_return == -1:
            function_end = content.find("def ", init_function_start + 1)
            if function_end == -1:
                function_end = len(content)
        else:
            function_end = next_return
        
        # Find the last non-comment, non-empty line before the end
        lines = content[function_body_start:function_end].split("\n")
        insert_pos = function_body_start
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith("#"):
                insert_pos = function_body_start + len("\n".join(lines[:i+1])) + 1
        
        # Determine the indentation level
        indent = "    "  # Default indentation
        for line in lines:
            if line.strip():
                indent = line[:len(line) - len(line.lstrip())]
                break
        
        # Insert the initialization call
        init_line = f"\n{indent}# Initialize {extension_id} extension\n{indent}{init_function}()"
        new_content = content[:insert_pos] + init_line + content[insert_pos:]
        
        # Write back the updated content
        with open(main_py_path, 'w') as f:
            f.write(new_content)
        
        log_info(f"Added initialization call to {main_py_path}")
    
    log_success("Backend extension registration complete")
    return True

def register_frontend_extension(manifest, dry_run=False):
    """Update frontend extension registry"""
    if dry_run:
        log_info("[DRY RUN] Would update frontend extension registry")
        return True
    
    extension_id = manifest["id"]
    module_name = extension_id  # Frontend uses hyphenated names
    
    index_ts_path = os.path.join(FRONTEND_DIR, "src/lib/extensions/index.ts")
    
    if not os.path.exists(index_ts_path):
        log_error(f"Frontend extension registry not found at {index_ts_path}")
        return False
    
    # Generate a PascalCase name for the extension import
    import_name = "".join(word.capitalize() for word in module_name.split("-"))
    
    # Read existing index.ts
    with open(index_ts_path, 'r') as f:
        content = f.read()
    
    # Check if extension is already imported
    import_line = f"import * as {import_name} from './{module_name}';"
    if import_line in content:
        log_info("Extension already imported in frontend registry")
    else:
        # Find a good place to add the import
        import_section_end = content.find("\n\n", content.find("import "))
        if import_section_end == -1:
            import_section_end = content.find("interface ExtensionMetadata")
        
        if import_section_end == -1:
            log_warning("Could not determine where to add import, you need to manually add:")
            log_warning(f"  {import_line}")
            return False
        
        # Insert the import line
        new_content = content[:import_section_end] + f"\n{import_line}" + content[import_section_end:]
        
        # Write back the updated content
        with open(index_ts_path, 'w') as f:
            f.write(new_content)
        
        log_info(f"Added import to {index_ts_path}")
    
    # Check if extension is registered in the registry object
    registry_entry = f"'{module_name}': "
    
    if registry_entry in content:
        log_info("Extension already registered in frontend registry")
    else:
        # Find the registry object
        registry_start = content.find("const extensionsRegistry")
        if registry_start == -1:
            log_warning("Could not find extensionsRegistry, you need to manually add:")
            log_warning(f"  '{module_name}': {{\n    ...{import_name}.metadata,\n    component: {import_name}.default\n  }}")
            return False
        
        # Find the end of the registry object
        registry_obj_start = content.find("{", registry_start)
        registry_obj_end = content.find("};", registry_obj_start)
        
        if registry_obj_end == -1:
            log_warning("Could not determine where to add registry entry, you need to manually add:")
            log_warning(f"  '{module_name}': {{\n    ...{import_name}.metadata,\n    component: {import_name}.default\n  }}")
            return False
        
        # Determine the indentation level
        lines = content[registry_obj_start:registry_obj_end].split("\n")
        indent = "    "  # Default indentation
        for line in lines:
            if line.strip() and ":" in line:
                indent = line[:len(line) - len(line.lstrip())]
                break
        
        # Insert the registry entry
        registry_entry = f"{indent}'{module_name}': {{\n{indent}    ...{import_name}.metadata,\n{indent}    component: {import_name}.default\n{indent}}},\n"
        new_content = content[:registry_obj_end] + registry_entry + content[registry_obj_end:]
        
        # Write back the updated content
        with open(index_ts_path, 'w') as f:
            f.write(new_content)
        
        log_info(f"Added registry entry to {index_ts_path}")
    
    # Check if extension is exported
    export_line = f"{import_name},"
    
    export_section = content.find("export {")
    if export_section != -1:
        export_section_end = content.find("}", export_section)
        exports = content[export_section:export_section_end]
        
        if export_line in exports:
            log_info("Extension already exported in frontend registry")
        else:
            # Find a good place to add the export
            new_content = content[:export_section_end] + f" {export_line}" + content[export_section_end:]
            
            # Write back the updated content
            with open(index_ts_path, 'w') as f:
                f.write(new_content)
            
            log_info(f"Added export to {index_ts_path}")
    
    log_success("Frontend extension registration complete")
    return True

def main():
    """Main entry point"""
    args = parse_args()
    
    # Validate package file
    if not os.path.exists(args.package):
        log_error(f"Package file not found: {args.package}")
        return 1
    
    if not args.package.endswith('.zip'):
        log_error(f"Package file must be a zip file: {args.package}")
        return 1
    
    # Check for basic realm structure
    if not os.path.isdir(BACKEND_DIR):
        log_error(f"Realm backend directory not found: {BACKEND_DIR}")
        return 1
    
    if not os.path.isdir(FRONTEND_DIR):
        log_error(f"Realm frontend directory not found: {FRONTEND_DIR}")
        return 1
    
    # Print header
    print(f"\n{Colors.HEADER}{Colors.BOLD}Smart Social Contracts Extension Installer{Colors.RESET}")
    print(f"Package: {args.package}")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Mode: {'Dry run (no changes will be made)' if args.dry_run else 'Live installation'}")
    print("-" * 50)
    
    # Create a temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the package
        if not extract_package(args.package, temp_dir):
            return 1
        
        # Read the manifest
        manifest = read_manifest(temp_dir)
        if not manifest:
            return 1
        
        extension_id = manifest.get("id")
        if not extension_id:
            log_error("Extension ID not specified in manifest.json")
            return 1
        
        log_info(f"Installing extension: {manifest.get('name', extension_id)} (ID: {extension_id})")
        
        # Install backend
        if not install_backend(temp_dir, manifest, args.dry_run):
            return 1
        
        # Install frontend
        if not install_frontend(temp_dir, manifest, args.dry_run):
            log_warning("Frontend installation had issues, but continuing")
        
        # Register extension in code (unless skipped)
        if not args.skip_register and not args.dry_run:
            if not register_backend_extension(manifest, args.dry_run):
                log_warning("Backend registration had issues, manual steps required")
            
            if not register_frontend_extension(manifest, args.dry_run):
                log_warning("Frontend registration had issues, manual steps required")
    
    # Print success message
    print("\n" + "-" * 50)
    log_success(f"Extension {manifest.get('name', extension_id)} installed successfully!")
    
    if not args.dry_run:
        print(f"\n{Colors.BOLD}Next steps:{Colors.RESET}")
        print("1. Review the changes to ensure they meet your requirements")
        print("2. Build and deploy the updated canisters:")
        print("   dfx deploy realm_backend --network local")
        print("   dfx deploy realm_frontend --network local")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
