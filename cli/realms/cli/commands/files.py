"""File registry commands — bulk publish extensions and codices."""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .extension import publish_extension_command, publish_codex_command

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


def files_publish_command(
    network: str,
    registry: Optional[str] = None,
    identity: Optional[str] = None,
    extensions_only: bool = False,
    codices_only: bool = False,
):
    """Publish all extensions and codices to the file registry."""
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
