#!/usr/bin/env python3
"""Helper utilities for icp canister calls."""

import json
import subprocess
from typing import Tuple

from fixtures.candid_parser import parse_candid


def dfx_call(
    canister: str,
    method: str,
    args: str = "()",
    output_json: bool = False,
    is_update: bool = False,
) -> Tuple[str, int]:
    """Call a canister method via icp.

    Args:
        canister: Canister name (e.g., "realm_backend")
        method: Method name to call
        args: Candid-encoded arguments
        output_json: Ignored (kept for API compat). Use dfx_call_json instead.
        is_update: Whether this is an update call (default: query)

    Returns:
        Tuple of (stdout, exit_code)
    """
    cmd = ["icp", "canister", "call", canister, method]
    if args:
        cmd.append(args)

    # Log the full command with proper quoting for args
    cmd_display = ["icp", "canister", "call", canister, method]
    if args:
        cmd_display.append(f'"{args}"')  # Add quotes around args for display
    cmd_str = " ".join(cmd_display)
    print(f"    [ICP CMD] {cmd_str}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Log exit code
    print(f"    [ICP EXIT CODE] {result.returncode}")

    # Log full stdout (no truncation)
    if result.stdout:
        print(f"    [ICP STDOUT] {len(result.stdout)} bytes:")
        print(result.stdout)
    else:
        print(f"    [ICP STDOUT] (empty)")

    # Log full stderr if present (no truncation)
    if result.stderr:
        print(f"    [ICP STDERR]:")
        print(result.stderr)

    return result.stdout, result.returncode


def dfx_call_json(
    canister: str, method: str, args: str = "()", is_update: bool = False
) -> dict:
    """Call a canister method and parse the response into a Python dict.

    Uses the Candid text parser to convert hash-based field names back
    to their original names.

    Args:
        canister: Canister name
        method: Method name to call
        args: Candid-encoded arguments
        is_update: Whether this is an update call (default: query)

    Returns:
        Parsed response as a Python dict

    Raises:
        RuntimeError: If call fails or parsing fails
    """
    print(f"    [ICP JSON CALL] {canister}.{method}({args})")
    output, code = dfx_call(
        canister, method, args, output_json=False, is_update=is_update
    )

    if code != 0:
        print(f"    [ERROR] icp call failed with exit code {code}")
        raise RuntimeError(f"icp call failed with code {code}: {output}")

    try:
        parsed = parse_candid(output)
        print(f"    [CANDID PARSED] Successfully parsed Candid response")
        if isinstance(parsed, dict):
            print(f"    [CANDID KEYS] {list(parsed.keys())[:10]}")
        return parsed
    except Exception as e:
        print(f"    [ERROR] Candid parsing failed: {e}")
        print(f"    [DEBUG] First 300 chars: {output[:300]}")
        raise RuntimeError(f"Failed to parse Candid response: {e}\nOutput: {output[:500]}")


def assert_success(output: str, message: str = "") -> None:
    """Assert that icp call was successful.

    Args:
        output: Output from icp call (Candid text format)
        message: Optional error message

    Raises:
        AssertionError: If call was not successful
    """
    # Try parsing the Candid output to check success field
    try:
        parsed = parse_candid(output)
        if isinstance(parsed, dict) and parsed.get("success") is True:
            return
    except Exception:
        pass

    # Fallback: text-based checks for various output formats
    lower = output.lower()
    if (
        '"success": true' in lower
        or '"success":true' in lower
        or '\\"success\\":true' in lower
        or '\\"success\\": true' in lower
        or "success = true" in lower
    ):
        return

    error_msg = f"Expected successful call{': ' + message if message else ''}"
    error_msg += f"\nGot output: {output[:500]}"
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
        error_msg = (
            f"Expected '{substring}' in output{': ' + message if message else ''}"
        )
        error_msg += f"\nGot output: {output}"
        raise AssertionError(error_msg)
