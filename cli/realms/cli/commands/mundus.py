"""Mundus deployment commands.

Implements the deployment pipeline described in REWRITE.md:
1. Parse descriptor YAML (deployment-descriptors/*.yml)
2. For each realm: resolve artifacts, upload to deployer, submit manifest, poll
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console

from ..utils import console, get_project_root

DEPLOYER_URL = os.environ.get("DEPLOYER_URL", "https://deploy.realmsgos.dev")
POLL_INTERVAL_S = 10
POLL_TIMEOUT_S = 3600

_REGISTRY_IDS = {
    "staging": "7wzxh-wyaaa-aaaau-aggyq-cai",
    "demo": "rhw4p-gqaaa-aaaac-qbw7q-cai",
    "test": "yhw3g-fyaaa-aaaas-qgorq-cai",
}

_INSTALLER_IDS = {
    "staging": "lusjm-wqaaa-aaaau-ago7q-cai",
    "demo": "2s4td-daaaa-aaaao-bazmq-cai",
    "test": "fltjm-tyaaa-aaaap-qunhq-cai",
}


def _dfx_call(canister_id: str, method: str, arg: str, network: str, *, query: bool = False) -> str:
    cmd = ["dfx", "canister", "call", canister_id, method, arg, "--network", network, "--output", "json"]
    if query:
        cmd.append("--query")
    project_root = get_project_root()
    env = {**os.environ, "TERM": "xterm", "DFX_WARNING": "-mainnet_plaintext_identity"}
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"dfx call failed: {result.stderr}")
    return result.stdout.strip()


def _upload_file(filepath: Path) -> str:
    """Upload a file to the deployer and return its URL."""
    import urllib.request
    import urllib.parse

    url = f"{DEPLOYER_URL}/upload-file"
    boundary = "----RealmsUploadBoundary"
    filename = filepath.name
    data = filepath.read_bytes()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
    return f"{DEPLOYER_URL}{result['url']}"


_build_cache: dict[str, str] = {}

_VITE_PARAM_MAP = {
    "TEST_MODE": "VITE_TEST_MODE",
    "TEST_MODE_II_BYPASS": "VITE_TEST_MODE_II_BYPASS",
    "TEST_MODE_ADMIN_SELF_REGISTRATION": "VITE_TEST_MODE_ADMIN_SELF_REGISTRATION",
    "TEST_MODE_DEMO_DATA": "VITE_TEST_MODE_DEMO_DATA",
    "TEST_MODE_SKIP_TERMS": "VITE_TEST_MODE_SKIP_TERMS",
    "TEST_MODE_SKIP_PASSPORT_ZKPROOF": "VITE_TEST_MODE_SKIP_PASSPORT_ZKPROOF",
}


def _build_artifacts(parameters: dict | None = None) -> dict[str, Path]:
    """Build backend WASM and frontend tarball from source. Returns artifact paths."""
    import gzip
    import tarfile
    import tempfile

    project_root = get_project_root()

    build_env = {**os.environ, "CANISTER_CANDID_PATH": str(project_root / "src" / "realm_backend" / "realm_backend.did")}

    backend_config_path = project_root / "src" / "realm_backend" / "config.py"
    backend_config_backup = None

    if parameters:
        for param_name, value in parameters.items():
            vite_key = _VITE_PARAM_MAP.get(param_name)
            if vite_key:
                build_env[vite_key] = str(value).lower()
        applied = {k: v for k, v in parameters.items() if k in _VITE_PARAM_MAP}
        if applied:
            console.print(f"  Build parameters: {applied}")

        # Patch backend config.py with matching parameters
        if backend_config_path.exists():
            backend_config_backup = backend_config_path.read_text()
            patched = backend_config_backup
            for param_name, value in parameters.items():
                py_value = "True" if value is True else "False" if value is False else repr(value)
                old = f"{param_name} = False"
                new = f"{param_name} = {py_value}"
                if old in patched:
                    patched = patched.replace(old, new)
                else:
                    old_true = f"{param_name} = True"
                    if old_true in patched:
                        patched = patched.replace(old_true, new)
            if patched != backend_config_backup:
                backend_config_path.write_text(patched)

    console.print("  Building backend WASM...")
    result = subprocess.run(
        ["python", "-m", "basilisk", "realm_backend", "src/realm_backend/main.py"],
        cwd=project_root, capture_output=True, text=True, env=build_env,
    )
    if result.returncode != 0:
        if backend_config_backup is not None:
            backend_config_path.write_text(backend_config_backup)
        console.print(f"[red]  Backend build failed (exit code {result.returncode})[/red]")
        console.print(f"[red]  stdout:[/red]\n{result.stdout or '(empty)'}")
        console.print(f"[red]  stderr:[/red]\n{result.stderr or '(empty)'}")
        raise RuntimeError(
            f"Backend build failed (exit code {result.returncode}):\n"
            f"--- stdout ---\n{result.stdout or '(empty)'}\n"
            f"--- stderr ---\n{result.stderr or '(empty)'}"
        )

    # Restore original config.py after backend build
    if backend_config_backup is not None:
        backend_config_path.write_text(backend_config_backup)

    wasm_path = project_root / ".basilisk" / "realm_backend" / "realm_backend.wasm"
    if not wasm_path.exists():
        raise FileNotFoundError(f"WASM not found at {wasm_path}")

    wasm_gz = Path(tempfile.mktemp(suffix=".wasm.gz", prefix="realm_backend_"))
    with open(wasm_path, "rb") as f_in, gzip.open(wasm_gz, "wb") as f_out:
        f_out.write(f_in.read())
    console.print(f"  Backend WASM built ({wasm_gz.stat().st_size // 1024} KB)")

    console.print("  Generating Candid declarations...")
    result = subprocess.run(
        ["dfx", "generate", "realm_backend"],
        cwd=project_root, capture_output=True, text=True, env=build_env,
    )
    if result.returncode != 0:
        console.print(f"  [yellow]dfx generate warning: {result.stderr[:200]}[/yellow]")

    decl_src = project_root / "src" / "declarations" / "realm_backend"
    decl_dst = project_root / "src" / "realm_frontend" / "src" / "lib" / "declarations" / "realm_backend"
    if decl_src.exists():
        import shutil
        decl_dst.parent.mkdir(parents=True, exist_ok=True)
        if decl_dst.exists():
            shutil.rmtree(decl_dst)
        shutil.copytree(decl_src, decl_dst)
        console.print("  Declarations copied to frontend")

    console.print("  Building frontend...")
    fe_dir = project_root / "src" / "realm_frontend"
    result = subprocess.run(["npm", "install", "--legacy-peer-deps"], cwd=fe_dir, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"npm install failed:\n{result.stderr}")
    result = subprocess.run(["npm", "run", "build"], cwd=fe_dir, capture_output=True, text=True, env=build_env)
    if result.returncode != 0:
        raise RuntimeError(f"Frontend build failed:\n{result.stderr}")

    dist_dir = fe_dir / "dist"
    if not dist_dir.exists():
        dist_dir = fe_dir / "build"
    if not dist_dir.exists():
        raise FileNotFoundError("Frontend dist/build directory not found")

    tarball = Path(tempfile.mktemp(suffix=".tar.gz", prefix="realm_frontend_"))
    with tarfile.open(tarball, "w:gz") as tar:
        for item in dist_dir.iterdir():
            tar.add(item, arcname=item.name)
    console.print(f"  Frontend tarball built ({tarball.stat().st_size // 1024} KB)")

    return {"realm_backend": wasm_gz, "realm_frontend": tarball}


def _resolve_artifact(ref: str, artifact_type: str, network: str,
                      parameters: dict | None = None) -> str:
    """Resolve an artifact reference to a URL.

    Supported formats:
      - URL (https://...) -> returned as-is
      - version (e.g. "0.3.2" or "v0.3.2") -> GitHub release URL
      - "latest" -> latest GitHub release
      - "build" -> compile from source, upload to deployer
      - local path -> upload to deployer
    """
    if ref.startswith("http://") or ref.startswith("https://"):
        return ref

    if ref == "build":
        cache_key = f"build:{artifact_type}"
        if cache_key in _build_cache:
            return _build_cache[cache_key]
        artifacts = _build_artifacts(parameters=parameters)
        for atype, path in artifacts.items():
            console.print(f"  Uploading {atype}: {path.name}")
            url = _upload_file(path)
            _build_cache[f"build:{atype}"] = url
            path.unlink(missing_ok=True)
        return _build_cache[cache_key]

    repo = "smart-social-contracts/realms"
    if ref == "latest":
        gh_url = f"https://api.github.com/repos/{repo}/releases/latest"
        import urllib.request
        with urllib.request.urlopen(gh_url, timeout=30) as resp:
            release = json.loads(resp.read())
        version = release["tag_name"].lstrip("v")
    elif ref.lstrip("v").replace(".", "").isdigit():
        version = ref.lstrip("v")
    else:
        local_path = Path(ref)
        if local_path.exists():
            console.print(f"  Uploading local artifact: {local_path.name}")
            return _upload_file(local_path)
        raise ValueError(f"Unknown artifact reference: {ref}")

    if artifact_type == "realm_backend":
        return f"https://github.com/{repo}/releases/download/v{version}/realm_backend.wasm.gz"
    elif artifact_type == "realm_frontend":
        return f"https://github.com/{repo}/releases/download/v{version}/realm_frontend.tar.gz"
    else:
        raise ValueError(f"Unknown artifact type: {artifact_type}")


def _build_manifest(realm_entry: dict, network: str, deploy_mode: str,
                    backend_url: str, frontend_url: str,
                    canister_filter: str = "", infra: dict | None = None) -> dict:
    """Build a deployment manifest for a single realm.

    canister_filter: "" = both, "backend" = backend only, "frontend" = frontend only.
    infra: shared infrastructure canister IDs from the descriptor's ``infra`` section.
    """
    project_root = get_project_root()
    manifest_path = realm_entry.get("manifest", "")
    realm_manifest = {}
    manifest_dir = None
    if manifest_path:
        full_path = project_root / manifest_path
        if full_path.exists():
            realm_manifest = json.loads(full_path.read_text())
            manifest_dir = full_path.parent

    branding = {}
    if manifest_dir:
        for name, key in [("logo.png", "logo"), ("background.png", "background")]:
            img = manifest_dir / name
            if img.exists():
                console.print(f"  Uploading branding: {name}")
                branding[key] = _upload_file(img)

    artifacts = {}
    canister_ids = {}

    if canister_filter != "frontend":
        artifacts["realm_backend"] = backend_url
        canister_ids["backend"] = realm_entry.get("canister_id", "")
    if canister_filter != "backend":
        artifacts["realm_frontend"] = frontend_url
        canister_ids["frontend"] = realm_entry.get("frontend_canister_id", "")

    result = {
        "name": realm_entry.get("display_name", realm_entry.get("name", "unknown")),
        "network": network,
        "deploy_mode": deploy_mode,
        "artifacts": artifacts,
        "canister_ids": canister_ids,
        "realm": {
            "name": realm_entry.get("display_name", realm_entry.get("name", "")),
            **{k: v for k, v in realm_manifest.items() if k not in ("name",)},
        },
        "registry_canister_id": _REGISTRY_IDS.get(network, ""),
        "installer_canister_id": _INSTALLER_IDS.get(network, ""),
    }
    if branding:
        result["branding"] = branding
    if infra:
        result["infra"] = infra
    return result


def _format_elapsed(seconds: int) -> str:
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}m{secs:02d}s"


def _poll_status_line(elapsed: int, status: str, detail: str = "") -> str:
    """Build a formatted poll status line."""
    ts = _format_elapsed(elapsed)
    line = f"  [{ts}] {status}"
    if detail:
        line += f" — {detail}"
    return line


def _submit_and_poll(manifest: dict, network: str) -> bool:
    """Submit deployment request and poll for completion."""
    realm_name = manifest.get("name", "unknown")
    registry_id = _REGISTRY_IDS.get(network, "")
    if not registry_id:
        console.print(f"[red]  No registry ID for network '{network}'[/red]")
        return False

    manifest_json = json.dumps(manifest)
    candid_arg = '("' + manifest_json.replace("\\", "\\\\").replace('"', '\\"') + '")'

    console.print(f"  Submitting to registry ({registry_id})...")
    try:
        raw = _dfx_call(registry_id, "request_deployment", candid_arg, network)
        result = json.loads(json.loads(raw) if raw.startswith('"') else raw)
    except Exception as e:
        console.print(f"[red]  request_deployment failed: {e}[/red]")
        return False

    if not result.get("success"):
        console.print(f"[red]  Rejected: {result.get('error', 'unknown')}[/red]")
        return False

    job_id = result.get("job_id", "")
    console.print(f"  Job enqueued: [bold]{job_id}[/bold]")

    installer_id = _INSTALLER_IDS.get(network, "")
    if not installer_id:
        console.print(f"[yellow]  No installer ID — cannot poll[/yellow]")
        return True

    console.print(f"  Polling installer ({installer_id})...\n")

    start = time.time()
    prev_status = ""
    prev_detail = ""
    same_status_count = 0

    while time.time() - start < POLL_TIMEOUT_S:
        time.sleep(POLL_INTERVAL_S)
        elapsed = int(time.time() - start)
        try:
            raw = _dfx_call(installer_id, "get_deployment_job_status", f'("{job_id}")', network, query=True)
            data = json.loads(raw)
            ok = data.get("Ok") or (data if "job_id" in data else None)
            if ok:
                status = ok.get("status", "unknown")
                detail = ""

                # Build contextual detail per phase
                if status == "pending":
                    detail = "waiting for installer to pick up job"
                elif status == "allocating":
                    be = ok.get("backend_canister_id", "")
                    fe = ok.get("frontend_canister_id", "")
                    if be or fe:
                        detail = f"backend={be or '...'} frontend={fe or '...'}"
                    else:
                        detail = "allocating canisters"
                elif status == "installing_wasm":
                    be = ok.get("backend_canister_id", "")
                    detail = f"uploading WASM to {be}" if be else "installing WASM"
                elif status == "verifying":
                    wasm_ok = ok.get("wasm_verified", 0)
                    assets_ok = ok.get("assets_verified", 0)
                    parts = []
                    if wasm_ok:
                        parts.append("wasm [green]✓[/green]")
                    else:
                        expected = ok.get("expected_wasm_hash", "")[:12]
                        actual = ok.get("actual_wasm_hash", "")[:12]
                        if actual:
                            parts.append(f"wasm hash {actual}{'==' if actual == expected[:12] else '≠'}{expected}")
                        else:
                            parts.append("verifying wasm hash")
                    if assets_ok:
                        parts.append("assets [green]✓[/green]")
                    else:
                        parts.append("verifying assets")
                    detail = " | ".join(parts)
                elif status == "deploying_frontend":
                    fe = ok.get("frontend_canister_id", "")
                    assets_ok = ok.get("assets_verified", 0)
                    detail = f"uploading assets to {fe}" if fe else "deploying frontend"
                    if assets_ok:
                        detail += " (verified)"
                elif status == "extensions":
                    task_id = ok.get("ext_deploy_task_id", "")
                    if task_id:
                        detail = f"installing extensions (task: {task_id[:16]}…)"
                    else:
                        detail = "installing extensions & codices"
                elif status == "registering":
                    detail = "registering realm in registry"
                elif status == "completed":
                    completed_at = ok.get("completed_at", 0)
                    be = ok.get("backend_canister_id", "")
                    fe = ok.get("frontend_canister_id", "")
                    error = ok.get("error", "")
                    duration = _format_elapsed(elapsed)
                    console.print(f"  [{duration}] [green bold]completed[/green bold]")
                    if be:
                        console.print(f"         backend:  {be}")
                    if fe:
                        console.print(f"         frontend: {fe}")
                    if error:
                        console.print(f"  [yellow]⚠ {error}[/yellow]")
                    console.print(f"  [green]Deployment succeeded ({duration} total)[/green]")
                    return True
                elif status in ("failed", "failed_verification", "cancelled"):
                    error = ok.get("error", "")
                    be = ok.get("backend_canister_id", "")
                    wasm_ok = ok.get("wasm_verified", 0)
                    assets_ok = ok.get("assets_verified", 0)
                    console.print(f"  [{_format_elapsed(elapsed)}] [red bold]{status}[/red bold]")
                    if error:
                        console.print(f"  [red]  Error: {error}[/red]")
                    if be:
                        console.print(f"         backend:  {be}")
                    if status == "failed_verification":
                        console.print(f"         wasm_verified={wasm_ok} assets_verified={assets_ok}")
                        expected_w = ok.get("expected_wasm_hash", "")
                        actual_w = ok.get("actual_wasm_hash", "")
                        if expected_w or actual_w:
                            console.print(f"         wasm expected: {expected_w}")
                            console.print(f"         wasm actual:   {actual_w}")
                    return False

                # Suppress repeated identical lines; show phase transitions prominently
                if status != prev_status:
                    same_status_count = 0
                    color = {"pending": "dim", "extensions": "cyan", "verifying": "yellow",
                             "registering": "magenta", "allocating": "blue",
                             "installing_wasm": "blue", "deploying_frontend": "blue"}.get(status, "white")
                    console.print(f"  [{_format_elapsed(elapsed)}] [{color}]{status}[/{color}] — {detail}")
                    prev_status = status
                    prev_detail = detail
                elif detail != prev_detail:
                    same_status_count = 0
                    console.print(_poll_status_line(elapsed, status, detail))
                    prev_detail = detail
                else:
                    same_status_count += 1
                    if same_status_count % 6 == 0:
                        console.print(f"  [{_format_elapsed(elapsed)}] still {status} ({_format_elapsed(elapsed)} elapsed)")
            else:
                err = data.get("Err", {})
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                console.print(f"  [{_format_elapsed(elapsed)}] [yellow]poll error: {msg}[/yellow]")
        except Exception as e:
            console.print(f"  [{_format_elapsed(elapsed)}] [yellow]poll error: {e}[/yellow]")

    console.print(f"[red]  Timeout after {_format_elapsed(POLL_TIMEOUT_S)} — job may still be running[/red]")
    console.print(f"[red]  Job ID: {job_id}[/red]")
    return False


def mundus_deploy_new_command(
    name: str,
    network: str,
    artifact_version: str = "latest",
    display_name: str = "",
    description: str = "",
    cleanup: bool = False,
) -> None:
    """Deploy a new realm (no existing canister IDs -- creates new ones)."""
    backend_url = _resolve_artifact(artifact_version, "realm_backend", network)
    frontend_url = _resolve_artifact(artifact_version, "realm_frontend", network)
    console.print(f"Artifacts resolved:")
    console.print(f"  backend:  {backend_url}")
    console.print(f"  frontend: {frontend_url}\n")

    manifest = {
        "name": display_name or name,
        "network": network,
        "deploy_mode": "install",
        "artifacts": {"realm_backend": backend_url, "realm_frontend": frontend_url},
        "realm": {
            "name": display_name or name,
            "display_name": display_name or name,
            "description": description or f"Realm {name}",
        },
        "registry_canister_id": _REGISTRY_IDS.get(network, ""),
        "installer_canister_id": _INSTALLER_IDS.get(network, ""),
    }

    console.print(f"--- {display_name or name} (new realm) ---")
    ok = _submit_and_poll(manifest, network)

    if ok and cleanup:
        installer_id = _INSTALLER_IDS.get(network, "")
        job_id = manifest.get("_job_id", "")
        console.print("[yellow]Cleanup requested but not yet implemented[/yellow]")

    if not ok:
        raise typer.Exit(1)
    

def mundus_deploy_descriptor_command(
    descriptor: str,
    network: str,
    deploy_mode: str = "upgrade",
    artifact_version: str = "latest",
    realm_filter: str = "",
    canister_filter: str = "",
) -> None:
    """Deploy realms from a mundus descriptor YAML file.

    Optional filters:
      realm_filter   — deploy only the realm matching this name/display_name
      canister_filter — "backend", "frontend", or "" (both)
    """
    descriptor_path = Path(descriptor)
    if not descriptor_path.is_absolute():
        descriptor_path = get_project_root() / descriptor_path

    if not descriptor_path.exists():
        console.print(f"[red]Descriptor not found: {descriptor_path}[/red]")
        raise typer.Exit(1)

    if canister_filter and canister_filter not in ("backend", "frontend"):
        console.print(f"[red]Invalid canister filter '{canister_filter}'. Use 'backend' or 'frontend'.[/red]")
        raise typer.Exit(1)

    with open(descriptor_path) as f:
        desc = yaml.safe_load(f)

    desc_network = desc.get("network", network)
    if network and network != desc_network:
        console.print(f"[yellow]Warning: overriding descriptor network '{desc_network}' with '{network}'[/yellow]")
    else:
        network = desc_network

    parameters = desc.get("parameters") or {}
    infra = desc.get("infra") or {}

    realms = [e for e in desc.get("mundus", []) if e.get("type", "realm") == "realm"]

    if realm_filter:
        realms = [
            e for e in realms
            if realm_filter.lower() in (
                e.get("name", "").lower(),
                e.get("display_name", "").lower(),
            )
        ]
        if not realms:
            console.print(f"[red]No realm matching '{realm_filter}' in descriptor[/red]")
            raise typer.Exit(1)

    if not realms:
        console.print("[yellow]No realm entries in descriptor[/yellow]")
        return

    scope = f"{len(realms)} realm(s)"
    if canister_filter:
        scope += f" ({canister_filter} only)"
    console.print(f"Deploying {scope} to {network} (mode={deploy_mode})")
    if parameters:
        console.print(f"Parameters: {parameters}")
    console.print()

    backend_url = ""
    frontend_url = ""
    if canister_filter != "frontend":
        backend_url = _resolve_artifact(artifact_version, "realm_backend", network, parameters=parameters)
        console.print(f"Artifacts resolved:")
        console.print(f"  backend:  {backend_url}")
    if canister_filter != "backend":
        frontend_url = _resolve_artifact(artifact_version, "realm_frontend", network, parameters=parameters)
        if not backend_url:
            console.print(f"Artifacts resolved:")
        console.print(f"  frontend: {frontend_url}")
    console.print()

    results = []
    for realm in realms:
        name = realm.get("display_name", realm.get("name", "?"))
        console.print(f"--- {name} ---")
        manifest = _build_manifest(realm, network, deploy_mode, backend_url, frontend_url, canister_filter, infra=infra)
        ok = _submit_and_poll(manifest, network)
        results.append((name, ok))
        console.print()

    console.print("Summary:")
    all_ok = True
    for name, ok in results:
        symbol = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
        console.print(f"  {name}: {symbol}")
        if not ok:
            all_ok = False

    if not all_ok:
        raise typer.Exit(1)
