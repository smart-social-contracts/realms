#!/usr/bin/env python3
"""
build_runtime_bundles.py — npm install + vite build for every extension's
frontend-rt/ directory.

For every directory matching::

    realms-extensions/extensions/<ext>/frontend-rt/package.json

this script runs (in order):

    1. npm install --no-audit --no-fund --silent           (skipped if node_modules/ exists and --skip-install-existing)
    2. npm run build                                       (must produce dist/index.js)

It then verifies that ``dist/index.js`` exists and prints the bundle size,
treating missing or zero-byte bundles as failures.

Used by:
  - the layered-deploy CI workflow before publish_layered.py
  - operators iterating locally on extension UIs

Usage:
    python scripts/build_runtime_bundles.py
    python scripts/build_runtime_bundles.py --extensions-repo ../realms-extensions
    python scripts/build_runtime_bundles.py --only voting,welcome
    python scripts/build_runtime_bundles.py --jobs 4
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTENSIONS_REPO = REPO_ROOT.parent / "realms-extensions"
SKIP_EXTENSION_IDS = {"_shared"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_extensions_root(repo: Path) -> Path:
    """Return the directory that holds per-extension subdirectories.

    Mirrors ``scripts/publish_layered.py::_resolve_extensions_root``. The
    ``realms-extensions`` submodule has a nested layout
    (``<repo>/extensions/extensions/<name>/``); a standalone
    ``realms-extensions`` checkout has a flat layout
    (``<repo>/extensions/<name>/``). Try nested first, fall back to
    flat. Fail loud if neither contains any extension dirs.

    A "valid" candidate is a dir with at least one child that is itself
    a dir (excluding ``_shared``) — even if that child has no
    ``frontend-rt/`` (most don't). The frontend-rt presence check is
    the caller's job; here we just resolve which dir to walk.
    """
    nested = repo / "extensions" / "extensions"
    flat = repo / "extensions"

    def _has_extension_dirs(candidate: Path) -> bool:
        if not candidate.is_dir():
            return False
        for child in candidate.iterdir():
            if not child.is_dir() or child.name in SKIP_EXTENSION_IDS:
                continue
            # An extension dir is one that has either a manifest.json
            # (any kind of extension) or a frontend-rt/ (the only thing
            # this script cares about). Either signal proves the layout.
            if (child / "manifest.json").exists() or (
                child / "frontend-rt" / "package.json"
            ).exists():
                return True
        return False

    if _has_extension_dirs(nested):
        return nested
    if _has_extension_dirs(flat):
        return flat
    raise SystemExit(
        "ERROR: no extension directories found under either of:\n"
        f"  {nested}  (nested realms+submodule layout)\n"
        f"  {flat}  (standalone realms-extensions checkout layout)\n"
        "Did the realms-extensions submodule fail to initialize? Try:\n"
        "  git submodule update --init --recursive"
    )


def _list_rt_dirs(extensions_root: Path, only: Optional[List[str]]) -> List[Path]:
    """Return every <extensions_root>/<ext>/frontend-rt that has a package.json."""
    if not extensions_root.is_dir():
        raise FileNotFoundError(f"Extensions root not found: {extensions_root}")
    out: List[Path] = []
    for child in sorted(extensions_root.iterdir()):
        if not child.is_dir() or child.name in SKIP_EXTENSION_IDS:
            continue
        if only and child.name not in only:
            continue
        rt_dir = child / "frontend-rt"
        if (rt_dir / "package.json").exists():
            out.append(rt_dir)
    return out


def _run(cmd: List[str], cwd: Path, env: Optional[dict] = None, log_prefix: str = "") -> Tuple[int, str]:
    """Run a subprocess capturing combined stdout+stderr; return (rc, output)."""
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc.returncode, proc.stdout


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:,.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:,.1f} TB"


def _build_one(
    rt_dir: Path,
    *,
    npm: str,
    skip_install_existing: bool,
    force_install: bool,
) -> Tuple[Path, bool, str]:
    """Build a single extension. Returns (rt_dir, ok, summary_line)."""
    ext_id = rt_dir.parent.name
    started = time.time()

    node_modules = rt_dir / "node_modules"
    needs_install = (
        force_install
        or not node_modules.is_dir()
        or not skip_install_existing
    )

    if needs_install:
        rc, out = _run(
            [npm, "install", "--no-audit", "--no-fund", "--silent"],
            cwd=rt_dir,
        )
        if rc != 0:
            return (
                rt_dir,
                False,
                f"  ✗ {ext_id}: npm install failed (rc={rc})\n{out[-1000:]}",
            )

    rc, out = _run([npm, "run", "build"], cwd=rt_dir)
    if rc != 0:
        return (
            rt_dir,
            False,
            f"  ✗ {ext_id}: vite build failed (rc={rc})\n{out[-1000:]}",
        )

    bundle = rt_dir / "dist" / "index.js"
    if not bundle.exists():
        return (
            rt_dir,
            False,
            f"  ✗ {ext_id}: build did not produce dist/index.js",
        )
    size = bundle.stat().st_size
    if size == 0:
        return (
            rt_dir,
            False,
            f"  ✗ {ext_id}: dist/index.js is empty (0 bytes)",
        )

    elapsed = time.time() - started
    return (
        rt_dir,
        True,
        f"  ✓ {ext_id:<22} {_human_size(size):>10}  ({elapsed:5.1f}s)",
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Iterable[str]) -> int:
    parser = argparse.ArgumentParser(
        description="npm install + vite build for every extension's frontend-rt/."
    )
    parser.add_argument(
        "--extensions-repo",
        default=str(DEFAULT_EXTENSIONS_REPO),
        help=f"Path to realms-extensions checkout (default: {DEFAULT_EXTENSIONS_REPO})",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="Comma-separated extension ids to build (default: all)",
    )
    parser.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=1,
        help="Number of concurrent builds (default: 1; node/npm I/O bound, "
        "raise to 4 on a beefy CI runner)",
    )
    parser.add_argument(
        "--skip-install-existing",
        action="store_true",
        help="Skip 'npm install' if node_modules/ already exists",
    )
    parser.add_argument(
        "--force-install",
        action="store_true",
        help="Always run 'npm install' even if node_modules/ exists",
    )
    parser.add_argument(
        "--npm",
        default=os.environ.get("NPM", "npm"),
        help="Path to the npm binary (default: npm from PATH)",
    )
    args = parser.parse_args(list(argv))

    if not shutil.which(args.npm):
        print(f"ERROR: npm binary not found in PATH: {args.npm}", file=sys.stderr)
        return 1

    extensions_root = _resolve_extensions_root(
        Path(args.extensions_repo).expanduser().resolve()
    )
    only_list: Optional[List[str]] = None
    if args.only:
        only_list = [s.strip() for s in args.only.split(",") if s.strip()]

    try:
        rt_dirs = _list_rt_dirs(extensions_root, only_list)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not rt_dirs:
        # It's legitimate for a repo to have extensions but none with a
        # frontend-rt/ — that just means there's nothing to bundle. Don't
        # fail loud here (unlike publish_layered._step_publish_extensions);
        # the caller's `--only` filter may simply target an extension
        # without a frontend-rt/. Just print and return success.
        if only_list:
            print(
                f"No frontend-rt/ directories found under {extensions_root} "
                f"matching --only={only_list}. Available with frontend-rt: "
                f"{sorted(p.parent.name for p in _list_rt_dirs(extensions_root, None))}"
            )
        else:
            print(f"No frontend-rt/ directories found to build under {extensions_root}.")
        return 0

    print(f"Building {len(rt_dirs)} runtime bundles from {extensions_root}")
    if only_list:
        print(f"  filter: {', '.join(only_list)}")
    print(f"  jobs:   {args.jobs}")
    started = time.time()

    failures: List[str] = []
    successes: List[str] = []

    if args.jobs > 1:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = [
                pool.submit(
                    _build_one,
                    rt,
                    npm=args.npm,
                    skip_install_existing=args.skip_install_existing,
                    force_install=args.force_install,
                )
                for rt in rt_dirs
            ]
            for fut in as_completed(futures):
                _rt, ok, summary = fut.result()
                print(summary)
                (successes if ok else failures).append(summary)
    else:
        for rt in rt_dirs:
            _rt, ok, summary = _build_one(
                rt,
                npm=args.npm,
                skip_install_existing=args.skip_install_existing,
                force_install=args.force_install,
            )
            print(summary)
            (successes if ok else failures).append(summary)

    elapsed = time.time() - started
    print(
        f"\nBuilt {len(successes)} OK, {len(failures)} failed, total {elapsed:.1f}s"
    )
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
