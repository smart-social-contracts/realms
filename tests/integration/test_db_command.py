#!/usr/bin/env python3
"""Integration tests for realms db command.

Tests the interactive database explorer command by running it programmatically.
These tests verify that the db command can connect to the deployed realm
and explore entities.
"""

import subprocess
import sys
import time
import traceback


def run_command(cmd, input_data=None, timeout=10):
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


def test_db_command_help():
    """Test db command help output."""
    print("🧪 Testing: db --help")

    stdout, stderr, code = run_command("realms db --help")

    assert code == 0, f"db --help failed with code {code}"
    assert (
        "database" in stdout.lower() or "explore" in stdout.lower()
    ), "Help output missing database/explore information"

    print("✅ PASSED: db --help works")


def test_db_command_starts():
    """Test that db command can start and display entity list."""
    print("🧪 Testing: db command startup")

    # Send 'q' immediately to quit the interactive interface
    stdout, stderr, code = run_command("realms db", input_data="q\n", timeout=15)

    # The command should exit cleanly when 'q' is pressed
    # Code might be 0 or 1 depending on how curses exits
    assert code in [0, 1], f"db command failed with unexpected code {code}"

    # Check for entity type names in output (the db explorer shows these)
    entity_types = ["User", "Organization", "Mandate", "Transfer"]
    found_entities = any(entity in stdout for entity in entity_types)

    assert (
        found_entities
    ), f"db command output missing entity types. Output:\n{stdout}\nStderr:\n{stderr}"

    print("✅ PASSED: db command starts and displays entities")


def test_db_command_with_network_option():
    """Test db command with network option."""
    print("🧪 Testing: db --network local")

    # Send 'q' to quit immediately
    stdout, stderr, code = run_command(
        "realms db --network local", input_data="q\n", timeout=15
    )

    assert code in [0, 1], f"db --network local failed with code {code}"

    # Should show entity explorer
    assert (
        "User" in stdout or "Organization" in stdout
    ), f"db command with network option failed. Output:\n{stdout}\nStderr:\n{stderr}"

    print("✅ PASSED: db --network option works")


def test_db_command_shows_counts():
    """Test that db command shows entity counts."""
    print("🧪 Testing: db command shows entity counts")

    # Send 'q' to quit
    stdout, stderr, code = run_command("realms db", input_data="q\n", timeout=15)

    assert code in [0, 1], f"db command failed with code {code}"

    # Should show entity counts in format like "User (10)" or "Organization (5)"
    # Even if counts are 0, they should be displayed
    has_counts = "(" in stdout and ")" in stdout

    assert has_counts, f"db command output missing entity counts. Output:\n{stdout}"

    print("✅ PASSED: db command shows entity counts")


def main():
    """Run all db command tests."""
    print("=" * 60)
    print("DB Command Integration Tests")
    print("=" * 60)
    print()

    tests = [
        test_db_command_help,
        test_db_command_starts,
        test_db_command_with_network_option,
        test_db_command_shows_counts,
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
        print("✅ All db command tests passed!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
