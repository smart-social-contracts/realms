"""
Installer commands — drive on-chain ``realm_installer.deploy_realm``.

This is the operator-facing wrapper around ``deploy_realm`` /
``get_deploy_status`` / ``list_deploys``.  The single ``deploy``
subcommand kicks off an end-to-end realm install (WASM + extensions +
codices) from a JSON manifest and (by default) blocks until the
on-chain task reaches a terminal status.

The corresponding ``realms wasm install`` (Layer-1, WASM-only) command
remains the right tool for "just upgrade the WASM" — this command is
for "redeploy this realm from scratch" workflows.

Examples::

    # Kick off a deploy and wait for completion
    realms installer deploy \\
        --installer <installer-canister-id> \\
        --manifest manifest.json \\
        --network staging

    # Fire-and-forget: print the task_id and return immediately
    realms installer deploy --installer <id> --manifest m.json --no-wait

    # Poll an existing task
    realms installer status \\
        --installer <id> --task-id deploy_1729382938012345 --network staging

    # List every deploy this installer has run
    realms installer list --installer <id> --network staging
"""

import json
import os
import subprocess
import time
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()


# ---------------------------------------------------------------------------
# dfx wrappers — kept here (instead of imported from wasm_registry) so this
# file is self-contained and the two command groups can evolve
# independently.
# ---------------------------------------------------------------------------

def _candid_text_arg(payload: str) -> str:
    """Wrap ``payload`` as a candid `text` literal, escaping per Candid."""
    escaped = payload.replace("\\", "\\\\").replace('"', '\\"')
    return '("' + escaped + '")'


def _unwrap_candid_text(out: str) -> str:
    """Strip the ``("...",)`` candid wrapper from a single-text return."""
    raw = (out or "").strip()
    if raw.startswith("(") and raw.endswith(")"):
        raw = raw[1:-1].strip()
    if raw.endswith(","):
        raw = raw[:-1].strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    return (
        raw.replace("\\\\", "\\")
        .replace('\\"', '"')
        .replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
    )


def _dfx_call(
    canister: str,
    method: str,
    arg: str,
    network: str,
    *,
    identity: Optional[str] = None,
    is_query: bool = False,
    timeout: int = 120,
) -> str:
    """Run a ``dfx canister call`` and return the unwrapped text reply."""
    cmd = ["dfx", "canister", "call"]
    if identity:
        cmd.extend(["--identity", identity])
    if network:
        cmd.extend(["--network", network])
    if is_query:
        cmd.append("--query")
    cmd.extend([canister, method, arg])
    try:
        cp = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        console.print(f"[red]Error: dfx call timed out after {timeout}s[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]Error: dfx not found. Install the DFINITY SDK.[/red]")
        raise typer.Exit(1)
    if cp.returncode != 0:
        console.print(f"[red]dfx error: {(cp.stderr or '').strip()}[/red]")
        raise typer.Exit(1)
    return _unwrap_candid_text(cp.stdout)


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def _load_manifest(manifest_path: Optional[str]) -> dict:
    """Read a manifest from a file path, or from stdin when ``-``.

    The file is expected to be JSON; we round-trip through ``json.loads``
    so we fail fast on bad payloads (instead of letting the canister
    reject them at the other end).
    """
    if not manifest_path:
        console.print("[red]Error: --manifest is required[/red]")
        raise typer.Exit(1)
    try:
        if manifest_path == "-":
            import sys
            raw = sys.stdin.read()
        else:
            with open(manifest_path, "r", encoding="utf-8") as fh:
                raw = fh.read()
    except OSError as e:
        console.print(f"[red]Error: cannot read manifest {manifest_path}: {e}[/red]")
        raise typer.Exit(1)
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error: manifest is not valid JSON: {e}[/red]")
        raise typer.Exit(1)
    if not isinstance(manifest, dict):
        console.print("[red]Error: manifest must be a JSON object[/red]")
        raise typer.Exit(1)
    return manifest


def _override(manifest: dict, target: Optional[str], registry: Optional[str]) -> dict:
    """Apply CLI overrides on top of the file's manifest.

    Operators commonly want to point the same manifest at different
    targets (staging vs. ic) without editing the file — `--target` and
    `--registry` are deliberately separate from the manifest body for
    that reason.
    """
    out = dict(manifest)
    if target:
        out["target_canister_id"] = target
    if registry:
        out["registry_canister_id"] = registry
    if not out.get("target_canister_id"):
        console.print(
            "[red]Error: target_canister_id must be set in manifest "
            "or via --target[/red]"
        )
        raise typer.Exit(1)
    if not out.get("registry_canister_id"):
        console.print(
            "[red]Error: registry_canister_id must be set in manifest "
            "or via --registry[/red]"
        )
        raise typer.Exit(1)
    return out


# ---------------------------------------------------------------------------
# Status rendering
# ---------------------------------------------------------------------------

_STATUS_STYLES = {
    "completed": "[green]completed[/green]",
    "running": "[yellow]running[/yellow]",
    "queued": "[dim]queued[/dim]",
    "pending": "[dim]pending[/dim]",
    "partial": "[yellow]partial[/yellow]",
    "failed": "[red]failed[/red]",
}


def _style(status: str) -> str:
    return _STATUS_STYLES.get(status or "", status or "")


def _render_status(data: dict) -> None:
    """Pretty-print a get_deploy_status payload."""
    head = Table(title=f"Deploy {data.get('task_id')}", show_header=False, box=None)
    head.add_column("Field", style="cyan")
    head.add_column("Value")
    head.add_row("Status", _style(data.get("status", "")))
    head.add_row("Target", data.get("target_canister_id", ""))
    head.add_row("Registry", data.get("registry_canister_id", ""))
    if data.get("started_at"):
        head.add_row("Started at", str(data.get("started_at")))
    if data.get("completed_at"):
        head.add_row("Completed at", str(data.get("completed_at")))
    if data.get("error"):
        head.add_row("Error", f"[red]{data['error']}[/red]")
    console.print(head)

    steps = Table(title="Steps", show_lines=False)
    steps.add_column("#", style="dim", justify="right")
    steps.add_column("Kind", style="cyan")
    steps.add_column("Label", style="white")
    steps.add_column("Status")
    steps.add_column("Detail", style="dim")

    def _add_step(s: dict) -> None:
        if not s:
            return
        detail = s.get("error") or ""
        if not detail and isinstance(s.get("result"), dict):
            res = s["result"]
            detail = (
                f"hash={res.get('wasm_module_hash_hex', '')[:12]}…"
                if "wasm_module_hash_hex" in res
                else ""
            )
        steps.add_row(
            str(s.get("idx", "")),
            s.get("kind", ""),
            s.get("label", ""),
            _style(s.get("status", "")),
            detail[:80],
        )

    _add_step(data.get("wasm"))
    for ext in (data.get("extensions") or []):
        _add_step(ext)
    for cdx in (data.get("codices") or []):
        _add_step(cdx)
    console.print(steps)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def installer_deploy_command(
    installer: str,
    manifest_path: str,
    target: Optional[str] = None,
    registry: Optional[str] = None,
    network: str = "ic",
    identity: Optional[str] = None,
    wait: bool = True,
    poll_interval: float = 5.0,
    max_wait: int = 1800,
) -> None:
    """Kick off a ``deploy_realm`` and (optionally) wait for completion.

    Returns the task_id on success.  When ``wait=True`` (the default),
    blocks until the on-chain task reaches ``completed | partial |
    failed``; exit code is non-zero unless the final status is
    ``completed``.
    """
    manifest = _override(_load_manifest(manifest_path), target, registry)
    target_id = manifest["target_canister_id"]
    registry_id = manifest["registry_canister_id"]
    n_ext = len(manifest.get("extensions") or [])
    n_cdx = len(manifest.get("codices") or [])
    has_wasm = bool(manifest.get("wasm"))
    console.print(
        f"[blue]Deploying via {installer} ({network}) → target={target_id}[/blue]"
    )
    console.print(
        f"  manifest: registry={registry_id}, "
        f"wasm={'yes' if has_wasm else 'no'}, "
        f"extensions={n_ext}, codices={n_cdx}"
    )

    raw = _dfx_call(
        installer,
        "deploy_realm",
        _candid_text_arg(json.dumps(manifest)),
        network,
        identity=identity,
        timeout=120,
    )
    try:
        kickoff = json.loads(raw)
    except json.JSONDecodeError:
        console.print(f"[red]deploy_realm returned non-JSON: {raw[:300]}[/red]")
        raise typer.Exit(1)
    if not kickoff.get("success"):
        console.print(f"[red]deploy_realm rejected: {kickoff.get('error')}[/red]")
        if kickoff.get("conflicting_task_id"):
            console.print(
                f"[dim]Hint: poll status with: realms installer status "
                f"--installer {installer} "
                f"--task-id {kickoff['conflicting_task_id']} --network {network}[/dim]"
            )
        raise typer.Exit(1)

    task_id = kickoff["task_id"]
    console.print(
        f"[green]✓ queued[/green] task_id=[cyan]{task_id}[/cyan] "
        f"(steps={kickoff.get('steps_count')})"
    )

    if not wait:
        return

    # Poll loop.  Print only on status transitions to keep the output
    # readable for long-running deploys.
    console.print(f"[dim]Polling every {poll_interval}s (timeout {max_wait}s)…[/dim]")
    deadline = time.time() + max_wait
    last_status = ""
    while time.time() < deadline:
        body = _dfx_call(
            installer, "get_deploy_status",
            _candid_text_arg(task_id),
            network, identity=identity, is_query=True, timeout=60,
        )
        try:
            status = json.loads(body)
        except json.JSONDecodeError:
            console.print(f"[yellow]unparseable status: {body[:200]}[/yellow]")
            time.sleep(poll_interval)
            continue
        if not status.get("success", True):
            console.print(f"[red]get_deploy_status error: {status.get('error')}[/red]")
            raise typer.Exit(1)
        cur = status.get("status", "")
        if cur != last_status:
            console.print(f"  [{cur}] {task_id}")
            last_status = cur
        if cur in ("completed", "partial", "failed"):
            _render_status(status)
            if cur == "completed":
                console.print(f"[green]✓ deploy {task_id} completed[/green]")
                return
            console.print(
                f"[red]✗ deploy {task_id} ended in status '{cur}'[/red]"
            )
            raise typer.Exit(1)
        time.sleep(poll_interval)
    console.print(
        f"[red]Timeout: task {task_id} did not finish within {max_wait}s "
        f"(last status: {last_status})[/red]"
    )
    raise typer.Exit(1)


def installer_cancel_command(
    installer: str,
    task_id: str,
    network: str = "ic",
    identity: Optional[str] = None,
) -> None:
    """Cancel an in-flight ``deploy_realm`` task.

    Idempotent: cancelling a terminal task is a no-op success.  Useful
    for freeing the per-target concurrency lock after a stuck deploy
    or for aborting a known-bad manifest.
    """
    body = _dfx_call(
        installer, "cancel_deploy",
        _candid_text_arg(task_id),
        network, identity=identity, timeout=60,
    )
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        console.print(f"[red]unparseable cancel response: {body[:200]}[/red]")
        raise typer.Exit(1)
    if not data.get("success"):
        console.print(f"[red]Error: {data.get('error')}[/red]")
        raise typer.Exit(1)
    if data.get("noop"):
        console.print(
            f"[yellow]task {task_id} already terminal "
            f"(status={data.get('status')}); no-op[/yellow]"
        )
        return
    console.print(
        f"[green]✓ cancelled[/green] {task_id} "
        f"(prev={data.get('prev_status')}, "
        f"cancelled_steps={data.get('cancelled_steps')})"
    )


def installer_status_command(
    installer: str,
    task_id: str,
    network: str = "ic",
    identity: Optional[str] = None,
) -> None:
    """Print the current status of a ``deploy_realm`` task."""
    body = _dfx_call(
        installer, "get_deploy_status",
        _candid_text_arg(task_id),
        network, identity=identity, is_query=True, timeout=60,
    )
    try:
        status = json.loads(body)
    except json.JSONDecodeError:
        console.print(f"[red]unparseable status: {body[:200]}[/red]")
        raise typer.Exit(1)
    if not status.get("success", True):
        console.print(f"[red]Error: {status.get('error')}[/red]")
        raise typer.Exit(1)
    _render_status(status)


def installer_list_command(
    installer: str,
    network: str = "ic",
    identity: Optional[str] = None,
) -> None:
    """List every ``deploy_realm`` task this installer has run."""
    body = _dfx_call(
        installer, "list_deploys", "()", network,
        identity=identity, is_query=True, timeout=60,
    )
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        console.print(f"[red]unparseable list: {body[:200]}[/red]")
        raise typer.Exit(1)
    if not data.get("success", True):
        console.print(f"[red]Error: {data.get('error')}[/red]")
        raise typer.Exit(1)
    tasks = data.get("tasks") or []
    if not tasks:
        console.print("[yellow]No deploys recorded for this installer.[/yellow]")
        return
    table = Table(title=f"Deploys on {installer} ({len(tasks)} total)")
    table.add_column("Task ID", style="cyan")
    table.add_column("Status")
    table.add_column("Target", style="dim")
    table.add_column("Steps", justify="right")
    table.add_column("Started", justify="right")
    table.add_column("Completed", justify="right")
    for t in tasks:
        table.add_row(
            t.get("task_id", ""),
            _style(t.get("status", "")),
            t.get("target_canister_id", ""),
            str(t.get("steps_count", 0)),
            str(t.get("started_at", 0) or "—"),
            str(t.get("completed_at", 0) or "—"),
        )
    console.print(table)
