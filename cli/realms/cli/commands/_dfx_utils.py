"""Shared utilities for CLI commands that interact with dfx canisters.

Provides dfx command construction and Candid output parsing, used by
both ``shell.py`` and ``run.py`` to avoid code duplication.
"""

import ast
import re
import subprocess
from typing import Optional

from rich.console import Console

console = Console()


# ---------------------------------------------------------------------------
# dfx command helpers
# ---------------------------------------------------------------------------

def build_dfx_call_cmd(
    canister_name: str,
    method: str,
    args: str,
    network: Optional[str] = None,
    output_format: Optional[str] = None,
) -> list[str]:
    """Build a ``dfx canister call`` command list."""
    cmd = ["dfx", "canister", "call"]
    if network:
        cmd.extend(["--network", network])
    cmd.extend([canister_name, method, args])
    if output_format:
        cmd.extend(["--output", output_format])
    return cmd


def run_dfx_call(
    canister_name: str,
    method: str,
    args: str,
    network: Optional[str] = None,
    cwd: Optional[str] = None,
    output_format: Optional[str] = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Run a ``dfx canister call`` and return the CompletedProcess."""
    cmd = build_dfx_call_cmd(canister_name, method, args, network, output_format)
    return subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=cwd, timeout=timeout)


# ---------------------------------------------------------------------------
# Candid output parsing
# ---------------------------------------------------------------------------

def parse_candid_string_output(output: str) -> str:
    """Parse a Candid-encoded string response from dfx.

    Handles the various string representations:
    - Tuple format: (  "content"  )
    - List-in-tuple: ("['item1', 'item2']\\n",)
    - Standard format: ("content")

    Returns the decoded string content.
    """
    output = output.strip()

    # Remove trailing commas and parentheses for list detection
    cleaned_output = output.rstrip(",)").lstrip("(")

    # Check if it looks like a string representation of a list
    if cleaned_output.strip().startswith('"[') and (
        "\n" in cleaned_output or ']"' in cleaned_output
    ):
        list_str_match = re.search(r'"(.*)"', cleaned_output, re.DOTALL)
        if list_str_match:
            list_str = list_str_match.group(1)
            try:
                unescaped_str = ast.literal_eval(f'"{list_str}"')
                try:
                    result = ast.literal_eval(unescaped_str)
                    return str(result)
                except (SyntaxError, ValueError):
                    return unescaped_str
            except (SyntaxError, ValueError):
                return list_str.replace("\\n", "\n").replace('\\"', '"')

    # General tuple pattern: (  "content"  ) or (  "content",  )
    # The ,? handles Candid's pretty-printed trailing comma in multiline output
    tuple_match = re.search(r'\(\s*"(.*)"\s*,?\s*\)', output, re.DOTALL)
    if tuple_match:
        tuple_content = tuple_match.group(1)
        try:
            unescaped_content = ast.literal_eval(f'"{tuple_content}"')
            if unescaped_content.startswith("[") and unescaped_content.endswith("]"):
                try:
                    list_content = ast.literal_eval(unescaped_content)
                    return str(list_content)
                except (SyntaxError, ValueError):
                    return unescaped_content
            return unescaped_content
        except (SyntaxError, ValueError):
            return tuple_content.replace("\\n", "\n").replace('\\"', '"')

    # Standard pattern: ("content")
    standard_match = re.search(r'\("(.*)"\)', output)
    if standard_match:
        response = standard_match.group(1)
        try:
            return ast.literal_eval(f'"{response}"')
        except (SyntaxError, ValueError):
            return response.replace("\\n", "\n").replace('\\"', '"')

    # Fallback: return raw output
    return output


def parse_candid_json_response(output: str) -> dict:
    """Parse a Candid-encoded JSON string response into a dict.

    The output from dfx is typically: ("{\\"key\\": \\"value\\"}",)
    This function extracts and parses the inner JSON.
    """
    import json

    inner = parse_candid_string_output(output)
    return json.loads(inner)
