"""Governance multisig seed helpers for ``realms seed``.

Ported from ``gos-as-a-service/cli/gaas/conductor_seed.py`` and
``gos-as-a-service/cli/gaas/phases.py`` (controller topology), adapted to
Realms CLI subprocess conventions.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .casals_product import (
    _CANISTER_ID_RE,
    _CONTROLLERS_RE,
    _PRODUCT_CASALS_REALMS_KEYS,
    _PRODUCT_REGISTRATIONS,
    _dfx_network_alias,
    _dfx_subprocess_env,
    _inventory_canister_id,
    _product_canister_id,
    check_canister_liveness,
    load_product_sheet,
    resolve_casals_src,
    resolve_conductor_id,
    run_casals_seed_catalog,
    run_casals_sheet_deploy,
    run_casals_tree,
)
from .commands.env import _set_canister_id, load_env_config
from .utils import console, get_project_root

# Matches gaas ORCHESTRATION_TEMPLATES orchestration-multisig version.
ORCHESTRATION_MULTISIG_VERSION = "1.2.0"
ORCHESTRATION_MULTISIG_KEY = f"orchestration-multisig@{ORCHESTRATION_MULTISIG_VERSION}"

_ANONYMOUS_PRINCIPAL = "2vxsx-fae"
_PRINCIPAL_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")

_GOVERNANCE_SECTION = "System"
_GOVERNANCE_STAND = "governance"
_MULTISIG_TREE_NAME = "multisig"

GOVERNANCE_SEED_PHASES: tuple[str, ...] = (
    "multisig_mint",
    "multisig_configure",
    "controller_topology",
)


@dataclass(frozen=True)
class MultisigConfig:
    backend_id: Optional[str]
    signers: tuple[str, ...]
    threshold: int


def _validate_principal(principal: str, *, label: str) -> None:
    p = (principal or "").strip()
    if not p:
        raise ValueError(f"{label} is required")
    if p == _ANONYMOUS_PRINCIPAL:
        raise ValueError(f"{label} cannot be the anonymous principal")
    if not _PRINCIPAL_RE.fullmatch(p) or len(p) < 20:
        raise ValueError(f"{label} does not look like an IC principal: {p!r}")


def parse_multisig_config(env_config: dict[str, Any]) -> Optional[MultisigConfig]:
    """Return parsed multisig config, or None when the block is absent."""
    block = env_config.get("multisig")
    if block is None:
        return None
    if not isinstance(block, dict):
        raise ValueError("multisig must be an object")
    backend_raw = block.get("backend_id")
    backend_id: Optional[str] = None
    if backend_raw is not None:
        backend_id = str(backend_raw).strip() or None
    signers_raw = block.get("signers")
    if signers_raw is None:
        signers: tuple[str, ...] = ()
    elif isinstance(signers_raw, list):
        signers = tuple(str(s).strip() for s in signers_raw if str(s).strip())
    else:
        raise ValueError("multisig.signers must be a list of principals")
    threshold_raw = block.get("threshold", 1)
    try:
        threshold = int(threshold_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"multisig.threshold must be an integer, got {threshold_raw!r}") from exc
    return MultisigConfig(backend_id=backend_id, signers=signers, threshold=threshold)


def validate_multisig_config(config: MultisigConfig) -> list[str]:
    """Validate a parsed multisig block; return human-readable errors."""
    errors: list[str] = []
    if config.backend_id:
        try:
            _validate_principal(config.backend_id, label="multisig.backend_id")
        except ValueError as exc:
            errors.append(str(exc))
    if not config.signers:
        errors.append("multisig.signers must contain at least one principal")
    for index, signer in enumerate(config.signers):
        try:
            _validate_principal(signer, label=f"multisig.signers[{index}]")
        except ValueError as exc:
            errors.append(str(exc))
    if config.threshold < 1:
        errors.append("multisig.threshold must be at least 1")
    if config.signers and config.threshold > len(config.signers):
        errors.append(
            f"multisig.threshold ({config.threshold}) exceeds signer count "
            f"({len(config.signers)})"
        )
    return errors


def plan_governance_phases(env_config: dict[str, Any]) -> list[str]:
    """Phases to run when a valid multisig block is present."""
    config = parse_multisig_config(env_config)
    if config is None:
        return []
    if validate_multisig_config(config):
        return []
    return list(GOVERNANCE_SEED_PHASES)


def is_production_topology_network(network: str) -> bool:
    """Strict controller handover applies only on production IC."""
    return (network or "").strip().lower() == "production"


def governance_deploy_sheet(project_root: Optional[Path] = None) -> dict[str, Any]:
    """Sheet fragment Casals may mint: governance/multisig only."""
    sheet = copy.deepcopy(load_product_sheet(project_root))
    sections: list[dict[str, Any]] = []
    for sec in sheet.get("sections") or []:
        if (sec.get("name") or "").strip() != _GOVERNANCE_SECTION:
            continue
        stands = [
            stand
            for stand in (sec.get("stands") or [])
            if (stand.get("name") or "").strip() == _GOVERNANCE_STAND
        ]
        if not stands:
            continue
        sec_copy = copy.deepcopy(sec)
        sec_copy["stands"] = stands
        sections.append(sec_copy)
    if not sections:
        raise RuntimeError(
            f"product sheet missing {_GOVERNANCE_SECTION}/{_GOVERNANCE_STAND}/multisig"
        )
    return {
        "name": sheet.get("name") or "realms-product",
        "description": sheet.get("description") or "",
        "sections": sections,
    }


def _find_canister_id(tree: dict[str, Any], name: str) -> str:
    for sec in tree.get("sections") or []:
        for stand in sec.get("stands") or []:
            for canister in stand.get("canisters") or []:
                if (canister.get("name") or "").strip() == name:
                    return (canister.get("canister_id") or "").strip()
    return ""


def _canister_names(tree: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for sec in tree.get("sections") or []:
        for stand in sec.get("stands") or []:
            for canister in stand.get("canisters") or []:
                name = (canister.get("name") or "").strip()
                if name:
                    names.add(name)
    return names


def _get_deployer_principal(identity: Optional[str]) -> str:
    cmd = ["dfx", "identity", "get-principal"]
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
        raise RuntimeError(f"dfx identity get-principal failed: {err}")
    principal = result.stdout.strip()
    if not principal:
        raise RuntimeError("dfx identity get-principal returned empty output")
    return principal


def _parse_controllers_from_info(stdout: str) -> tuple[str, ...]:
    for line in stdout.splitlines():
        match = _CONTROLLERS_RE.search(line)
        if match:
            return tuple(_CANISTER_ID_RE.findall(match.group(1)))
    return ()


def public_canister_controllers(canister_id: str, *, network: str) -> tuple[str, ...]:
    """Controller set via ``dfx canister info`` (public read_state)."""
    cmd = [
        "dfx",
        "canister",
        "info",
        canister_id,
        "--network",
        _dfx_network_alias(network),
        "--identity",
        "anonymous",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        env=_dfx_subprocess_env(),
    )
    if result.returncode != 0:
        combined = f"{result.stderr}\n{result.stdout}".strip()
        raise RuntimeError(f"dfx canister info {canister_id} failed: {combined}")
    return _parse_controllers_from_info(result.stdout)


def replace_canister_controllers(
    canister_id: str,
    controllers: list[str],
    *,
    network: str,
    identity: Optional[str],
) -> None:
    """Replace the IC controller set for a canister (``--yes`` for non-interactive)."""
    if not controllers:
        raise RuntimeError("replace_canister_controllers requires at least one controller")
    cmd = [
        "dfx",
        "canister",
        "--network",
        _dfx_network_alias(network),
        "update-settings",
        canister_id,
    ]
    if identity:
        cmd.extend(["--identity", identity])
    for controller in controllers:
        cmd.extend(["--set-controller", controller])
    cmd.append("--yes")
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
            f"update-settings {canister_id} -> {controllers} failed: {err}"
        )


def persist_multisig_backend_id(
    env_name: str,
    network: str,
    multisig_id: str,
    *,
    project_root: Optional[Path] = None,
) -> None:
    """Write ``multisig.backend_id`` to the env descriptor and ``canister_ids.json``."""
    root = project_root or get_project_root()
    multisig_id = (multisig_id or "").strip()
    if not multisig_id:
        return
    _set_canister_id(root, "multisig", network, multisig_id)
    path = root / "environments" / f"{env_name}.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        if isinstance(data, dict):
            block = data.setdefault("multisig", {})
            if isinstance(block, dict):
                block["backend_id"] = multisig_id
                path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def ensure_orchestration_multisig_authorized(
    *,
    network: str,
    identity: Optional[str],
    project_root: Optional[Path] = None,
) -> None:
    """Ensure ``orchestration-multisig@1.2.0`` is authorized (via Casals seed catalog)."""
    root = project_root or get_project_root()
    casals_src = resolve_casals_src(root)
    if not casals_src:
        console.print(
            "[yellow]⚠️  skip orchestration-multisig authorize: no Casals checkout[/yellow]"
        )
        return
    console.print(f"[dim]authorizing {ORCHESTRATION_MULTISIG_KEY} via Casals seed catalog…[/dim]")
    run_casals_seed_catalog(
        network=network,
        identity=identity,
        casals_src=casals_src,
    )


def ensure_multisig_minted(
    *,
    env_name: str,
    network: str,
    identity: Optional[str],
    config: MultisigConfig,
    project_root: Optional[Path] = None,
) -> str:
    """Mint or adopt the governance multisig; persist ``backend_id`` when minted."""
    root = project_root or get_project_root()
    conductor = resolve_conductor_id(env_name, root)
    if not conductor:
        raise RuntimeError("no Realms GOS Casals conductor id for multisig mint")
    casals_src = resolve_casals_src(root)
    if not casals_src:
        raise RuntimeError("no Casals checkout (set CASALS_SRC or clone ../Casals)")

    ensure_orchestration_multisig_authorized(
        network=network, identity=identity, project_root=root
    )

    tree = run_casals_tree(
        network=network,
        identity=identity,
        casals_src=casals_src,
        canister=conductor,
    )
    tree_id = _find_canister_id(tree, _MULTISIG_TREE_NAME)
    descriptor_id = (config.backend_id or "").strip()

    if descriptor_id:
        if tree_id and descriptor_id != tree_id:
            console.print(
                f"[yellow]⚠️  descriptor multisig.backend_id={descriptor_id} "
                f"differs from tree {tree_id}; adopting live tree id[/yellow]"
            )
        elif not tree_id:
            try:
                live = check_canister_liveness(
                    descriptor_id, network=network, identity=identity
                )
            except RuntimeError:
                live = False
            if live:
                console.print(
                    f"[dim]multisig: adopt pinned {descriptor_id} (live, not yet in tree)[/dim]"
                )
                persist_multisig_backend_id(
                    env_name, network, descriptor_id, project_root=root
                )
                return descriptor_id

    if tree_id:
        console.print(f"[dim]multisig: adopt {tree_id}[/dim]")
        persist_multisig_backend_id(env_name, network, tree_id, project_root=root)
        return tree_id

    console.print("  deploy_sheet (System/governance/multisig)…")
    fragment = governance_deploy_sheet(root)
    result = run_casals_sheet_deploy(
        fragment,
        network=network,
        identity=identity,
        casals_src=casals_src,
        canister=conductor,
    )
    created = result.get("created_canisters") or []
    if created:
        console.print(f"  created canisters: {', '.join(created)}")
    errors = result.get("errors") or []
    if errors:
        raise RuntimeError(f"deploy_sheet governance errors: {errors}")

    tree = run_casals_tree(
        network=network,
        identity=identity,
        casals_src=casals_src,
        canister=conductor,
    )
    multisig_id = _find_canister_id(tree, _MULTISIG_TREE_NAME)
    if not multisig_id:
        raise RuntimeError("deploy_sheet completed but multisig not found in get_tree")
    persist_multisig_backend_id(env_name, network, multisig_id, project_root=root)
    console.print(f"[green]✓ multisig minted[/green] {multisig_id}")
    return multisig_id


def configure_multisig_signers(
    multisig_id: str,
    signers: list[str],
    *,
    network: str,
    identity: Optional[str],
    threshold: int = 1,
    expiry_secs: int = 604800,
) -> None:
    """Configure multisig signers and threshold (idempotent)."""
    signer_vec = "; ".join(f'principal "{s}"' for s in signers)
    arg = (
        f"(vec {{ {signer_vec} }} : vec principal, {threshold} : nat, "
        f"{expiry_secs} : nat)"
    )
    network_key = network.strip().lower()
    if network_key in ("local", "localhost"):
        cmd = [
            "dfx",
            "canister",
            "call",
            multisig_id,
            "configure",
            arg,
            "--network",
            network,
        ]
    else:
        cmd = [
            "icp",
            "canister",
            "call",
            multisig_id,
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
        raise RuntimeError(f"multisig configure failed: {err}")
    text = (result.stdout or "").strip().lower()
    if "ok" in text or "already configured" in text:
        console.print(
            f"[green]✓ multisig configured[/green] {threshold}-of-{len(signers)} signers"
        )
        return
    raise RuntimeError(f"multisig configure unexpected reply: {result.stdout.strip()}")


def configure_multisig_from_descriptor(
    *,
    env_name: str,
    network: str,
    identity: Optional[str],
    config: MultisigConfig,
    multisig_id: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> None:
    """Configure signers/threshold from the env descriptor."""
    root = project_root or get_project_root()
    multisig = (multisig_id or config.backend_id or "").strip()
    if not multisig:
        conductor = resolve_conductor_id(env_name, root)
        casals_src = resolve_casals_src(root)
        if conductor and casals_src:
            tree = run_casals_tree(
                network=network,
                identity=identity,
                casals_src=casals_src,
                canister=conductor,
            )
            multisig = _find_canister_id(tree, _MULTISIG_TREE_NAME)
    if not multisig:
        raise RuntimeError("multisig backend_id required before configure")
    signers = list(config.signers)
    threshold = int(config.threshold or 1)
    if not signers:
        deployer = _get_deployer_principal(identity)
        signers = [deployer]
        console.print(
            "[yellow]⚠️  multisig.signers empty — using deployer as sole 1-of-1 signer[/yellow]"
        )
    configure_multisig_signers(
        multisig,
        signers,
        network=network,
        identity=identity,
        threshold=threshold,
    )


def _casals_stack_ids(network: str, project_root: Path) -> dict[str, str]:
    ids: dict[str, str] = {}
    for key in _PRODUCT_CASALS_REALMS_KEYS:
        cid = _inventory_canister_id(project_root, key, network)
        if cid:
            ids[key] = cid
    return ids


def _product_canister_ids(network: str, project_root: Path) -> dict[str, str]:
    ids: dict[str, str] = {}
    for _stand, _reg_name, ids_key, _kind in _PRODUCT_REGISTRATIONS:
        cid = _product_canister_id(network, ids_key, project_root)
        if cid:
            ids[ids_key] = cid
    return ids


def platform_controller_expectations(
    *,
    network: str,
    multisig_id: str,
    casals_backend_id: str,
    deployer: str,
    project_root: Path,
) -> dict[str, list[str]]:
    """Expected controller sets for production topology."""
    expectations: dict[str, list[str]] = {}
    casals_stack = _casals_stack_ids(network, project_root)
    for name, canister_id in casals_stack.items():
        if canister_id:
            expectations[name] = [multisig_id]
    for name, canister_id in _product_canister_ids(network, project_root).items():
        if canister_id:
            expectations[name] = [casals_backend_id]
    if not is_production_topology_network(network):
        for name in list(expectations):
            base = expectations[name]
            if deployer and deployer not in base:
                expectations[name] = base + [deployer]
    return expectations


def apply_controller_topology(
    *,
    env_name: str,
    network: str,
    identity: Optional[str],
    multisig_id: str,
    project_root: Optional[Path] = None,
) -> None:
    """Apply production controller topology (multisig → Casals stack, Casals → products)."""
    root = project_root or get_project_root()
    if not is_production_topology_network(network):
        console.print(
            "[yellow]⚠️  skip controller topology: non-production network keeps deployer[/yellow]"
        )
        return
    casals_backend = _inventory_canister_id(root, "casals_backend", network)
    if not casals_backend:
        raise RuntimeError("casals_backend id required for controller topology")
    deployer = _get_deployer_principal(identity)
    expectations = platform_controller_expectations(
        network=network,
        multisig_id=multisig_id,
        casals_backend_id=casals_backend,
        deployer=deployer,
        project_root=root,
    )
    changed = 0
    for name, target in expectations.items():
        if name in _PRODUCT_CASALS_REALMS_KEYS:
            canister_id = _inventory_canister_id(root, name, network)
        else:
            canister_id = _product_canister_id(network, name, root)
        if not canister_id:
            continue
        current = public_canister_controllers(canister_id, network=network)
        target_set = set(target)
        if set(current) == target_set:
            console.print(f"[dim]{name}: controllers already correct[/dim]")
            continue
        console.print(f"  {name}: controllers -> {', '.join(target)}")
        replace_canister_controllers(
            canister_id, target, network=network, identity=identity
        )
        current = public_canister_controllers(canister_id, network=network)
        if set(current) != target_set:
            raise RuntimeError(
                f"{name} ({canister_id}) controller apply failed: "
                f"{list(current)} != {target}"
            )
        changed += 1
    if changed:
        console.print(f"[green]✓ updated controllers on {changed} canister(s)[/green]")
    else:
        console.print("[dim]controller topology already applied (no changes)[/dim]")


def verify_controller_topology(
    *,
    network: str,
    multisig_id: str,
    project_root: Optional[Path] = None,
) -> None:
    """Verify controller topology via public ``dfx canister info``."""
    root = project_root or get_project_root()
    if not is_production_topology_network(network):
        console.print(
            "[yellow]⚠️  skip controller topology verification on non-production[/yellow]"
        )
        return
    casals_backend = _inventory_canister_id(root, "casals_backend", network)
    if not casals_backend:
        raise RuntimeError("casals_backend id required for controller verification")
    expectations = platform_controller_expectations(
        network=network,
        multisig_id=multisig_id,
        casals_backend_id=casals_backend,
        deployer="",
        project_root=root,
    )
    errors: list[str] = []
    for name, expected in expectations.items():
        canister_id = (
            _inventory_canister_id(root, name, network)
            if name in _PRODUCT_CASALS_REALMS_KEYS
            else _product_canister_id(network, name, root)
        )
        if not canister_id:
            continue
        try:
            controllers = public_canister_controllers(canister_id, network=network)
        except RuntimeError as exc:
            errors.append(f"{name} ({canister_id}): cannot read controllers ({exc})")
            continue
        if set(controllers) != set(expected):
            errors.append(
                f"{name} ({canister_id}): actual={sorted(controllers)} "
                f"expected={sorted(expected)}"
            )
    if errors:
        raise RuntimeError(
            "controller topology verification failed:\n  - " + "\n  - ".join(errors)
        )
    console.print(
        f"[green]✓ verified controller topology on {len(expectations)} canister(s)[/green]"
    )


def run_governance_phases(
    *,
    env_name: str,
    network: str,
    identity: Optional[str],
    config: MultisigConfig,
    from_phase: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> None:
    """Run mint → configure → topology when ``multisig`` is configured."""
    root = project_root or get_project_root()
    phases = list(GOVERNANCE_SEED_PHASES)
    start_key = (from_phase or "").strip().replace("-", "_")
    if start_key:
        if start_key not in phases:
            raise RuntimeError(
                f"unknown governance --from-phase {from_phase!r} "
                f"(expected: {', '.join(phases)})"
            )
        phases = phases[phases.index(start_key) :]

    multisig_id = (config.backend_id or "").strip()
    for phase in phases:
        if phase == "multisig_mint":
            multisig_id = ensure_multisig_minted(
                env_name=env_name,
                network=network,
                identity=identity,
                config=config,
                project_root=root,
            )
            refreshed = load_env_config(env_name, root)
            parsed = parse_multisig_config(refreshed)
            if parsed and parsed.backend_id:
                config = parsed
                multisig_id = parsed.backend_id or multisig_id
        elif phase == "multisig_configure":
            configure_multisig_from_descriptor(
                env_name=env_name,
                network=network,
                identity=identity,
                config=config,
                multisig_id=multisig_id,
                project_root=root,
            )
        elif phase == "controller_topology":
            if not multisig_id:
                multisig_id = (config.backend_id or "").strip()
            if not multisig_id:
                raise RuntimeError(
                    "multisig backend_id required for controller topology"
                )
            apply_controller_topology(
                env_name=env_name,
                network=network,
                identity=identity,
                multisig_id=multisig_id,
                project_root=root,
            )
            verify_controller_topology(
                network=network,
                multisig_id=multisig_id,
                project_root=root,
            )
