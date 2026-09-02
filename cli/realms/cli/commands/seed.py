"""``realms seed`` — Realms GOS product infrastructure per network.

Always destroys and re-creates the Casals conductor (``casals new``), then
deploys the ``*.realmsgos.org`` stack (marketplace, fleet file_registry,
token, nft) and publishes the extension/codex catalog. GaaS (``gaas new``)
does not own these canisters. ``--skip-product`` is catalog-only and does not
destroy anything.

After the product stack is deployed, registers GaaS + product canister IDs
on the new conductor and runs ``casals sheet deploy`` of the **union** of
``gos-as-a-service/casals.json`` and repo-root ``casals.json``. Product-only
deploy is forbidden (Pass 2 would stop installer/registry).
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.panel import Panel

from ..casals_product import (
    authorize_product_wasms,
    deploy_product_sheet_on_casals,
    rebuild_casals_conductor,
)
from .env import (
    env_deploy_command,
    load_env_config,
    _read_canister_ids,
    destroy_product_stack_except_frontend,
)
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
    destroy_except_frontend: bool = False,
) -> None:
    """Deploy Realms product infra and publish the package catalog.

    Destroys Casals and product canisters (except marketplace_frontend) unless
    ``skip_product`` is set.
    """
    project_root = get_project_root()
    env_config = load_env_config(env_name, project_root)
    network = env_config.get("network", env_name)
    rebuild = not skip_product

    console.print(
        Panel.fit(
            f"🌱 realms seed\n"
            f"Environment: [bold]{env_name}[/bold]  Network: [bold]{network}[/bold]\n"
            f"Destroys Casals + product (keeps marketplace_frontend DNS).\n"
            f"Owns marketplace + file_registry + token/nft + catalog — not the GaaS portal.",
            style="bold blue",
        )
    )

    if skip_product and destroy_except_frontend:
        console.print(
            "[red]❌ --destroy-except-marketplace-frontend cannot be combined "
            "with --skip-product (the non-DNS canisters would stay gone).[/red]"
        )
        raise typer.Exit(1)

    if rebuild:
        destroy_product_stack_except_frontend(
            network=network,
            project_root=project_root,
            identity=identity,
            yes=yes,
        )
        try:
            rebuild_casals_conductor(
                env_name=env_name,
                network=network,
                identity=identity,
                project_root=project_root,
                yes=yes,
            )
        except RuntimeError as exc:
            console.print(f"[red]❌ casals new failed: {exc}[/red]")
            raise typer.Exit(1) from exc

        env_deploy_command(
            env_name=env_name,
            mode="auto",
            identity=identity,
            yes=yes,
            skip_frontend_build=skip_frontend_build,
            with_domain=with_domain,
        )

        try:
            authorize_product_wasms(
                env_name=env_name,
                network=network,
                identity=identity,
                project_root=project_root,
            )
            console.print("[green]✓ Product WASMs authorized in Casals catalog[/green]")
        except RuntimeError as exc:
            console.print(f"[red]❌ Product WASM authorize failed: {exc}[/red]")
            raise typer.Exit(1) from exc

        try:
            deployed, detail = deploy_product_sheet_on_casals(
                env_name=env_name,
                network=network,
                identity=identity,
                project_root=project_root,
            )
            if deployed:
                console.print(
                    f"[green]✓ Union sheet deployed on GaaS Casals[/green] "
                    f"[dim]({detail})[/dim]"
                )
            else:
                console.print(
                    f"[dim]Casals union sheet skipped: {detail}[/dim]"
                )
        except RuntimeError as exc:
            console.print(f"[yellow]⚠️  Casals union sheet failed: {exc}[/yellow]")
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

    console.print(f"\n[green]✅ realms seed complete for {env_name} ({network})[/green]")
