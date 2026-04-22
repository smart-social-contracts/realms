#!/usr/bin/env python3
"""
publish_layered.py — orchestrate end-to-end publication of the layered realm
artifacts (Layer 1 base WASM, Layer 2 extension bundles, Layer 3 codex packages)
to a single ``file_registry`` canister.

What it does (in order):

    1. Optionally builds all per-extension frontend-rt/ ESM bundles by
       shelling into ``scripts/build_runtime_bundles.py`` (skip with
       ``--skip-frontend-build``).
    2. Optionally publishes the realm base WASM (gzip) to
       ``wasm/realm-base-{version}.wasm.gz`` if ``--base-wasm <path>`` is
       provided. Uses ``store_file_chunk`` + ``finalize_chunked_file`` for
       large WASMs (>768 KiB).
    3. For every extension under ``realms-extensions/extensions/`` with a
       ``manifest.json``, runs ``realms extension publish`` which uploads:
           ext/<id>/<version>/manifest.json
           ext/<id>/<version>/backend/*.py
           ext/<id>/<version>/frontend/dist/index.js
           ext/<id>/<version>/frontend/i18n/**.json
       and then publishes the namespace.
    4. For every codex under ``codices/codices/`` (excluding ``_common``
       and ``common``), runs ``realms codex publish`` to upload all .py
       files + manifest under ``codex/<id>/<version>/``.

The script is the operator-side entrypoint behind the
``layered-deploy-dominion`` GitHub Actions workflow, but can be run locally
against a ``file_registry`` canister deployed to any network.

Usage:

    # Publish everything to a staging file_registry, including building all
    # frontend-rt bundles first:
    python scripts/publish_layered.py \\
        --registry $FILE_REGISTRY_CANISTER_ID \\
        --network staging \\
        --identity $DFX_IDENTITY \\
        --base-wasm out/realm-base.wasm.gz \\
        --base-wasm-version 0.5.0

    # Skip the WASM (assume it's already published) and only re-publish
    # extensions and codices, without rebuilding frontend bundles:
    python scripts/publish_layered.py \\
        --registry $FILE_REGISTRY_CANISTER_ID \\
        --network staging \\
        --skip-base-wasm --skip-frontend-build

    # Publish only a subset of extensions (handy when iterating on one
    # extension's UI):
    python scripts/publish_layered.py \\
        --registry $FILE_REGISTRY_CANISTER_ID \\
        --network staging \\
        --skip-base-wasm \\
        --only-extensions voting,welcome
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTENSIONS_REPO = REPO_ROOT.parent / "realms-extensions"
DEFAULT_CODICES_ROOT = REPO_ROOT / "codices" / "codices"
SKIP_EXTENSION_IDS = {"_shared"}
SKIP_CODEX_IDS = {"_common", "common"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: List[str], cwd: Optional[Path] = None, *, quiet: bool = False) -> int:
    """Run a subprocess and stream its stdout/stderr live; return rc.

    When *quiet* is True, the command echo is truncated and stdout is
    captured (not streamed) to avoid flooding CI logs with base64 data.
    stderr is still printed on failure.
    """
    if not quiet:
        print(f"$ {' '.join(cmd)}")
        proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    else:
        proc = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None,
            capture_output=True,
        )
        if proc.returncode != 0 and proc.stderr:
            sys.stderr.buffer.write(proc.stderr)
    return proc.returncode


def _resolve_extensions_root(repo: Path) -> Path:
    """Return the directory that holds per-extension subdirectories.

    The ``realms-extensions`` submodule has a nested layout — extensions
    live under ``<repo>/extensions/extensions/<name>/manifest.json`` (the
    outer ``extensions/`` dir is the submodule root, which also contains
    README.md, marketplace/, testing/, etc. and would otherwise be
    iterated as if they were extensions).

    But when this script is invoked against a *standalone* checkout of
    the ``realms-extensions`` repo (the historical local-dev mode, e.g.
    ``--extensions-repo ../realms-extensions``) the layout is flat:
    ``<repo>/extensions/<name>/manifest.json``.

    Try the nested layout first, fall back to the flat one. Fail loud
    if neither contains any ``manifest.json`` — silently iterating an
    empty dir and "publishing" zero extensions is exactly the bug that
    let ``package_manager`` fail to install on staging in #183.
    """
    nested = repo / "extensions" / "extensions"
    flat = repo / "extensions"

    def _has_manifests(candidate: Path) -> bool:
        if not candidate.is_dir():
            return False
        for child in candidate.iterdir():
            if not child.is_dir() or child.name in SKIP_EXTENSION_IDS:
                continue
            if (child / "manifest.json").exists():
                return True
        return False

    if _has_manifests(nested):
        return nested
    if _has_manifests(flat):
        return flat
    raise SystemExit(
        "ERROR: no extension manifests found under either of:\n"
        f"  {nested}  (nested realms+submodule layout)\n"
        f"  {flat}  (standalone realms-extensions checkout layout)\n"
        "Did the realms-extensions submodule fail to initialize? Try:\n"
        "  git submodule update --init --recursive"
    )


def _list_extensions(extensions_root: Path, only: Optional[List[str]]) -> List[Path]:
    if not extensions_root.is_dir():
        raise FileNotFoundError(f"Extensions root not found: {extensions_root}")
    out: List[Path] = []
    for child in sorted(extensions_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name in SKIP_EXTENSION_IDS:
            continue
        if not (child / "manifest.json").exists():
            continue
        if only and child.name not in only:
            continue
        out.append(child)
    return out


def _list_codices(codices_root: Path, only: Optional[List[str]]) -> List[Path]:
    if not codices_root.is_dir():
        raise FileNotFoundError(f"Codices root not found: {codices_root}")
    out: List[Path] = []
    for child in sorted(codices_root.iterdir()):
        if not child.is_dir() or child.name in SKIP_CODEX_IDS:
            continue
        if only and child.name not in only:
            continue
        # Only include codex dirs that have at least one .py file.
        if not any(p.suffix == ".py" for p in child.iterdir()):
            continue
        out.append(child)
    return out


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def _step_build_frontends(
    extensions_repo: Path,
    only: Optional[List[str]],
    jobs: int,
    skip_install_existing: bool,
) -> int:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "build_runtime_bundles.py"),
        "--extensions-repo",
        str(extensions_repo),
        "--jobs",
        str(jobs),
    ]
    if only:
        cmd.extend(["--only", ",".join(only)])
    if skip_install_existing:
        cmd.append("--skip-install-existing")
    return _run(cmd)


def _step_publish_base_wasm(
    *,
    realms_cli: List[str],
    registry: str,
    network: str,
    identity: Optional[str],
    base_wasm_path: Path,
    base_wasm_version: str,
    namespace: str,
    registry_path: str,
) -> int:
    """Upload the base realm WASM directly to file_registry using the
    `extension publish` chunked-upload helper, then publish the namespace.

    For simplicity we ride on the ``store_file`` / ``store_file_chunk`` /
    ``publish_namespace`` calls that the ``realms extension publish`` command
    already exercises, by invoking dfx directly. We avoid a separate Python
    canister call helper here so this script stays a thin orchestrator over
    the ``realms`` CLI.
    """
    import base64
    import json

    if not base_wasm_path.exists():
        print(f"ERROR: --base-wasm not found: {base_wasm_path}", file=sys.stderr)
        return 1

    # Use realms wasm install/hash helpers? No — those *install* the WASM.
    # For *publishing* the WASM we use file_registry directly.
    size = base_wasm_path.stat().st_size
    print(
        f"Publishing base WASM {base_wasm_path} ({size:,} bytes) "
        f"→ {namespace}/{registry_path} on {registry} ({network})"
    )

    chunk_size = 768 * 1024  # 768 KiB raw -> ~1 MiB after base64
    threshold = chunk_size

    def _dfx_call(method: str, payload: dict) -> int:
        import tempfile as _tempfile
        cmd = ["dfx", "canister", "call"]
        if identity:
            cmd.extend(["--identity", identity])
        if network:
            cmd.extend(["--network", network])
        candid = '("' + json.dumps(payload).replace("\\", "\\\\").replace('"', '\\"') + '")'
        if len(candid.encode("utf-8")) >= 100 * 1024:
            fd, arg_path = _tempfile.mkstemp(prefix="dfx-arg-", suffix=".did")
            try:
                with os.fdopen(fd, "w") as fh:
                    fh.write(candid)
                cmd.extend([registry, method, "--argument-file", arg_path])
                return _run(cmd)
            finally:
                try:
                    os.unlink(arg_path)
                except OSError:
                    pass
        cmd.extend([registry, method, candid])
        return _run(cmd)

    if size <= threshold:
        with base_wasm_path.open("rb") as fh:
            blob = fh.read()
        rc = _dfx_call(
            "store_file",
            {
                "namespace": namespace,
                "path": registry_path,
                "content_b64": base64.b64encode(blob).decode("ascii"),
                "content_type": "application/wasm",
            },
        )
        if rc != 0:
            return rc
    else:
        total_chunks = (size + chunk_size - 1) // chunk_size
        print(f"  chunked upload: {total_chunks} chunks of up to {chunk_size:,} bytes")
        with base_wasm_path.open("rb") as fh:
            for i in range(total_chunks):
                blob = fh.read(chunk_size)
                rc = _dfx_call(
                    "store_file_chunk",
                    {
                        "namespace": namespace,
                        "path": registry_path,
                        "chunk_index": i,
                        "total_chunks": total_chunks,
                        "data_b64": base64.b64encode(blob).decode("ascii"),
                        "content_type": "application/wasm",
                    },
                )
                if rc != 0:
                    print(f"  chunk {i + 1}/{total_chunks} upload failed", file=sys.stderr)
                    return rc
        # Use the *incremental* finalize_chunked_file_step rather than the
        # single-shot finalize_chunked_file: a multi-MB WASM running through
        # SHA-256 in WASI Python costs >40B instructions and trips the
        # per-message instruction budget. We compute the SHA-256 locally
        # and pass it on the first step call; the registry stores it as-is.
        import hashlib as _hashlib
        h = _hashlib.sha256()
        with base_wasm_path.open("rb") as fh:
            for blob in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(blob)
        expected_sha = h.hexdigest()
        print(f"  finalizing incrementally (sha256={expected_sha[:16]}…)")

        first = True
        while True:
            payload = {"namespace": namespace, "path": registry_path,
                       "batch_size": 1}
            if first:
                payload["expected_sha256"] = expected_sha
                first = False
            # Capture stdout so we can parse {"done": true/false, ...}.
            import subprocess as _sp
            cmd = ["dfx", "canister", "call"]
            if identity:
                cmd.extend(["--identity", identity])
            if network:
                cmd.extend(["--network", network])
            candid = '("' + json.dumps(payload).replace("\\", "\\\\").replace('"', '\\"') + '")'
            cmd.extend([registry, "finalize_chunked_file_step", candid])
            print("$", " ".join(cmd), flush=True)
            cp = _sp.run(cmd, capture_output=True, text=True)
            if cp.returncode != 0:
                print(cp.stderr, file=sys.stderr)
                return cp.returncode
            # dfx wraps the response as a Candid record:
            #   ("{\"ok\":true,...}",)   -- single line, OR
            #   (\n  "{\"ok\":true,...}",\n)   -- multi-line
            # Extract the json string between the first `"` and the last `"`.
            raw = cp.stdout
            try:
                start = raw.index('"')
                end = raw.rindex('"')
                inner = raw[start + 1:end].encode("utf-8").decode("unicode_escape")
                resp = json.loads(inner)
            except Exception as e:
                print(f"  could not parse step response: {raw!r} ({e})",
                      file=sys.stderr)
                return 1
            if resp.get("error"):
                print(f"  finalize step error: {resp['error']}", file=sys.stderr)
                return 1
            print(f"  step ok: processed={resp.get('processed')}/"
                  f"{resp.get('total')} done={resp.get('done')}")
            if resp.get("done"):
                break

    return _dfx_call("publish_namespace", {"namespace": namespace})


def _step_publish_extensions(
    *,
    realms_cli: List[str],
    registry: str,
    network: str,
    identity: Optional[str],
    extensions_repo: Path,
    only: Optional[List[str]],
    namespace_prefix: str,
) -> int:
    ext_dirs = _list_extensions(_resolve_extensions_root(extensions_repo), only)
    if not ext_dirs:
        # _resolve_extensions_root guarantees the dir has at least one
        # manifest.json, so an empty `ext_dirs` here means the `--only`
        # filter excluded everything. That's a user mistake, not an
        # auto-recoverable no-op — fail loud.
        if only:
            raise SystemExit(
                f"ERROR: --only-extensions={only} matched zero extensions "
                f"under {_resolve_extensions_root(extensions_repo)}. "
                "Available: "
                f"{sorted(p.name for p in _resolve_extensions_root(extensions_repo).iterdir() if p.is_dir())}"
            )
        # Genuinely empty (no extensions at all) is also unexpected and
        # would be silently ignored historically — surface it.
        raise SystemExit(
            "ERROR: zero extensions found. This used to silently succeed "
            "and is the root cause of issue: package_manager not "
            "publishing on staging."
        )
    print(f"\nPublishing {len(ext_dirs)} extensions → {registry}:{namespace_prefix}/<id>/<ver>")
    failures: List[str] = []
    for ext_dir in ext_dirs:
        cmd = realms_cli + [
            "extension",
            "publish",
            "--registry",
            registry,
            "--source-dir",
            str(ext_dir),
            "--namespace-prefix",
            namespace_prefix,
            "--network",
            network,
        ]
        if identity:
            cmd.extend(["--identity", identity])
        rc = _run(cmd)
        if rc != 0:
            failures.append(ext_dir.name)
    if failures:
        print(f"\nExtension publish failed for: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


def _step_publish_codices(
    *,
    realms_cli: List[str],
    registry: str,
    network: str,
    identity: Optional[str],
    codices_root: Path,
    only: Optional[List[str]],
    namespace_prefix: str,
) -> int:
    codex_dirs = _list_codices(codices_root, only)
    if not codex_dirs:
        print("No codices to publish.")
        return 0
    print(f"\nPublishing {len(codex_dirs)} codices → {registry}:{namespace_prefix}/<id>/<ver>")
    failures: List[str] = []
    for codex_dir in codex_dirs:
        cmd = realms_cli + [
            "codex",
            "publish",
            "--registry",
            registry,
            "--source-dir",
            str(codex_dir),
            "--namespace-prefix",
            namespace_prefix,
            "--network",
            network,
        ]
        if identity:
            cmd.extend(["--identity", identity])
        rc = _run(cmd)
        if rc != 0:
            failures.append(codex_dir.name)
    if failures:
        print(f"\nCodex publish failed for: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


# ---------------------------------------------------------------------------
# Frontend asset publish
# ---------------------------------------------------------------------------

_CONTENT_TYPE_MAP = {
    ".html": "text/html",
    ".js": "application/javascript",
    ".mjs": "application/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".txt": "text/plain",
    ".xml": "application/xml",
    ".webmanifest": "application/manifest+json",
    ".map": "application/json",
    ".wasm": "application/wasm",
}

_COMPRESSIBLE_CONTENT_TYPES = {
    "text/html",
    "application/javascript",
    "text/css",
    "application/json",
    "image/svg+xml",
    "text/plain",
    "application/xml",
    "application/manifest+json",
    "application/wasm",
}


def _guess_content_type(path: Path) -> str:
    ct = _CONTENT_TYPE_MAP.get(path.suffix.lower())
    if ct:
        return ct
    guess, _ = mimetypes.guess_type(str(path))
    return guess or "application/octet-stream"


def _upload_blob_to_registry(
    blob: bytes,
    *,
    registry: str,
    network: str,
    identity: Optional[str],
    namespace: str,
    path: str,
    content_type: str,
    chunk_size: int = 200 * 1024,
) -> int:
    """Upload a single blob to file_registry, using chunked upload if needed.

    The chunk_size default (200 KiB) is tuned to stay within the IC's
    40-billion-instruction-per-message limit when the file_registry is a
    Python/WASI canister (base64 decode + SHA-256 + stable-memory write
    are instruction-heavy in WASI).

    Returns 0 on success, non-zero on failure.
    """

    def _dfx_call(method: str, payload: dict) -> int:
        import tempfile as _tempfile
        cmd = ["dfx", "canister", "call"]
        if identity:
            cmd.extend(["--identity", identity])
        if network:
            cmd.extend(["--network", network])
        candid = '("' + json.dumps(payload).replace("\\", "\\\\").replace('"', '\\"') + '")'
        if len(candid.encode("utf-8")) >= 100 * 1024:
            fd, arg_path = _tempfile.mkstemp(prefix="dfx-arg-", suffix=".did")
            try:
                with os.fdopen(fd, "w") as fh:
                    fh.write(candid)
                cmd.extend([registry, method, "--argument-file", arg_path])
                return _run(cmd, quiet=True)
            finally:
                try:
                    os.unlink(arg_path)
                except OSError:
                    pass
        cmd.extend([registry, method, candid])
        return _run(cmd, quiet=True)

    file_size = len(blob)
    if file_size <= chunk_size:
        return _dfx_call("store_file", {
            "namespace": namespace,
            "path": path,
            "content_b64": base64.b64encode(blob).decode("ascii"),
            "content_type": content_type,
        })

    total_chunks = (file_size + chunk_size - 1) // chunk_size
    for i in range(total_chunks):
        start = i * chunk_size
        end = min(start + chunk_size, file_size)
        rc = _dfx_call("store_file_chunk", {
            "namespace": namespace,
            "path": path,
            "chunk_index": i,
            "total_chunks": total_chunks,
            "data_b64": base64.b64encode(blob[start:end]).decode("ascii"),
            "content_type": content_type,
        })
        if rc != 0:
            print(f"  chunk {i + 1}/{total_chunks} failed for {path}", file=sys.stderr)
            return rc

    expected_sha = hashlib.sha256(blob).hexdigest()
    first = True
    while True:
        payload = {"namespace": namespace, "path": path, "batch_size": 1}
        if first:
            payload["expected_sha256"] = expected_sha
            first = False
        cmd = ["dfx", "canister", "call"]
        if identity:
            cmd.extend(["--identity", identity])
        if network:
            cmd.extend(["--network", network])
        candid = '("' + json.dumps(payload).replace("\\", "\\\\").replace('"', '\\"') + '")'
        cmd.extend([registry, "finalize_chunked_file_step", candid])
        cp = subprocess.run(cmd, capture_output=True, text=True)
        if cp.returncode != 0:
            print(cp.stderr, file=sys.stderr)
            return cp.returncode
        raw = cp.stdout
        try:
            s = raw.index('"')
            e = raw.rindex('"')
            inner = raw[s + 1:e].encode("utf-8").decode("unicode_escape")
            resp = json.loads(inner)
        except Exception as exc:
            print(f"  finalize parse error: {raw!r} ({exc})", file=sys.stderr)
            return 1
        if resp.get("error"):
            print(f"  finalize error: {resp['error']}", file=sys.stderr)
            return 1
        if resp.get("done"):
            break

    return 0


def _step_publish_frontend(
    *,
    registry: str,
    network: str,
    identity: Optional[str],
    dist_dir: Path,
    namespace: str,
) -> int:
    """Upload every file in *dist_dir* to file_registry under *namespace*,
    then upload a ``_manifest.json`` listing all files with metadata, and
    finally ``publish_namespace``.

    For compressible text types (HTML, JS, CSS, JSON, SVG, etc.), we also
    upload a gzip-compressed variant alongside the identity (raw) version.
    The manifest records both encodings so the on-chain installer can push
    both to the asset canister, enabling browsers to receive compressed
    responses.
    """
    if not dist_dir.is_dir():
        print(f"ERROR: dist dir not found: {dist_dir}", file=sys.stderr)
        return 1

    all_files = sorted(
        p for p in dist_dir.rglob("*") if p.is_file()
    )
    if not all_files:
        print(f"ERROR: dist dir is empty: {dist_dir}", file=sys.stderr)
        return 1

    def _dfx_call(method: str, payload: dict) -> int:
        import tempfile as _tempfile
        cmd = ["dfx", "canister", "call"]
        if identity:
            cmd.extend(["--identity", identity])
        if network:
            cmd.extend(["--network", network])
        candid = '("' + json.dumps(payload).replace("\\", "\\\\").replace('"', '\\"') + '")'
        if len(candid.encode("utf-8")) >= 100 * 1024:
            fd, arg_path = _tempfile.mkstemp(prefix="dfx-arg-", suffix=".did")
            try:
                with os.fdopen(fd, "w") as fh:
                    fh.write(candid)
                cmd.extend([registry, method, "--argument-file", arg_path])
                return _run(cmd, quiet=True)
            finally:
                try:
                    os.unlink(arg_path)
                except OSError:
                    pass
        cmd.extend([registry, method, candid])
        return _run(cmd, quiet=True)

    print(
        f"\nPublishing frontend ({len(all_files)} files) from {dist_dir} "
        f"→ {registry}:{namespace}"
    )

    manifest_entries = []

    for filepath in all_files:
        rel = filepath.relative_to(dist_dir).as_posix()
        content_type = _guess_content_type(filepath)
        raw_bytes = filepath.read_bytes()
        file_size = len(raw_bytes)
        file_hash = hashlib.sha256(raw_bytes).hexdigest()

        key = "/" + rel if not rel.startswith("/") else rel

        entry = {
            "path": rel,
            "key": key,
            "content_type": content_type,
            "size": file_size,
            "sha256": file_hash,
            "encodings": ["identity"],
        }

        # Upload identity (raw) version
        rc = _upload_blob_to_registry(
            raw_bytes,
            registry=registry,
            network=network,
            identity=identity,
            namespace=namespace,
            path=rel,
            content_type=content_type,
        )
        if rc != 0:
            print(f"  FAILED to upload {rel}", file=sys.stderr)
            return rc

        # Upload gzip version for compressible types
        if content_type in _COMPRESSIBLE_CONTENT_TYPES and file_size > 0:
            gz_bytes = gzip.compress(raw_bytes, compresslevel=9)
            savings_pct = (1 - len(gz_bytes) / file_size) * 100 if file_size else 0
            if len(gz_bytes) < file_size:
                gz_path = rel + ".gz"
                gz_hash = hashlib.sha256(gz_bytes).hexdigest()
                rc = _upload_blob_to_registry(
                    gz_bytes,
                    registry=registry,
                    network=network,
                    identity=identity,
                    namespace=namespace,
                    path=gz_path,
                    content_type=content_type,
                )
                if rc != 0:
                    print(f"  FAILED to upload {gz_path}", file=sys.stderr)
                    return rc

                entry["encodings"].append("gzip")
                entry["gzip_path"] = gz_path
                entry["gzip_size"] = len(gz_bytes)
                entry["gzip_sha256"] = gz_hash

                print(
                    f"  ✓ {rel} ({file_size:,} bytes, {content_type}) "
                    f"+ gzip ({len(gz_bytes):,} bytes, {savings_pct:.0f}% smaller)"
                )
            else:
                print(f"  ✓ {rel} ({file_size:,} bytes, {content_type}) [gzip not smaller, skipped]")
        else:
            print(f"  ✓ {rel} ({file_size:,} bytes, {content_type})")

        manifest_entries.append(entry)

    manifest = {
        "version": 2,
        "files": manifest_entries,
        "total_files": len(manifest_entries),
        "total_size": sum(e["size"] for e in manifest_entries),
    }
    manifest_json = json.dumps(manifest, indent=2)
    rc = _dfx_call("store_file", {
        "namespace": namespace,
        "path": "_manifest.json",
        "content_b64": base64.b64encode(manifest_json.encode()).decode("ascii"),
        "content_type": "application/json",
    })
    if rc != 0:
        print("  FAILED to upload _manifest.json", file=sys.stderr)
        return rc
    print(f"  ✓ _manifest.json ({len(manifest_entries)} files listed)")

    rc = _dfx_call("publish_namespace", {"namespace": namespace})
    if rc != 0:
        print(f"  FAILED to publish namespace {namespace}", file=sys.stderr)
        return rc

    gzip_count = sum(1 for e in manifest_entries if "gzip" in e.get("encodings", []))
    print(
        f"  frontend published: {namespace} "
        f"({len(manifest_entries)} files, {gzip_count} with gzip, "
        f"{manifest['total_size']:,} bytes)"
    )
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Iterable[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Publish base WASM, all extension bundles, and all codex packages "
            "to a single file_registry canister."
        )
    )
    parser.add_argument(
        "--registry", "-r",
        required=True,
        help="file_registry canister id on the target network",
    )
    parser.add_argument(
        "--network", "-n",
        default="ic",
        help="dfx network (default: ic)",
    )
    parser.add_argument(
        "--identity",
        default=None,
        help="dfx identity name (default: current dfx identity)",
    )
    parser.add_argument(
        "--extensions-repo",
        default=str(DEFAULT_EXTENSIONS_REPO),
        help=f"Path to realms-extensions checkout (default: {DEFAULT_EXTENSIONS_REPO})",
    )
    parser.add_argument(
        "--codices-root",
        default=str(DEFAULT_CODICES_ROOT),
        help=f"Path to codices/codices/ (default: {DEFAULT_CODICES_ROOT})",
    )
    parser.add_argument(
        "--realms-cli",
        default=os.environ.get("REALMS_CLI", "realms"),
        help="`realms` CLI invocation (e.g. 'python -m realms.cli.main') "
        "(default: realms from PATH)",
    )

    parser.add_argument(
        "--only-extensions",
        default=None,
        help="Comma-separated extension ids to publish (default: all)",
    )
    parser.add_argument(
        "--only-codices",
        default=None,
        help="Comma-separated codex ids to publish (default: all)",
    )

    parser.add_argument(
        "--skip-frontend-build",
        action="store_true",
        help="Do not run scripts/build_runtime_bundles.py; assume dist/index.js "
        "is already up to date in every frontend-rt/",
    )
    parser.add_argument(
        "--skip-extensions",
        action="store_true",
        help="Skip publishing extensions",
    )
    parser.add_argument(
        "--skip-codices",
        action="store_true",
        help="Skip publishing codices",
    )

    parser.add_argument(
        "--skip-base-wasm",
        action="store_true",
        help="Skip publishing the base WASM (use when only re-publishing exts/codices)",
    )
    parser.add_argument(
        "--base-wasm",
        default=None,
        help="Path to the base realm WASM (.wasm.gz) to publish",
    )
    parser.add_argument(
        "--base-wasm-version",
        default=None,
        help="Version string for the base WASM (used in the registry path)",
    )
    parser.add_argument(
        "--base-wasm-namespace",
        default="wasm",
        help="Registry namespace for the base WASM (default: wasm)",
    )
    parser.add_argument(
        "--base-wasm-path-template",
        default="realm-base-{version}.wasm.gz",
        help="Path template inside the namespace (default: realm-base-{version}.wasm.gz)",
    )
    parser.add_argument(
        "--extra-wasm",
        action="append",
        default=[],
        metavar="PATH:VERSION:REGISTRY_PATH[:NAMESPACE]",
        help=(
            "Publish an additional WASM to the registry. Repeatable. "
            "Format: <path>:<version>:<registry_path>[:<namespace>]. "
            "Example: --extra-wasm out/realm_registry.wasm.gz:0.5.0:realm-registry-{version}.wasm.gz "
            "Use this to publish per-canister-type WASMs (e.g. realm_registry_backend) "
            "alongside the realm base WASM."
        ),
    )

    parser.add_argument(
        "--ext-namespace-prefix",
        default="ext",
        help="Registry namespace prefix for extensions (default: ext)",
    )
    parser.add_argument(
        "--codex-namespace-prefix",
        default="codex",
        help="Registry namespace prefix for codices (default: codex)",
    )

    parser.add_argument(
        "--frontend-build-jobs", type=int, default=1,
        help="Concurrent frontend-rt builds (default: 1)",
    )
    parser.add_argument(
        "--skip-install-existing",
        action="store_true",
        help="Skip 'npm install' if frontend-rt/node_modules already exists",
    )

    parser.add_argument(
        "--publish-frontend",
        action="append",
        default=[],
        metavar="DIST_DIR:NAMESPACE",
        help=(
            "Publish a frontend dist/ directory to file_registry. Repeatable. "
            "Format: <dist_dir>:<namespace>. "
            "Example: --publish-frontend src/realm_registry_frontend/dist:frontend/realm_registry_frontend"
        ),
    )

    args = parser.parse_args(list(argv))

    if not shutil.which("dfx"):
        print("ERROR: dfx not found in PATH", file=sys.stderr)
        return 1

    # `realms` CLI may be a single binary or a python invocation; split on whitespace.
    realms_cli = args.realms_cli.split()

    only_ext: Optional[List[str]] = None
    if args.only_extensions:
        only_ext = [s.strip() for s in args.only_extensions.split(",") if s.strip()]
    only_cdx: Optional[List[str]] = None
    if args.only_codices:
        only_cdx = [s.strip() for s in args.only_codices.split(",") if s.strip()]

    started = time.time()

    # 1. Build frontends ----------------------------------------------------
    if not args.skip_frontend_build:
        rc = _step_build_frontends(
            extensions_repo=Path(args.extensions_repo).expanduser().resolve(),
            only=only_ext,
            jobs=args.frontend_build_jobs,
            skip_install_existing=args.skip_install_existing,
        )
        if rc != 0:
            print("\nERROR: frontend bundle build step failed", file=sys.stderr)
            return rc

    # 2. Publish base WASM --------------------------------------------------
    if not args.skip_base_wasm:
        if not args.base_wasm or not args.base_wasm_version:
            print(
                "ERROR: --base-wasm AND --base-wasm-version are required unless "
                "--skip-base-wasm is set.",
                file=sys.stderr,
            )
            return 1
        registry_path = args.base_wasm_path_template.format(
            version=args.base_wasm_version
        )
        rc = _step_publish_base_wasm(
            realms_cli=realms_cli,
            registry=args.registry,
            network=args.network,
            identity=args.identity,
            base_wasm_path=Path(args.base_wasm).expanduser().resolve(),
            base_wasm_version=args.base_wasm_version,
            namespace=args.base_wasm_namespace,
            registry_path=registry_path,
        )
        if rc != 0:
            print("\nERROR: base WASM publish failed", file=sys.stderr)
            return rc

    # 2b. Publish extra WASMs (e.g. realm_registry, file_registry) ----------
    for spec in args.extra_wasm:
        parts = spec.split(":")
        if len(parts) < 3 or len(parts) > 4:
            print(
                f"ERROR: --extra-wasm must be PATH:VERSION:REGISTRY_PATH[:NAMESPACE], "
                f"got {spec!r}",
                file=sys.stderr,
            )
            return 1
        ew_path, ew_version, ew_template = parts[0], parts[1], parts[2]
        ew_namespace = parts[3] if len(parts) == 4 else "wasm"
        ew_registry_path = ew_template.format(version=ew_version)
        rc = _step_publish_base_wasm(
            realms_cli=realms_cli,
            registry=args.registry,
            network=args.network,
            identity=args.identity,
            base_wasm_path=Path(ew_path).expanduser().resolve(),
            base_wasm_version=ew_version,
            namespace=ew_namespace,
            registry_path=ew_registry_path,
        )
        if rc != 0:
            print(f"\nERROR: extra WASM publish failed for {spec}", file=sys.stderr)
            return rc

    # 3. Publish extensions -------------------------------------------------
    if not args.skip_extensions:
        rc = _step_publish_extensions(
            realms_cli=realms_cli,
            registry=args.registry,
            network=args.network,
            identity=args.identity,
            extensions_repo=Path(args.extensions_repo).expanduser().resolve(),
            only=only_ext,
            namespace_prefix=args.ext_namespace_prefix,
        )
        if rc != 0:
            print("\nERROR: extension publish failed", file=sys.stderr)
            return rc

    # 4. Publish codices ----------------------------------------------------
    if not args.skip_codices:
        rc = _step_publish_codices(
            realms_cli=realms_cli,
            registry=args.registry,
            network=args.network,
            identity=args.identity,
            codices_root=Path(args.codices_root).expanduser().resolve(),
            only=only_cdx,
            namespace_prefix=args.codex_namespace_prefix,
        )
        if rc != 0:
            print("\nERROR: codex publish failed", file=sys.stderr)
            return rc

    # 5. Publish frontends ---------------------------------------------------
    for spec in args.publish_frontend:
        parts = spec.split(":", 1)
        if len(parts) != 2:
            print(
                f"ERROR: --publish-frontend must be DIST_DIR:NAMESPACE, "
                f"got {spec!r}",
                file=sys.stderr,
            )
            return 1
        fe_dist, fe_namespace = parts
        rc = _step_publish_frontend(
            registry=args.registry,
            network=args.network,
            identity=args.identity,
            dist_dir=Path(fe_dist).expanduser().resolve(),
            namespace=fe_namespace,
        )
        if rc != 0:
            print(f"\nERROR: frontend publish failed for {spec}", file=sys.stderr)
            return rc

    elapsed = time.time() - started
    print(f"\n[OK] layered publish complete in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
