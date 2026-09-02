"""Casals product-sheet helpers for ``realms seed``."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import typer

from .commands.env import _read_canister_ids, load_env_config
from .utils import get_project_root

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

# GaaS IDs from gos-as-a-service/environments/<env>.json (stand, name, descriptor key, kind)
_GAAS_REGISTRATIONS: tuple[tuple[str, str, str, str], ...] = (
    ("installer", "realm-installer", "realm_installer", "backend"),
    ("realm-registry", "realm-registry-backend", "realm_registry_backend", "backend"),
    ("realm-registry", "realm-registry-frontend", "realm_registry_frontend", "frontend"),
)


def casals_env(network: str) -> str:
    if network in ("ic", "mainnet"):
        return "ic"
    return "local"


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
    """Resolve the GaaS Casals conductor backend for an environment."""
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

    gos_path = root.parent / "gos-as-a-service" / "environments" / f"{env_name}.json"
    if gos_path.is_file():
        try:
            gos = json.loads(gos_path.read_text(encoding="utf-8"))
            cid = ((gos.get("canisters") or {}).get("casals_backend") or "").strip()
            if cid:
                return cid
        except (json.JSONDecodeError, OSError):
            pass

    cid = os.environ.get("CASALS_BACKEND", "").strip()
    return cid or None


def product_sheet_path(project_root: Optional[Path] = None) -> Path:
    root = project_root or get_project_root()
    return root / "casals.json"


def gaas_sheet_path(project_root: Optional[Path] = None) -> Path:
    """Locate gos-as-a-service/casals.json (GAAS_SRC / sibling checkout)."""
    root = (project_root or get_project_root()).resolve()
    env = (os.environ.get("GAAS_SRC") or os.environ.get("GOS_SRC") or "").strip()
    if env:
        candidate = Path(env) / "casals.json"
        if candidate.is_file():
            return candidate
    return root.parent / "gos-as-a-service" / "casals.json"


def merge_sheets(gaas: dict, product: dict) -> dict:
    """Union GaaS + product sheets by section / stand / canister name.

    ``deploy_sheet`` Pass 2 retires every orchestra canister not listed. A
    Product-only sheet on a conductor that still has GaaS canisters would
    stop installer / registry / multisig.
    """
    merged: dict[str, Any] = copy.deepcopy(
        {k: v for k, v in gaas.items() if k != "$comment"}
    )
    merged["name"] = "gaas-realms-union"
    merged["description"] = (
        "Union of gos-as-a-service/casals.json and realms/casals.json"
    )
    sections: list[dict] = list(merged.get("sections") or [])
    by_name = {(sec.get("name") or ""): sec for sec in sections}

    for sec in product.get("sections") or []:
        sname = (sec.get("name") or "").strip()
        if not sname:
            continue
        if sname not in by_name:
            cloned = copy.deepcopy(sec)
            sections.append(cloned)
            by_name[sname] = cloned
            continue
        existing = by_name[sname]
        stands = list(existing.get("stands") or [])
        stand_by_name = {(st.get("name") or ""): st for st in stands}
        for stand in sec.get("stands") or []:
            dname = (stand.get("name") or "").strip()
            if not dname:
                continue
            if dname not in stand_by_name:
                cloned_stand = copy.deepcopy(stand)
                stands.append(cloned_stand)
                stand_by_name[dname] = cloned_stand
                continue
            dest = stand_by_name[dname]
            canisters = list(dest.get("canisters") or [])
            can_by_name = {(c.get("name") or ""): c for c in canisters}
            for canister in stand.get("canisters") or []:
                cname = (canister.get("name") or "").strip()
                if not cname:
                    continue
                if cname not in can_by_name:
                    canisters.append(copy.deepcopy(canister))
                    can_by_name[cname] = canisters[-1]
            dest["canisters"] = canisters
        existing["stands"] = stands
    merged["sections"] = sections
    return merged


def load_union_sheet(project_root: Optional[Path] = None) -> dict:
    root = project_root or get_project_root()
    gaas_path = gaas_sheet_path(root)
    product_path = product_sheet_path(root)
    if not gaas_path.is_file():
        raise RuntimeError(
            f"GaaS sheet missing at {gaas_path} "
            "(clone ../gos-as-a-service or set GAAS_SRC)"
        )
    if not product_path.is_file():
        raise RuntimeError(f"product sheet missing at {product_path}")
    try:
        gaas = json.loads(gaas_path.read_text(encoding="utf-8"))
        product = json.loads(product_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid Casals sheet JSON: {exc}") from exc
    return merge_sheets(gaas, product)


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
    argv: list[str] = [
        sys.executable,
        str(casals_src / "scripts" / "casals.py"),
        "-e",
        env,
        "--canister",
        canister,
        *command,
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


def register_gaas_canisters(
    *,
    conductor: str,
    network: str,
    identity: Optional[str],
    casals_src: Path,
    env_name: str,
    project_root: Optional[Path] = None,
) -> None:
    """Register existing GaaS canisters so union sheet deploy reinstalls them."""
    root = project_root or get_project_root()
    gos = load_gos_canisters(env_name, root)
    tree = run_casals_tree(
        network=network,
        identity=identity,
        casals_src=casals_src,
        canister=conductor,
    )
    registered = canister_ids_from_tree(tree)

    missing: list[str] = []
    for stand, name, ids_key, kind in _GAAS_REGISTRATIONS:
        cid = (gos.get(ids_key) or "").strip()
        if not cid:
            missing.append(ids_key)
            continue
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
    if missing:
        raise RuntimeError(
            "missing GaaS canister ids for union sheet register: "
            + ", ".join(missing)
            + f" (gos-as-a-service/environments/{env_name}.json)"
        )


def deploy_product_sheet_on_casals(
    *,
    env_name: str,
    network: str,
    identity: Optional[str],
    project_root: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Register GaaS + product canisters and deploy the union sheet."""
    root = project_root or get_project_root()
    conductor = resolve_conductor_id(env_name, root)
    if not conductor:
        return False, "no Casals conductor id (set CASALS_BACKEND or gos-as-a-service descriptor)"

    casals_src = resolve_casals_src(root)
    if not casals_src:
        return False, "no Casals checkout (set CASALS_SRC or clone ../Casals)"

    try:
        union = load_union_sheet(root)
    except RuntimeError as exc:
        return False, str(exc)

    ensure_sheet_stands(
        union,
        conductor=conductor,
        network=network,
        identity=identity,
        casals_src=casals_src,
    )
    register_gaas_canisters(
        conductor=conductor,
        network=network,
        identity=identity,
        casals_src=casals_src,
        env_name=env_name,
        project_root=root,
    )
    register_product_canisters(
        conductor=conductor,
        network=network,
        identity=identity,
        casals_src=casals_src,
        project_root=root,
    )
    run_casals_sheet_deploy(
        union,
        network=network,
        identity=identity,
        casals_src=casals_src,
        canister=conductor,
    )
    return True, f"conductor {conductor} (union sheet)"

