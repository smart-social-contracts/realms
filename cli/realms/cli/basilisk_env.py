"""Isolated basilisk venv for dfx custom builds.

dfx invokes ``python -m basilisk ...`` during marketplace_backend deploys.
Basilisk's modulefinder rejects native packages in the host site-packages, so
builds must use a minimal ``.venv-basilisk`` (same pins as gos-as-a-service).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from .utils import get_logger, stderr_console

_BASILISK_REQUIREMENTS = (
    "ic-basilisk==0.14.2",
    "ic-basilisk-toolkit==0.5.3",
)

logger = get_logger("basilisk_env")


def _venv_dir(project_root: Path) -> Path:
    return project_root / ".venv-basilisk"


def _venv_python(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _venv_bin(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts"
    return venv / "bin"


def _venv_pip(venv: Path) -> Path:
    bin_dir = _venv_bin(venv)
    name = "pip.exe" if sys.platform == "win32" else "pip"
    return bin_dir / name


def _basilisk_import_ok(py: Path) -> bool:
    try:
        result = subprocess.run(
            [str(py), "-c", "import basilisk"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _create_basilisk_venv(project_root: Path) -> Path:
    """Create ``.venv-basilisk`` with pinned basilisk packages; return bin dir."""
    venv = _venv_dir(project_root)
    py = _venv_python(venv)
    bin_dir = _venv_bin(venv)

    logger.info("Creating basilisk venv at %s", venv)
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv)],
        check=True,
        cwd=str(project_root),
    )
    pip = _venv_pip(venv)
    subprocess.run([str(pip), "install", "-q", "--upgrade", "pip"], check=True)
    subprocess.run(
        [str(pip), "install", "-q", *_BASILISK_REQUIREMENTS],
        check=True,
    )
    if not _basilisk_import_ok(py):
        raise RuntimeError(f"basilisk import check failed after creating {venv}")
    return bin_dir


def ensure_basilisk_venv(project_root: Path) -> Path:
    """Ensure ``<project_root>/.venv-basilisk`` exists and return its ``bin`` dir."""
    venv = _venv_dir(project_root)
    py = _venv_python(venv)
    bin_dir = _venv_bin(venv)

    if py.is_file() and _basilisk_import_ok(py):
        logger.debug("Using existing basilisk venv at %s", venv)
        return bin_dir

    if venv.exists():
        logger.warning("Repairing basilisk venv at %s", venv)
        shutil.rmtree(venv, ignore_errors=True)

    return _create_basilisk_venv(project_root)


def dfx_env_with_basilisk(
    project_root: Path,
    base_env: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Return a copy of *base_env* with the basilisk venv ``bin`` prepended to ``PATH``."""
    env = (base_env or os.environ).copy()
    try:
        bin_dir = ensure_basilisk_venv(project_root)
        current_path = env.get("PATH", "")
        env["PATH"] = f"{bin_dir}{os.pathsep}{current_path}"
        env["VIRTUAL_ENV"] = str(_venv_dir(project_root))
        env.pop("PYTHONPATH", None)
    except Exception as exc:
        logger.warning("Could not prepare basilisk venv: %s", exc)
        stderr_console.print(
            f"[yellow]⚠️  Could not prepare isolated basilisk venv: {exc}[/yellow]"
        )
        stderr_console.print(
            "[yellow]   dfx basilisk builds may fail if system Python has native packages.[/yellow]"
        )
    return env


def basilisk_python_executable(project_root: Path) -> str:
    """Return the isolated venv Python path for direct ``python -m basilisk`` calls."""
    ensure_basilisk_venv(project_root)
    return str(_venv_python(_venv_dir(project_root)))
