"""Per-environment Realms GOS product-stack deploy commands.

Deploys the complete product surface for one IC environment (demo / staging /
test): ``file_registry``, ``file_registry_frontend``, ``marketplace_backend``,
and ``marketplace_frontend`` (landing + marketplace), wired together and
prepared for a custom ``*.realmsgos.org`` domain.

Subcommands::

  realms env deploy --env <name>   — deploy / upgrade the full stack
  realms env status --env <name>   — show canister IDs and dfx status
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.panel import Panel
from rich.table import Table

from .marketplace import (
    FILE_REGISTRY,
    MARKETPLACE_BACKEND,
    MARKETPLACE_FRONTEND,
    _dfx_call,
    _dfx_canister_id,
)
from ..basilisk_env import basilisk_python_executable, dfx_env_with_basilisk
from ..utils import (
    console,
    display_canister_urls_json,
    get_project_root,
    get_realms_logger,
    run_command,
    set_log_dir,
)

FILE_REGISTRY_FRONTEND = "file_registry_frontend"

PRODUCT_STACK = (
    FILE_REGISTRY,
    FILE_REGISTRY_FRONTEND,
    MARKETPLACE_BACKEND,
    MARKETPLACE_FRONTEND,
)


def _environments_dir(project_root: Path) -> Path:
    return project_root / "environments"


def load_env_config(env_name: str, project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load ``environments/<name>.json``; raise ``typer.Exit`` when missing."""
    root = project_root or get_project_root()
    path = _environments_dir(root) / f"{env_name}.json"
    if not path.is_file():
        console.print(
            f"[red]❌ Environment config not found: {path}[/red]\n"
            f"[dim]Expected environments/{{demo,staging,test}}.json at the repo root.[/dim]"
        )
        raise typer.Exit(1)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        console.print(f"[red]❌ Invalid JSON in {path}: {exc}[/red]")
        raise typer.Exit(1)
    if data.get("name") != env_name:
        console.print(
            f"[yellow]⚠️  Config name '{data.get('name')}' does not match --env '{env_name}'[/yellow]"
        )
    return data


def _read_canister_ids(project_root: Path) -> Dict[str, Dict[str, str]]:
    path = project_root / "canister_ids.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_canister_ids(project_root: Path, data: Dict[str, Dict[str, str]]) -> None:
    path = project_root / "canister_ids.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _set_canister_id(
    project_root: Path,
    canister_name: str,
    network: str,
    canister_id: str,
) -> None:
    data = _read_canister_ids(project_root)
    data.setdefault(canister_name, {})[network] = canister_id
    _write_canister_ids(project_root, data)


def _clear_canister_id(project_root: Path, canister_name: str, network: str) -> None:
    data = _read_canister_ids(project_root)
    if canister_name in data and network in data[canister_name]:
        del data[canister_name][network]
        if not data[canister_name]:
            del data[canister_name]
        _write_canister_ids(project_root, data)


def _canister_status_line(canister_ref: str, network: str) -> str:
    """Return a one-line ``dfx canister status`` summary or an error hint."""
    try:
        result = subprocess.run(
            ["dfx", "canister", "status", canister_ref, "--network", network],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:
        return f"error: {exc}"
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "unknown error").strip().splitlines()
        return err[0][:120] if err else "status unavailable"
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("Status:") or stripped.startswith("Balance:"):
            return stripped
    first = result.stdout.strip().splitlines()
    return first[0][:120] if first else "ok"


def _is_canister_dead(canister_ref: str, network: str) -> bool:
    """Return True when the replica reports the canister does not exist."""
    try:
        result = subprocess.run(
            ["dfx", "canister", "status", canister_ref, "--network", network],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:
        return False
    if result.returncode == 0:
        return False
    combined = f"{result.stderr}\n{result.stdout}".lower()
    dead_markers = (
        "not found",
        "does not exist",
        "canister_not_found",
        "canister not found",
        "no route",
    )
    return any(marker in combined for marker in dead_markers)


def _create_canister(
    canister_name: str,
    network: str,
    identity: Optional[str],
    *,
    logger,
) -> str:
    cmd = ["dfx", "canister", "create", canister_name, "--network", network]
    if identity:
        cmd.extend(["--identity", identity])
    rc = run_command(cmd, logger=logger)
    if rc.returncode != 0:
        console.print(f"[red]❌ dfx canister create {canister_name} failed[/red]")
        raise typer.Exit(rc.returncode)
    cid = _dfx_canister_id(canister_name, network)
    if not cid:
        console.print(f"[red]❌ Could not resolve id after creating {canister_name}[/red]")
        raise typer.Exit(1)
    return cid


def resolve_or_create_canister(
    canister_name: str,
    network: str,
    project_root: Path,
    *,
    identity: Optional[str] = None,
    yes: bool = False,
    logger=None,
) -> str:
    """Ensure ``canister_name`` has a live id on ``network``.

  When ``canister_ids.json`` or dfx resolves an id that no longer exists on the
  replica, offer to recreate (or recreate immediately with ``yes=True``).
    """
    existing = _dfx_canister_id(canister_name, network)
    if existing and not _is_canister_dead(existing, network):
        return existing

    if existing and _is_canister_dead(existing, network):
        console.print(
            Panel.fit(
                f"⚠️  Canister [bold]{canister_name}[/bold] id [cyan]{existing}[/cyan] "
                f"on network [bold]{network}[/bold] is missing or wiped on the IC.\n"
                "A new canister will be created and canister_ids.json updated.\n"
                "To wipe in-place state instead, re-run with [bold]--mode reinstall[/bold].",
                style="yellow",
            )
        )
        if not yes and not typer.confirm("Create a replacement canister?", default=True):
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)
        _clear_canister_id(project_root, canister_name, network)

    if not existing:
        console.print(f"[dim]No live id for {canister_name} on {network} — creating…[/dim]")

    return _create_canister(canister_name, network, identity, logger=logger)


def _dfx_deploy(
    canister: str,
    network: str,
    mode: str,
    identity: Optional[str],
    *,
    extra_args: Optional[List[str]] = None,
    env: Optional[Dict[str, str]] = None,
    logger=None,
) -> None:
    cmd = ["dfx", "deploy", canister, "--network", network, "--yes"]
    if mode != "auto":
        cmd.extend(["--mode", mode])
    if identity:
        cmd.extend(["--identity", identity])
    if extra_args:
        cmd.extend(extra_args)
    rc = run_command(cmd, env=env, logger=logger)
    if rc.returncode != 0:
        console.print(f"[red]❌ {canister} deploy failed[/red]")
        if "not found" in (rc.stderr or "").lower() or "not found" in (rc.stdout or "").lower():
            console.print(
                "[yellow]Hint: the canister id may be stale. Re-run with a fresh create "
                "(the command auto-recreates dead ids) or pass [bold]--mode reinstall[/bold].[/yellow]"
            )
        raise typer.Exit(rc.returncode)


def _fetch_gos_frontend_artifacts(project_root: Path, *, logger) -> None:
    script = project_root / "scripts" / "fetch_gos_artifacts.py"
    if not script.is_file():
        console.print(f"[red]❌ {script} not found — cannot deploy file_registry_frontend[/red]")
        raise typer.Exit(1)
    rc = run_command(
        [sys.executable, str(script), "--what", "frontend"],
        cwd=str(project_root),
        logger=logger,
    )
    if rc.returncode != 0:
        console.print("[red]❌ fetch_gos_artifacts.py failed[/red]")
        raise typer.Exit(rc.returncode)
    dist = project_root / ".external-assets" / "file_registry_frontend" / "dist"
    if not dist.is_dir() or not any(dist.iterdir()):
        console.print(f"[red]❌ file_registry_frontend dist missing at {dist}[/red]")
        raise typer.Exit(1)


def _ensure_marketplace_declarations(
    project_root: Path,
    *,
    dfx_env: Optional[Dict[str, str]] = None,
    logger=None,
) -> None:
    """Generate candid declarations needed by marketplace_frontend build."""
    did_path = project_root / "src" / MARKETPLACE_BACKEND / f"{MARKETPLACE_BACKEND}.did"
    if did_path.is_file():
        run_command(
            ["dfx", "generate", MARKETPLACE_BACKEND],
            cwd=str(project_root),
            env=dfx_env,
            logger=logger,
        )
        return
    env = (dfx_env or os.environ).copy()
    env["CANISTER_CANDID_PATH"] = str(did_path)
    main_py = project_root / "src" / MARKETPLACE_BACKEND / "main.py"
    if main_py.is_file():
        basilisk_py = basilisk_python_executable(project_root)
        run_command(
            [
                basilisk_py,
                "-m",
                "basilisk",
                MARKETPLACE_BACKEND,
                str(main_py),
            ],
            cwd=str(project_root),
            env=env,
            logger=logger,
        )
    if did_path.is_file():
        run_command(
            ["dfx", "generate", MARKETPLACE_BACKEND],
            cwd=str(project_root),
            env=dfx_env,
            logger=logger,
        )


def _write_ic_domains(project_root: Path, domain: str) -> None:
    """Write ``.well-known/ic-domains`` into marketplace_frontend static assets."""
    static_dir = project_root / "src" / MARKETPLACE_FRONTEND / "static" / ".well-known"
    static_dir.mkdir(parents=True, exist_ok=True)
    (static_dir / "ic-domains").write_text(f"{domain.strip()}\n", encoding="utf-8")
    console.print(f"[dim]Wrote {static_dir / 'ic-domains'}[/dim]")


def _build_marketplace_frontend(
    project_root: Path,
    network: str,
    env_config: Dict[str, Any],
    *,
    marketplace_backend_id: str,
    file_registry_id: str,
    skip_build: bool,
    dfx_env: Optional[Dict[str, str]] = None,
    logger=None,
) -> None:
    dist = project_root / "src" / MARKETPLACE_FRONTEND / "dist"
    if skip_build:
        if not dist.is_dir() or not any(dist.iterdir()):
            console.print(
                f"[red]❌ --skip-frontend-build set but {dist} is empty[/red]"
            )
            raise typer.Exit(1)
        console.print("[dim]Skipping marketplace_frontend npm build (--skip-frontend-build)[/dim]")
        return

    _ensure_marketplace_declarations(project_root, dfx_env=dfx_env, logger=logger)

    build_env = os.environ.copy()
    build_env["DFX_NETWORK"] = network
    build_env["CANISTER_ID_MARKETPLACE_BACKEND"] = marketplace_backend_id
    build_env["CANISTER_ID_FILE_REGISTRY"] = file_registry_id
    # VITE_-prefixed aliases: import.meta.env (the only env object that exists
    # in the browser bundle) only exposes VITE_* vars.
    build_env["VITE_CANISTER_ID_MARKETPLACE_BACKEND"] = marketplace_backend_id
    build_env["VITE_CANISTER_ID_FILE_REGISTRY"] = file_registry_id
    build_env["VITE_ENV_NAME"] = env_config.get("name", "")
    build_env["VITE_PORTAL_URL"] = env_config.get("portal_url", "")
    build_env["VITE_CASALS_URL"] = env_config.get("casals_url", "")
    build_env["VITE_REALMS_VERSION"] = env_config.get("realms_version", "main")
    billing_url = env_config.get("billing_service_url") or env_config.get("services", {}).get(
        "billing_url", ""
    )
    if billing_url:
        build_env["VITE_BILLING_SERVICE_URL"] = billing_url

    # Persist the build-time config as a Vite env file so that ANY production
    # build bakes the right values — including dfx's post-build `npm run build`
    # at the repo root, which runs with dfx's own env (no VITE_* vars) and would
    # otherwise overwrite dist/ with a config-less bundle before the asset sync.
    env_file = project_root / "src" / MARKETPLACE_FRONTEND / ".env.production"
    env_vars: Dict[str, str] = {}
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                env_vars[k.strip()] = v.strip()
    env_vars.update(
        {
            "VITE_CANISTER_ID_MARKETPLACE_BACKEND": marketplace_backend_id,
            "VITE_CANISTER_ID_FILE_REGISTRY": file_registry_id,
            "VITE_ENV_NAME": env_config.get("name", ""),
            "VITE_PORTAL_URL": env_config.get("portal_url", ""),
            "VITE_CASALS_URL": env_config.get("casals_url", ""),
            "VITE_REALMS_VERSION": env_config.get("realms_version", "main"),
        }
    )
    if billing_url:
        env_vars["VITE_BILLING_SERVICE_URL"] = billing_url
    if env_file.parent.is_dir():
        env_file.write_text("\n".join(f"{k}={v}" for k, v in env_vars.items()) + "\n")
        if logger:
            logger.info(f"Wrote {env_file} ({len(env_vars)} vars)")

    console.print(Panel.fit("🔨 Building marketplace_frontend", style="bold blue"))
    rc = run_command(
        ["npm", "run", "build", "--workspace=marketplace_frontend"],
        cwd=str(project_root),
        env=build_env,
        logger=logger,
    )
    if rc.returncode != 0:
        console.print("[red]❌ marketplace_frontend build failed[/red]")
        raise typer.Exit(rc.returncode)
    if not dist.is_dir() or not any(dist.iterdir()):
        console.print(f"[red]❌ Build did not produce {dist}[/red]")
        raise typer.Exit(1)


def _wire_marketplace_backend(
    network: str,
    file_registry_id: str,
    billing_service_principal: str,
) -> None:
    if file_registry_id:
        console.print("[dim]→ set_file_registry_canister_id[/dim]")
        result = _dfx_call(
            MARKETPLACE_BACKEND,
            "set_file_registry_canister_id",
            f'("{file_registry_id}")',
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


def _print_dns_instructions(domain: str, frontend_id: str) -> None:
    console.print("\n[bold cyan]🌐 Custom domain setup[/bold cyan]")
    console.print(
        f"  1. Upload complete — [bold].well-known/ic-domains[/bold] lists [cyan]{domain}[/cyan]."
    )
    console.print(
        f"  2. DNS: add a [bold]CNAME[/bold] record:\n"
        f"       [cyan]{domain}[/cyan]  →  [cyan]{domain}.icp1.io[/cyan]"
    )
    console.print(
        "     (Alternatively use the A/AAAA records shown at "
        "[link=https://reg.icp0.io]reg.icp0.io[/link] for your domain.)"
    )
    console.print(
        f"  3. Register the domain at [link=https://reg.icp0.io]https://reg.icp0.io[/link] "
        f"pointing to frontend canister [cyan]{frontend_id}[/cyan] (manual step)."
    )
    console.print(
        f"  4. After DNS propagates, open [link=https://{domain}]https://{domain}[/link]"
    )


def _print_deploy_summary(
    env_config: Dict[str, Any],
    network: str,
    canister_ids: Dict[str, str],
) -> None:
    domain = env_config.get("domain", "")
    portal = env_config.get("portal_url", "")
    table = Table(title=f"Environment '{env_config.get('name')}' deployment summary")
    table.add_column("Canister", style="cyan")
    table.add_column("ID", style="green")
    table.add_column("URL", style="blue")

    for name in PRODUCT_STACK:
        cid = canister_ids.get(name, "")
        if not cid:
            continue
        if "frontend" in name:
            url = f"https://{cid}.icp0.io/"
            if name == MARKETPLACE_FRONTEND and domain:
                url += f"\nhttps://{domain}/"
        else:
            url = f"https://rxs6w-5qaaa-aaaah-avp2a-cai.icp0.io/?id={cid}"
        table.add_row(name, cid, url)

    console.print(table)
    if portal:
        console.print(f"\n[dim]GaaS portal (separate stack): {portal}[/dim]")
    console.print(
        "\n[dim]Re-run [bold]realms env deploy --env "
        f"{env_config.get('name')}[/bold] to upgrade in place (default mode: auto).[/dim]"
    )


def env_deploy_command(
    *,
    env_name: str,
    mode: str = "auto",
    identity: Optional[str] = None,
    yes: bool = False,
    skip_frontend_build: bool = False,
    with_domain: bool = True,
) -> None:
    """Deploy the full Realms GOS product stack for one environment."""
    project_root = get_project_root()
    log_dir = project_root.absolute()
    set_log_dir(log_dir)
    logger = get_realms_logger(log_dir=log_dir)

    env_config = load_env_config(env_name, project_root)
    network = env_config.get("network", env_name)
    domain = env_config.get("domain", "")
    billing_principal = (env_config.get("billing_service_principal") or "").strip()

    logger.info("=" * 60)
    logger.info(f"env deploy → env={env_name} network={network} mode={mode}")
    if identity:
        logger.info(f"identity={identity}")
    logger.info("=" * 60)

    dfx_env = dfx_env_with_basilisk(project_root)

    console.print(
        Panel.fit(
            f"🚀 Deploying Realms product stack\n"
            f"Environment: [bold]{env_name}[/bold]  Network: [bold]{network}[/bold]\n"
            f"Domain: [cyan]{domain or '(none)'}[/cyan]",
            style="bold blue",
        )
    )

    if mode == "reinstall" and not yes:
        if not typer.confirm(
            f"--mode reinstall will wipe canister state on {network}. Continue?",
            default=False,
        ):
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

    # a. Resolve / create canister ids for the whole stack.
    resolved: Dict[str, str] = {}
    for canister_name in PRODUCT_STACK:
        console.print(f"[dim]Resolving {canister_name}…[/dim]")
        resolved[canister_name] = resolve_or_create_canister(
            canister_name,
            network,
            project_root,
            identity=identity,
            yes=yes,
            logger=logger,
        )

    # b. file_registry + file_registry_frontend
    console.print(Panel.fit("📦 Deploying file_registry", style="bold blue"))
    _dfx_deploy(FILE_REGISTRY, network, mode, identity, env=dfx_env, logger=logger)

    console.print(Panel.fit("📦 Deploying file_registry_frontend", style="bold blue"))
    _fetch_gos_frontend_artifacts(project_root, logger=logger)
    _dfx_deploy(
        FILE_REGISTRY_FRONTEND, network, mode, identity, env=dfx_env, logger=logger
    )

    fr_id = _dfx_canister_id(FILE_REGISTRY, network) or resolved[FILE_REGISTRY]

    # c. marketplace_backend + wiring
    console.print(Panel.fit("🛒 Deploying marketplace_backend", style="bold blue"))
    _dfx_deploy(
        MARKETPLACE_BACKEND,
        network,
        mode,
        identity,
        extra_args=["--argument", "(null)"],
        env=dfx_env,
        logger=logger,
    )
    _wire_marketplace_backend(network, fr_id, billing_principal)

    mb_id = _dfx_canister_id(MARKETPLACE_BACKEND, network) or resolved[MARKETPLACE_BACKEND]

    # d. marketplace_frontend build + deploy
    if with_domain and domain:
        _write_ic_domains(project_root, domain)

    _build_marketplace_frontend(
        project_root,
        network,
        env_config,
        marketplace_backend_id=mb_id,
        file_registry_id=fr_id,
        skip_build=skip_frontend_build,
        dfx_env=dfx_env,
        logger=logger,
    )

    console.print(Panel.fit("🖼️  Deploying marketplace_frontend", style="bold blue"))
    _dfx_deploy(
        MARKETPLACE_FRONTEND, network, mode, identity, env=dfx_env, logger=logger
    )

    mf_id = _dfx_canister_id(MARKETPLACE_FRONTEND, network) or resolved[MARKETPLACE_FRONTEND]

    console.print("\n[green]✅ Environment stack deployed successfully![/green]")
    display_canister_urls_json(project_root, network, f"{env_name} product stack")

    final_ids = {name: _dfx_canister_id(name, network) or resolved.get(name, "") for name in PRODUCT_STACK}
    _print_deploy_summary(env_config, network, final_ids)

    if with_domain and domain:
        _print_dns_instructions(domain, mf_id)


def env_status_command(*, env_name: str, identity: Optional[str] = None) -> None:
    """Print canister IDs and one-line dfx status for the product stack."""
    project_root = get_project_root()
    env_config = load_env_config(env_name, project_root)
    network = env_config.get("network", env_name)

    console.print(
        Panel.fit(
            f"📊 Environment status: [bold]{env_name}[/bold] (network [bold]{network}[/bold])",
            style="bold blue",
        )
    )

    table = Table()
    table.add_column("Canister", style="cyan")
    table.add_column("ID", style="green")
    table.add_column("dfx canister status", style="dim")

    for canister_name in PRODUCT_STACK:
        cid = _dfx_canister_id(canister_name, network) or ""
        if not cid:
            ids = _read_canister_ids(project_root)
            cid = ids.get(canister_name, {}).get(network, "")
        status = _canister_status_line(cid, network) if cid else "not configured"
        table.add_row(canister_name, cid or "—", status)

    console.print(table)

    domain = env_config.get("domain", "")
    mf_id = _dfx_canister_id(MARKETPLACE_FRONTEND, network) or ""
    if domain and mf_id:
        console.print(f"\n[dim]Product URL: https://{domain}/  (icp0: https://{mf_id}.icp0.io/)[/dim]")
    portal = env_config.get("portal_url", "")
    if portal:
        console.print(f"[dim]GaaS portal: {portal}[/dim]")

    if identity:
        console.print(f"[dim]Identity: {identity}[/dim]")
