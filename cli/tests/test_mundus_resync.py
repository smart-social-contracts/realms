"""Mundus must restore /ext/ bundles after a frontend deploy."""

from unittest.mock import patch

import pytest

from realms.cli.commands.mundus import (
    _resync_extension_frontends_after_deploy,
    _resync_frontends_payload,
    _should_resync_extension_frontends,
)


def test_should_resync_after_frontend_or_full_deploy():
    assert _should_resync_extension_frontends("") is True
    assert _should_resync_extension_frontends("frontend") is True
    assert _should_resync_extension_frontends("backend") is False


def test_resync_payload_includes_frontend_and_registry():
    raw = _resync_frontends_payload("fe-id", "reg-id")
    assert raw.startswith('("')
    assert raw.endswith('")')
    assert "fe-id" in raw
    assert "reg-id" in raw
    assert "frontend_canister_id" in raw
    assert "registry_canister_id" in raw


def test_resync_payload_omits_empty_registry():
    raw = _resync_frontends_payload("fe-id")
    assert "registry_canister_id" not in raw


@patch("realms.cli.commands.extension._dfx_call")
def test_resync_after_deploy_calls_backend(mock_call):
    mock_call.return_value = '{"success": true, "synced": [{"extension_id": "member_dashboard"}]}'
    realm = {"canister_id": "backend-id", "frontend_canister_id": "frontend-id"}
    infra = {"file_registry_canister_id": "registry-id"}

    _resync_extension_frontends_after_deploy(realm, "test", infra)

    methods = [c.args[1] for c in mock_call.call_args_list]
    assert methods == ["grant_permission", "resync_extension_frontends"]
    resync_arg = mock_call.call_args_list[1].args[2]
    assert "frontend-id" in resync_arg
    assert "registry-id" in resync_arg


@patch("realms.cli.commands.extension._dfx_call")
def test_resync_after_deploy_raises_on_backend_error(mock_call):
    mock_call.side_effect = [
        "()",
        '{"success": false, "error": "no frontend files"}',
    ]
    realm = {"canister_id": "backend-id", "frontend_canister_id": "frontend-id"}
    with pytest.raises(RuntimeError, match="no frontend files"):
        _resync_extension_frontends_after_deploy(realm, "test", {})
