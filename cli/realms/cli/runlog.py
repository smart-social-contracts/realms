"""Run-scoped logging for long CLI commands (``realms new``)."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

_LOG_TS_FMT = "%Y%m%d_%H%M%S"
_STAMPED_STEM_RE = re.compile(r"_\d{8}_\d{6}$")
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_DEFAULT_LOG_PREFIX = "realms-new"

_console = Console()
_active: RunLog | None = None


class _TeeStream:
    """Mirror stdout/stderr into the run log (ANSI stripped) while keeping the TTY."""

    def __init__(self, primary, log: RunLog) -> None:
        self._primary = primary
        self._log = log

    def write(self, data) -> int:
        if isinstance(data, bytes):
            text = data.decode("utf-8", errors="replace")
        else:
            text = data if isinstance(data, str) else str(data)
        n = self._primary.write(data)
        stripped = _ANSI_RE.sub("", text)
        if stripped:
            self._log._file.write(stripped)
            self._log._file.flush()
        return n if isinstance(n, int) else len(text)

    def flush(self) -> None:
        self._primary.flush()
        self._log._file.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._primary, "isatty", lambda: False)())

    def fileno(self) -> int:
        return self._primary.fileno()

    def __getattr__(self, name: str):
        return getattr(self._primary, name)


class RunLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = path.open("a", encoding="utf-8", buffering=1)
        self._stdout_orig = None
        self._stderr_orig = None

    def write(self, line: str) -> None:
        self._file.write(line.rstrip("\n") + "\n")
        self._file.flush()

    def log_command(self, cmd: list[str], *, cwd: str | Path | None = None) -> None:
        parts = [f"$ {' '.join(cmd)}"]
        if cwd:
            parts.append(f"  (cwd={cwd})")
        self.write("\n".join(parts))

    def log_output(self, text: str) -> None:
        if not text:
            return
        self._file.write(text)
        if not text.endswith("\n"):
            self._file.write("\n")
        self._file.flush()

    def install_tee(self) -> None:
        if self._stdout_orig is not None:
            return
        self._stdout_orig = sys.stdout
        self._stderr_orig = sys.stderr
        sys.stdout = _TeeStream(sys.stdout, self)
        sys.stderr = _TeeStream(sys.stderr, self)

    def uninstall_tee(self) -> None:
        if self._stdout_orig is None:
            return
        sys.stdout = self._stdout_orig
        sys.stderr = self._stderr_orig
        self._stdout_orig = None
        self._stderr_orig = None

    def close(self) -> None:
        self.uninstall_tee()
        self._file.close()


def _safe_env_name(env_name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in env_name) or "run"


def default_log_dir() -> Path:
    """``<git-root>/logs`` when cwd is inside a checkout, otherwise ``./logs``."""
    here = Path.cwd().resolve()
    for candidate in [here, *here.parents]:
        if (candidate / ".git").exists():
            return candidate / "logs"
    return here / "logs"


def _is_log_directory(path: Path) -> bool:
    if path.exists():
        return path.is_dir()
    return path.suffix == ""


def dated_log_name(prefix: str, env_name: str, ts: str) -> str:
    return f"{prefix}-{_safe_env_name(env_name)}_{ts}.log"


def inject_log_timestamp(path: Path, ts: str) -> Path:
    """Insert ``_YYYYMMDD_HHMMSS`` before the suffix unless already stamped."""
    stem = path.stem
    if _STAMPED_STEM_RE.search(stem):
        return path
    suffix = path.suffix or ".log"
    return path.with_name(f"{stem}_{ts}{suffix}")


def resolve_log_path(
    env_name: str,
    *,
    log_dir: Path | None = None,
    log_file: str | Path | None = None,
    prefix: str = _DEFAULT_LOG_PREFIX,
    ts: str | None = None,
) -> Path:
    """Default: ``<repo>/logs/realms-new-<env>_YYYYMMDD_HHMMSS.log``.

    ``--log-file`` to a directory (or a path with no suffix) writes a dated
    file there. A file path gets ``_YYYYMMDD_HHMMSS`` inserted before the
    extension unless it is already stamped.
    """
    stamp = ts or datetime.now(timezone.utc).strftime(_LOG_TS_FMT)
    if log_file:
        path = Path(log_file).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if _is_log_directory(path):
            return path / dated_log_name(prefix, env_name, stamp)
        return inject_log_timestamp(path, stamp)
    base = log_dir or default_log_dir()
    return base / dated_log_name(prefix, env_name, stamp)


def start_run_log(
    env_name: str,
    *,
    log_dir: Path | None = None,
    log_file: str | Path | None = None,
    command: str = "realms new",
) -> RunLog:
    """Create and activate a per-invocation run log; tee console into it."""
    global _active
    ts = datetime.now(timezone.utc).strftime(_LOG_TS_FMT)
    path = resolve_log_path(env_name, log_dir=log_dir, log_file=log_file, ts=ts)
    log = RunLog(path)
    log.write(f"=== {command} {env_name} started {ts} UTC ===")
    log.write(f"log_file={path}")
    log.install_tee()
    _active = log
    return log


def get_run_log() -> RunLog | None:
    return _active


def print_log_path(*, console: Console | None = None) -> None:
    if _active is not None:
        (console or _console).print(
            f"Full logs: {_active.path}",
            overflow="ignore",
            crop=False,
            no_wrap=True,
        )


def stop_run_log() -> None:
    global _active
    if _active is not None:
        _active.close()
        _active = None
