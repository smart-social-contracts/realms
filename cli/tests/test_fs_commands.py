"""Tests for fs CLI commands."""

import base64
from unittest.mock import Mock, patch

import pytest

from realms.cli.commands.fs import (
    _execute_python,
    fs_cat_command,
    fs_ls_command,
    fs_rm_command,
    fs_write_command,
)


class TestExecutePython:
    """Tests for the _execute_python helper."""

    def test_successful_execution(self):
        """Test successful Python code execution on canister."""
        mock_result = Mock()
        mock_result.stdout = '("Hello world",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = _execute_python("print('Hello world')", "realm_backend", "local")
            assert result == "Hello world"
            mock_run.assert_called_once()

    def test_execution_with_network(self):
        """Test that network parameter is passed to dfx."""
        mock_result = Mock()
        mock_result.stdout = '("ok",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            _execute_python("print('ok')", "realm_backend", "ic")
            cmd = mock_run.call_args[0][0]
            assert "-e" in cmd
            assert "ic" in cmd

    def test_execution_without_network(self):
        """Test execution without explicit network (local default)."""
        mock_result = Mock()
        mock_result.stdout = '("ok",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            _execute_python("print('ok')", "realm_backend", None)
            cmd = mock_run.call_args[0][0]
            assert "-e" not in cmd

    def test_execution_error(self):
        """Test handling of subprocess error."""
        from subprocess import CalledProcessError

        with patch("subprocess.run", side_effect=CalledProcessError(1, "cmd", stderr="canister error")):
            result = _execute_python("bad_code", "realm_backend", "local")
            assert "Error" in result

    def test_execution_timeout(self):
        """Test handling of timeout."""
        from subprocess import TimeoutExpired

        with patch("subprocess.run", side_effect=TimeoutExpired("cmd", 30)):
            result = _execute_python("slow_code", "realm_backend", "local")
            assert "timed out" in result

    def test_multiline_response_parsing(self):
        """Test parsing of multiline Candid tuple response."""
        mock_result = Mock()
        mock_result.stdout = '("line1\\nline2\\nline3",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = _execute_python("print('multi')", "realm_backend", "local")
            assert "line1" in result
            assert "line2" in result

    def test_escaped_quotes_in_response(self):
        """Test parsing response with escaped quotes."""
        mock_result = Mock()
        mock_result.stdout = '("he said \\"hello\\"",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = _execute_python("print('quotes')", "realm_backend", "local")
            assert '"hello"' in result

    def test_cwd_passed_through(self):
        """Test that cwd is passed to subprocess."""
        mock_result = Mock()
        mock_result.stdout = '("ok",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            _execute_python("print('ok')", "realm_backend", "local", cwd="/my/realm")
            assert mock_run.call_args[1]["cwd"] == "/my/realm"


class TestFsLs:
    """Tests for fs ls command."""

    def test_ls_root(self):
        """Test listing root directory."""
        mock_result = Mock()
        mock_result.stdout = '("d  subdir/\\nf  manifest  (42 bytes)\\nf  my_codex  (100 bytes)",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            with patch("builtins.print") as mock_print:
                fs_ls_command("/", "local", "realm_backend")
                output = mock_print.call_args[0][0]
                assert "subdir" in output
                assert "manifest" in output

    def test_ls_with_path(self):
        """Test listing a subdirectory."""
        mock_result = Mock()
        mock_result.stdout = '("f  file1  (10 bytes)",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch("builtins.print"):
                fs_ls_command("/subdir", "local", "realm_backend")
                # Verify the path is included in the Python code sent to canister
                cmd = mock_run.call_args[0][0]
                call_arg = cmd[-1]  # last arg is the Python code wrapped in Candid
                assert "/subdir" in call_arg

    def test_ls_empty_directory(self):
        """Test listing an empty directory."""
        mock_result = Mock()
        mock_result.stdout = '("",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            # Should not raise
            fs_ls_command("/empty", "local", "realm_backend")

    def test_ls_error(self):
        """Test listing a non-existent directory."""
        mock_result = Mock()
        mock_result.stdout = '("Error: [Errno 2] No such file or directory: \'/nonexistent\'",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            with patch("builtins.print") as mock_print:
                fs_ls_command("/nonexistent", "local", "realm_backend")
                output = mock_print.call_args[0][0]
                assert "Error" in output


class TestFsCat:
    """Tests for fs cat command."""

    def test_cat_file(self):
        """Test reading a file."""
        mock_result = Mock()
        mock_result.stdout = '("print(\\"Hello from codex\\")",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            with patch("builtins.print") as mock_print:
                fs_cat_command("/my_codex", "local", "realm_backend")
                output = mock_print.call_args[0][0]
                assert "Hello from codex" in output

    def test_cat_nonexistent_file(self):
        """Test reading a non-existent file."""
        mock_result = Mock()
        mock_result.stdout = '("Error: [Errno 2] No such file or directory: \'/missing\'",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            with patch("builtins.print") as mock_print:
                fs_cat_command("/missing", "local", "realm_backend")
                output = mock_print.call_args[0][0]
                assert "Error" in output


class TestFsWrite:
    """Tests for fs write command."""

    def test_write_file(self):
        """Test writing content to a file."""
        mock_result = Mock()
        mock_result.stdout = '("Written 13 bytes to /test_file",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch("realms.cli.commands.fs.console"):
                fs_write_command("/test_file", "Hello, world!", "local", "realm_backend")
                # Verify base64-encoded content is in the command
                cmd = mock_run.call_args[0][0]
                call_arg = cmd[-1]
                encoded = base64.b64encode(b"Hello, world!").decode()
                assert encoded in call_arg

    def test_write_preserves_content(self):
        """Test that special characters are preserved via base64 encoding."""
        content = "def hello():\n    print('Hello world')\n"
        mock_result = Mock()
        mock_result.stdout = f'("Written {len(content)} bytes to /codex",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch("realms.cli.commands.fs.console"):
                fs_write_command("/codex", content, "local", "realm_backend")
                cmd = mock_run.call_args[0][0]
                call_arg = cmd[-1]
                encoded = base64.b64encode(content.encode()).decode()
                assert encoded in call_arg


class TestFsRm:
    """Tests for fs rm command."""

    def test_rm_file(self):
        """Test removing a file."""
        mock_result = Mock()
        mock_result.stdout = '("Removed /old_file",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            with patch("realms.cli.commands.fs.console") as mock_console:
                fs_rm_command("/old_file", "local", "realm_backend")
                mock_console.print.assert_called()
                output = mock_console.print.call_args[0][0]
                assert "Removed" in output

    def test_rm_nonexistent_file(self):
        """Test removing a non-existent file."""
        mock_result = Mock()
        mock_result.stdout = '("Error: [Errno 2] No such file or directory: \'/missing\'",)'
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            with patch("realms.cli.commands.fs.console") as mock_console:
                fs_rm_command("/missing", "local", "realm_backend")
                output = mock_console.print.call_args[0][0]
                assert "Error" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
