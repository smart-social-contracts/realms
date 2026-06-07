"""File registry commands — bulk publish extensions and codices."""

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .extension import (
    publish_extension_command,
    publish_codex_command,
    _dfx_call,
    _fetch_namespace_hashes,
    _publish_namespace,
    _upload_one_file,
)

console = Console()

_FILE_REGISTRY_IDS = {
    "staging": "iebdk-kqaaa-aaaau-agoxq-cai",
    "demo": "vi64l-3aaaa-aaaae-qj4va-cai",
    "test": "uq2mu-kaaaa-aaaah-avqcq-cai",
}


def _resolve_registry(network: str, registry: Optional[str]) -> str:
    if registry:
        return registry
    rid = _FILE_REGISTRY_IDS.get(network, "")
    if not rid:
        raise typer.BadParameter(
            f"No file_registry canister ID for network '{network}'. Use --registry."
        )
    return rid


def _find_project_root() -> Path:
    p = Path.cwd()
    while p != p.parent:
        if (p / "dfx.json").exists():
            return p
        p = p.parent
    return Path.cwd()


def files_reset_command(
    network: str,
    registry: Optional[str] = None,
    identity: Optional[str] = None,
):
    """Reinstall the file registry canister (wipes all stored files)."""
    reg = _resolve_registry(network, registry)
    root = _find_project_root()

    console.print(f"[bold red]Resetting file registry {reg} on {network}...[/bold red]")

    env = {**os.environ, "DFX_WARNING": "-mainnet_plaintext_identity"}

    console.print("  Uninstalling canister code...")
    cmd = ["dfx", "canister", "uninstall-code", reg, "--network", network]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=root, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"uninstall-code failed: {result.stderr}")

    console.print("  Building file_registry WASM...")
    build_env = {
        **env,
        "CANISTER_CANDID_PATH": str(root / "src" / "file_registry" / "file_registry.did"),
    }
    result = subprocess.run(
        ["python3", "-m", "basilisk", "file_registry", "src/file_registry/main.py"],
        capture_output=True, text=True, cwd=root, env=build_env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"WASM build failed: {result.stderr}")

    wasm_path = root / ".basilisk" / "file_registry" / "file_registry.wasm"
    console.print("  Installing fresh canister...")
    cmd = [
        "dfx", "canister", "install", reg,
        "--wasm", str(wasm_path),
        "--mode", "install", "--yes", "--network", network,
    ]
    if identity:
        cmd.extend(["--identity", identity])
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=root, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"canister install failed: {result.stderr}")

    console.print("[bold green]File registry reset complete.[/bold green]")


def files_build_command(
    extension_names: Optional[list[str]] = None,
):
    """Build frontend-rt bundles for extensions that have a package.json.

    Runs ``npm install && npm run build`` in each extension's frontend-rt/ directory
    and verifies that dist/index.js is produced.
    """
    root = _find_project_root()
    ext_root = root / "extensions" / "extensions"

    if not ext_root.is_dir():
        console.print(f"[red]Extensions directory not found: {ext_root}[/red]")
        raise typer.Exit(1)

    ext_dirs = sorted([
        d for d in ext_root.iterdir()
        if d.is_dir()
        and not d.name.startswith("_")
        and (d / "frontend-rt" / "package.json").exists()
    ])

    if extension_names is not None:
        names_set = set(extension_names)
        ext_dirs = [d for d in ext_dirs if d.name in names_set]

    if not ext_dirs:
        console.print("[yellow]No extensions with frontend-rt/package.json found.[/yellow]")
        return

    console.print(f"\n[bold]Building frontend bundles for {len(ext_dirs)} extensions[/bold]\n")

    failed = []
    for ed in ext_dirs:
        fe_dir = ed / "frontend-rt"
        console.print(f"[blue]  Building {ed.name}...[/blue]")

        result = subprocess.run(
            ["npm", "install"], cwd=fe_dir, capture_output=True, text=True
        )
        if result.returncode != 0:
            console.print(f"[red]    ✗ npm install failed[/red]")
            console.print(f"[dim]      {result.stderr.strip()[:200]}[/dim]")
            failed.append(ed.name)
            continue

        result = subprocess.run(
            ["npm", "run", "build"], cwd=fe_dir, capture_output=True, text=True
        )
        if result.returncode != 0:
            console.print(f"[red]    ✗ build failed[/red]")
            console.print(f"[dim]      {result.stderr.strip()[:200]}[/dim]")
            failed.append(ed.name)
            continue

        bundle = fe_dir / "dist" / "index.js"
        if not bundle.exists():
            console.print(f"[red]    ✗ dist/index.js not produced[/red]")
            failed.append(ed.name)
            continue

        size = bundle.stat().st_size
        console.print(f"[green]    ✓[/green] dist/index.js ({size:,} bytes)")

    if failed:
        console.print(f"\n[bold red]Build failed for: {', '.join(failed)}[/bold red]")
        raise typer.Exit(1)

    console.print(f"\n[bold green]All {len(ext_dirs)} extension bundles built successfully.[/bold green]")


def files_publish_command(
    network: str,
    registry: Optional[str] = None,
    identity: Optional[str] = None,
    extensions_only: bool = False,
    codices_only: bool = False,
    extension_names: Optional[list[str]] = None,
    codex_names: Optional[list[str]] = None,
):
    """Publish extensions and codices to the file registry.

    extension_names / codex_names: if provided, only publish these specific IDs.
    """
    reg = _resolve_registry(network, registry)
    root = _find_project_root()
    ext_root = root / "extensions" / "extensions"
    codex_root = root / "codices" / "codices"

    if not extensions_only:
        if codex_root.is_dir():
            codex_dirs = sorted([
                d for d in codex_root.iterdir()
                if d.is_dir() and not d.name.startswith("_")
            ])
            if codex_names is not None:
                codex_names_set = set(codex_names)
                codex_dirs = [d for d in codex_dirs if d.name in codex_names_set]
            console.print(f"\n[bold]Publishing {len(codex_dirs)} codices to {reg} ({network})[/bold]\n")
            for cd in codex_dirs:
                try:
                    publish_codex_command(
                        registry=reg,
                        source_dir=str(cd),
                        network=network,
                        identity=identity,
                    )
                except (typer.Exit, SystemExit):
                    console.print(f"[red]Failed to publish codex {cd.name}, continuing...[/red]")
        else:
            console.print(f"[yellow]Codices directory not found: {codex_root}[/yellow]")

    if not codices_only:
        if ext_root.is_dir():
            ext_dirs = sorted([
                d for d in ext_root.iterdir()
                if d.is_dir() and not d.name.startswith("_")
            ])
            if extension_names is not None:
                ext_names_set = set(extension_names)
                ext_dirs = [d for d in ext_dirs if d.name in ext_names_set]
            console.print(f"\n[bold]Publishing {len(ext_dirs)} extensions to {reg} ({network})[/bold]\n")
            for ed in ext_dirs:
                if not (ed / "manifest.json").exists():
                    console.print(f"[dim]  Skipping {ed.name} (no manifest.json)[/dim]")
                    continue
                try:
                    publish_extension_command(
                        registry=reg,
                        source_dir=str(ed),
                        network=network,
                        identity=identity,
                    )
                except (typer.Exit, SystemExit):
                    console.print(f"[red]Failed to publish extension {ed.name}, continuing...[/red]")
        else:
            console.print(f"[yellow]Extensions directory not found: {ext_root}[/yellow]")

    console.print("\n[bold green]File registry publish complete.[/bold green]")


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _casals_add_authorized_wasm(casals: str, params: dict, network: str, identity: Optional[str]) -> bool:
    """Call Casals add_authorized_wasm with a JSON arg. Returns success."""
    arg = json.dumps(params)
    candid_arg = '("' + arg.replace("\\", "\\\\").replace('"', '\\"') + '")'
    raw = _dfx_call(casals, "add_authorized_wasm", candid_arg, network, identity, timeout=120)
    try:
        res = json.loads(raw)
    except json.JSONDecodeError:
        res = {"raw": raw}
    if isinstance(res, dict) and res.get("ok") is True:
        console.print(f"  [green]✓[/green] authorized wasm {params.get('key')}")
        return True
    console.print(f"  [red]✗[/red] add_authorized_wasm({params.get('key')}) failed: {res}")
    return False


def files_publish_release_command(
    network: str,
    family: str,
    version: str,
    backend_wasm: Optional[str] = None,
    frontend_dist: Optional[str] = None,
    registry: Optional[str] = None,
    identity: Optional[str] = None,
    casals: Optional[str] = None,
    assets_wasm: Optional[str] = None,
    registry_backend: Optional[str] = None,
):
    """Publish a realm release fully on-chain (replaces the GitHub-release + off-chain
    worker download path).

    Uploads:
      - the backend WASM         -> file_registry  wasm/<family>-backend/<version>/<file>
      - the frontend build dir   -> file_registry  frontend/<family>-assets/<version>/<rel>

    Then, when the relevant targets are provided:
      - --casals + --assets-wasm: authorize the backend WASM and the certified-assets
        WASM (the latter carrying bundle_namespace = the frontend namespace) so Casals
        can install + upload the bundle per realm;
      - --registry-backend: record the version in the realm version catalog.
    """
    reg = _resolve_registry(network, registry)

    if not backend_wasm and not frontend_dist:
        raise typer.BadParameter("provide at least one of --backend-wasm / --frontend-dist")

    backend_ns = f"wasm/{family}-backend/{version}"
    frontend_ns = f"frontend/{family}-assets/{version}"
    backend_key = f"{family}-backend@{version}"
    frontend_key = f"{family}-assets@{version}"
    backend_hash = ""
    backend_path = ""

    # 1. Backend WASM -------------------------------------------------------
    if backend_wasm:
        if not os.path.isfile(backend_wasm):
            raise typer.BadParameter(f"backend wasm not found: {backend_wasm}")
        backend_path = os.path.basename(backend_wasm)
        backend_hash = _sha256_file(backend_wasm)
        console.print(f"\n[bold]Backend WASM → {reg}:{backend_ns}/{backend_path}[/bold]")
        console.print(f"  sha256={backend_hash}")
        existing = _fetch_namespace_hashes(reg, backend_ns, network, identity)
        if _upload_one_file(reg, backend_ns, backend_path, backend_wasm, network, identity, existing) == "failed":
            raise typer.Exit(1)
        _publish_namespace(reg, backend_ns, network, identity)

    # 2. Frontend bundle ----------------------------------------------------
    fe_count = 0
    if frontend_dist:
        if not os.path.isdir(frontend_dist):
            raise typer.BadParameter(f"frontend dist not found: {frontend_dist}")
        console.print(f"\n[bold]Frontend bundle → {reg}:{frontend_ns}/[/bold]")
        existing = _fetch_namespace_hashes(reg, frontend_ns, network, identity)
        failed = 0
        for root, _dirs, files in os.walk(frontend_dist):
            for fname in sorted(files):
                local = os.path.join(root, fname)
                rel = os.path.relpath(local, frontend_dist).replace(os.sep, "/")
                r = _upload_one_file(reg, frontend_ns, rel, local, network, identity, existing)
                if r == "failed":
                    failed += 1
                elif r == "uploaded":
                    fe_count += 1
        if failed:
            console.print(f"[red]frontend upload had {failed} failures[/red]")
            raise typer.Exit(1)
        _publish_namespace(reg, frontend_ns, network, identity)
        console.print(f"  {fe_count} files uploaded")

    # 3. Authorize in Casals ------------------------------------------------
    if casals:
        console.print(f"\n[bold]Authorizing WASMs in Casals {casals}[/bold]")
        if backend_wasm:
            _casals_add_authorized_wasm(casals, {
                "key": backend_key, "kind": "backend",
                "registry_namespace": backend_ns, "registry_path": backend_path,
                "wasm_hash": backend_hash,
                "description": f"{family} realm backend {version}",
            }, network, identity)
        if frontend_dist:
            if not assets_wasm or not os.path.isfile(assets_wasm):
                console.print(
                    "  [yellow]![/yellow] skipping frontend authorize: pass --assets-wasm "
                    "(the certified-assets canister WASM) to authorize the frontend"
                )
            else:
                assets_hash = _sha256_file(assets_wasm)
                assets_ns = f"wasm/{family}-assetstorage/{version}"
                assets_path = os.path.basename(assets_wasm)
                console.print(f"  assets wasm → {reg}:{assets_ns}/{assets_path} (sha256={assets_hash})")
                ex = _fetch_namespace_hashes(reg, assets_ns, network, identity)
                if _upload_one_file(reg, assets_ns, assets_path, assets_wasm, network, identity, ex) != "failed":
                    _publish_namespace(reg, assets_ns, network, identity)
                _casals_add_authorized_wasm(casals, {
                    "key": frontend_key, "kind": "frontend",
                    "registry_namespace": assets_ns, "registry_path": assets_path,
                    "wasm_hash": assets_hash,
                    "bundle_namespace": frontend_ns,
                    "description": f"{family} realm frontend {version}",
                }, network, identity)

    # 4. Record the version in the realm catalog ----------------------------
    if registry_backend:
        console.print(f"\n[bold]Publishing version {version} to registry {registry_backend}[/bold]")
        pv = json.dumps({
            "version": version,
            "backend_wasm_url": f"fileregistry://{reg}/{backend_ns}/{backend_path}" if backend_wasm else "",
            "frontend_tar_url": f"fileregistry://{reg}/{frontend_ns}" if frontend_dist else "",
            "backend_wasm_hash": backend_hash,
            "frontend_tar_hash": "",
        })
        candid_arg = '("' + pv.replace("\\", "\\\\").replace('"', '\\"') + '")'
        raw = _dfx_call(registry_backend, "publish_version", candid_arg, network, identity, timeout=120)
        console.print(f"  registry: {raw}")

    console.print("\n[bold green]Release publish complete.[/bold green]")
