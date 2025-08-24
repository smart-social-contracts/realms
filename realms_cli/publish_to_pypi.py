#!/usr/bin/env python3
"""
Script to publish Realms CLI to PyPI.

This script handles the complete publishing workflow:
1. Version management
2. Building the package
3. Publishing to Test PyPI (optional)
4. Publishing to PyPI
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Optional

def get_current_version() -> str:
    """Get current version from pyproject.toml."""
    pyproject_path = Path("realms_cli/pyproject.toml")
    
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found")
    
    with open(pyproject_path, 'r') as f:
        content = f.read()
    
    # Simple version extraction
    for line in content.split('\n'):
        if line.strip().startswith('version = '):
            return line.split('"')[1]
    
    raise ValueError("Version not found in pyproject.toml")

def update_version(new_version: str) -> None:
    """Update version in pyproject.toml and __init__.py."""
    
    # Update pyproject.toml
    pyproject_path = Path("realms_cli/pyproject.toml")
    with open(pyproject_path, 'r') as f:
        content = f.read()
    
    # Replace version line
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith('version = '):
            lines[i] = f'version = "{new_version}"'
            break
    
    with open(pyproject_path, 'w') as f:
        f.write('\n'.join(lines))
    
    # Update __init__.py
    init_path = Path("realms_cli/__init__.py")
    with open(init_path, 'w') as f:
        f.write(f'"""Realms CLI - A tool for managing Realms project lifecycle."""\n\n__version__ = "{new_version}"\n')
    
    print(f"✅ Updated version to {new_version}")

def run_tests() -> bool:
    """Run tests before publishing."""
    print("🧪 Running tests...")
    
    try:
        # Run our custom test suite
        result = subprocess.run([
            sys.executable, "test_realms_cli.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Tests passed")
            return True
        else:
            print(f"❌ Tests failed: {result.stdout}")
            return False
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False

def build_package() -> bool:
    """Build the package."""
    print("📦 Building package...")
    
    try:
        # Clean previous builds
        dist_dir = Path("realms_cli/dist")
        if dist_dir.exists():
            import shutil
            shutil.rmtree(dist_dir)
        
        # Build package
        result = subprocess.run([
            sys.executable, "-m", "build"
        ], cwd="realms_cli", capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Package built successfully")
            return True
        else:
            print(f"❌ Build failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Build error: {e}")
        return False

def check_package() -> bool:
    """Check package with twine."""
    print("🔍 Checking package...")
    
    try:
        result = subprocess.run([
            "twine", "check", "dist/*"
        ], cwd="realms_cli", capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Package check passed")
            return True
        else:
            print(f"❌ Package check failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Package check error: {e}")
        return False

def publish_to_test_pypi() -> bool:
    """Publish to Test PyPI."""
    print("🚀 Publishing to Test PyPI...")
    
    try:
        result = subprocess.run([
            "twine", "upload", "--repository", "testpypi", "dist/*"
        ], cwd="realms_cli")
        
        if result.returncode == 0:
            print("✅ Published to Test PyPI successfully")
            print("🔗 Check: https://test.pypi.org/project/realms-cli/")
            return True
        else:
            print("❌ Test PyPI upload failed")
            return False
            
    except Exception as e:
        print(f"❌ Test PyPI upload error: {e}")
        return False

def publish_to_pypi() -> bool:
    """Publish to PyPI."""
    print("🚀 Publishing to PyPI...")
    
    try:
        result = subprocess.run([
            "twine", "upload", "dist/*"
        ], cwd="realms_cli")
        
        if result.returncode == 0:
            print("✅ Published to PyPI successfully")
            print("🔗 Check: https://pypi.org/project/realms-cli/")
            return True
        else:
            print("❌ PyPI upload failed")
            return False
            
    except Exception as e:
        print(f"❌ PyPI upload error: {e}")
        return False

def create_git_tag(version: str) -> None:
    """Create git tag for the version."""
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"Release v{version}"], check=True)
        subprocess.run(["git", "tag", f"v{version}"], check=True)
        print(f"✅ Created git tag v{version}")
    except subprocess.CalledProcessError:
        print("⚠️  Git operations failed (this is okay if not in a git repo)")

def main():
    """Main publishing workflow."""
    print("📦 Realms CLI Publishing Workflow\n")
    
    # Check if we're in the right directory
    if not Path("realms_cli").exists():
        print("❌ Please run this script from the project root directory")
        return 1
    
    # Get current version
    try:
        current_version = get_current_version()
        print(f"Current version: {current_version}")
    except Exception as e:
        print(f"❌ Failed to get current version: {e}")
        return 1
    
    # Ask for new version
    new_version = input(f"Enter new version (current: {current_version}): ").strip()
    if not new_version:
        new_version = current_version
        print(f"Using current version: {current_version}")
    
    # Update version if changed
    if new_version != current_version:
        update_version(new_version)
    
    # Run tests
    if not run_tests():
        print("❌ Tests failed, aborting publish")
        return 1
    
    # Build package
    if not build_package():
        print("❌ Build failed, aborting publish")
        return 1
    
    # Check package
    if not check_package():
        print("❌ Package check failed, aborting publish")
        return 1
    
    # Ask about Test PyPI
    test_pypi = input("Publish to Test PyPI first? (y/N): ").strip().lower()
    if test_pypi in ['y', 'yes']:
        if not publish_to_test_pypi():
            print("❌ Test PyPI publish failed")
            return 1
        
        # Ask to continue
        continue_to_pypi = input("Continue to PyPI? (y/N): ").strip().lower()
        if continue_to_pypi not in ['y', 'yes']:
            print("✅ Stopped at Test PyPI")
            return 0
    
    # Publish to PyPI
    pypi_confirm = input(f"Publish v{new_version} to PyPI? (y/N): ").strip().lower()
    if pypi_confirm not in ['y', 'yes']:
        print("❌ Publish cancelled")
        return 1
    
    if not publish_to_pypi():
        print("❌ PyPI publish failed")
        return 1
    
    # Create git tag
    create_git_tag(new_version)
    
    print(f"\n🎉 Successfully published Realms CLI v{new_version} to PyPI!")
    print("\n📋 Next steps:")
    print("1. Push git tags: git push --tags")
    print("2. Create GitHub release")
    print("3. Update documentation")
    print(f"4. Test installation: pip install realms-cli=={new_version}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
