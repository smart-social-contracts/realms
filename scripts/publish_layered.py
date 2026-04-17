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

def _run(cmd: List[str], cwd: Optional[Path] = None) -> int:
    """Run a subprocess and stream its stdout/stderr live; return rc."""
    print(f"$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    return proc.returncode


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
        rc = _dfx_call(
            "finalize_chunked_file",
            {"namespace": namespace, "path": registry_path},
        )
        if rc != 0:
            return rc

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
    ext_dirs = _list_extensions(extensions_repo / "extensions", only)
    if not ext_dirs:
        print("No extensions to publish.")
        return 0
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

    elapsed = time.time() - started
    print(f"\n[OK] layered publish complete in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
