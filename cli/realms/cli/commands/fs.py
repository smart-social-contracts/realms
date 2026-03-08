"""Filesystem commands for browsing canister filesystem."""

import subprocess
import os
from typing import Optional

import typer
from rich.console import Console

from ..utils import get_effective_cwd

console = Console()


def _execute_python(code: str, canister: str, network: Optional[str], cwd: Optional[str] = None) -> str:
    """Execute Python code on the canister and return the result."""
    escaped_code = code.replace('"', '\\"')
    cmd = ["dfx", "canister", "call"]
    if network:
        cmd.extend(["--network", network])
    cmd.extend([canister, "execute_code_shell", f'("{escaped_code}")'])

    env = os.environ.copy()
    env["DFX_WARNING"] = "-mainnet_plaintext_identity"

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=cwd, env=env, timeout=30)
        output = result.stdout.strip()
        # Parse Candid tuple response: ("content",)
        import re, ast
        tuple_match = re.search(r'\(\s*"(.*)"\s*,?\s*\)', output, re.DOTALL)
        if tuple_match:
            try:
                return ast.literal_eval(f'"{tuple_match.group(1)}"')
            except (SyntaxError, ValueError):
                return tuple_match.group(1).replace("\\n", "\n").replace('\\"', '"')
        return output
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Call timed out"
    except Exception as e:
        return f"Error: {e}"


def fs_ls_command(path: str, network: Optional[str], canister: str, cwd: Optional[str] = None) -> None:
    """List files in the canister filesystem."""
    code = f"""
import os
path = "{path}"
try:
    entries = os.listdir(path)
    for e in sorted(entries):
        full = os.path.join(path, e)
        if os.path.isdir(full):
            print(f"d  {{e}}/")
        else:
            try:
                size = os.path.getsize(full)
                print(f"f  {{e}}  ({{size}} bytes)")
            except OSError:
                print(f"f  {{e}}")
except Exception as ex:
    print(f"Error: {{ex}}")
""".strip()
    result = _execute_python(code, canister, network, cwd)
    if result:
        print(result)


def fs_cat_command(path: str, network: Optional[str], canister: str, cwd: Optional[str] = None) -> None:
    """Read a file from the canister filesystem."""
    code = f"""
try:
    with open("{path}", "r") as f:
        print(f.read())
except Exception as ex:
    print(f"Error: {{ex}}")
""".strip()
    result = _execute_python(code, canister, network, cwd)
    if result:
        print(result)


def fs_write_command(path: str, content: str, network: Optional[str], canister: str, cwd: Optional[str] = None) -> None:
    """Write content to a file on the canister filesystem."""
    import base64
    encoded = base64.b64encode(content.encode()).decode()
    code = f"""
import base64
try:
    content = base64.b64decode("{encoded}").decode()
    with open("{path}", "w") as f:
        f.write(content)
    print(f"Written {{len(content)}} bytes to {path}")
except Exception as ex:
    print(f"Error: {{ex}}")
""".strip()
    result = _execute_python(code, canister, network, cwd)
    if result:
        console.print(result)


def fs_rm_command(path: str, network: Optional[str], canister: str, cwd: Optional[str] = None) -> None:
    """Remove a file from the canister filesystem."""
    code = f"""
import os
try:
    os.remove("{path}")
    print(f"Removed {path}")
except Exception as ex:
    print(f"Error: {{ex}}")
""".strip()
    result = _execute_python(code, canister, network, cwd)
    if result:
        console.print(result)
