#!/usr/bin/env python3
"""Integration tests for realms shell and realms run commands.

Tests the Python shell/execution commands by running simple Python code
that interacts with the deployed realm backend.
"""

import os
import subprocess
import sys
import tempfile
import traceback


def run_command(cmd, input_data=None, timeout=30):
    """Run a command and return output, error, and exit code."""
    try:
        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True if isinstance(cmd, str) else False,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timeout", 124


def test_shell_command_help():
    """Test shell command help output."""
    print("🧪 Testing: shell --help")
    
    stdout, stderr, code = run_command("realms shell --help")
    
    assert code == 0, f"shell --help failed with code {code}"
    assert "shell" in stdout.lower() or "interactive" in stdout.lower(), \
        "Help output missing shell/interactive information"
    
    print("✅ PASSED: shell --help works")


def test_run_command_help():
    """Test run command help output."""
    print("🧪 Testing: run --help")
    
    stdout, stderr, code = run_command("realms run --help")
    
    assert code == 0, f"run --help failed with code {code}"
    assert "shell" in stdout.lower() or "execute" in stdout.lower(), \
        "Help output missing shell/execute information"
    
    print("✅ PASSED: run --help works")


def test_run_command_with_simple_code():
    """Test run command with simple Python code execution."""
    print("🧪 Testing: run --file with simple code")
    
    # Create a temporary Python file with simple code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
# Simple test to verify Python execution
result = 2 + 2
# Code executes in canister - no direct print output
""")
        temp_file = f.name
    
    try:
        stdout, stderr, code = run_command(f"realms run --file {temp_file}")
        
        assert code == 0, f"run --file failed with code {code}. Stderr: {stderr}"
        # Check for successful execution indicator
        assert "Successfully executed" in stdout, \
            f"Expected success message not found. Output:\n{stdout}\nStderr:\n{stderr}"
        # Check for JSON response indicating code was executed
        assert '"status":' in stdout or 'status' in stdout, \
            f"Expected status in output. Output:\n{stdout}"
        
        print("✅ PASSED: run --file executes simple code")
    finally:
        os.unlink(temp_file)


def test_run_command_with_ggg_imports():
    """Test run command can import GGG entities."""
    print("🧪 Testing: run --file with GGG imports")
    
    # Create a temporary Python file that imports GGG entities
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
# Test GGG entity imports - code runs in canister
from ggg.user import User
from ggg.organization import Organization
# If imports fail, execution will error out
user_class_name = User.__name__
org_class_name = Organization.__name__
""")
        temp_file = f.name
    
    try:
        stdout, stderr, code = run_command(f"realms run --file {temp_file}", timeout=45)
        
        assert code == 0, f"run --file with GGG imports failed with code {code}. Stderr: {stderr}"
        # Check for successful execution - if imports failed, command would have errored
        assert "Successfully executed" in stdout, \
            f"GGG imports failed - no success message. Output:\n{stdout}\nStderr:\n{stderr}"
        assert '"status":' in stdout or 'status' in stdout, \
            f"Expected status in output. Output:\n{stdout}"
        
        print("✅ PASSED: run --file can import GGG entities")
    finally:
        os.unlink(temp_file)


def test_run_command_with_entity_query():
    """Test run command can query entities from the deployed realm."""
    print("🧪 Testing: run --file with entity query")
    
    # Create a temporary Python file that queries entities
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
# Test entity querying - code runs in canister
from ggg.user import User

# Try to load users - this tests database connectivity
users = User.load_all()
# If query fails, execution will error out
user_count = len(users)
""")
        temp_file = f.name
    
    try:
        stdout, stderr, code = run_command(f"realms run --file {temp_file}", timeout=45)
        
        assert code == 0, f"run --file with entity query failed with code {code}. Stderr: {stderr}"
        # Check for successful execution - if query failed, command would have errored
        assert "Successfully executed" in stdout, \
            f"Entity query failed - no success message. Output:\n{stdout}\nStderr:\n{stderr}"
        assert '"status":' in stdout or 'status' in stdout, \
            f"Expected status in output. Output:\n{stdout}"
        
        print("✅ PASSED: run --file can query entities")
    finally:
        os.unlink(temp_file)


def test_run_command_with_network_option():
    """Test run command with network option."""
    print("🧪 Testing: run --network local --file")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('# Test network option\nresult = 1 + 1\n')
        temp_file = f.name
    
    try:
        stdout, stderr, code = run_command(f"realms run --network local --file {temp_file}")
        
        assert code == 0, f"run --network failed with code {code}. Stderr: {stderr}"
        assert "Successfully executed" in stdout, \
            f"Expected success message not found. Output:\n{stdout}"
        
        print("✅ PASSED: run --network option works")
    finally:
        os.unlink(temp_file)


def test_shell_interactive_mode_exits():
    """Test that shell command can start and exit gracefully."""
    print("🧪 Testing: shell interactive mode startup/exit")
    
    # Send 'exit()' to quit the interactive shell
    stdout, stderr, code = run_command("realms shell", input_data="exit()\n", timeout=20)
    
    # Code 0 or 1 is acceptable (depends on how the shell exits)
    assert code in [0, 1], f"shell command failed with unexpected code {code}. Stderr: {stderr}"
    
    # Should show Python shell prompt or startup message
    shell_indicators = [">>>", "Python", "InteractiveConsole"]
    has_shell = any(indicator in stdout or indicator in stderr for indicator in shell_indicators)
    
    # If we don't see shell indicators, at least it shouldn't crash
    if not has_shell:
        print("⚠️  WARNING: Shell indicators not found, but command didn't crash")
    
    print("✅ PASSED: shell command starts and exits")


def main():
    """Run all shell/run command tests."""
    print("=" * 60)
    print("Shell/Run Command Integration Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_shell_command_help,
        test_run_command_help,
        test_run_command_with_simple_code,
        test_run_command_with_ggg_imports,
        test_run_command_with_entity_query,
        test_run_command_with_network_option,
        test_shell_interactive_mode_exits,
    ]
    
    failed = 0
    
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            print(f"    Traceback:")
            traceback.print_exc()
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            print(f"    Traceback:")
            traceback.print_exc()
            failed += 1
        print()
    
    print("=" * 60)
    if failed == 0:
        print("✅ All shell/run command tests passed!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
