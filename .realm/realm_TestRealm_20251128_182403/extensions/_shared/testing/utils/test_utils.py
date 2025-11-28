#!/usr/bin/env python3
"""
Shared utility functions for Realms extension testing.

This module provides common testing utilities that can be used across
all extension test suites, including:
- Command execution helpers
- Realm extension API calls
- GGG entity queries
- ICRC token operations
- Test identity management
- Output formatting
"""

import json
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

# Terminal colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
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


def print_info(message: str):
    """Print an info message with blue icon."""
    print(f"{BLUE}ℹ {message}{RESET}")


def run_command(command: str, capture_output: bool = True) -> Optional[str]:
    """
    Run a shell command and return its output.

    Args:
        command: Shell command to execute
        capture_output: Whether to capture output

    Returns:
        Command output as string, or None if command failed
    """
    print_info(f"Running: {command}")
    process = subprocess.run(
        command, shell=True, capture_output=capture_output, text=True
    )
    if process.returncode != 0:
        print_error(f"Command failed: {command}")
        if capture_output:
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
    """
    Get the canister ID for the given canister name.

    Args:
        canister_name: Name of the canister

    Returns:
        Canister ID string, or None if not found
    """
    result = run_command(f"dfx canister id {canister_name}")
    if not result:
        print_error(f"Failed to get ID of canister {canister_name}")
        return None
    return result


def get_current_principal() -> Optional[str]:
    """
    Get the principal ID of the current identity.

    Returns:
        Principal ID string, or None if failed
    """
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
        f"dfx canister call realm_backend call_extension "
        f'\'("{extension_name}", "{method_name}", "{escaped_args}")\' '
        f"--output json"
    )

    result = run_command_json(command)
    if not result:
        return None

    # The response is nested: result["data"]["extension_response"]
    # which itself contains JSON that needs parsing
    if "data" in result and "extension_response" in result["data"]:
        extension_response_str = result["data"]["extension_response"]
        try:
            return json.loads(extension_response_str)
        except json.JSONDecodeError:
            print_error(f"Failed to parse extension response: {extension_response_str}")
            return None

    return result


def query_ggg_entities(
    entity_type: str, page_num: int = 0, page_size: int = 100, order: str = "desc"
) -> Optional[Dict[str, Any]]:
    """
    Query ggg entities using the realm backend API.

    Args:
        entity_type: Entity type name (e.g., "Transfer", "Balance", "User")
        page_num: Page number (0-indexed)
        page_size: Number of items per page
        order: Sort order ("asc" or "desc")

    Returns:
        Dict with items list and pagination info, or None if failed
    """
    command = (
        f"dfx canister call realm_backend list_objects_paginated "
        f'\'("{entity_type}", {page_num}, {page_size}, "{order}")\' '
        f"--output json"
    )

    return run_command_json(command)


def send_icrc_tokens(
    ledger_id: str,
    to_principal: str,
    amount: int,
    identity: Optional[str] = None,
) -> Optional[int]:
    """
    Send ICRC tokens from current identity to a principal.

    Args:
        ledger_id: Ledger canister ID
        to_principal: Destination principal
        amount: Amount to send
        identity: Optional dfx identity to use

    Returns:
        Transaction ID if successful, None otherwise
    """
    identity_arg = f"--identity {identity}" if identity else ""

    transfer_arg = (
        f"(record {{"
        f"  to = record {{"
        f'    owner = principal "{to_principal}";'
        f"    subaccount = null;"
        f"  }};"
        f"  amount = {amount};"
        f"  fee = null;"
        f"  memo = null;"
        f"  from_subaccount = null;"
        f"  created_at_time = null;"
        f"}})"
    )

    command = (
        f"dfx {identity_arg} canister call --output json "
        f"{ledger_id} icrc1_transfer '{transfer_arg}'"
    )

    result = run_command_json(command)
    if not result:
        return None

    if "Ok" in result:
        tx_id = int(result["Ok"])
        return tx_id
    else:
        error = result.get("Err", "Unknown error")
        print_error(f"Transfer failed: {json.dumps(error, indent=2)}")
        return None


def check_icrc_balance(ledger_id: str, principal: str) -> Optional[int]:
    """
    Check ICRC token balance for a principal.

    Args:
        ledger_id: Ledger canister ID
        principal: Principal to check balance for

    Returns:
        Balance amount, or None if check failed
    """
    balance_arg = (
        f"(record {{"
        f'  owner = principal "{principal}";'
        f"  subaccount = null;"
        f"}})"
    )

    command = (
        f"dfx canister call --output json "
        f"{ledger_id} icrc1_balance_of '{balance_arg}'"
    )

    result = run_command(command)
    if not result:
        return None

    try:
        # Response is just a number in JSON format
        balance_str = result.strip().strip('"')
        balance = int(balance_str.replace("_", ""))
        return balance
    except (ValueError, json.JSONDecodeError) as e:
        print_error(f"Failed to parse balance: {e}")
        return None


def create_test_identities(identity_names: List[str]) -> Dict[str, str]:
    """
    Create test dfx identities.

    Args:
        identity_names: List of identity names to create

    Returns:
        Dictionary mapping identity names to their principal IDs
    """
    identities = {}
    current_identity = run_command("dfx identity whoami")

    try:
        for name in identity_names:
            # Create identity if needed
            existing = run_command("dfx identity list")
            if existing and name not in existing.split():
                run_command(f"dfx identity new --disable-encryption {name}")

            # Get principal ID
            run_command(f"dfx identity use {name}")
            principal = get_current_principal()

            if principal:
                identities[name] = principal
                print_info(f"{name}: {principal}")
    finally:
        if current_identity:
            run_command(f"dfx identity use {current_identity}")

    return identities


def wait_for_canister_ready(
    canister_name: str, max_attempts: int = 30, delay: int = 2
) -> bool:
    """
    Wait for a canister to be ready by attempting to query its status.

    Args:
        canister_name: Name of the canister to check
        max_attempts: Maximum number of retry attempts
        delay: Delay in seconds between attempts

    Returns:
        True if canister is ready, False if timeout
    """
    import time

    for attempt in range(max_attempts):
        try:
            result = run_command(f"dfx canister status {canister_name}")
            if result and "Running" in result:
                print_ok(f"Canister {canister_name} is ready")
                return True
        except Exception:
            pass

        if attempt < max_attempts - 1:
            print_info(
                f"Waiting for {canister_name} to be ready... ({attempt + 1}/{max_attempts})"
            )
            time.sleep(delay)

    print_error(f"Canister {canister_name} did not become ready within timeout")
    return False


def validate_json_response(data: dict, expected_keys: list, context: str) -> bool:
    """
    Validate that JSON response has expected structure.

    Args:
        data: JSON data to validate
        expected_keys: List of required keys
        context: Context string for error messages

    Returns:
        True if all expected keys present, False otherwise
    """
    for key in expected_keys:
        if key not in data:
            print_warning(f"Missing key '{key}' in {context}")
            return False
    return True
