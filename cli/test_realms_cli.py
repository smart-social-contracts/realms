#!/usr/bin/env python3
"""Test script for Realms CLI functionality."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Add the cli directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from realms_cli.main import app
    from realms_cli.models import RealmConfig
    from realms_cli.utils import load_config, save_config
except ImportError as e:
    print(f"❌ Failed to import realms_cli modules: {e}")
    print("Make sure to install the package first: cd cli && pip install -e .")
    sys.exit(1)


def test_cli_help():
    """Test CLI help command."""
    print("🧪 Testing CLI help...")
    try:
        # Test CLI installation and help command
        result = subprocess.run(
            [sys.executable, "-m", "realms_cli.main", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and "realms" in result.stdout.lower():
            print("✅ CLI help command works")
            return True
        else:
            print(f"❌ CLI help failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ CLI help failed: {e}")
        return False


def test_config_validation():
    """Test configuration validation."""
    print("🧪 Testing configuration validation...")

    # Test valid configuration
    valid_config = {
        "realm": {
            "id": "test_realm",
            "name": "Test Realm",
            "description": "A test realm for validation",
            "admin_principal": "2vxsx-fae",
        },
        "deployment": {"network": "local"},
        "extensions": {"initial": [{"name": "demo_loader", "enabled": True}]},
    }

    try:
        config = RealmConfig(**valid_config)
        print(f"✅ Valid config parsed: {config.realm.name}")
        return True
    except Exception as e:
        print(f"❌ Config validation failed: {e}")
        return False


def test_config_file_operations():
    """Test configuration file operations."""
    print("🧪 Testing config file operations...")

    test_config = {
        "realm": {
            "id": "file_test",
            "name": "File Test Realm",
            "description": "Testing file operations",
            "admin_principal": "2vxsx-fae",
        },
        "deployment": {"network": "local"},
    }

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_path = f.name

        # Test save
        save_config(test_config, config_path)

        # Test load
        loaded_config = load_config(config_path)

        # Cleanup
        os.unlink(config_path)

        if loaded_config["realm"]["id"] == "file_test":
            print("✅ Config file operations successful")
            return True
        else:
            print("❌ Config file data mismatch")
            return False

    except Exception as e:
        print(f"❌ Config file operations failed: {e}")
        return False


def test_project_scaffolding():
    """Test project scaffolding logic."""
    print("🧪 Testing project scaffolding...")

    try:
        from realms_cli.commands.init import (
            _get_dfx_json_template,
            _get_readme_template,
        )

        # Test template generation
        dfx_json = _get_dfx_json_template("test_realm")
        readme = _get_readme_template("Test Realm", "test_realm")

        # Check if templates contain expected content
        dfx_contains_realm = "test_realm" in dfx_json or "realm_backend" in dfx_json
        readme_contains_name = "Test Realm" in readme or "test_realm" in readme

        if dfx_contains_realm and readme_contains_name:
            print("✅ Project scaffolding templates work")
            return True
        else:
            print(
                f"❌ Template validation failed - dfx: {dfx_contains_realm}, readme: {readme_contains_name}"
            )
            return False

    except Exception as e:
        print(f"❌ Project scaffolding test failed: {e}")
        return False


def test_realm_generator_parameters():
    """Test that realm_generator correctly uses members parameter."""
    print("🧪 Testing realm generator parameters...")
    
    try:
        scripts_path = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_path))
        from realm_generator import RealmGenerator
        
        # Test that members parameter is correctly used
        generator = RealmGenerator(seed=42)
        test_data = generator.generate_realm_data(members=10, organizations=2)
        
        # Count users (should be 10 + 1 system user = 11)
        users = [item for item in test_data if hasattr(item, '__class__') and item.__class__.__name__ == 'User']
        
        if len(users) == 11:  # 10 members + 1 system user
            print(f"✅ Realm generator correctly uses members parameter (10 members + 1 system user = {len(users)} users)")
            return True
        else:
            print(f"❌ Expected 11 users, got {len(users)}")
            return False
            
    except Exception as e:
        print(f"❌ Realm generator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("🏛️  Realms CLI Test Suite\n")

    tests = [
        test_cli_help,
        test_config_validation,
        test_config_file_operations,
        test_project_scaffolding,
        test_realm_generator_parameters,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Realms CLI is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
