"""``realms seed`` — Realms GOS product infrastructure per network.

By default, **adopts** existing product canisters and the Realms GOS Casals
conductor (authorize + register + sheet reconcile). Pass ``--rebuild`` to
destroy product canisters (except ``marketplace_frontend`` DNS), delete the
Realms GOS Casals stack, and mint a new conductor.

Does not touch GaaS Casals (``gaas new``). ``--skip-product`` is catalog-only
and does not destroy anything.

After the product stack is reconciled, registers product canister IDs on the
conductor and runs ``casals sheet deploy`` of repo-root ``casals.json``
only (never a union with GaaS, never onto GaaS Casals). Then writes the
product Casals frontend principal onto the marketplace backend.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel

from ..casals_product import (
    _PRODUCT_CASALS_REALMS_KEYS,
    _gaas_casals_ids,
    authorize_product_wasms,
    check_canister_liveness,
    configure_gaas_installer_product_pointers,
    deploy_product_sheet_on_casals,
    finish_casals_rebuild,
    load_gos_canisters,
    log_stale_product_canisters,
    partition_product_canister_inventory,
    publish_casals_frontend_to_marketplace,
    rebuild_casals_conductor,
    resolve_conductor_id,
)
from .env import (
    DNS_PRODUCT_FRONTEND,
    PRODUCT_STACK_DESTROY,
    _product_canister_id,
    _read_canister_ids,
    env_deploy_command,
    load_env_config,
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


def _resolve_seed_phase(
    from_phase: Optional[str],
    rebuild: bool,
    destroy_except_frontend: bool,
) -> str:
    if from_phase:
        return from_phase.replace("-", "_")
    if rebuild or destroy_except_frontend:
        return "destroy"
    return "authorize"


def _print_resume_hint(env_name: str, phase: str) -> None:
    """Print the command that continues this run, so a failure is not a restart.

    Without it an operator has to infer the phase from the CLI help, and picking
    the wrong one silently skips steps (e.g. resuming at ``env_deploy`` leaves the
    Casals file registry on the Casals-repo WASM, which lacks the methods the
    catalog phase needs).
    """
    console.print(
        f"[dim]Resume with: realms seed -e {env_name} --from-phase {phase}[/dim]"
    )


def _filter_live_destroy_targets(
    targets: list[tuple[str, str]],
    *,
    network: str,
    identity: Optional[str],
) -> list[tuple[str, str]]:
    """Drop principals already absent on IC from a destroy plan."""
    live: list[tuple[str, str]] = []
    for name, cid in targets:
        try:
            exists = check_canister_liveness(
                cid, network=network, identity=identity
            )
        except RuntimeError:
            exists = True
        if exists:
            live.append((name, cid))
        else:
            console.print(
                f"[dim]{name} {cid} already absent on IC — skipping delete[/dim]"
            )
    return live


def _reconcile_stale_product_ids_on_adopt(
    *,
    env_name: str,
    network: str,
    identity: Optional[str],
    project_root: Path,
    yes: bool,
    skip_frontend_build: bool,
    with_domain: bool,
) -> None:
    """Mint or deploy replacements for absent product ids before adopt."""
    conductor = resolve_conductor_id(env_name, project_root)
    conductor_dead = False
    if conductor:
        try:
            conductor_dead = not check_canister_liveness(
                conductor, network=network, identity=identity
            )
        except RuntimeError as exc:
            raise RuntimeError(
                f"cannot verify Realms GOS Casals conductor {conductor}: {exc}"
            ) from exc
    else:
        conductor_dead = True

    _live, dead_product = partition_product_canister_inventory(
        network, project_root, identity=identity
    )

    if conductor_dead:
        stale = conductor or "(none configured)"
        console.print(
            f"[yellow]⚠️  casals_backend: stale principal {stale} not on IC "
            f"— minting new Realms GOS Casals conductor[/yellow]"
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

    if dead_product:
        log_stale_product_canisters(
            dead_product, action="recreating via env deploy"
        )
        env_deploy_command(
            env_name=env_name,
            mode="auto",
            identity=identity,
            yes=yes,
            skip_frontend_build=skip_frontend_build,
            with_domain=with_domain,
        )


def _plan_rebuild_destroy_targets(
    *,
    env_name: str,
    network: str,
    project_root: Path,
    identity: Optional[str] = None,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return (product_targets, casals_targets) as ``(name, canister_id)`` pairs."""
    gos = load_gos_canisters(env_name, project_root)
    keep_ids: list[str] = []
    for cid in (
        (_product_canister_id(network, DNS_PRODUCT_FRONTEND, project_root) or "").strip(),
        (gos.get(DNS_PRODUCT_FRONTEND) or "").strip(),
    ):
        if cid and cid not in keep_ids:
            keep_ids.append(cid)

    product_targets: list[tuple[str, str]] = []
    seen: set[str] = set(keep_ids)
    for name in PRODUCT_STACK_DESTROY:
        cids: list[str] = []
        primary = (_product_canister_id(network, name, project_root) or "").strip()
        if primary:
            cids.append(primary)
        extra = (gos.get(name) or "").strip()
        if extra and extra not in cids:
            cids.append(extra)
        for cid in cids:
            if cid in keep_ids or cid in seen:
                continue
            seen.add(cid)
            product_targets.append((name, cid))

    protected = _gaas_casals_ids(env_name, project_root)
    realms_ids = _read_canister_ids(project_root)
    casals_targets: list[tuple[str, str]] = []
    casals_seen: set[str] = set()
    for key in _PRODUCT_CASALS_REALMS_KEYS:
        cid = ((realms_ids.get(key) or {}).get(network) or "").strip()
        if not cid or cid in casals_seen or cid in protected:
            continue
        casals_seen.add(cid)
        casals_targets.append((key, cid))

    product_targets = _filter_live_destroy_targets(
        product_targets, network=network, identity=identity
    )
    casals_targets = _filter_live_destroy_targets(
        casals_targets, network=network, identity=identity
    )
    return product_targets, casals_targets


def _confirm_rebuild_destroy(
    *,
    env_name: str,
    network: str,
    project_root: Path,
    yes: bool,
    identity: Optional[str] = None,
) -> None:
    """Prompt before the destructive rebuild path (skipped when ``yes``)."""
    product_targets, casals_targets = _plan_rebuild_destroy_targets(
        env_name=env_name,
        network=network,
        project_root=project_root,
        identity=identity,
    )
    if not product_targets and not casals_targets:
        console.print(
            "[dim]No product or Realms GOS Casals ids in inventory to destroy.[/dim]"
        )
        return

    lines = [
        f"Environment: [bold]{env_name}[/bold]  Network: [bold]{network}[/bold]",
        "",
        "[bold red]This will delete_canister on every id below[/bold red] "
        "(recover cycles), then mint a [bold]new[/bold] Realms GOS Casals conductor.",
        "GaaS Casals, installer, and registry are not touched.",
        "",
    ]
    if product_targets:
        lines.append(
            "Product canisters to delete (marketplace_frontend DNS id is kept):"
        )
        for name, cid in product_targets:
            lines.append(f"  • {name}: {cid}")
        lines.append("")
    if casals_targets:
        lines.append(
            "Realms GOS Casals stack to delete (casals new will mint replacements):"
        )
        for name, cid in casals_targets:
            lines.append(f"  • {name}: {cid}")
        lines.append("")

    console.print(Panel.fit("\n".join(lines), title="realms seed --rebuild", style="yellow"))

    if yes:
        return
    if not typer.confirm(
        "Proceed with delete_canister on the ids above and mint a new conductor?",
        default=False,
    ):
        console.print("[yellow]Aborted.[/yellow]")
        raise typer.Exit(0)


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
    rebuild: bool = False,
    from_phase: Optional[str] = None,
) -> None:
    """Deploy Realms product infra and publish the package catalog.

    Default: adopt existing product canisters and Realms GOS Casals (no destroy).
    ``--rebuild`` destroys product + Casals and mints a new conductor.
    ``from_phase`` resumes after a failed rebuild:
    ``catalog`` retries Casals catalog seed then product deploy; ``env_deploy``
    skips destroy and Casals recreate; ``destroy`` runs the full rebuild path.
    """
    project_root = get_project_root()
    env_config = load_env_config(env_name, project_root)
    network = env_config.get("network", env_name)
    do_product = not skip_product
    phase = _resolve_seed_phase(from_phase, rebuild, destroy_except_frontend)
    if phase not in ("destroy", "catalog", "env_deploy", "authorize"):
        console.print(
            f"[red]❌ unknown --from-phase {from_phase!r} "
            "(destroy, catalog, env_deploy, authorize)[/red]"
        )
        raise typer.Exit(1)

    default_adopt = phase == "authorize" and not from_phase and not rebuild
    panel_lines = [
        f"🌱 realms seed\n"
        f"Environment: [bold]{env_name}[/bold]  Network: [bold]{network}[/bold]",
    ]
    if default_adopt:
        panel_lines.append(
            "Adopts existing Realms GOS Casals + product canisters (no destroy)."
        )
    elif phase == "destroy":
        panel_lines.append(
            "Rebuild: destroys Realms GOS Casals + product "
            "(keeps marketplace_frontend DNS)."
        )
    else:
        panel_lines.append(f"Resume from phase: [bold]{phase}[/bold]")
    panel_lines.append("Does not touch GaaS Casals / installer / registry.")
    console.print(Panel.fit("\n".join(panel_lines), style="bold blue"))

    if skip_product and destroy_except_frontend:
        console.print(
            "[red]❌ --destroy-except-marketplace-frontend cannot be combined "
            "with --skip-product (the non-DNS canisters would stay gone).[/red]"
        )
        raise typer.Exit(1)

    if skip_product and from_phase:
        console.print(
            "[red]❌ --from-phase cannot be combined with --skip-product[/red]"
        )
        raise typer.Exit(1)

    if do_product:
        if phase == "destroy":
            _confirm_rebuild_destroy(
                env_name=env_name,
                network=network,
                project_root=project_root,
                yes=yes,
                identity=identity,
            )
            destroy_yes = True
            destroy_product_stack_except_frontend(
                network=network,
                project_root=project_root,
                identity=identity,
                yes=destroy_yes,
                env_name=env_name,
            )
            try:
                rebuild_casals_conductor(
                    env_name=env_name,
                    network=network,
                    identity=identity,
                    project_root=project_root,
                    yes=destroy_yes,
                )
            except RuntimeError as exc:
                console.print(f"[red]❌ casals new failed: {exc}[/red]")
                # If the conductor was already minted, the destroy + mint work is
                # done and only the finish/catalog steps are missing.
                minted = _product_canister_id(
                    network, "casals_backend", project_root
                )
                _print_resume_hint(
                    env_name,
                    "catalog"
                    if minted
                    and check_canister_liveness(
                        minted, network=network, identity=identity
                    )
                    else "destroy",
                )
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

        if phase == "authorize":
            _reconcile_stale_product_ids_on_adopt(
                env_name=env_name,
                network=network,
                identity=identity,
                project_root=project_root,
                yes=yes,
                skip_frontend_build=skip_frontend_build,
                with_domain=with_domain,
            )

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
