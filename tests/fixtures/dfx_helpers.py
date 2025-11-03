#!/usr/bin/env python3
"""Helper utilities for dfx canister calls."""

import json
import subprocess
from typing import Tuple


def dfx_call(
    canister: str, method: str, args: str = "()", output_json: bool = False
) -> Tuple[str, int]:
    """Call a canister method via dfx.
    
    Args:
        canister: Canister name (e.g., "realm_backend")
        method: Method name to call
        args: Candid-encoded arguments
        output_json: Whether to use --output json flag
        
    Returns:
        Tuple of (stdout, exit_code)
    """
    cmd = ["dfx", "canister", "call", canister, method]
    if args:
        cmd.append(args)
    cmd.append("--query")  # Most realm_backend methods are queries
    if output_json:
        cmd.extend(["--output", "json"])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout, result.returncode


def dfx_call_json(canister: str, method: str, args: str = "()") -> dict:
    """Call a canister method and parse JSON response.
    
    Args:
        canister: Canister name
        method: Method name to call
        args: Candid-encoded arguments
        
    Returns:
        Parsed JSON response
        
    Raises:
        RuntimeError: If call fails or JSON parsing fails
    """
    output, code = dfx_call(canister, method, args, output_json=True)
    
    if code != 0:
        raise RuntimeError(f"dfx call failed with code {code}: {output}")
    
    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON response: {e}\nOutput: {output}")


def assert_success(output: str, message: str = "") -> None:
    """Assert that dfx call was successful.
    
    Args:
        output: Output from dfx call
        message: Optional error message
        
    Raises:
        AssertionError: If call was not successful
    """
    # Check for JSON success field or Candid success = true
    if '"success": true' not in output and "success = true" not in output:
        error_msg = f"Expected successful call{': ' + message if message else ''}"
        error_msg += f"\nGot output: {output}"
        raise AssertionError(error_msg)


def assert_contains(output: str, substring: str, message: str = "") -> None:
    """Assert that output contains substring.
    
    Args:
        output: Output to check
        substring: Substring to find
        message: Optional error message
        
    Raises:
        AssertionError: If substring not found
    """
    if substring not in output:
        error_msg = f"Expected '{substring}' in output{': ' + message if message else ''}"
        error_msg += f"\nGot output: {output}"
        raise AssertionError(error_msg)
