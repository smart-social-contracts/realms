"""Tests for isolated basilisk venv helpers."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from realms.cli.basilisk_env import (
    _BASILISK_REQUIREMENTS,
    dfx_env_with_basilisk,
    ensure_basilisk_venv,
)


class TestBasiliskRequirements:
    def test_pinned_versions_match_gaas(self):
        assert "ic-basilisk==0.14.2" in _BASILISK_REQUIREMENTS
        assert "ic-basilisk-toolkit==0.5.3" in _BASILISK_REQUIREMENTS


class TestEnsureBasiliskVenv:
    @patch("realms.cli.basilisk_env._basilisk_import_ok", return_value=True)
    @patch("realms.cli.basilisk_env._venv_python")
    def test_reuses_existing_venv(self, mock_venv_python, mock_import_ok, tmp_path):
        venv = tmp_path / ".venv-basilisk"
        bin_dir = venv / "bin"
        bin_dir.mkdir(parents=True)
        py = bin_dir / "python"
        py.touch()
        mock_venv_python.return_value = py

        result = ensure_basilisk_venv(tmp_path)

        assert result == bin_dir
        mock_import_ok.assert_called_once_with(py)

    @patch("realms.cli.basilisk_env._create_basilisk_venv")
    @patch("realms.cli.basilisk_env._basilisk_import_ok", return_value=False)
    @patch("realms.cli.basilisk_env._venv_python")
    def test_recreates_broken_venv(
        self, mock_venv_python, mock_import_ok, mock_create, tmp_path
    ):
        venv = tmp_path / ".venv-basilisk"
        venv.mkdir()
        py = venv / "bin" / "python"
        py.parent.mkdir(parents=True)
        py.touch()
        mock_venv_python.return_value = py
        expected_bin = tmp_path / ".venv-basilisk" / "bin"
        mock_create.return_value = expected_bin

        result = ensure_basilisk_venv(tmp_path)

        assert result == expected_bin
        mock_create.assert_called_once_with(tmp_path)


class TestDfxEnvWithBasilisk:
    @patch("realms.cli.basilisk_env.ensure_basilisk_venv")
    def test_prepends_venv_bin_to_path(self, mock_ensure, tmp_path):
        bin_dir = tmp_path / ".venv-basilisk" / "bin"
        bin_dir.mkdir(parents=True)
        mock_ensure.return_value = bin_dir
        base = {"PATH": "/usr/bin", "HOME": "/tmp"}

        env = dfx_env_with_basilisk(tmp_path, base_env=base)

        assert env["PATH"].startswith(f"{bin_dir}{os.pathsep}")
        assert "/usr/bin" in env["PATH"]
        assert env["VIRTUAL_ENV"] == str(tmp_path / ".venv-basilisk")
        assert "PYTHONPATH" not in env

    @patch("realms.cli.basilisk_env.stderr_console")
    @patch(
        "realms.cli.basilisk_env.ensure_basilisk_venv",
        side_effect=RuntimeError("pip install failed"),
    )
    def test_fallback_on_venv_failure(self, mock_ensure, mock_stderr, tmp_path):
        base = {"PATH": "/usr/bin", "FOO": "bar"}

        env = dfx_env_with_basilisk(tmp_path, base_env=base)

        assert env["PATH"] == "/usr/bin"
        assert env["FOO"] == "bar"
        mock_stderr.print.assert_called()
