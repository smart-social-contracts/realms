"""``realms seed`` — Realms GOS product infrastructure per network.

Deploys the ``*.realmsgos.org`` stack (marketplace + file_registry) and
publishes the extension/codex catalog. GaaS (``gaas new``) does not own these
canisters.

The Realms Casals orchestra (second stack) is created when Casals GitHub
release assets ship (``casals_backend.wasm.gz`` etc.). Until then this command
prints that skip rather than minting a half-wired conductor.
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.panel import Panel

from .env import env_deploy_command, load_env_config, _read_canister_ids
from .files import files_publish_branding_command, files_publish_command
from .marketplace import FILE_REGISTRY, _dfx_canister_id
from ..utils import console, get_project_root


def _live_file_registry_id(network: str, project_root=None) -> Optional[str]:
    """Prefer canister_ids.json (updated by env deploy) over baked NETWORK_INFRA."""
    root = project_root or get_project_root()
    cid = (_read_canister_ids(root).get("file_registry") or {}).get(network)
    if cid:
        return cid
    return _dfx_canister_id(FILE_REGISTRY, network)


def seed_command(
    *,
    env_name: str,
    mode: str = "auto",
    identity: Optional[str] = None,
    yes: bool = False,
    skip_frontend_build: bool = False,
    skip_product: bool = False,
    skip_catalog: bool = False,
    skip_branding: bool = False,
    with_domain: bool = True,
) -> None:
    """Deploy Realms product infra and publish the package catalog."""
    project_root = get_project_root()
    env_config = load_env_config(env_name, project_root)
    network = env_config.get("network", env_name)

    console.print(
        Panel.fit(
            f"🌱 realms seed\n"
            f"Environment: [bold]{env_name}[/bold]  Network: [bold]{network}[/bold]\n"
            f"Owns marketplace + file_registry + catalog — not the GaaS portal.",
            style="bold blue",
        )
    )

    if not skip_product:
        env_deploy_command(
            env_name=env_name,
            mode=mode,
            identity=identity,
            yes=yes,
            skip_frontend_build=skip_frontend_build,
            with_domain=with_domain,
        )
    else:
        console.print("[dim]skip product stack (--skip-product)[/dim]")

    if not skip_catalog:
        console.print(Panel.fit("📚 Publishing extension/codex catalog", style="bold blue"))
        registry = _live_file_registry_id(network, project_root)
        files_publish_command(
            network=network,
            identity=identity,
            registry=registry,
        )
        if not skip_branding:
            try:
                files_publish_branding_command(
                    network=network,
                    identity=identity,
                    registry=registry,
                )
            except typer.Exit:
                console.print(
                    "[yellow]branding publish skipped (demo branding sources missing)[/yellow]"
                )
    else:
        console.print("[dim]skip catalog (--skip-catalog)[/dim]")

    console.print(
        "[dim]Realms Casals orchestra not minted: Casals GitHub releases do not "
        "yet publish casals_backend.wasm.gz / orchestration templates. "
        "GaaS Casals stays with `gaas new`.[/dim]"
    )
    console.print(f"\n[green]✅ realms seed complete for {env_name} ({network})[/green]")
