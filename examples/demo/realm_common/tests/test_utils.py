#!/usr/bin/env python3
"""
Utility functions for realm testing.
"""

import json
import subprocess
from typing import Any, Dict, Optional

# Terminal colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def print_ok(message: str):
    """Print a success message with green checkmark."""
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message: str):
    """Print an error message with red cross."""
    print(f"{RED}✗ {message}{RESET}")


def print_warning(message: str):
    """Print a warning message with yellow icon."""
    print(f"{YELLOW}⚠ {message}{RESET}")


def run_command(command: str, capture_output: bool = True) -> Optional[str]:
    """
    Run a shell command and return its output.

    Args:
        command: Shell command to execute
        capture_output: Whether to capture output

    Returns:
        Command output as string, or None if command failed
    """
    print(f"Running: {command}")
    process = subprocess.run(
        command, shell=True, capture_output=capture_output, text=True
    )
    if process.returncode != 0:
        print_error(f"Error executing command: {command}")
        print_error(f"Error: {process.stderr}")
        return None
    return process.stdout.strip() if capture_output else ""


def run_command_json(command: str) -> Optional[Dict[str, Any]]:
    """
    Run a command and parse JSON response.

    Args:
        command: Shell command to execute

    Returns:
        Parsed JSON dict, or None if command failed or response invalid
    """
    result = run_command(command)
    if not result:
        return None

    try:
        return json.loads(result)
    except json.JSONDecodeError as e:
        print_error(f"Failed to parse JSON response: {e}")
        print_error(f"Raw output: {result}")
        return None


def get_canister_id(canister_name: str) -> Optional[str]:
    """Get the canister ID for the given canister name."""
    result = run_command(f"dfx canister id {canister_name}")
    if not result:
        print_error(f"Failed to get ID of canister {canister_name}")
        return None
    return result


def get_current_principal() -> Optional[str]:
    """Get the principal ID of the current identity."""
    principal = run_command("dfx identity get-principal")
    if not principal:
        print_error("Failed to get principal")
        return None
    return principal


def call_realm_extension(
    extension_name: str, method_name: str, args: str = "{}"
) -> Optional[Dict[str, Any]]:
    """
    Call a method on a realm extension.

    Args:
        extension_name: Name of the extension (e.g., "vault")
        method_name: Method to call (e.g., "refresh")
        args: JSON string of arguments

    Returns:
        Parsed JSON response, or None if call failed
    """
    # Escape the JSON args for shell
    escaped_args = args.replace('"', '\\"')

    command = (
        f"dfx canister call realm_backend extension_async_call "
        f'\'(record {{ extension_name = "{extension_name}"; function_name = "{method_name}"; args = "{escaped_args}" }})\' '
        f"--output json"
    )

    result = run_command_json(command)
    if not result:
        return None

    # The response is in result["response"] as a JSON string
    if "response" in result:
        try:
            return json.loads(result["response"])
        except json.JSONDecodeError:
            print_error(f"Failed to parse extension response: {result['response']}")
            return None

    return result
