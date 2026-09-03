"""Casals product-sheet helpers for ``realms seed``."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

import typer

from .commands.env import _read_canister_ids, load_env_config
from .utils import console, get_project_root

_SRV_CASALS = Path("/srv/dev/Casals")

# (stand, registered name, canister_ids.json key, kind)
_PRODUCT_REGISTRATIONS: tuple[tuple[str, str, str, str], ...] = (
    ("marketplace", "marketplace-backend", "marketplace_backend", "backend"),
    ("marketplace", "marketplace-frontend", "marketplace_frontend", "frontend"),
    ("file-registry", "file-registry", "file_registry", "backend"),
    ("file-registry", "file-registry-frontend", "file_registry_frontend", "frontend"),
    ("token", "token-backend", "token_backend", "backend"),
    ("token", "token-frontend", "token_frontend", "frontend"),
    ("nft", "nft-backend", "nft_backend", "backend"),
    ("nft", "nft-frontend", "nft_frontend", "frontend"),
)


def casals_env(network: str) -> str:
    """Map a Realms/dfx network name to a Casals/icp environment.

    ``test`` / ``demo`` / ``staging`` are IC replica networks, not icp ``local``.
    """
    if (network or "").strip().lower() in ("local", "localhost"):
        return "local"
    return "ic"


def _is_casals_checkout(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return (resolved / "src" / "main.py").is_file() and (
        resolved / "casals_backend.did"
    ).is_file()


def resolve_casals_src(project_root: Optional[Path] = None) -> Optional[Path]:
    """Resolve a Casals checkout: CASALS_SRC, sibling ../Casals, /srv/dev/Casals."""
    env = os.environ.get("CASALS_SRC", "").strip()
    if env:
        path = Path(env)
        if _is_casals_checkout(path):
            return path.resolve()
        return None

    root = (project_root or get_project_root()).resolve()
    for candidate in (root.parent / "Casals", _SRV_CASALS):
        if _is_casals_checkout(candidate):
            return candidate.resolve()
    return None


def resolve_conductor_id(
    env_name: str,
    project_root: Optional[Path] = None,
) -> Optional[str]:
    """Resolve the **Realms GOS** Casals conductor backend for an environment.

    Never falls back to the GaaS descriptor — that conductor is a different
    instance and must not receive the product sheet.
    """
    root = project_root or get_project_root()

    try:
        env_cfg = load_env_config(env_name, root)
    except typer.Exit:
        env_cfg = {}

    for key in ("casals_backend", "casals"):
        cid = (env_cfg.get(key) or "").strip()
        if cid:
            return cid

    canisters = env_cfg.get("canisters")
    if isinstance(canisters, dict):
        cid = (canisters.get("casals_backend") or "").strip()
        if cid:
            return cid

    network = (env_cfg.get("network") or env_name or "").strip()
    realms_ids = _read_canister_ids(root)
    cid = ((realms_ids.get("casals_backend") or {}).get(network) or "").strip()
    if cid:
        return cid

    cid = os.environ.get("CASALS_BACKEND", "").strip()
    return cid or None


def product_sheet_path(project_root: Optional[Path] = None) -> Path:
    root = project_root or get_project_root()
    return root / "casals.json"


def load_product_sheet(project_root: Optional[Path] = None) -> dict:
    """Load ``realms/casals.json`` (product orchestra only)."""
    path = product_sheet_path(project_root)
    if not path.is_file():
        raise RuntimeError(f"product sheet missing at {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid Casals sheet JSON: {exc}") from exc


def load_gos_canisters(
    env_name: str, project_root: Optional[Path] = None
) -> Dict[str, str]:
    root = (project_root or get_project_root()).resolve()
    env = (os.environ.get("GAAS_SRC") or os.environ.get("GOS_SRC") or "").strip()
    candidates = []
    if env:
        candidates.append(Path(env) / "environments" / f"{env_name}.json")
    candidates.append(
        root.parent / "gos-as-a-service" / "environments" / f"{env_name}.json"
    )
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        canisters = data.get("canisters") or {}
        if isinstance(canisters, dict):
            return {
                str(k): str(v).strip()
                for k, v in canisters.items()
                if str(v).strip()
            }
    return {}


def _run_casals_cli(
    command: list[str],
    *,
    network: str,
    identity: Optional[str],
    casals_src: Path,
    canister: str,
) -> dict:
    env = casals_env(network)
    # Global flags (--identity, --canister) must precede the subcommand.
    argv: list[str] = [
        sys.executable,
        str(casals_src / "scripts" / "casals.py"),
        "-e",
        env,
    ]
    if identity:
        argv.extend(["--identity", identity])
    argv.extend(["--canister", canister, *command])

    result = subprocess.run(
        argv,
        cwd=casals_src,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"casals {' '.join(command)} failed (exit {result.returncode}): {stderr}"
        )

    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError(f"casals {' '.join(command)} produced no JSON on stdout")

    parsed = json.loads(stdout)
    if isinstance(parsed, dict) and parsed.get("ok") is False:
        raise RuntimeError(
            f"casals {' '.join(command)} returned ok=false: "
            f"{parsed.get('error', parsed)}"
        )
    return parsed


def run_casals_tree(
    *,
    network: str,
    identity: Optional[str],
    casals_src: Path,
    canister: str,
) -> dict:
    return _run_casals_cli(
        ["tree"],
        network=network,
        identity=identity,
        casals_src=casals_src,
        canister=canister,
    )


def run_casals_section_create(
    name: str,
    *,
    network: str,
    identity: Optional[str],
    casals_src: Path,
    canister: str,
    description: str = "",
) -> dict:
    cmd = ["section", "create", name]
    if description:
        cmd.extend(["--description", description])
    return _run_casals_cli(
        cmd,
        network=network,
        identity=identity,
        casals_src=casals_src,
        canister=canister,
    )


def run_casals_stand_create(
    section: str,
    name: str,
    *,
    network: str,
    identity: Optional[str],
    casals_src: Path,
    canister: str,
    description: str = "",
) -> dict:
    cmd = ["stand", "create", section, name]
    if description:
        cmd.extend(["--description", description])
    return _run_casals_cli(
        cmd,
        network=network,
        identity=identity,
        casals_src=casals_src,
        canister=canister,
    )


def run_casals_register(
    stand: str,
    name: str,
    canister_id: str,
    kind: str,
    *,
    network: str,
    identity: Optional[str],
    casals_src: Path,
    canister: str,
    wasm_type: Optional[str] = None,
) -> dict:
    cmd = ["register", stand, name, canister_id, kind]
    if wasm_type:
        cmd.extend(["--wasm-type", wasm_type])
    return _run_casals_cli(
        cmd,
        network=network,
        identity=identity,
        casals_src=casals_src,
        canister=canister,
    )


def run_casals_sheet_deploy(
    sheet: dict | Path,
    *,
    network: str,
    identity: Optional[str],
    casals_src: Path,
    canister: str,
) -> dict:
    sheet_path: Path | None = None
    tmp_path: Path | None = None
    if isinstance(sheet, dict):
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".sheet.json",
            delete=False,
            encoding="utf-8",
        )
        json.dump(sheet, tmp)
        tmp.close()
        tmp_path = Path(tmp.name)
        sheet_path = tmp_path
    else:
        sheet_path = Path(sheet)

    try:
        return _run_casals_cli(
            ["sheet", "deploy", str(sheet_path)],
            network=network,
            identity=identity,
            casals_src=casals_src,
            canister=canister,
        )
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def canister_ids_from_tree(tree: dict) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for sec in tree.get("sections") or []:
        for stand in sec.get("stands") or []:
            for c in stand.get("canisters") or []:
                name = (c.get("name") or "").strip()
                cid = (c.get("canister_id") or "").strip()
                if name and cid:
                    out[name] = cid
    return out


def _product_canister_id(
    network: str,
    key: str,
    project_root: Path,
) -> str:
    return (_read_canister_ids(project_root).get(key) or {}).get(network, "").strip()


def _already_exists(exc: Exception) -> bool:
    return "already exists" in str(exc).lower()


def ensure_sheet_stands(
    sheet: dict,
    *,
    conductor: str,
    network: str,
    identity: Optional[str],
    casals_src: Path,
) -> None:
    """Create sections and stands from a sheet dict (idempotent)."""
    for sec in sheet.get("sections") or []:
        sname = (sec.get("name") or "").strip()
        if not sname:
            continue
        try:
            run_casals_section_create(
                sname,
                network=network,
                identity=identity,
                casals_src=casals_src,
                canister=conductor,
                description=(sec.get("description") or ""),
            )
        except RuntimeError as exc:
            if not _already_exists(exc):
                raise
        for stand in sec.get("stands") or []:
            dname = (stand.get("name") or "").strip()
            if not dname:
                continue
            try:
                run_casals_stand_create(
                    sname,
                    dname,
                    network=network,
                    identity=identity,
                    casals_src=casals_src,
                    canister=conductor,
                    description=(stand.get("description") or ""),
                )
            except RuntimeError as exc:
                if not _already_exists(exc):
                    raise


def ensure_product_stands(
    *,
    conductor: str,
    network: str,
    identity: Optional[str],
    casals_src: Path,
    project_root: Optional[Path] = None,
) -> None:
    """Create Product section and stands from realms/casals.json (idempotent)."""
    root = project_root or get_project_root()
    sheet = json.loads(product_sheet_path(root).read_text(encoding="utf-8"))
    ensure_sheet_stands(
        sheet,
        conductor=conductor,
        network=network,
        identity=identity,
        casals_src=casals_src,
    )


def _register_named(
    *,
    conductor: str,
    network: str,
    identity: Optional[str],
    casals_src: Path,
    registered: Dict[str, str],
    stand: str,
    name: str,
    cid: str,
    kind: str,
) -> None:
    existing = registered.get(name, "")
    if existing:
        if existing == cid:
            return
        raise RuntimeError(
            f"{name} already registered as {existing}, expected {cid}"
        )
    wasm_type = "assets" if kind == "frontend" else None
    run_casals_register(
        stand,
        name,
        cid,
        kind,
        network=network,
        identity=identity,
        casals_src=casals_src,
        canister=conductor,
        wasm_type=wasm_type,
    )
    registered[name] = cid


def register_product_canisters(
    *,
    conductor: str,
    network: str,
    identity: Optional[str],
    casals_src: Path,
    project_root: Optional[Path] = None,
) -> None:
    """Register existing product canisters on Casals stands (idempotent)."""
    root = project_root or get_project_root()
    tree = run_casals_tree(
        network=network,
        identity=identity,
        casals_src=casals_src,
        canister=conductor,
    )
    registered = canister_ids_from_tree(tree)

    for stand, name, ids_key, kind in _PRODUCT_REGISTRATIONS:
        cid = _product_canister_id(network, ids_key, root)
        if not cid:
            raise RuntimeError(
                f"missing {ids_key} canister id for network {network!r} "
                f"(needed to register {name})"
            )
        _register_named(
            conductor=conductor,
            network=network,
            identity=identity,
            casals_src=casals_src,
            registered=registered,
            stand=stand,
            name=name,
            cid=cid,
            kind=kind,
        )


_CASALS_STACK_GOS_KEYS: tuple[str, ...] = (
    "casals_backend",
    "casals_frontend",
    "casals_file_registry",
    "casals_file_registry_frontend",
)

_IC_TOKENS_VERSION = "0.1.0"
_IC_TOKENS_BASE = (
    "https://github.com/smart-social-contracts/ic-tokens/releases/download/"
    f"v{_IC_TOKENS_VERSION}"
)
_CERTIFIED_ASSETS_URL = (
    "https://github.com/smart-social-contracts/certified-assets"
    "/releases/download/v0.3.0/assetstorage.wasm.gz"
)
_CERTIFIED_ASSETS_CACHE = Path("/tmp/realms-assetstorage.wasm.gz")
# icp create leaves Casals file-registry ~0.4T after WASM install; catalog
# seed then OOGs. Top up before seed.py uploads.
_CASALS_FILE_REGISTRY_TOPUP = 2_000_000_000_000
_CASALS_CONDUCTOR_TOPUP = 8_000_000_000_000
_WALLET_RESERVE_CYCLES = 200_000_000_000
_CYCLES_BALANCE_RE = re.compile(
    r"([\d_]+(?:\.\d+)?)\s*(TC|t|cycles)",
    re.IGNORECASE,
)


def gos_descriptor_path(
    env_name: str, project_root: Optional[Path] = None
) -> Path:
    root = (project_root or get_project_root()).resolve()
    env = (os.environ.get("GAAS_SRC") or os.environ.get("GOS_SRC") or "").strip()
    if env:
        candidate = Path(env) / "environments" / f"{env_name}.json"
        if candidate.is_file():
            return candidate
    return root.parent / "gos-as-a-service" / "environments" / f"{env_name}.json"


def persist_casals_ids_to_realms(
    network: str,
    canisters: dict,
    project_root: Optional[Path] = None,
) -> None:
    """Write new **Realms GOS** conductor IDs into ``canister_ids.json``."""
    from .commands.env import _set_canister_id

    root = project_root or get_project_root()
    mapping = {
        "casals_backend": "casals_backend",
        "casals_frontend": "casals_frontend",
        "ic_file_registry": "casals_file_registry",
        "ic_file_registry_frontend": "casals_file_registry_frontend",
    }
    for casals_key, realms_key in mapping.items():
        cid = (canisters.get(casals_key) or "").strip()
        if cid:
            _set_canister_id(root, realms_key, network, cid)


def persist_casals_url_to_env(
    env_name: str,
    canisters: dict,
    project_root: Optional[Path] = None,
) -> None:
    """Point ``environments/<env>.json`` ``casals_url`` at Realms GOS Casals frontend."""
    frontend = (canisters.get("casals_frontend") or "").strip()
    if not frontend:
        return
    root = project_root or get_project_root()
    path = root / "environments" / f"{env_name}.json"
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    if not isinstance(data, dict):
        return
    data["casals_url"] = f"https://{frontend}.icp0.io"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def configure_gaas_installer_product_pointers(
    *,
    env_name: str,
    network: str,
    identity: Optional[str],
    project_root: Optional[Path] = None,
) -> None:
    """Point the GaaS installer at the fleet file-registry and marketplace.

    Does not write those ids into the GaaS descriptor. ``casals_canister_id``
    stays the GaaS conductor.
    """
    root = project_root or get_project_root()
    path = gos_descriptor_path(env_name, root)
    if not path.is_file():
        console.print(
            f"[yellow]⚠️  no GaaS descriptor at {path}; skip installer product pointers[/yellow]"
        )
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"invalid GaaS descriptor {path}: {exc}") from exc
    cans = data.get("canisters") if isinstance(data, dict) else None
    if not isinstance(cans, dict):
        raise RuntimeError(f"{path} canisters must be an object")
    installer = (cans.get("realm_installer") or "").strip()
    if not installer:
        console.print("[yellow]⚠️  no realm_installer in GaaS descriptor; skip[/yellow]")
        return
    file_registry = _product_canister_id(network, "file_registry", root)
    marketplace = _product_canister_id(network, "marketplace_backend", root)
    if not file_registry or not marketplace:
        console.print(
            "[yellow]⚠️  missing fleet file_registry or marketplace_backend; "
            "skip installer product pointers[/yellow]"
        )
        return
    domain = str((data.get("domain") or "")).strip()
    portal = domain if domain.startswith("http") else (f"https://{domain}" if domain else "")
    threshold_tc = 2.0
    cycles = data.get("cycles") if isinstance(data.get("cycles"), dict) else {}
    try:
        threshold_tc = float(cycles.get("threshold_tc") or 2.0)
    except (TypeError, ValueError):
        pass
    payload = {
        "registry_backend_id": (cans.get("realm_registry_backend") or "").strip(),
        "file_registry_id": file_registry,
        "marketplace_id": marketplace,
        "casals_canister_id": (cans.get("casals_backend") or "").strip(),
        "casals_section": "Deployments",
        "portal_url": portal,
        "provision_via_casals": True,
        "create_stand_baton": True,
        "baton_wasm_key": "orchestration-baton@1.3.0",
        "cycle_threshold_cycles": int(threshold_tc * 1_000_000_000_000),
    }
    arg = _candid_text_arg(json.dumps(payload))
    cmd = [
        "icp",
        "canister",
        "call",
        installer,
        "configure",
        arg,
        "-n",
        "https://icp0.io",
        "--root-key",
        "mainnet",
    ]
    if identity:
        cmd.extend(["--identity", identity])
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        env=_dfx_subprocess_env(),
    )
    if result.returncode != 0:
        dfx_cmd = [
            "dfx",
            "canister",
            "call",
            installer,
            "configure",
            arg,
        ]
        if identity:
            dfx_cmd.extend(["--identity", identity])
        if network:
            dfx_cmd.extend(["--network", network])
        result = subprocess.run(
            dfx_cmd,
            capture_output=True,
            text=True,
            check=False,
            env=_dfx_subprocess_env(),
        )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"installer configure (product pointers) failed: {err}")
    console.print(
        f"[green]✓ installer file_registry + marketplace[/green] "
        f"[dim]({installer})[/dim]"
    )


def _candid_text_arg(payload: str) -> str:
    escaped = payload.replace("\\", "\\\\").replace('"', '\\"')
    return f'("{escaped}")'


def _dfx_subprocess_env() -> dict:
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["DFX_WARNING"] = "-mainnet_plaintext_identity"
    env.pop("NO_COLOR", None)
    env.pop("FORCE_COLOR", None)
    return env


def _gaas_casals_ids(env_name: str, project_root: Optional[Path] = None) -> set[str]:
    """Principals of the GaaS Casals stack — seed must never delete these."""
    gos = load_gos_canisters(env_name, project_root)
    ids: set[str] = set()
    for key in _CASALS_STACK_GOS_KEYS:
        cid = (gos.get(key) or "").strip()
        if cid:
            ids.add(cid)
    path = gos_descriptor_path(env_name, project_root)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            mid = ((data.get("multisig") or {}).get("backend_id") or "").strip()
            if mid:
                ids.add(mid)
        except (json.JSONDecodeError, OSError, AttributeError):
            pass
    return ids


_PRODUCT_CASALS_REALMS_KEYS: tuple[str, ...] = (
    "casals_backend",
    "casals_frontend",
    "casals_file_registry",
    "casals_file_registry_frontend",
)


def publish_casals_frontend_to_marketplace(
    *,
    env_name: str,
    canisters: dict,
    network: str,
    identity: Optional[str],
    project_root: Optional[Path] = None,
) -> None:
    """Write the Realms GOS Casals frontend principal onto marketplace backend.

    Sheet deploy may reinstall the backend (wiping config), so call this
    **after** ``casals sheet deploy``. Do not write this id to the GaaS registry.
    """
    frontend = (canisters.get("casals_frontend") or "").strip()
    if not frontend:
        ids = _read_canister_ids(project_root or get_project_root())
        frontend = ((ids.get("casals_frontend") or {}).get(network) or "").strip()
    if not frontend:
        return
    root = project_root or get_project_root()
    marketplace = _product_canister_id(network, "marketplace_backend", root)
    if not marketplace:
        console.print(
            "[yellow]⚠️  no marketplace_backend id; skip Casals frontend publish[/yellow]"
        )
        return

    arg = _candid_text_arg(frontend)
    cmd = [
        "icp",
        "canister",
        "call",
        marketplace,
        "set_casals_frontend_canister_id",
        arg,
        "-n",
        "https://icp0.io",
        "--root-key",
        "mainnet",
    ]
    if identity:
        cmd.extend(["--identity", identity])
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        env=_dfx_subprocess_env(),
    )
    if result.returncode != 0:
        dfx_cmd = [
            "dfx",
            "canister",
            "call",
            marketplace,
            "set_casals_frontend_canister_id",
            arg,
        ]
        if identity:
            dfx_cmd.extend(["--identity", identity])
        if network:
            dfx_cmd.extend(["--network", network])
        result = subprocess.run(
            dfx_cmd,
            capture_output=True,
            text=True,
            check=False,
            env=_dfx_subprocess_env(),
        )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"marketplace set_casals_frontend_canister_id failed: {err}"
        )
    console.print(
        f"[green]✓ marketplace casals_frontend[/green] {frontend} "
        f"[dim]({marketplace})[/dim]"
    )


def destroy_casals_stack(
    *,
    env_name: str,
    network: str,
    identity: Optional[str],
    project_root: Optional[Path] = None,
    yes: bool = False,
) -> Dict[str, list]:
    """Sweep cycles and delete the **Realms GOS** Casals stack only."""
    from .commands.env import (
        _clear_canister_id,
        _delete_canister_recover_cycles,
        _is_canister_dead,
        _read_canister_ids,
    )

    root = project_root or get_project_root()
    protected = _gaas_casals_ids(env_name, root)
    realms_ids = _read_canister_ids(root)
    targets: list[tuple[str, str]] = []
    seen: set[str] = set()
    skipped_gaas: list[str] = []

    def _add(name: str, cid: str) -> None:
        cid = (cid or "").strip()
        if not cid or cid in seen:
            return
        if cid in protected:
            skipped_gaas.append(f"{name} ({cid})")
            return
        seen.add(cid)
        targets.append((name, cid))

    for key in _PRODUCT_CASALS_REALMS_KEYS:
        _add(key, (realms_ids.get(key) or {}).get(network) or "")

    if skipped_gaas:
        console.print(
            "[yellow]Leaving GaaS Casals IDs untouched:[/yellow] "
            + ", ".join(skipped_gaas)
        )

    if not targets:
        console.print("[dim]No Realms GOS Casals stack IDs to destroy.[/dim]")
        return {"destroyed": []}

    from rich.panel import Panel

    console.print(
        Panel.fit(
            "Destroy Realms GOS Casals stack (recover cycles)\n"
            "GaaS Casals, installer, and registry are not deleted.\n"
            "Delete: " + ", ".join(f"{n} ({c})" for n, c in targets),
            style="yellow",
        )
    )
    if not yes and not typer.confirm(
        "Stop, recover cycles, and destroy the Realms GOS Casals conductor?",
        default=False,
    ):
        console.print("[yellow]Aborted.[/yellow]")
        raise typer.Exit(0)

    destroyed: list[str] = []
    for name, cid in targets:
        if _is_canister_dead(cid, network):
            console.print(f"[dim]{name} {cid} already gone[/dim]")
        else:
            console.print(f"[dim]Destroying {name} {cid} (recover cycles)…[/dim]")
            _delete_canister_recover_cycles(cid, network, identity)
        destroyed.append(cid)
        if name in _PRODUCT_CASALS_REALMS_KEYS:
            _clear_canister_id(root, name, network)
        console.print(f"  recovered+deleted {name} {cid}")
    return {"destroyed": destroyed}


def run_casals_new_fresh(
    *,
    network: str,
    identity: Optional[str],
    casals_src: Path,
) -> dict:
    """Mint a new Casals conductor. Never pass existing IDs (never upgrade/adopt)."""
    env = casals_env(network)
    # Global flags (--identity) must precede the subcommand.
    argv: list[str] = [
        sys.executable,
        str(casals_src / "scripts" / "casals.py"),
        "-e",
        env,
    ]
    if identity:
        argv.extend(["--identity", identity])
    argv.extend(["new", "-y", "--no-seed"])

    result = subprocess.run(
        argv,
        cwd=casals_src,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"casals new failed (exit {result.returncode}): {stderr}")
    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError("casals new produced no JSON on stdout")
    parsed = json.loads(stdout)
    if not parsed.get("ok"):
        raise RuntimeError(
            f"casals new returned ok=false: {parsed.get('error', parsed)}"
        )
    if parsed.get("mode") == "upgrade":
        raise RuntimeError(
            "casals new upgraded an existing conductor; seed requires a fresh create"
        )
    return parsed


def run_casals_seed_catalog(
    *,
    network: str,
    identity: Optional[str],
    casals_src: Path,
) -> None:
    """Authorize Casals default templates (orchestration) without deploying a sheet."""
    env = casals_env(network)
    argv: list[str] = [
        sys.executable,
        str(casals_src / "scripts" / "seed.py"),
        "-e",
        env,
    ]
    if identity:
        argv.extend(["--identity", identity])

    result = subprocess.run(
        argv,
        cwd=casals_src,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"casals seed catalog failed (exit {result.returncode}): {stderr}"
        )


def parse_cycles_balance(text: str) -> Optional[int]:
    match = _CYCLES_BALANCE_RE.search(text or "")
    if not match:
        return None
    raw, unit = match.group(1), match.group(2).lower()
    value = float(raw.replace("_", ""))
    if unit == "tc" or unit == "t":
        return int(value * 1_000_000_000_000)
    return int(value)


def cycles_ledger_balance(*, identity: Optional[str] = None) -> Optional[int]:
    cmd = ["dfx", "cycles", "balance", "--network", "ic"]
    if identity:
        cmd.extend(["--identity", identity])
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["DFX_WARNING"] = "-mainnet_plaintext_identity"
    env.pop("NO_COLOR", None)
    env.pop("FORCE_COLOR", None)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    if result.returncode != 0:
        return None
    return parse_cycles_balance(result.stdout or result.stderr or "")


def top_up_canister_cycles(
    canister_id: str,
    *,
    identity: Optional[str],
    amount: int,
) -> None:
    """Deposit cycles from the identity's ledger into ``canister_id``.

    Clamps to the wallet balance minus a reserve so a 2T/8T target cannot
    abort ``realms seed`` after ``casals new`` already minted the stack.
    """
    available = cycles_ledger_balance(identity=identity)
    if available is not None:
        sendable = max(0, available - _WALLET_RESERVE_CYCLES)
        if sendable <= 0:
            console.print(
                f"[yellow]skip top-up {canister_id}: wallet "
                f"{available / 1_000_000_000_000:.3f} TC at/under reserve[/yellow]"
            )
            return
        if sendable < amount:
            console.print(
                f"[yellow]clamping top-up {canister_id} to "
                f"{sendable / 1_000_000_000_000:.3f} TC "
                f"(wanted {amount / 1_000_000_000_000:.1f} TC)[/yellow]"
            )
            amount = sendable
    cmd = [
        "dfx",
        "cycles",
        "top-up",
        canister_id,
        str(amount),
        "--network",
        "ic",
    ]
    if identity:
        cmd.extend(["--identity", identity])
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["DFX_WARNING"] = "-mainnet_plaintext_identity"
    env.pop("NO_COLOR", None)
    env.pop("FORCE_COLOR", None)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"dfx cycles top-up {canister_id} {amount} failed: {stderr}"
        )
    console.print(
        f"[dim]topped up {canister_id} with {amount / 1_000_000_000_000:.1f} TC[/dim]"
    )


def install_gos_file_registry_wasm(
    canister_id: str,
    *,
    identity: Optional[str],
    project_root: Path,
) -> None:
    """Replace Casals' bundled file_registry with the GOS WASM (step finalize)."""
    env = (os.environ.get("GAAS_SRC") or os.environ.get("GOS_SRC") or "").strip()
    candidates = []
    if env:
        candidates.append(Path(env) / ".basilisk" / "file_registry" / "file_registry.wasm")
    candidates.append(
        project_root.parent / "gos-as-a-service" / ".basilisk" / "file_registry" / "file_registry.wasm"
    )
    cached = project_root / ".external-wasms" / "file_registry.wasm.gz"
    wasm: Path | None = None
    for plain in candidates:
        if plain.is_file():
            gz = Path("/tmp/realms-gos-file_registry.wasm.gz")
            import gzip as gzip_mod

            with plain.open("rb") as src, gzip_mod.open(gz, "wb") as out:
                out.write(src.read())
            wasm = gz
            break
    if wasm is None and cached.is_file():
        wasm = cached
    if wasm is None:
        raise RuntimeError(
            "no GOS file_registry WASM (build gos-as-a-service file_registry "
            "or place file_registry.wasm.gz in .external-wasms/)"
        )
    cmd = [
        "dfx",
        "canister",
        "install",
        canister_id,
        "--wasm",
        str(wasm),
        "--mode",
        "upgrade",
        "--network",
        "ic",
        "--yes",
        "--argument",
        "(null)",
    ]
    if identity:
        cmd.extend(["--identity", identity])
    env_vars = os.environ.copy()
    env_vars["TERM"] = "xterm-256color"
    env_vars["DFX_WARNING"] = "-mainnet_plaintext_identity"
    env_vars.pop("NO_COLOR", None)
    env_vars.pop("FORCE_COLOR", None)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env_vars)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"install GOS file_registry on {canister_id} failed: {stderr}")
    console.print(f"[dim]installed GOS file_registry WASM on {canister_id}[/dim]")


def rebuild_casals_conductor(
    *,
    env_name: str,
    network: str,
    identity: Optional[str],
    project_root: Optional[Path] = None,
    yes: bool = False,
) -> Tuple[str, dict]:
    """Destroy the **Realms GOS** Casals stack, ``casals new``, persist IDs. Returns (conductor, parsed)."""
    root = project_root or get_project_root()
    casals_src = resolve_casals_src(root)
    if not casals_src:
        raise RuntimeError("no Casals checkout (set CASALS_SRC or clone ../Casals)")

    destroy_casals_stack(
        env_name=env_name,
        network=network,
        identity=identity,
        project_root=root,
        yes=yes,
    )
    parsed = run_casals_new_fresh(
        network=network,
        identity=identity,
        casals_src=casals_src,
    )
    canisters = parsed.get("canisters") or {}
    persist_casals_ids_to_realms(network, canisters, root)
    persist_casals_url_to_env(env_name, canisters, root)
    conductor = (canisters.get("casals_backend") or "").strip()
    if not conductor:
        raise RuntimeError("casals new did not return casals_backend")
    file_registry = (canisters.get("ic_file_registry") or "").strip()
    finish_casals_rebuild(
        env_name=env_name,
        network=network,
        identity=identity,
        project_root=root,
        conductor=conductor,
        file_registry=file_registry,
    )
    console.print(
        f"[green]✓ casals new[/green] conductor {conductor} "
        f"[dim](mode={parsed.get('mode')}, catalog seeded)[/dim]"
    )
    return conductor, parsed


def _inventory_canister_id(root: Path, name: str, network: str) -> str:
    entry = _read_canister_ids(root).get(name) or {}
    if not isinstance(entry, dict):
        return ""
    return (entry.get(network) or entry.get("ic") or "").strip()


def finish_casals_rebuild(
    *,
    env_name: str,
    network: str,
    identity: Optional[str],
    project_root: Optional[Path] = None,
    conductor: Optional[str] = None,
    file_registry: Optional[str] = None,
) -> None:
    """Top up + GOS file-registry WASM + catalog after ``casals new``.

    Safe to re-run when ``casals new`` succeeded but a later 2T/8T top-up
    hit InsufficientFunds.
    """
    root = project_root or get_project_root()
    casals_src = resolve_casals_src(root)
    if not casals_src:
        raise RuntimeError("no Casals checkout (set CASALS_SRC or clone ../Casals)")
    conductor = (conductor or _inventory_canister_id(root, "casals_backend", network)).strip()
    file_registry = (
        file_registry
        or _inventory_canister_id(root, "casals_file_registry", network)
    ).strip()
    if file_registry:
        top_up_canister_cycles(
            file_registry,
            identity=identity,
            amount=_CASALS_FILE_REGISTRY_TOPUP,
        )
        install_gos_file_registry_wasm(
            file_registry, identity=identity, project_root=root
        )
    if conductor:
        top_up_canister_cycles(
            conductor,
            identity=identity,
            amount=_CASALS_CONDUCTOR_TOPUP,
        )
    run_casals_seed_catalog(
        network=network,
        identity=identity,
        casals_src=casals_src,
    )


def _download_url(url: str, dest: Path) -> Path:
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)
    return dest


def _certified_assets_wasm() -> Path:
    if _CERTIFIED_ASSETS_CACHE.is_file():
        return _CERTIFIED_ASSETS_CACHE
    _download_url(_CERTIFIED_ASSETS_URL, _CERTIFIED_ASSETS_CACHE)
    return _CERTIFIED_ASSETS_CACHE


def authorize_product_wasms(
    *,
    env_name: str,
    network: str,
    identity: Optional[str],
    project_root: Optional[Path] = None,
    conductor: Optional[str] = None,
) -> None:
    """Upload product-sheet WASMs into Realms GOS Casals' file-registry and authorize them."""
    from .commands.files import files_publish_release_command

    root = project_root or get_project_root()
    conductor = conductor or resolve_conductor_id(env_name, root)
    if not conductor:
        raise RuntimeError("no Realms GOS Casals conductor id for product WASM authorize")
    realms_ids = _read_canister_ids(root)
    casals_fr = (
        (realms_ids.get("casals_file_registry") or {}).get(network) or ""
    ).strip()
    if not casals_fr:
        raise RuntimeError(
            "casals_file_registry id required to authorize product WASMs "
            "(realms canister_ids.json after casals new)"
        )

    assets = _certified_assets_wasm()
    cache = Path("/tmp/realms-seed-wasms")
    cache.mkdir(parents=True, exist_ok=True)
    empty_dist = cache / "empty-frontend-dist"
    empty_dist.mkdir(parents=True, exist_ok=True)
    keep = empty_dist / ".keep"
    if not keep.is_file():
        keep.write_text("", encoding="utf-8")

    marketplace_wasm = (
        root / ".basilisk" / "marketplace_backend" / "marketplace_backend.wasm"
    )
    marketplace_dist = root / "src" / "marketplace_frontend" / "dist"
    file_registry_wasm = root / ".external-wasms" / "file_registry.wasm.gz"
    file_registry_dist = (
        root / ".external-assets" / "file_registry_frontend" / "dist"
    )
    token_wasm = cache / "token_backend.wasm"
    nft_wasm = cache / "nft_backend.wasm"
    if not token_wasm.is_file():
        _download_url(f"{_IC_TOKENS_BASE}/token_backend.wasm", token_wasm)
    if not nft_wasm.is_file():
        _download_url(f"{_IC_TOKENS_BASE}/nft_backend.wasm", nft_wasm)

    missing: list[str] = []
    for path, label in (
        (marketplace_wasm, "marketplace backend WASM (.basilisk/marketplace_backend)"),
        (file_registry_wasm, "fleet file_registry WASM (.external-wasms)"),
    ):
        if not path.is_file():
            missing.append(label)
    if missing:
        raise RuntimeError("missing artifacts to authorize: " + "; ".join(missing))

    jobs: list[dict] = [
        {
            "family": "marketplace",
            "version": "main",
            "backend_wasm": str(marketplace_wasm),
            "frontend_dist": str(marketplace_dist) if marketplace_dist.is_dir() else None,
        },
        {
            "family": "file-registry",
            "version": "main",
            "backend_wasm": str(file_registry_wasm),
            "frontend_dist": str(file_registry_dist)
            if file_registry_dist.is_dir()
            else None,
        },
        {
            "family": "token",
            "version": _IC_TOKENS_VERSION,
            "backend_wasm": str(token_wasm),
            "frontend_dist": str(empty_dist),
        },
        {
            "family": "nft",
            "version": _IC_TOKENS_VERSION,
            "backend_wasm": str(nft_wasm),
            "frontend_dist": str(empty_dist),
        },
    ]

    for job in jobs:
        console.print(
            f"[dim]authorize {job['family']}@{job['version']} in Casals catalog…[/dim]"
        )
        files_publish_release_command(
            network=network,
            family=job["family"],
            version=job["version"],
            backend_wasm=job["backend_wasm"],
            frontend_dist=job["frontend_dist"],
            registry=casals_fr,
            identity=identity,
            casals=conductor,
            assets_wasm=str(assets),
        )


def deploy_product_sheet_on_casals(
    *,
    env_name: str,
    network: str,
    identity: Optional[str],
    project_root: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Register product canisters and deploy ``realms/casals.json`` on Realms GOS Casals."""
    root = project_root or get_project_root()
    conductor = resolve_conductor_id(env_name, root)
    if not conductor:
        return False, "no Realms GOS Casals conductor id (canister_ids.json casals_backend or CASALS_BACKEND)"

    casals_src = resolve_casals_src(root)
    if not casals_src:
        return False, "no Casals checkout (set CASALS_SRC or clone ../Casals)"

    try:
        sheet = load_product_sheet(root)
    except RuntimeError as exc:
        return False, str(exc)

    ensure_sheet_stands(
        sheet,
        conductor=conductor,
        network=network,
        identity=identity,
        casals_src=casals_src,
    )
    register_product_canisters(
        conductor=conductor,
        network=network,
        identity=identity,
        casals_src=casals_src,
        project_root=root,
    )
    run_casals_sheet_deploy(
        sheet,
        network=network,
        identity=identity,
        casals_src=casals_src,
        canister=conductor,
    )
    return True, f"conductor {conductor} (product sheet)"

