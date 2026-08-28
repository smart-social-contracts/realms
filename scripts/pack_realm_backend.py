#!/usr/bin/env python3
"""Leftover-free realm_backend pack. Cedar is the only template."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from basilisk_cedar_template import apply_cedar_template_env  # noqa: E402


def pack_realm_backend(repo_root: Optional[Path] = None) -> int:
    """Pack ``src/realm_backend/main.py`` with the pinned Cedar template."""
    root = repo_root or _SCRIPTS.parent
    main_py = root / "src" / "realm_backend" / "main.py"
    if not main_py.is_file():
        raise SystemExit(f"realm_backend main.py not found at {main_py}")

    env = apply_cedar_template_env()
    cmd = [sys.executable, "-m", "basilisk", "realm_backend", str(main_py)]
    print(f"   🐍 {' '.join(cmd)}")
    print(f"   🌲 template: {env['BASILISK_TEMPLATE_WASM']}")
    return subprocess.run(cmd, cwd=str(root), env=env).returncode


def main() -> int:
    return pack_realm_backend()


if __name__ == "__main__":
    sys.exit(main())
