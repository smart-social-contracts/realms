#!/usr/bin/env python3
"""Helper utilities for dfx canister calls."""

import json
import subprocess
from typing import Tuple


def dfx_call(
    canister: str, method: str, args: str = "()", output_json: bool = False, is_update: bool = False
) -> Tuple[str, int]:
    """Call a canister method via dfx.
    
    Args:
        canister: Canister name (e.g., "realm_backend")
        method: Method name to call
        args: Candid-encoded arguments
        output_json: Whether to use --output json flag
        is_update: Whether this is an update call (default: query)
        
    Returns:
        Tuple of (stdout, exit_code)
    """
    cmd = ["dfx", "canister", "call", canister, method]
    if args:
        cmd.append(args)
    if not is_update:
        cmd.append("--query")  # Most realm_backend methods are queries
    if output_json:
        cmd.extend(["--output", "json"])
    
    # Log the full command
    cmd_str = " ".join(cmd)
    print(f"    [DFX CMD] {cmd_str}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Log exit code
    print(f"    [DFX EXIT CODE] {result.returncode}")
    
    # Log output length and first part of output
    output_preview = result.stdout[:200] if result.stdout else "(empty)"
    print(f"    [DFX STDOUT] {len(result.stdout)} bytes: {output_preview}{'...' if len(result.stdout) > 200 else ''}")
    
    # Log stderr if present
    if result.stderr:
        stderr_preview = result.stderr[:200]
        print(f"    [DFX STDERR] {stderr_preview}{'...' if len(result.stderr) > 200 else ''}")
    
    return result.stdout, result.returncode


def dfx_call_json(canister: str, method: str, args: str = "()", is_update: bool = False) -> dict:
    """Call a canister method and parse JSON response.
    
    Args:
        canister: Canister name
        method: Method name to call
        args: Candid-encoded arguments
        is_update: Whether this is an update call (default: query)
        
    Returns:
        Parsed JSON response
        
    Raises:
        RuntimeError: If call fails or JSON parsing fails
    """
    print(f"    [DFX JSON CALL] {canister}.{method}({args})")
    output, code = dfx_call(canister, method, args, output_json=True, is_update=is_update)
    
    if code != 0:
        print(f"    [ERROR] dfx call failed with exit code {code}")
        raise RuntimeError(f"dfx call failed with code {code}: {output}")
    
    try:
        parsed = json.loads(output)
        print(f"    [JSON PARSED] Successfully parsed JSON response")
        return parsed
    except json.JSONDecodeError as e:
        print(f"    [ERROR] JSON parsing failed: {e}")
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
