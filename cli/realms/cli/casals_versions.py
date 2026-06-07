"""Version labels for Casals publish + rollout.

Semver releases (e.g. ``0.4.0``) are cut manually and published with an explicit
version.  Main-branch snapshots use the ``main.<unix_ts>.<git_sha>`` channel so
each commit is traceable and sortable without bumping ``version.txt``.

Rollout ``--version main`` (or ``latest-main``) picks the newest authorized WASM
in that channel for each family.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Iterable, Optional


MAIN_CHANNEL = "main"


def is_main_channel(version: str) -> bool:
    v = (version or "").strip()
    return v == MAIN_CHANNEL or v.startswith(f"{MAIN_CHANNEL}.")


def ver_tuple(version: str) -> tuple[int, ...]:
    """Comparable tuple aligned with Casals' ``_ver_tuple`` (digits sort, else 0)."""
    out: list[int] = []
    for part in (version or "0").replace("-", ".").split("."):
        out.append(int(part) if part.isdigit() else 0)
    return tuple(out)


def git_short_sha(repo_root: Optional[Path] = None) -> str:
    root = repo_root or Path.cwd()
    while root != root.parent:
        if (root / ".git").exists():
            break
        root = root.parent
    return subprocess.check_output(
        ["git", "rev-parse", "--short=7", "HEAD"],
        cwd=str(root),
        text=True,
    ).strip()


def main_build_version(repo_root: Optional[Path] = None) -> str:
    """Version string for a snapshot build from the current main checkout."""
    return f"{MAIN_CHANNEL}.{int(time.time())}.{git_short_sha(repo_root)}"


def pick_latest_main_key(candidates: Iterable[dict]) -> Optional[str]:
    """Newest authorized WASM whose version is in the main channel."""
    main_only = [w for w in candidates if is_main_channel(w.get("version") or "")]
    if not main_only:
        return None
    main_only.sort(key=lambda w: ver_tuple(w.get("version") or ""), reverse=True)
    return main_only[0].get("key")
