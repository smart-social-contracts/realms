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

# Always exported on the Cedar pack. Do not gate these behind leftover-free
# or a per-deploy sandbox allowlist — the GOS installer calls enter_setup
# on every new realm (IC0536 if the method is missing from WASM exports).
REQUIRED_UPDATE_EXPORTS = ("enter_setup",)


def _assert_required_exports(did_path: Path) -> None:
    if not did_path.is_file():
        raise SystemExit(
            f"realm_backend pack did not write candid at {did_path}; "
            f"required exports {REQUIRED_UPDATE_EXPORTS}"
        )
    text = did_path.read_text()
    missing = [name for name in REQUIRED_UPDATE_EXPORTS if f'"{name}"' not in text]
    if missing:
        raise SystemExit(
            f"realm_backend pack dropped required update exports: {missing}"
        )


def pack_realm_backend(repo_root: Optional[Path] = None) -> int:
    """Pack ``src/realm_backend/main.py`` with the pinned Cedar template."""
    root = repo_root or _SCRIPTS.parent
    main_py = root / "src" / "realm_backend" / "main.py"
    if not main_py.is_file():
        raise SystemExit(f"realm_backend main.py not found at {main_py}")

    env = apply_cedar_template_env()
    did = root / "src" / "realm_backend" / "realm_backend.did"
    env.setdefault("CANISTER_CANDID_PATH", str(did))
    cmd = [sys.executable, "-m", "basilisk", "realm_backend", str(main_py)]
    print(f"   🐍 {' '.join(cmd)}")
    print(f"   🌲 template: {env['BASILISK_TEMPLATE_WASM']}")
    result = subprocess.run(cmd, cwd=str(root), env=env)
    if result.returncode != 0:
        return result.returncode
    _assert_required_exports(Path(env["CANISTER_CANDID_PATH"]))
    return 0


def main() -> int:
    return pack_realm_backend()


if __name__ == "__main__":
    sys.exit(main())
