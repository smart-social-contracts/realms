"""Marketplace CLI commands.

The marketplace canisters (``marketplace_backend`` + ``marketplace_frontend``)
now live in the realms repo proper at ``src/marketplace_backend/`` and
``src/marketplace_frontend/`` and are declared as first-class entries in
the root ``dfx.json``. Deployment is therefore a thin wrapper around
``dfx deploy``.

Subcommands:

  realms marketplace deploy [--network ...] [--with-registry/--no-with-registry]
                            [--file-registry-canister-id ID]
                            [--billing-service-principal P]
                            [--mode auto|install|reinstall|upgrade]
                            [--identity NAME-OR-PEM]

  realms marketplace call <method> [args]      — forward to dfx canister call
  realms marketplace status                    — pretty-print status() output

The legacy ``realms marketplace create`` subcommand (which copied the
old extensions/marketplace folder into a new directory) is no longer
needed and has been removed; use ``realms marketplace deploy`` from
the repo root instead.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from ..utils import (
    console,
    display_canister_urls_json,
    ensure_dfx_running,
    get_project_root,
    get_realms_logger,
    run_command,
    set_log_dir,
)


# Canister names this CLI manages.
MARKETPLACE_BACKEND = "marketplace_backend"
MARKETPLACE_FRONTEND = "marketplace_frontend"
FILE_REGISTRY = "file_registry"


def _dfx_canister_id(name: str, network: str) -> Optional[str]:
    """Return the canister id (text) for ``name`` on ``network``, or None."""
    try:
        result = subprocess.run(
            ["dfx", "canister", "id", name, "--network", network],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            cid = result.stdout.strip()
            return cid or None
    except Exception:
        pass
    return None


def _dfx_call(
    canister: str,
    method: str,
    candid_args: str,
    network: str,
    *,
    update: bool = True,
    quiet: bool = False,
) -> subprocess.CompletedProcess:
    """Run ``dfx canister call`` and return the CompletedProcess."""
    cmd = ["dfx", "canister", "call", "--network", network]
    if not update:
        cmd.append("--query")
    cmd.extend([canister, method, candid_args])
    env = os.environ.copy()
    env.setdefault("DFX_WARNING", "-mainnet_plaintext_identity")
    if not quiet:
        console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)


def marketplace_deploy_command(
    *,
    network: str = "local",
    mode: str = "auto",
    identity: Optional[str] = None,
    with_registry: Optional[bool] = None,
    file_registry_canister_id: Optional[str] = None,
    billing_service_principal: Optional[str] = None,
) -> None:
    """Deploy the marketplace canisters from the realms repo root.

    Steps:
      1. (Optional) deploy ``file_registry`` first when --with-registry.
      2. Deploy ``marketplace_backend`` (passes init arg with file_registry id).
      3. Deploy ``marketplace_frontend``.
      4. Set ``file_registry_canister_id`` and ``billing_service_principal``
         on marketplace_backend via update calls (idempotent — these are
         skipped if the canister was created with the right init arg).
    """
    project_root = get_project_root()
    log_dir = project_root.absolute()
    set_log_dir(log_dir)
    logger = get_realms_logger(log_dir=log_dir)
    logger.info("=" * 60)
    logger.info(f"Marketplace deploy → network={network} mode={mode}")
    if identity:
        logger.info(f"identity={identity}")
    logger.info("=" * 60)

    if not (project_root / "src" / MARKETPLACE_BACKEND / "main.py").exists():
        console.print(f"[red]❌ marketplace_backend source not found at src/{MARKETPLACE_BACKEND}/main.py[/red]")
        raise typer.Exit(1)

    if network == "local":
        ensure_dfx_running()

    # Default --with-registry behaviour: True for local, False elsewhere.
    if with_registry is None:
        with_registry = (network == "local")

    # 1. file_registry first (so we can wire its canister id into the
    #    marketplace's init arg).
    if with_registry:
        console.print(Panel.fit("📦 Deploying file_registry", style="bold blue"))
        deploy_args = ["dfx", "deploy", FILE_REGISTRY, "--network", network, "--yes"]
        if mode != "auto":
            deploy_args.extend(["--mode", mode])
        if identity:
            deploy_args.extend(["--identity", identity])
        rc = run_command(deploy_args, cwd=str(project_root), logger=logger)
        if rc.returncode != 0:
            console.print("[red]❌ file_registry deploy failed[/red]")
            raise typer.Exit(rc.returncode)

    # Resolve the file_registry id (may have come from a previous deploy).
    fr_id = file_registry_canister_id or _dfx_canister_id(FILE_REGISTRY, network) or ""
    if fr_id:
        console.print(f"[dim]file_registry canister id = {fr_id}[/dim]")
    else:
        console.print("[yellow]⚠️  No file_registry canister id resolved — marketplace will be configured later via set_file_registry_canister_id.[/yellow]")

    # 2. marketplace_backend with init arg (only honoured on first install).
    console.print(Panel.fit("🛒 Deploying marketplace_backend", style="bold blue"))
    init_arg_parts = []
    if fr_id:
        init_arg_parts.append(f'file_registry = opt "{fr_id}"')
    if billing_service_principal:
        init_arg_parts.append(f'billing_service_principal = opt "{billing_service_principal}"')
    init_arg = (
        f'(opt record {{ {"; ".join(init_arg_parts)} }})'
        if init_arg_parts
        else "(null)"
    )
    deploy_args = [
        "dfx", "deploy", MARKETPLACE_BACKEND,
        "--network", network, "--yes",
        "--argument", init_arg,
    ]
    if mode != "auto":
        deploy_args.extend(["--mode", mode])
    if identity:
        deploy_args.extend(["--identity", identity])
    rc = run_command(deploy_args, cwd=str(project_root), logger=logger)
    if rc.returncode != 0:
        console.print("[red]❌ marketplace_backend deploy failed[/red]")
        raise typer.Exit(rc.returncode)

    # 3. marketplace_frontend (depends on backend declarations being generated).
    console.print(Panel.fit("🖼️  Deploying marketplace_frontend", style="bold blue"))
    deploy_args = ["dfx", "deploy", MARKETPLACE_FRONTEND, "--network", network, "--yes"]
    if mode != "auto":
        deploy_args.extend(["--mode", mode])
    if identity:
        deploy_args.extend(["--identity", identity])
    rc = run_command(deploy_args, cwd=str(project_root), logger=logger)
    if rc.returncode != 0:
        console.print("[red]❌ marketplace_frontend deploy failed[/red]")
        raise typer.Exit(rc.returncode)

    # 4. Re-apply config on every deploy (idempotent) so an upgrade picks up
    #    a new file_registry id even if the init arg was only honoured on
    #    first install.
    if fr_id:
        console.print("[dim]→ set_file_registry_canister_id[/dim]")
        result = _dfx_call(
            MARKETPLACE_BACKEND,
            "set_file_registry_canister_id",
            f'("{fr_id}")',
            network,
            update=True,
            quiet=True,
        )
        if result.returncode != 0 and result.stderr:
            console.print(f"[yellow]   warning: {result.stderr.strip()[:200]}[/yellow]")
    if billing_service_principal:
        console.print("[dim]→ set_billing_service_principal[/dim]")
        result = _dfx_call(
            MARKETPLACE_BACKEND,
            "set_billing_service_principal",
            f'("{billing_service_principal}")',
            network,
            update=True,
            quiet=True,
        )
        if result.returncode != 0 and result.stderr:
            console.print(f"[yellow]   warning: {result.stderr.strip()[:200]}[/yellow]")

    console.print("\n[green]✅ Marketplace deployed successfully![/green]")
    display_canister_urls_json(project_root, network, "Marketplace Deployment Summary")


def marketplace_call_command(
    method: str,
    args: str,
    network: str,
    canister_id: Optional[str],
    output: str,
    verbose: bool,
) -> None:
    """Forward to ``dfx canister call``. ``canister_id`` falls back to dfx-resolved id."""
    if output not in ("json", "candid"):
        console.print(f"[red]❌ Invalid output format: {output}. Use 'json' or 'candid'[/red]")
        raise typer.Exit(1)

    cid = canister_id or _dfx_canister_id(MARKETPLACE_BACKEND, network)
    if not cid:
        console.print(f"[red]❌ Could not resolve marketplace_backend canister id on network '{network}'[/red]")
        raise typer.Exit(1)

    if verbose:
        console.print(f"[dim]Marketplace canister: {cid}[/dim]")
        console.print(f"[dim]Network: {network}[/dim]")
        console.print(f"[dim]Method: {method}[/dim]")
        console.print(f"[dim]Args: {args}[/dim]\n")

    cmd = ["dfx", "canister", "call", "--network", network, cid, method, args]
    if output == "json":
        cmd.extend(["--output", "json"])
    env = os.environ.copy()
    env.setdefault("DFX_WARNING", "-mainnet_plaintext_identity")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
    except subprocess.TimeoutExpired:
        sys.stderr.write("Error: Call timed out\n")
        raise typer.Exit(1)
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        if result.stderr:
            sys.stderr.write(f"Error: {result.stderr}\n")
        raise typer.Exit(1)


def marketplace_status_command(network: str = "local") -> None:
    """Pretty-print marketplace_backend.status() output."""
    cid = _dfx_canister_id(MARKETPLACE_BACKEND, network)
    if not cid:
        console.print(f"[red]❌ Could not resolve marketplace_backend canister id on network '{network}'[/red]")
        raise typer.Exit(1)
    console.print(f"[dim]Querying status() on {cid} ({network})…[/dim]")
    result = _dfx_call(
        MARKETPLACE_BACKEND, "status", "()", network, update=False, quiet=True,
    )
    if result.returncode != 0:
        console.print(f"[red]❌ status query failed[/red]\n{result.stderr}")
        raise typer.Exit(result.returncode)
    print(result.stdout.strip())
