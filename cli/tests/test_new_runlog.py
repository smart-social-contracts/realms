"""Tests for ``realms new`` run-scoped logging."""

import re
from pathlib import Path

from typer.testing import CliRunner

from realms.cli.main import app
from realms.cli.runlog import start_run_log, stop_run_log


def test_start_run_log_explicit_log_file(tmp_path: Path) -> None:
    stop_run_log()
    target = tmp_path / "nested" / "realms-new.log"
    log = start_run_log("demo", log_file=target)
    try:
        assert log.path.parent == target.parent
        assert log.path.name.startswith("realms-new_")
        assert re.search(r"_\d{8}_\d{6}\.log$", log.path.name)
        print("credits founder on demo")
        text = log.path.read_text(encoding="utf-8")
        assert "=== realms new demo started" in text
        assert f"log_file={log.path}" in text
        assert "credits founder on demo" in text
    finally:
        stop_run_log()


def test_start_run_log_default_prefix(tmp_path: Path) -> None:
    stop_run_log()
    log = start_run_log("demo", log_dir=tmp_path)
    try:
        assert log.path.parent == tmp_path
        assert log.path.name.startswith("realms-new-demo_")
        assert re.search(r"_\d{8}_\d{6}\.log$", log.path.name)
    finally:
        stop_run_log()


def test_start_run_log_directory_log_file(tmp_path: Path) -> None:
    stop_run_log()
    dest = tmp_path / "logs"
    dest.mkdir()
    log = start_run_log("demo", log_file=dest)
    try:
        assert log.path.parent == dest
        assert log.path.name.startswith("realms-new-demo_")
        assert re.search(r"_\d{8}_\d{6}\.log$", log.path.name)
    finally:
        stop_run_log()


def test_realms_new_help_has_log_file() -> None:
    result = CliRunner().invoke(app, ["new", "--help"])
    assert result.exit_code == 0
    output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--log-file" in output
    assert "--gaas-config" in output
    assert "YYYYMMDD_HHMMSS" in output
