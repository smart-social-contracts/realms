"""``realm_installer`` helpers.

The on-chain end-to-end ``deploy_realm`` / ``get_deploy_status`` / ``list_deploys``
API has been removed.  Full realm deploys go through
``realm_registry`` → ``enqueue_deployment`` and the dfx-based deploy worker.
Use ``realms registry deploy`` / ``realm deploy status`` for the queue, or
``realms wasm install`` for WASM-only from the file registry.
"""

import os
import subprocess
from typing import Optional

import json
import typer
from rich.console import Console

console = Console()


def _dfx_unset_env() -> dict:
    run_env = os.environ.copy()
    for k in (
        "COLORTERM", "CLICOLOR", "CLICOLOR_FORCE", "LS_COLORS",
        "TERM_PROGRAM", "TERM_PROGRAM_VERSION",
    ):
        run_env.pop(k, None)
    run_env.setdefault("NO_COLOR", "1")
    run_env.setdefault("TERM", "linux")
    return run_env


def installer_health_command(
    installer: str,
    network: str = "ic",
    identity: Optional[str] = None,
) -> None:
    """Call ``realm_installer.health`` (liveness + limits)."""
    run_env = _dfx_unset_env()
    if identity:
        run_env["DFX_IDENTITY"] = identity
    cmd = [
        "dfx", "canister", "call", installer, "health", "()",
        "--network", network, "--output", "json",
    ]
    try:
        cp = subprocess.run(
            cmd, capture_output=True, text=True, env=run_env, timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise typer.Exit(1) from e
    if cp.returncode != 0:
        console.print(
            f"[red]dfx canister call failed: {cp.stderr or cp.stdout}[/red]"
        )
        raise typer.Exit(cp.returncode)
    try:
        data = json.loads((cp.stdout or "").strip())
    except json.JSONDecodeError:
        console.print(f"[red]Non-JSON response: {cp.stdout[:300]}[/red]")
        raise typer.Exit(1) from None
    console.print(data)
    if isinstance(data, dict) and data.get("ok") is True:
        console.print(f"[green]OK[/green] {installer} on {network}")
