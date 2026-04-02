#!/usr/bin/env python3
"""Helper utilities for icp canister calls."""

import json
import re
import subprocess
from typing import Tuple


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


def _extract_json_from_candid(output: str) -> str:
    """Extract JSON string from Candid text output.

    icp canister call returns Candid text like:
        ("{\\"success\\":true,...}")
    or:
        (record { ... })
    This extracts the inner JSON string if present.
    """
    # Try to find a JSON string inside Candid text (quoted with escaped quotes)
    # Pattern: look for content between outer quotes that contains JSON
    # The Candid output has backslash-escaped quotes inside strings
    match = re.search(r'"((?:\\.|[^"\\])*)"', output)
    if match:
        raw = match.group(1)
        # Unescape Candid string escapes
        unescaped = raw.replace('\\"', '"').replace('\\\\', '\\')
        return unescaped
    return output


def dfx_call_json(
    canister: str, method: str, args: str = "()", is_update: bool = False
) -> dict:
    """Call a canister method and parse JSON response.

    Gets Candid text output and extracts JSON from it, since
    icp --json outputs CLI metadata, not the canister response.

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
    print(f"    [ICP JSON CALL] {canister}.{method}({args})")
    output, code = dfx_call(
        canister, method, args, output_json=False, is_update=is_update
    )

    if code != 0:
        print(f"    [ERROR] icp call failed with exit code {code}")
        raise RuntimeError(f"icp call failed with code {code}: {output}")

    # Extract JSON from Candid text output
    json_str = _extract_json_from_candid(output)

    try:
        parsed = json.loads(json_str)
        print(f"    [JSON PARSED] Successfully parsed JSON response")
        return parsed
    except json.JSONDecodeError as e:
        print(f"    [ERROR] JSON parsing failed: {e}")
        print(f"    [DEBUG] Extracted string: {json_str[:200]}")
        raise RuntimeError(f"Failed to parse JSON response: {e}\nOutput: {output}")


def assert_success(output: str, message: str = "") -> None:
    """Assert that icp call was successful.

    Args:
        output: Output from icp call (Candid text format)
        message: Optional error message

    Raises:
        AssertionError: If call was not successful
    """
    # Check multiple formats: Candid escaped, JSON, Candid record
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
        error_msg = (
            f"Expected '{substring}' in output{': ' + message if message else ''}"
        )
        error_msg += f"\nGot output: {output}"
        raise AssertionError(error_msg)
