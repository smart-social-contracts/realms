"""Tests for ``realms installer`` CLI commands.

These tests live in ``cli/tests/`` (pytest, mocked subprocess) so they
run on every CLI build without needing a live IC replica.

They cover the user-facing ``installer_deploy_command`` /
``installer_status_command`` / ``installer_list_command`` plus the
small helpers (``_load_manifest``, ``_override``,
``_unwrap_candid_text``, ``_candid_text_arg``).

A separate, replica-required smoke test for the on-chain
``deploy_realm`` flow lives in ``tests/integration/`` and is gated on
the ``realm_installer`` canister actually being deployed.
"""

import io
import json
from unittest.mock import Mock, patch

import pytest
import typer

from realms.cli.commands.installer import (
    _candid_text_arg,
    _load_manifest,
    _override,
    _unwrap_candid_text,
    installer_cancel_command,
    installer_deploy_command,
    installer_list_command,
    installer_status_command,
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestCandidTextArg:
    def test_simple_string(self):
        assert _candid_text_arg("hello") == '("hello")'

    def test_escapes_double_quotes(self):
        # Inner " must be backslash-escaped per Candid text rules.
        assert _candid_text_arg('a"b') == '("a\\"b")'

    def test_escapes_backslashes(self):
        assert _candid_text_arg("a\\b") == '("a\\\\b")'

    def test_round_trips_json(self):
        # The inverse of _unwrap_candid_text on dfx output should
        # recover the original payload.
        payload = json.dumps({"k": "v\"with\"quotes", "n": 1})
        wrapped = _candid_text_arg(payload)
        # Simulate dfx returning '("…",)' by stripping our wrapper and
        # re-feeding through _unwrap_candid_text.
        recovered = _unwrap_candid_text(f'({wrapped[1:-1]},)')
        assert recovered == payload


class TestUnwrapCandidText:
    def test_basic(self):
        assert _unwrap_candid_text('("hello")') == "hello"

    def test_trailing_comma(self):
        # dfx sometimes prints a trailing comma in the tuple form.
        assert _unwrap_candid_text('("hello",)') == "hello"

    def test_decodes_escapes(self):
        assert _unwrap_candid_text('("line1\\nline2")') == "line1\nline2"
        assert _unwrap_candid_text('("a\\"b")') == 'a"b'
        assert _unwrap_candid_text('("a\\\\b")') == "a\\b"

    def test_passthrough_on_unparseable(self):
        # Should not raise; returns input verbatim so callers see the
        # raw error text in logs.
        assert _unwrap_candid_text("not candid at all") == "not candid at all"


# ---------------------------------------------------------------------------
# _load_manifest / _override
# ---------------------------------------------------------------------------


class TestLoadManifest:
    def test_loads_valid_json_file(self, tmp_path):
        p = tmp_path / "m.json"
        p.write_text('{"target_canister_id": "abc", "registry_canister_id": "def"}')
        out = _load_manifest(str(p))
        assert out == {"target_canister_id": "abc", "registry_canister_id": "def"}

    def test_loads_from_stdin(self):
        manifest = '{"target_canister_id": "abc", "registry_canister_id": "def"}'
        with patch("sys.stdin", io.StringIO(manifest)):
            assert _load_manifest("-")["target_canister_id"] == "abc"

    def test_missing_path_exits(self):
        with pytest.raises(typer.Exit):
            _load_manifest(None)

    def test_missing_file_exits(self, tmp_path):
        with pytest.raises(typer.Exit):
            _load_manifest(str(tmp_path / "does-not-exist.json"))

    def test_invalid_json_exits(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not valid json")
        with pytest.raises(typer.Exit):
            _load_manifest(str(p))

    def test_non_object_exits(self, tmp_path):
        # Manifest must be an object, not a list/scalar.
        p = tmp_path / "list.json"
        p.write_text("[1, 2, 3]")
        with pytest.raises(typer.Exit):
            _load_manifest(str(p))


class TestOverride:
    def test_passthrough_when_overrides_none(self):
        m = {"target_canister_id": "t", "registry_canister_id": "r"}
        assert _override(m, None, None) == m

    def test_cli_target_wins(self):
        m = {"target_canister_id": "old", "registry_canister_id": "r"}
        out = _override(m, target="new", registry=None)
        assert out["target_canister_id"] == "new"
        assert out["registry_canister_id"] == "r"

    def test_cli_registry_wins(self):
        m = {"target_canister_id": "t", "registry_canister_id": "old"}
        out = _override(m, target=None, registry="new")
        assert out["registry_canister_id"] == "new"

    def test_missing_target_exits(self):
        with pytest.raises(typer.Exit):
            _override({"registry_canister_id": "r"}, None, None)

    def test_missing_registry_exits(self):
        with pytest.raises(typer.Exit):
            _override({"target_canister_id": "t"}, None, None)

    def test_does_not_mutate_input(self):
        m = {"target_canister_id": "t", "registry_canister_id": "r"}
        snapshot = json.dumps(m, sort_keys=True)
        _override(m, target="other", registry="other2")
        assert json.dumps(m, sort_keys=True) == snapshot


# ---------------------------------------------------------------------------
# installer_deploy_command — kickoff + wait flow with mocked dfx
# ---------------------------------------------------------------------------


def _mock_dfx(stdout: str, *, returncode: int = 0) -> Mock:
    """Build a subprocess.run mock that returns ``stdout``."""
    m = Mock()
    m.stdout = stdout
    m.stderr = ""
    m.returncode = returncode
    return m


def _candid_wrap(payload: str) -> str:
    """Encode ``payload`` as the candid text reply dfx would print."""
    escaped = payload.replace("\\", "\\\\").replace('"', '\\"')
    return f'("{escaped}")'


class TestInstallerDeploy:
    def _manifest(self, tmp_path):
        p = tmp_path / "m.json"
        p.write_text(json.dumps({
            "target_canister_id": "ijdaw-dyaaa-aaaac-beh2a-cai",
            "registry_canister_id": "iebdk-baaaa-aaaac-bejga-cai",
            "extensions": [{"id": "voting"}],
        }))
        return str(p)

    def test_kickoff_then_complete_no_wait(self, tmp_path):
        # --no-wait: only the deploy_realm call should fire; no polling.
        kickoff = _candid_wrap(json.dumps({
            "success": True,
            "task_id": "deploy_42",
            "status": "queued",
            "steps_count": 2,
        }))
        with patch("realms.cli.commands.installer.subprocess.run",
                   return_value=_mock_dfx(kickoff)) as run:
            installer_deploy_command(
                installer="rinst",
                manifest_path=self._manifest(tmp_path),
                network="local",
                wait=False,
            )
        # exactly one dfx invocation: the deploy_realm update call.
        assert run.call_count == 1
        argv = run.call_args[0][0]
        assert argv[:3] == ["dfx", "canister", "call"]
        assert "deploy_realm" in argv
        # update call → no --query
        assert "--query" not in argv

    def test_kickoff_rejected_exits(self, tmp_path):
        # Concurrency-control rejection from the canister → CLI must
        # exit non-zero so CI scripts notice.
        rejected = _candid_wrap(json.dumps({
            "success": False,
            "error": "deploy already in progress for target …",
            "conflicting_task_id": "deploy_99",
        }))
        with patch("realms.cli.commands.installer.subprocess.run",
                   return_value=_mock_dfx(rejected)):
            with pytest.raises(typer.Exit):
                installer_deploy_command(
                    installer="rinst",
                    manifest_path=self._manifest(tmp_path),
                    network="local",
                    wait=True,
                )

    def test_kickoff_then_wait_until_completed(self, tmp_path):
        # First call → kickoff (update); subsequent calls → status
        # query that flips queued → running → completed.
        statuses = [
            {"success": True, "task_id": "deploy_42", "status": "queued",
             "target_canister_id": "t", "registry_canister_id": "r"},
            {"success": True, "task_id": "deploy_42", "status": "running",
             "target_canister_id": "t", "registry_canister_id": "r"},
            {"success": True, "task_id": "deploy_42", "status": "completed",
             "target_canister_id": "t", "registry_canister_id": "r",
             "wasm": None, "extensions": [], "codices": []},
        ]
        replies = iter([
            _mock_dfx(_candid_wrap(json.dumps({
                "success": True, "task_id": "deploy_42",
                "status": "queued", "steps_count": 1,
            }))),
            *(_mock_dfx(_candid_wrap(json.dumps(s))) for s in statuses),
        ])
        with patch("realms.cli.commands.installer.subprocess.run",
                   side_effect=lambda *a, **k: next(replies)):
            with patch("realms.cli.commands.installer.time.sleep"):
                # Should return cleanly (no Exit raised).
                installer_deploy_command(
                    installer="rinst",
                    manifest_path=self._manifest(tmp_path),
                    network="local",
                    wait=True,
                    poll_interval=0,
                    max_wait=10,
                )

    def test_kickoff_then_wait_until_partial_exits(self, tmp_path):
        # Partial status (some steps failed) is still terminal but
        # signals deploy failure → CLI exits non-zero.
        partial = {
            "success": True, "task_id": "deploy_42", "status": "partial",
            "target_canister_id": "t", "registry_canister_id": "r",
            "extensions": [
                {"idx": 1, "kind": "extension", "label": "ext/voting",
                 "status": "failed", "error": "registry returned: not found"},
            ],
        }
        replies = iter([
            _mock_dfx(_candid_wrap(json.dumps({
                "success": True, "task_id": "deploy_42",
                "status": "queued", "steps_count": 1,
            }))),
            _mock_dfx(_candid_wrap(json.dumps(partial))),
        ])
        with patch("realms.cli.commands.installer.subprocess.run",
                   side_effect=lambda *a, **k: next(replies)):
            with patch("realms.cli.commands.installer.time.sleep"):
                with pytest.raises(typer.Exit):
                    installer_deploy_command(
                        installer="rinst",
                        manifest_path=self._manifest(tmp_path),
                        network="local",
                        wait=True,
                        poll_interval=0,
                        max_wait=10,
                    )

    def test_dfx_error_exits(self, tmp_path):
        with patch("realms.cli.commands.installer.subprocess.run",
                   return_value=_mock_dfx("", returncode=1)):
            with pytest.raises(typer.Exit):
                installer_deploy_command(
                    installer="rinst",
                    manifest_path=self._manifest(tmp_path),
                    network="local",
                    wait=False,
                )


# ---------------------------------------------------------------------------
# installer_status_command / installer_list_command
# ---------------------------------------------------------------------------


class TestInstallerStatus:
    def test_renders_status(self):
        body = _candid_wrap(json.dumps({
            "success": True, "task_id": "deploy_42", "status": "completed",
            "target_canister_id": "t", "registry_canister_id": "r",
            "wasm": {"idx": 0, "kind": "wasm", "label": "wasm/foo",
                     "status": "completed",
                     "result": {"wasm_module_hash_hex": "abcdef0123456789"}},
            "extensions": [], "codices": [],
        }))
        with patch("realms.cli.commands.installer.subprocess.run",
                   return_value=_mock_dfx(body)) as run:
            installer_status_command(
                installer="rinst", task_id="deploy_42", network="local",
            )
        argv = run.call_args[0][0]
        # status is a query
        assert "--query" in argv
        assert "get_deploy_status" in argv

    def test_error_exits(self):
        body = _candid_wrap(json.dumps({"success": False, "error": "no such task"}))
        with patch("realms.cli.commands.installer.subprocess.run",
                   return_value=_mock_dfx(body)):
            with pytest.raises(typer.Exit):
                installer_status_command(
                    installer="rinst", task_id="deploy_99", network="local",
                )


class TestInstallerCancel:
    def test_cancel_active_task(self):
        body = _candid_wrap(json.dumps({
            "success": True,
            "task_id": "deploy_42",
            "prev_status": "running",
            "status": "cancelled",
            "cancelled_steps": 3,
            "noop": False,
        }))
        with patch("realms.cli.commands.installer.subprocess.run",
                   return_value=_mock_dfx(body)) as run:
            installer_cancel_command(
                installer="rinst", task_id="deploy_42", network="local",
            )
        argv = run.call_args[0][0]
        # cancel is an update call
        assert "--query" not in argv
        assert "cancel_deploy" in argv

    def test_cancel_terminal_is_noop(self):
        # Cancelling an already-completed task should print a friendly
        # warning but not raise.
        body = _candid_wrap(json.dumps({
            "success": True, "task_id": "deploy_42",
            "prev_status": "completed", "status": "completed",
            "cancelled_steps": 0, "noop": True,
        }))
        with patch("realms.cli.commands.installer.subprocess.run",
                   return_value=_mock_dfx(body)):
            installer_cancel_command(
                installer="rinst", task_id="deploy_42", network="local",
            )

    def test_cancel_unknown_task_exits(self):
        body = _candid_wrap(json.dumps({
            "success": False, "error": "unknown task_id: deploy_99",
        }))
        with patch("realms.cli.commands.installer.subprocess.run",
                   return_value=_mock_dfx(body)):
            with pytest.raises(typer.Exit):
                installer_cancel_command(
                    installer="rinst", task_id="deploy_99", network="local",
                )


class TestInstallerList:
    def test_renders_table(self):
        body = _candid_wrap(json.dumps({
            "success": True,
            "tasks": [
                {"task_id": "deploy_1", "status": "completed",
                 "target_canister_id": "t1", "steps_count": 3,
                 "started_at": 1, "completed_at": 2},
                {"task_id": "deploy_2", "status": "running",
                 "target_canister_id": "t2", "steps_count": 5,
                 "started_at": 10, "completed_at": None},
            ],
        }))
        with patch("realms.cli.commands.installer.subprocess.run",
                   return_value=_mock_dfx(body)) as run:
            installer_list_command(installer="rinst", network="local")
        argv = run.call_args[0][0]
        assert "--query" in argv
        assert "list_deploys" in argv

    def test_empty_list(self):
        body = _candid_wrap(json.dumps({"success": True, "tasks": []}))
        with patch("realms.cli.commands.installer.subprocess.run",
                   return_value=_mock_dfx(body)):
            # Should not raise.
            installer_list_command(installer="rinst", network="local")
