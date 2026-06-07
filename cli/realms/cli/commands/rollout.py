"""Casals-native upgrade rollout orchestrator.

`realms rollout` upgrades (or reinstalls) any combination of

    environments  x  targets (realms + infra)  x  canister-kind

by driving each environment's Casals instance directly:

  - backend canisters  -> Casals `upgrade_to` (snapshot -> install -> verify
    module hash -> rollback-all-on-failure, built in);
  - frontend canisters -> Casals `upgrade_to` (install the new certified-assets
    WASM, which repoints the canister's `wasm_key`/bundle namespace) followed by
    the batched `provision_assets` loop to upload the new asset bundle.

Snapshot management is automatic and always on (it is part of `upgrade_to`).
The orchestrator is dry-run by default and prints the full action matrix before
touching anything; `--execute` is required to apply, and `reinstall` requires an
extra confirmation because a successful reinstall permanently wipes state.

This path is independent of the legacy off-chain deployer: it never touches the
registry version catalog, so old and new deployment paths coexist.
"""

import json
import time
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..casals_versions import MAIN_CHANNEL, pick_latest_main_key
from .extension import _dfx_call

console = Console()

# ── Per-environment Casals canister IDs ─────────────────────────────────────
# Casals instances live on IC mainnet; add staging/demo once deployed there.
_CASALS_IDS = {
    "test": "qthgp-3yaaa-aaaae-agveq-cai",
    "demo": "jo3cj-faaaa-aaaac-bffea-cai",
    "staging": "jj2e5-iyaaa-aaaac-bffeq-cai",
}

# Casals canisters are on mainnet; every dfx network alias points at icp0.io,
# so we always reach them via the built-in `ic` network.
_CASALS_NETWORK = "ic"

_DEPLOYMENTS_SECTION = "Deployments"
_INFRA_SECTION = "Infra"

# Stands in the Deployments section are realms and use this artifact family.
_REALM_FAMILY = "realm"

# Infra stand name -> artifact family base. Backend WASMs are published under
# "<family>-backend@<version>" and frontends under "<family>-assets@<version>".
_INFRA_FAMILY = {
    "installer": "installer",
    "realm-registry": "registry",
    "file-registry": "file-registry",
    "platform-dashboard": "dashboard",
    "marketplace": "marketplace",
    "token": "token",
    "nft": "nft",
}

# Reinstalling these wipes shared platform state (artifact store / realm
# catalog), so they are excluded from reinstall unless explicitly opted in.
_DESTRUCTIVE_INFRA_REINSTALL = {"file-registry", "realm-registry"}

# How many bundle files to copy per provision_assets ingress call. Kept small so
# a single call (which pulls each file from file_registry and pushes it into the
# asset canister) finishes well within the ~5 min ingress window even when the
# batch contains large multi-chunk files (e.g. background.png).
_BUNDLE_BATCH = 6
_BUNDLE_MAX_ITERS = 400


def _casals_query(casals: str, method: str, payload: Optional[dict] = None):
    if payload is None:
        candid = "()"
    else:
        arg = json.dumps(payload)
        candid = '("' + arg.replace("\\", "\\\\").replace('"', '\\"') + '")'
    raw = _dfx_call(casals, method, candid, _CASALS_NETWORK, None, is_query=True, timeout=120)
    return json.loads(raw)


def _casals_update(casals: str, method: str, payload: dict, identity: Optional[str]):
    arg = json.dumps(payload)
    candid = '("' + arg.replace("\\", "\\\\").replace('"', '\\"') + '")'
    raw = _dfx_call(casals, method, candid, _CASALS_NETWORK, identity, timeout=300)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "error": f"unparseable response: {raw[:200]}"}


def _resolve_environments(environments: str) -> list[str]:
    raw = [e.strip() for e in environments.split(",") if e.strip()]
    if not raw or raw == ["all"]:
        return list(_CASALS_IDS.keys())
    return raw


def _wasm_family(pub_family: str, kind: str) -> str:
    return f"{pub_family}-backend" if kind == "backend" else f"{pub_family}-assets"


def _resolve_wasm_key(authorized: list, pub_family: str, kind: str, version: str) -> Optional[str]:
    """Find the authorized-wasm key for (family, kind, version) in an env's Casals."""
    fam = _wasm_family(pub_family, kind)
    candidates = [w for w in authorized if w.get("family") == fam]
    if not candidates:
        return None
    if version in (MAIN_CHANNEL, "latest-main"):
        return pick_latest_main_key(candidates)
    if version == "latest":
        for w in candidates:
            if w.get("latest"):
                return w.get("key")
        # Fallback: list_authorized_wasms returns newest-first within a family.
        return candidates[0].get("key")
    for w in candidates:
        if w.get("version") == version:
            return w.get("key")
    return None


def _family_for_stand(section_name: str, stand_name: str, realm_family: str) -> Optional[str]:
    if section_name == _DEPLOYMENTS_SECTION:
        return realm_family
    if section_name == _INFRA_SECTION:
        return _INFRA_FAMILY.get(stand_name)
    return None


def _select_stands(tree: dict, targets: list[str]) -> list[tuple[str, dict]]:
    """Return (section_name, stand_view) tuples matching the target selectors."""
    want_realms = any(t in ("all", "all-realms") for t in targets)
    want_infra = any(t in ("all", "all-infra") for t in targets)
    explicit = {t for t in targets if t not in ("all", "all-realms", "all-infra")}

    selected = []
    for sec in tree.get("sections", []):
        sname = sec.get("name", "")
        for stand in sec.get("stands", []):
            stname = stand.get("name", "")
            if (
                (want_realms and sname == _DEPLOYMENTS_SECTION)
                or (want_infra and sname == _INFRA_SECTION)
                or (stname in explicit)
            ):
                selected.append((sname, stand))
    return selected


def _build_plan(env: str, casals: str, targets: list[str], scope: str,
                mode: str, version: str, realm_family: str) -> list[dict]:
    """Return a list of planned per-canister actions for one environment."""
    tree = _casals_query(casals, "get_tree")
    authorized = _casals_query(casals, "list_authorized_wasms", {})

    actions: list[dict] = []
    for section_name, stand in _select_stands(tree, targets):
        stand_name = stand.get("name", "")
        pub_family = _family_for_stand(section_name, stand_name, realm_family)
        for can in stand.get("canisters", []):
            kind = can.get("kind", "")
            if scope != "both" and kind != scope:
                continue
            if kind not in ("backend", "frontend"):
                continue
            action = {
                "env": env, "casals": casals, "section": section_name,
                "stand": stand_name, "canister": can.get("name", ""),
                "canister_id": can.get("canister_id", ""), "kind": kind,
                "mode": mode, "wasm_key": None, "note": "",
            }
            if not pub_family:
                action["note"] = f"no family mapping for stand '{stand_name}'"
            else:
                key = _resolve_wasm_key(authorized, pub_family, kind, version)
                if key:
                    action["wasm_key"] = key
                else:
                    action["note"] = (
                        f"no authorized {_wasm_family(pub_family, kind)} "
                        f"@{version} in {env} Casals"
                    )
            actions.append(action)
    return actions


def _print_plan(actions: list[dict]) -> None:
    table = Table(title="Rollout plan", show_lines=False, header_style="bold cyan")
    table.add_column("env")
    table.add_column("section")
    table.add_column("stand")
    table.add_column("canister")
    table.add_column("kind")
    table.add_column("mode")
    table.add_column("wasm_key / note")
    for a in actions:
        target = a["wasm_key"] or f"[yellow]SKIP: {a['note']}[/yellow]"
        mode_disp = a["mode"]
        if a["mode"] == "reinstall":
            mode_disp = f"[red]{a['mode']}[/red]"
        table.add_row(a["env"], a["section"], a["stand"], a["canister"],
                      a["kind"], mode_disp, target)
    console.print(table)


def _upgrade_frontend(action: dict, identity: Optional[str]) -> tuple[bool, str]:
    casals, name = action["casals"], action["canister"]
    # 1. Install the new certified-assets WASM (repoints wasm_key/bundle namespace).
    res = _casals_update(casals, "upgrade_to", {
        "canister": name, "wasm_key": action["wasm_key"],
        "reinstall": action["mode"] == "reinstall",
    }, identity)
    if not res.get("ok"):
        return False, f"upgrade_to: {res.get('error', res)}"
    # 2. Upload the new asset bundle in batches that fit the ingress window.
    offset = 0
    for _ in range(_BUNDLE_MAX_ITERS):
        # Each batch is retried a few times so a transient replica comms error
        # (e.g. a dropped read_state) doesn't abort the whole bundle.
        res = None
        for attempt in range(4):
            try:
                res = _casals_update(casals, "provision_assets", {
                    "canister": name, "offset": offset, "limit": _BUNDLE_BATCH,
                }, identity)
                break
            except Exception as e:  # noqa: BLE001 - transient; retry
                if attempt == 3:
                    return False, f"provision_assets(offset={offset}): {e}"
                time.sleep(3)
        if not res.get("ok"):
            return False, f"provision_assets: {res.get('error', res)}"
        bundle = res.get("bundle")
        if not bundle:
            break
        if bundle.get("done"):
            return True, f"bundle {bundle.get('total', '?')} files"
        offset = bundle.get("next_offset", offset + _BUNDLE_BATCH)
    return True, "uploaded"


def _upgrade_backend(action: dict, identity: Optional[str]) -> tuple[bool, str]:
    res = _casals_update(action["casals"], "upgrade_to", {
        "canister": action["canister"], "wasm_key": action["wasm_key"],
        "reinstall": action["mode"] == "reinstall",
    }, identity)
    if not res.get("ok"):
        return False, f"{res.get('error', res)}"
    return True, f"hash {(res.get('wasm_hash') or '')[:16]}"


def rollout_command(
    environments: str,
    targets: str,
    scope: str = "both",
    mode: str = "upgrade",
    version: str = "latest",
    realm_family: str = "realm",
    execute: bool = False,
    include_infra_reinstall: bool = False,
    yes: bool = False,
    identity: Optional[str] = None,
) -> None:
    if scope not in ("backend", "frontend", "both"):
        raise typer.BadParameter("--scope must be backend, frontend, or both")
    if mode not in ("upgrade", "reinstall"):
        raise typer.BadParameter("--mode must be upgrade or reinstall")

    env_list = _resolve_environments(environments)
    target_list = [t.strip() for t in targets.split(",") if t.strip()]
    if not target_list:
        raise typer.BadParameter("provide --targets (e.g. all-realms, all-infra, all, or stand names)")

    # Build the plan across all environments first.
    all_actions: list[dict] = []
    for env in env_list:
        casals = _CASALS_IDS.get(env)
        if not casals:
            console.print(f"[yellow]Skipping '{env}': no Casals instance configured.[/yellow]")
            continue
        console.print(f"[dim]Reading {env} Casals ({casals})...[/dim]")
        all_actions.extend(
            _build_plan(env, casals, target_list, scope, mode, version, realm_family)
        )

    if not all_actions:
        console.print("[yellow]No matching canisters to act on.[/yellow]")
        return

    _print_plan(all_actions)

    actionable = [a for a in all_actions if a["wasm_key"]]
    skipped = len(all_actions) - len(actionable)
    if skipped:
        console.print(f"[yellow]{skipped} target(s) will be skipped (no resolvable WASM).[/yellow]")

    if not actionable:
        console.print("[yellow]Nothing actionable. Aborting.[/yellow]")
        raise typer.Exit(1)

    if not execute:
        console.print("\n[bold]Dry run.[/bold] Re-run with [cyan]--execute[/cyan] to apply.")
        return

    # Guardrails for destructive reinstalls.
    if mode == "reinstall":
        destructive = [a for a in actionable if a["stand"] in _DESTRUCTIVE_INFRA_REINSTALL]
        if destructive and not include_infra_reinstall:
            names = ", ".join(sorted({a["stand"] for a in destructive}))
            console.print(
                f"[red]Refusing to reinstall infra stands that wipe shared state: {names}.\n"
                f"Pass --include-infra-reinstall to override (this PERMANENTLY wipes their state).[/red]"
            )
            raise typer.Exit(1)
        if not yes:
            console.print(
                "[red bold]reinstall mode WIPES canister state on success "
                "(the protective snapshot is dropped after a verified reinstall).[/red bold]"
            )
            confirm = typer.prompt("Type 'reinstall' to proceed")
            if confirm.strip() != "reinstall":
                console.print("[yellow]Aborted.[/yellow]")
                raise typer.Exit(0)
    elif not yes:
        if not typer.confirm(f"Apply {len(actionable)} {mode}(s) now?"):
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

    # Execute.
    results = []
    for a in actionable:
        label = f"{a['env']}/{a['stand']}/{a['canister']} ({a['kind']}, {a['mode']})"
        console.print(f"\n[blue]→ {label}[/blue]  {a['wasm_key']}")
        try:
            if a["kind"] == "frontend":
                ok, detail = _upgrade_frontend(a, identity)
            else:
                ok, detail = _upgrade_backend(a, identity)
        except Exception as e:  # noqa: BLE001 - report and continue
            ok, detail = False, str(e)
        mark = "[green]✓[/green]" if ok else "[red]✗[/red]"
        console.print(f"  {mark} {detail}")
        results.append((label, ok, detail))

    # Summary.
    table = Table(title="Rollout results", header_style="bold cyan")
    table.add_column("target")
    table.add_column("result")
    table.add_column("detail")
    failures = 0
    for label, ok, detail in results:
        table.add_row(label, "[green]ok[/green]" if ok else "[red]FAILED[/red]", detail)
        if not ok:
            failures += 1
    console.print(table)

    if failures:
        console.print(f"[red]{failures} of {len(results)} target(s) failed.[/red]")
        raise typer.Exit(1)
    console.print(f"[bold green]All {len(results)} target(s) succeeded.[/bold green]")
