"""
WASM Registry commands — pull base WASM from the file registry.

Provides functionality for downloading the base realm WASM from the on-chain
file registry canister, used in the layered deployment architecture.
"""

import base64
import json
import os
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def _dfx_call(canister, method, arg, network, identity=None, is_query=False, timeout=120):
    """Run a dfx canister call and return raw output."""
    cmd = ["dfx", "canister", "call"]
    if identity:
        cmd.extend(["--identity", identity])
    if network:
        cmd.extend(["--network", network])
    if is_query:
        cmd.append("--query")
    cmd.extend([canister, method, arg])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            console.print(f"[red]Error: {result.stderr.strip()}[/red]")
            raise typer.Exit(1)
        raw = result.stdout.strip()
        if raw.startswith("(") and raw.endswith(")"):
            raw = raw[1:-1].strip()
        if raw.endswith(","):
            raw = raw[:-1].strip()
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1]
        raw = raw.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
        return raw
    except subprocess.TimeoutExpired:
        console.print(f"[red]Error: canister call timed out ({timeout}s)[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]Error: dfx not found. Install the DFINITY SDK.[/red]")
        raise typer.Exit(1)


def wasm_list_command(registry: str, network: str = "ic", identity: Optional[str] = None):
    """List available base WASM versions in the file registry."""
    console.print(f"[blue]Listing base WASM files from {registry} ({network})...[/blue]")

    payload = json.dumps({"namespace": "wasm"})
    candid_arg = '("' + payload.replace("\\", "\\\\").replace('"', '\\"') + '")'

    raw = _dfx_call(registry, "list_files", candid_arg, network, identity, is_query=True)

    try:
        files = json.loads(raw)
    except json.JSONDecodeError:
        console.print(raw)
        return

    if isinstance(files, dict) and "error" in files:
        console.print(f"[red]Error: {files['error']}[/red]")
        raise typer.Exit(1)

    wasm_files = [f for f in files if f.get("path", "").startswith("realm-base-")]
    if not wasm_files:
        console.print("[yellow]No base WASM files found in registry.[/yellow]")
        return

    table = Table(title="Available Base WASMs")
    table.add_column("Path", style="cyan")
    table.add_column("Size", style="green", justify="right")
    table.add_column("SHA256", style="dim")

    for f in sorted(wasm_files, key=lambda x: x.get("path", ""), reverse=True):
        size = f.get("size", 0)
        size_str = f"{size:,} bytes" if size < 1048576 else f"{size / 1048576:.1f} MB"
        table.add_row(
            f.get("path", ""),
            size_str,
            f.get("sha256", "")[:16] + "...",
        )

    console.print(table)


def wasm_pull_command(
    registry: str,
    version: Optional[str] = None,
    output: Optional[str] = None,
    network: str = "ic",
    identity: Optional[str] = None,
):
    """Pull a base WASM from the file registry.

    If version is not specified, pulls the latest version by scanning
    available files in the wasm/ namespace.
    """
    console.print(f"[blue]Pulling base WASM from {registry} ({network})...[/blue]")

    if not version:
        # Discover latest version by listing files in wasm/ namespace
        payload = json.dumps({"namespace": "wasm"})
        candid_arg = '("' + payload.replace("\\", "\\\\").replace('"', '\\"') + '")'

        raw = _dfx_call(registry, "list_files", candid_arg, network, identity, is_query=True)

        try:
            files = json.loads(raw)
        except json.JSONDecodeError:
            console.print(f"[red]Failed to parse file list: {raw}[/red]")
            raise typer.Exit(1)

        # Find latest realm-base-*.wasm.gz
        wasm_files = []
        for f in files:
            path = f.get("path", "")
            if path.startswith("realm-base-") and path.endswith(".wasm.gz"):
                ver = path.replace("realm-base-", "").replace(".wasm.gz", "")
                wasm_files.append((ver, path))

        if not wasm_files:
            console.print("[red]No base WASM files found in registry.[/red]")
            raise typer.Exit(1)

        # Sort by semver
        def _semver_key(item):
            try:
                parts = item[0].split(".")
                return tuple(int(p) for p in parts)
            except (ValueError, AttributeError):
                return (0, 0, 0)

        wasm_files.sort(key=_semver_key)
        version = wasm_files[-1][0]
        console.print(f"  Latest version: {version}")

    file_path = f"realm-base-{version}.wasm.gz"
    output_path = output or file_path

    console.print(f"  Downloading: wasm/{file_path}")

    # Use get_file to download
    payload = json.dumps({"namespace": "wasm", "path": file_path})
    candid_arg = '("' + payload.replace("\\", "\\\\").replace('"', '\\"') + '")'

    raw = _dfx_call(registry, "get_file", candid_arg, network, identity, is_query=True, timeout=300)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        console.print(f"[red]Failed to parse response[/red]")
        raise typer.Exit(1)

    if "error" in data:
        console.print(f"[red]Error: {data['error']}[/red]")
        raise typer.Exit(1)

    content_b64 = data.get("content_b64", "")
    if not content_b64:
        console.print("[red]Empty file content[/red]")
        raise typer.Exit(1)

    content = base64.b64decode(content_b64)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(content)

    size_str = f"{len(content):,}" if len(content) < 1048576 else f"{len(content) / 1048576:.1f} MB"
    console.print(f"[green]  ✓ Saved to {output_path} ({size_str})[/green]")
    console.print(f"  SHA256: {data.get('sha256', 'unknown')}")


def wasm_install_command(
    installer: str,
    registry: str,
    target: str,
    version: Optional[str] = None,
    wasm_path: Optional[str] = None,
    namespace: str = "wasm",
    mode: str = "upgrade",
    init_arg_b64: str = "",
    network: str = "ic",
    identity: Optional[str] = None,
):
    """Deprecated direct install path (removed)."""
    _ = (installer, registry, target, version, wasm_path, namespace, mode, init_arg_b64)
    _ = (network, identity)
    console.print(
        "[red]`wasm install` was removed from this CLI command. "
        "Use the queue deployment flow via `request_deployment`.[/red]"
    )
    raise typer.Exit(1)


def wasm_hash_command(
    installer: str,
    registry: str,
    version: Optional[str] = None,
    wasm_path: Optional[str] = None,
    namespace: str = "wasm",
    network: str = "ic",
    identity: Optional[str] = None,
):
    """Deprecated direct hash path (removed)."""
    _ = (installer, registry, version, wasm_path, namespace, network, identity)
    console.print(
        "[red]`wasm hash` was removed from this CLI command. "
        "Use release checksums + installer verification reports instead.[/red]"
    )
    raise typer.Exit(1)


def wasm_command(
    action: str = typer.Argument(
        ...,
        help="Action to perform: list or pull",
    ),
    registry: Optional[str] = typer.Option(
        None, "--registry", "-r", help="File registry canister ID"
    ),
    installer: Optional[str] = typer.Option(
        None, "--installer", "-I",
        help="realm_installer canister ID (required for install/hash)",
    ),
    target: Optional[str] = typer.Option(
        None, "--target", "-t",
        help="Target canister ID to install onto (required for install)",
    ),
    version: Optional[str] = typer.Option(
        None, "--version", "-v", help="Version to pull/install (default: latest)"
    ),
    wasm_path: Optional[str] = typer.Option(
        None, "--wasm-path",
        help="Override default 'realm-base-{version}.wasm.gz' path in the registry",
    ),
    namespace: str = typer.Option(
        "wasm", "--namespace", help="Registry namespace for the WASM (default: wasm)"
    ),
    mode: str = typer.Option(
        "upgrade", "--mode", "-m",
        help="Install mode for install action: install | reinstall | upgrade",
    ),
    init_arg_b64: str = typer.Option(
        "", "--init-arg-b64",
        help="Optional base64-encoded candid blob to pass as init/post-upgrade arg",
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file path for pull"
    ),
    network: str = typer.Option(
        "ic", "--network", "-n", help="Network: local, ic"
    ),
    identity: Optional[str] = typer.Option(
        None, "--identity", help="dfx identity to use"
    ),
) -> None:
    """Manage realm base WASM (Layer 1).

    Subcommands:
      list     — list base WASMs available in the file registry
      pull     — download a base WASM from the registry to disk
      install/hash are removed; deployment is queue-based only.
    """
    if action == "list":
        if not registry:
            console.print("[red]Error: --registry is required[/red]")
            raise typer.Exit(1)
        wasm_list_command(registry, network, identity)
    elif action == "pull":
        if not registry:
            console.print("[red]Error: --registry is required[/red]")
            raise typer.Exit(1)
        wasm_pull_command(registry, version, output, network, identity)
    elif action == "install":
        wasm_install_command(
            installer=installer,
            registry=registry,
            target=target,
            version=version,
            wasm_path=wasm_path,
            namespace=namespace,
            mode=mode,
            init_arg_b64=init_arg_b64,
            network=network,
            identity=identity,
        )
    elif action == "hash":
        wasm_hash_command(
            installer=installer,
            registry=registry,
            version=version,
            wasm_path=wasm_path,
            namespace=namespace,
            network=network,
            identity=identity,
        )
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("[yellow]Available actions: list, pull[/yellow]")
        raise typer.Exit(1)
