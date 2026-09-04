"""Casals product-sheet helpers for ``realms seed``."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

import typer

from .commands.env import _read_canister_ids, _write_canister_ids, load_env_config
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


def sync_product_canister_ids_from_tree(
    *,
    conductor: str,
    network: str,
    identity: Optional[str],
    casals_src: Path,
    project_root: Optional[Path] = None,
) -> None:
    """Update ``canister_ids.json`` product entries from the Casals tree."""
    root = project_root or get_project_root()
    tree = run_casals_tree(
        network=network,
        identity=identity,
        casals_src=casals_src,
        canister=conductor,
    )
    # Tree names use hyphens (token-frontend); keys use underscores (token_frontend).
    tree_ids = canister_ids_from_tree(tree)
    data = _read_canister_ids(root)
    changed = False
    for _stand, tree_name, ids_key, _kind in _PRODUCT_REGISTRATIONS:
        tree_cid = (tree_ids.get(tree_name) or "").strip()
        if not tree_cid:
            continue
        current = ((data.get(ids_key) or {}).get(network) or "").strip()
        if current == tree_cid:
            continue
        data.setdefault(ids_key, {})[network] = tree_cid
        changed = True
        console.print(
            f"[green]✓ canister_ids.json[/green] {ids_key}.{network}: "
            f"{current or '(unset)'} → {tree_cid}"
        )
    if changed:
        _write_canister_ids(root, data)


def _product_canister_id(
    network: str,
    key: str,
    project_root: Path,
) -> str:
    return (_read_canister_ids(project_root).get(key) or {}).get(network, "").strip()


_DEAD_CANISTER_MARKERS = (
    "not found",
    "does not exist",
    "canister_not_found",
    "canister not found",
    "no route",
)

# A canister whose controller was deleted still answers on the IC, but the
# deployer can neither read its status nor install into it, so an id pinned to
# one is as unusable as a deleted one: seed must mint a replacement rather than
# fail. IC0542 is the management canister's rejection for that.
_UNCONTROLLED_CANISTER_MARKERS = (
    "ic0542",
    "is not allowed to read the canister status",
)


def check_canister_liveness(
    canister_id: str,
    *,
    network: str,
    identity: Optional[str] = None,
) -> bool:
    """Return True when the canister exists and this identity can control it.

    Return False when the replica reports not-found, or when it exists but
    rejects the status read (orphaned by a deleted controller) — both mean the
    pinned id is unusable and seed should mint a replacement. Raise
    ``RuntimeError`` for anything else, such as a transient replica error.
    """
    canister_id = (canister_id or "").strip()
    if not canister_id:
        raise RuntimeError("check_canister_liveness requires a canister id")

    network_key = network.strip().lower()
    if network_key in ("local", "localhost"):
        cmd = ["dfx", "canister", "status", canister_id, "--network", network]
        if identity:
            cmd.extend(["--identity", identity])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            env=_dfx_subprocess_env(),
        )
    else:
        cmd = [
            "icp",
            "canister",
            "status",
            canister_id,
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
        # icp answers definitively here (status, "was not found", or a rejection
        # code), so there is no dfx fallback: hosts that wrap dfx reject a bare
        # invocation, which used to turn a readable answer into a hard failure.

    if result.returncode == 0:
        return True
    combined = f"{result.stderr}\n{result.stdout}"
    if any(marker in combined.lower() for marker in _DEAD_CANISTER_MARKERS):
        return False
    if "ic0301" in combined.lower():
        return False
    if any(
        marker in combined.lower() for marker in _UNCONTROLLED_CANISTER_MARKERS
    ):
        return False
    raise RuntimeError(
        f"cannot check liveness for {canister_id}: {combined.strip()}"
    )


def partition_product_canister_inventory(
    network: str,
    project_root: Path,
    *,
    identity: Optional[str] = None,
) -> tuple[dict[str, str], list[tuple[str, str, str]]]:
    """Split product inventory into live ids and absent (stale) entries.

    Returns ``(live, dead)`` where ``live`` maps ``ids_key`` → canister_id and
    ``dead`` is ``(ids_key, registered_name, stale_cid)`` tuples.
    """
    live: dict[str, str] = {}
    dead: list[tuple[str, str, str]] = []
    for _stand, reg_name, ids_key, _kind in _PRODUCT_REGISTRATIONS:
        cid = _product_canister_id(network, ids_key, project_root)
        if not cid:
            continue
        if check_canister_liveness(cid, network=network, identity=identity):
            live[ids_key] = cid
        else:
            dead.append((ids_key, reg_name, cid))
    return live, dead


def log_stale_product_canisters(
    dead: list[tuple[str, str, str]],
    *,
    action: str,
) -> None:
    """Log every stale product principal so operators see what was healed."""
    for ids_key, reg_name, cid in dead:
        console.print(
            f"[yellow]⚠️  {reg_name} ({ids_key}): stale principal {cid} "
            f"not on IC — {action}[/yellow]"
        )


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
    live, dead = partition_product_canister_inventory(
        network, root, identity=identity
    )
    if dead:
        log_stale_product_canisters(
            dead, action="skipping Casals registration"
        )
    tree = run_casals_tree(
        network=network,
        identity=identity,
        casals_src=casals_src,
        canister=conductor,
    )
    registered = canister_ids_from_tree(tree)

    for stand, name, ids_key, kind in _PRODUCT_REGISTRATIONS:
        cid = live.get(ids_key)
        if not cid:
            if any(entry[0] == ids_key for entry in dead):
                continue
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
_IC_TOKENS_TOKEN_BACKEND_SHA256 = (
    "a1734ad2ec260ce85e541f860dbcaf8c846423709177587c7e5f70adc47e461a"
)
_IC_TOKENS_NFT_BACKEND_SHA256 = (
    "abea08d97de800d4e299545be786dd02c9c6a7d93aaccc3770a08c213dfa484b"
)
_WASM_MAGIC = b"\x00asm"
_GZIP_MAGIC = b"\x1f\x8b"
_CANISTER_ID_RE = re.compile(
    r"([a-z0-9]{5}(?:-[a-z0-9]{5}){3,10}-[a-z0-9]{3})"
)
_CONTROLLERS_RE = re.compile(r"controllers:\s*(.+)", re.I)
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
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"installer configure (product pointers) failed: {err}")
    # The installer answers an authorization failure with a 200 and
    # {"success": false}, so the exit code alone is not evidence it took effect.
    applied = _parse_installer_configure_response(result.stdout)
    if not applied.get("success"):
        raise RuntimeError(
            f"installer configure rejected: {applied.get('error') or result.stdout.strip()}"
        )
    for key, expected in (
        ("file_registry_id", file_registry),
        ("marketplace_id", marketplace),
    ):
        if applied.get(key) and applied[key] != expected:
            raise RuntimeError(
                f"installer {key} is {applied[key]}, expected {expected}"
            )
    console.print(
        f"[green]✓ installer file_registry + marketplace[/green] "
        f"[dim]({installer})[/dim]"
    )


def _parse_installer_configure_response(raw: str) -> dict:
    """Pull the JSON payload out of a candid ``(\"{...}\")`` reply.

    Returns an empty dict when the reply is not the expected shape, which the
    caller treats as a failure rather than assuming success.
    """
    match = re.search(r'"(\{.*\})"', raw or "", re.S)
    if not match:
        return {}
    body = match.group(1).replace('\\"', '"').replace("\\\\", "\\")
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


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
    cmd = [
        "icp",
        "cycles",
        "balance",
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
    # icp, not dfx: operator hosts wrap dfx and reject a bare invocation, which
    # turned this top-up into a hard seed failure.
    cmd = [
        "icp",
        "canister",
        "top-up",
        canister_id,
        "--amount",
        str(amount),
        "-n",
        "https://icp0.io",
        "--root-key",
        "mainnet",
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
            f"icp canister top-up {canister_id} {amount} failed: {stderr}"
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
        "icp",
        "canister",
        "install",
        canister_id,
        "--wasm",
        str(wasm),
        "--mode",
        "upgrade",
        "--args",
        "(null)",
        "-y",
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
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"install GOS file_registry on {canister_id} failed: {stderr}"
        )
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


def _seed_wasm_cache_dir() -> Path:
    raw = os.environ.get("REALMS_SEED_WASM_CACHE", "").strip()
    return Path(raw) if raw else Path("/tmp/realms-seed-wasms")


def _wasm_payload(data: bytes) -> bytes:
    if data[:2] == _GZIP_MAGIC:
        return gzip.decompress(data)
    return data


def _validate_wasm_artifact(
    path: Path,
    *,
    label: str,
    expected_sha256: str | None = None,
) -> None:
    if not path.is_file():
        raise RuntimeError(f"{label}: missing artifact at {path}")
    raw = path.read_bytes()
    if not raw:
        raise RuntimeError(f"{label}: artifact at {path} is empty")
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if expected_sha256 and actual_sha256 != expected_sha256.lower():
        raise RuntimeError(
            f"{label}: sha256 mismatch for {path.name}: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )
    payload = _wasm_payload(raw)
    if not payload.startswith(_WASM_MAGIC):
        raise RuntimeError(
            f"{label}: {path.name} is not a valid WASM module "
            f"(missing \\x00asm magic; sha256={actual_sha256})"
        )


def _ensure_cached_wasm(
    url: str,
    dest: Path,
    *,
    label: str,
    expected_sha256: str,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        try:
            _validate_wasm_artifact(
                dest, label=label, expected_sha256=expected_sha256
            )
            return dest
        except RuntimeError:
            dest.unlink(missing_ok=True)
    _download_url(url, dest)
    _validate_wasm_artifact(dest, label=label, expected_sha256=expected_sha256)
    return dest


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


def _ic_canister_call(
    canister_id: str,
    method: str,
    arg: str,
    *,
    network: str,
    identity: Optional[str],
    query: bool = False,
) -> str:
    cmd = [
        "icp",
        "canister",
        "call",
        canister_id,
        method,
        arg,
        "-n",
        "https://icp0.io",
        "--root-key",
        "mainnet",
    ]
    if query:
        cmd.append("--query")
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
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"{method} on {canister_id} failed: {err}")
    return (result.stdout or "").strip()


def _parse_controllers(status_raw: str) -> tuple[str, ...]:
    for line in status_raw.splitlines():
        match = _CONTROLLERS_RE.search(line)
        if match:
            return tuple(_CANISTER_ID_RE.findall(match.group(1)))
    return ()


def _dfx_canister_status(
    canister_id: str,
    *,
    network: str,
    identity: Optional[str],
) -> str:
    network_key = network.strip().lower()
    if network_key in ("local", "localhost"):
        cmd = ["dfx", "canister", "status", canister_id, "--network", network]
    else:
        cmd = [
            "icp",
            "canister",
            "status",
            canister_id,
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
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"cannot read status for {canister_id}: {err}")
    return (result.stdout or "").strip()


def _add_canister_controller(
    canister_id: str,
    controller: str,
    *,
    network: str,
    identity: Optional[str],
) -> None:
    controller = (controller or "").strip()
    if not controller:
        raise RuntimeError("add_canister_controller requires a controller principal")
    status = _dfx_canister_status(
        canister_id, network=network, identity=identity
    )
    if controller in _parse_controllers(status):
        console.print(
            f"[dim]{canister_id}: {controller} already a controller[/dim]"
        )
        return
    network_key = network.strip().lower()
    if network_key in ("local", "localhost"):
        cmd = [
            "dfx",
            "canister",
            "update-settings",
            canister_id,
            "--add-controller",
            controller,
            "--network",
            network,
        ]
    else:
        cmd = [
            "icp",
            "canister",
            "settings",
            "update",
            canister_id,
            "--add-controller",
            controller,
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
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"add controller {controller} to {canister_id} failed: {err}"
        )


def _live_product_canister_inventory(
    network: str,
    project_root: Path,
    *,
    identity: Optional[str] = None,
) -> tuple[dict[str, str], list[tuple[str, str, str]]]:
    """Return live product canisters; log and omit stale principals."""
    live, dead = partition_product_canister_inventory(
        network, project_root, identity=identity
    )
    if dead:
        log_stale_product_canisters(
            dead, action="skipping controller changes"
        )
    return live, dead


def apply_product_controller_topology(
    *,
    conductor: str,
    network: str,
    identity: Optional[str],
    project_root: Optional[Path] = None,
) -> None:
    """Add the Realms GOS Casals conductor as co-controller on product canisters."""
    if network.strip().lower() in ("local", "localhost"):
        console.print(
            "[yellow]skip product controller topology on local network[/yellow]"
        )
        return
    root = project_root or get_project_root()
    inventory, _dead = _live_product_canister_inventory(
        network, root, identity=identity
    )
    if not inventory:
        console.print(
            "[dim]no live product canisters for controller topology[/dim]"
        )
        return
    changed = 0
    for name, canister_id in inventory.items():
        status = _dfx_canister_status(
            canister_id, network=network, identity=identity
        )
        if conductor in _parse_controllers(status):
            console.print(f"[dim]{name}: Casals conductor already a controller[/dim]")
            continue
        console.print(
            f"[dim]{name}: adding Casals conductor {conductor} as co-controller[/dim]"
        )
        _add_canister_controller(
            canister_id,
            conductor,
            network=network,
            identity=identity,
        )
        changed += 1
    if changed:
        console.print(
            f"[green]✓ added Casals conductor on {changed} product canister(s)[/green]"
        )
    else:
        console.print("[dim]product controller topology already applied[/dim]")


def verify_product_controller_topology(
    *,
    conductor: str,
    network: str,
    identity: Optional[str],
    project_root: Optional[Path] = None,
) -> None:
    """Fail loudly if the Casals conductor is missing from any product canister."""
    if network.strip().lower() in ("local", "localhost"):
        return
    root = project_root or get_project_root()
    inventory, dead = _live_product_canister_inventory(
        network, root, identity=identity
    )
    if dead:
        log_stale_product_canisters(
            dead, action="skipping controller verification"
        )
    if not inventory:
        console.print(
            "[dim]no live product canisters to verify controller topology[/dim]"
        )
        return
    errors: list[str] = []
    for name, canister_id in inventory.items():
        status = _dfx_canister_status(
            canister_id, network=network, identity=identity
        )
        controllers = set(_parse_controllers(status))
        if conductor not in controllers:
            errors.append(
                f"{name} ({canister_id}): missing Casals conductor controller "
                f"{conductor} (actual={sorted(controllers)})"
            )
    if errors:
        raise RuntimeError(
            "product controller verification failed:\n  - "
            + "\n  - ".join(errors)
        )
    console.print(
        f"[green]✓ verified Casals conductor on {len(inventory)} product canister(s)[/green]"
    )


def ensure_product_controller_topology(
    *,
    conductor: str,
    network: str,
    identity: Optional[str],
    project_root: Optional[Path] = None,
) -> None:
    apply_product_controller_topology(
        conductor=conductor,
        network=network,
        identity=identity,
        project_root=project_root,
    )
    verify_product_controller_topology(
        conductor=conductor,
        network=network,
        identity=identity,
        project_root=project_root,
    )


def _parse_casals_settings(raw: str) -> dict:
    from .commands._dfx_utils import parse_candid_json_response

    return parse_candid_json_response(raw)


def _casals_settings(
    conductor: str,
    *,
    network: str,
    identity: Optional[str],
) -> dict:
    raw = _ic_canister_call(
        conductor,
        "get_settings",
        "()",
        network=network,
        identity=identity,
        query=True,
    )
    return _parse_casals_settings(raw)


def canister_cycles_balance(
    canister_id: str,
    *,
    identity: Optional[str] = None,
) -> Optional[int]:
    """Live cycle balance of ``canister_id``, or None when unreadable."""
    cmd = [
        "icp",
        "canister",
        "status",
        canister_id,
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
        return None
    match = re.search(r"Cycles:\s*([0-9_]+)", result.stdout or "")
    if not match:
        return None
    return int(match.group(1).replace("_", ""))


# Provisioning one realm makes the conductor mint three canisters: backend,
# frontend, and the stand's baton.
CONDUCTOR_CANISTERS_PER_REALM = 3
_CONDUCTOR_FALLBACK_REQUIREMENT = 10_000_000_000_000


def conductor_cycles_requirement(
    conductor: str,
    *,
    network: str,
    identity: Optional[str],
) -> int:
    """Cycles the conductor needs on hand to provision one more realm.

    Casals funds each new canister with ``create_cycles`` and refuses to spend
    below ``treasury_reserve``, so the floor is reserve + 3 × create_cycles.
    """
    try:
        settings = _casals_settings(conductor, network=network, identity=identity)
    except RuntimeError:
        return _CONDUCTOR_FALLBACK_REQUIREMENT
    try:
        create = int(settings.get("create_cycles") or 0)
        reserve = int(settings.get("treasury_reserve") or 0)
    except (TypeError, ValueError):
        return _CONDUCTOR_FALLBACK_REQUIREMENT
    if create <= 0:
        return _CONDUCTOR_FALLBACK_REQUIREMENT
    return reserve + create * CONDUCTOR_CANISTERS_PER_REALM


def ensure_conductor_cycles(
    conductor: str,
    *,
    network: str,
    identity: Optional[str],
    realms: int = 1,
) -> None:
    """Top the conductor up to what provisioning ``realms`` more realms costs.

    The conductor is its own treasury and nothing refills it as realms are
    created, so it drains after a few deploys and the next one dies mid-job with
    IC0504 — after the realm canisters exist but before the baton hand-off.
    Checking the live balance here (not Casals' cached snapshot, which can be
    hours stale) turns that into an automatic top-up.
    """
    target = conductor_cycles_requirement(
        conductor, network=network, identity=identity
    ) * max(1, realms)
    balance = canister_cycles_balance(conductor, identity=identity)
    if balance is None:
        console.print(
            f"[yellow]⚠️  cannot read conductor {conductor} cycles; "
            f"skipping top-up preflight[/yellow]"
        )
        return
    if balance >= target:
        console.print(
            f"[dim]conductor cycles {balance / 1_000_000_000_000:.1f} TC "
            f"(needs {target / 1_000_000_000_000:.1f} TC)[/dim]"
        )
        return
    shortfall = target - balance
    console.print(
        f"conductor {conductor} at {balance / 1_000_000_000_000:.1f} TC, "
        f"needs {target / 1_000_000_000_000:.1f} TC — topping up "
        f"{shortfall / 1_000_000_000_000:.1f} TC"
    )
    top_up_canister_cycles(conductor, identity=identity, amount=shortfall)


def ensure_orchestra_name(
    *,
    conductor: str,
    network: str,
    identity: Optional[str],
    project_root: Optional[Path] = None,
) -> None:
    """Set Casals orchestra_name from the product sheet (idempotent)."""
    root = project_root or get_project_root()
    sheet = load_product_sheet(root)
    desired = (sheet.get("name") or "").strip()
    if not desired:
        raise RuntimeError("product sheet is missing a non-empty name field")
    current = (_casals_settings(conductor, network=network, identity=identity)
               .get("orchestra_name") or "").strip()
    if current == desired:
        console.print(
            f"[dim]orchestra_name already {desired!r}[/dim]"
        )
        return
    payload = json.dumps({"orchestra_name": desired})
    raw = _ic_canister_call(
        conductor,
        "set_settings",
        _candid_text_arg(payload),
        network=network,
        identity=identity,
    )
    result = _parse_casals_settings(raw)
    if isinstance(result, dict) and result.get("ok") is False:
        raise RuntimeError(
            f"set_settings orchestra_name failed: {result.get('error', result)}"
        )
    updated = (_casals_settings(conductor, network=network, identity=identity)
                 .get("orchestra_name") or "").strip()
    if updated != desired:
        raise RuntimeError(
            f"orchestra_name mismatch after set_settings: "
            f"expected {desired!r}, got {updated!r}"
        )
    console.print(f"[green]✓ orchestra_name[/green] {desired}")


def ensure_casals_frontend_canister_id(
    *,
    conductor: str,
    network: str,
    identity: Optional[str],
    project_root: Optional[Path] = None,
) -> None:
    """Set Casals conductor casals_frontend_canister_id (idempotent)."""
    root = project_root or get_project_root()
    desired = _product_canister_id(network, "casals_frontend", root)
    if not desired:
        console.print(
            "[dim]skip casals_frontend_canister_id: no casals_frontend in "
            "canister_ids.json[/dim]"
        )
        return
    try:
        live = check_canister_liveness(
            desired, network=network, identity=identity
        )
    except RuntimeError as exc:
        console.print(
            f"[dim]skip casals_frontend_canister_id: {exc}[/dim]"
        )
        return
    if not live:
        console.print(
            f"[dim]skip casals_frontend_canister_id: {desired} not on IC[/dim]"
        )
        return
    current = (
        _casals_settings(conductor, network=network, identity=identity)
        .get("casals_frontend_canister_id")
        or ""
    ).strip()
    if current == desired:
        console.print(
            f"[dim]casals_frontend_canister_id already {desired!r}[/dim]"
        )
        return
    payload = json.dumps({"casals_frontend_canister_id": desired})
    raw = _ic_canister_call(
        conductor,
        "set_settings",
        _candid_text_arg(payload),
        network=network,
        identity=identity,
    )
    result = _parse_casals_settings(raw)
    if isinstance(result, dict) and result.get("ok") is False:
        raise RuntimeError(
            "set_settings casals_frontend_canister_id failed: "
            f"{result.get('error', result)}"
        )
    updated = (
        _casals_settings(conductor, network=network, identity=identity)
        .get("casals_frontend_canister_id")
        or ""
    ).strip()
    if updated != desired:
        raise RuntimeError(
            "casals_frontend_canister_id mismatch after set_settings: "
            f"expected {desired!r}, got {updated!r}"
        )
    console.print(f"[green]✓ casals_frontend_canister_id[/green] {desired}")


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
    cache = _seed_wasm_cache_dir()
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
    token_wasm = _ensure_cached_wasm(
        f"{_IC_TOKENS_BASE}/token_backend.wasm",
        cache / "token_backend.wasm",
        label="ic-tokens token_backend.wasm",
        expected_sha256=_IC_TOKENS_TOKEN_BACKEND_SHA256,
    )
    nft_wasm = _ensure_cached_wasm(
        f"{_IC_TOKENS_BASE}/nft_backend.wasm",
        cache / "nft_backend.wasm",
        label="ic-tokens nft_backend.wasm",
        expected_sha256=_IC_TOKENS_NFT_BACKEND_SHA256,
    )

    missing: list[str] = []
    for path, label in (
        (marketplace_wasm, "marketplace backend WASM (.basilisk/marketplace_backend)"),
        (file_registry_wasm, "fleet file_registry WASM (.external-wasms)"),
    ):
        if not path.is_file():
            missing.append(label)
    if missing:
        raise RuntimeError("missing artifacts to authorize: " + "; ".join(missing))

    _validate_wasm_artifact(
        marketplace_wasm,
        label="marketplace backend WASM",
    )
    _validate_wasm_artifact(
        file_registry_wasm,
        label="fleet file_registry WASM",
    )

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

    ensure_orchestra_name(
        conductor=conductor,
        network=network,
        identity=identity,
        project_root=root,
    )
    ensure_casals_frontend_canister_id(
        conductor=conductor,
        network=network,
        identity=identity,
        project_root=root,
    )
    ensure_product_controller_topology(
        conductor=conductor,
        network=network,
        identity=identity,
        project_root=root,
    )
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
    try:
        sync_product_canister_ids_from_tree(
            conductor=conductor,
            network=network,
            identity=identity,
            casals_src=casals_src,
            project_root=root,
        )
    except Exception as exc:
        console.print(
            "[yellow]⚠️  could not sync canister_ids.json from Casals tree: "
            f"{exc}[/yellow]"
        )
    return True, f"conductor {conductor} (product sheet)"

