"""``realms seed`` — Realms GOS product infrastructure per network.

Always destroys and re-creates the **Realms GOS** Casals conductor
(``casals new``), then deploys the ``*.realmsgos.org`` stack (marketplace,
fleet file_registry, token, nft) and publishes the extension/codex catalog.
Does not touch GaaS Casals (``gaas new``). ``--skip-product`` is catalog-only
and does not destroy anything.

After the product stack is deployed, registers product canister IDs on the
new conductor and runs ``casals sheet deploy`` of repo-root ``casals.json``
only (never a union with GaaS, never onto GaaS Casals). Then writes the
product Casals frontend principal onto the marketplace backend.
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.panel import Panel

from ..casals_product import (
    authorize_product_wasms,
    configure_gaas_installer_product_pointers,
    deploy_product_sheet_on_casals,
    finish_casals_rebuild,
    publish_casals_frontend_to_marketplace,
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
    from_phase: Optional[str] = None,
) -> None:
    """Deploy Realms product infra and publish the package catalog.

    Destroys Realms GOS Casals and product canisters (except marketplace_frontend)
    unless ``skip_product`` is set. ``from_phase`` resumes after a failed rebuild:
    ``catalog`` retries Casals catalog seed then product deploy; ``env_deploy``
    skips destroy and Casals recreate.
    """
    project_root = get_project_root()
    env_config = load_env_config(env_name, project_root)
    network = env_config.get("network", env_name)
    rebuild = not skip_product
    phase = (from_phase or "destroy").replace("-", "_")
    if phase not in ("destroy", "catalog", "env_deploy", "authorize"):
        console.print(
            f"[red]❌ unknown --from-phase {from_phase!r} "
            "(destroy, catalog, env_deploy, authorize)[/red]"
        )
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"🌱 realms seed\n"
            f"Environment: [bold]{env_name}[/bold]  Network: [bold]{network}[/bold]\n"
            f"Destroys Realms GOS Casals + product (keeps marketplace_frontend DNS).\n"
            f"Does not touch GaaS Casals / installer / registry.",
            style="bold blue",
        )
    )

    if skip_product and destroy_except_frontend:
        console.print(
            "[red]❌ --destroy-except-marketplace-frontend cannot be combined "
            "with --skip-product (the non-DNS canisters would stay gone).[/red]"
        )
        raise typer.Exit(1)

    if skip_product and phase != "destroy":
        console.print(
            "[red]❌ --from-phase cannot be combined with --skip-product[/red]"
        )
        raise typer.Exit(1)

    if rebuild:
        if phase == "destroy":
            destroy_product_stack_except_frontend(
                network=network,
                project_root=project_root,
                identity=identity,
                yes=yes,
                env_name=env_name,
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
        elif phase == "catalog":
            try:
                finish_casals_rebuild(
                    env_name=env_name,
                    network=network,
                    identity=identity,
                    project_root=project_root,
                )
                console.print("[green]✓ Casals catalog seeded[/green]")
            except RuntimeError as exc:
                console.print(f"[red]❌ casals finish/catalog failed: {exc}[/red]")
                raise typer.Exit(1) from exc

        if phase != "authorize":
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
                    f"[green]✓ Product sheet deployed on Realms GOS Casals[/green] "
                    f"[dim]({detail})[/dim]"
                )
            else:
                console.print(
                    f"[dim]Casals product sheet skipped: {detail}[/dim]"
                )
        except RuntimeError as exc:
            console.print(f"[yellow]⚠️  Casals product sheet failed: {exc}[/yellow]")

        try:
            publish_casals_frontend_to_marketplace(
                env_name=env_name,
                canisters={},
                network=network,
                identity=identity,
                project_root=project_root,
            )
        except RuntimeError as exc:
            console.print(f"[yellow]⚠️  {exc}[/yellow]")

        try:
            configure_gaas_installer_product_pointers(
                env_name=env_name,
                network=network,
                identity=identity,
                project_root=project_root,
            )
        except RuntimeError as exc:
            console.print(f"[yellow]⚠️  {exc}[/yellow]")
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
