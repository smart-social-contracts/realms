"""``core.extension_errors`` — stamp permission_denied on inner extension JSON."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "realm_backend"))
sys.modules.setdefault("_cdk", MagicMock())

from core.extension_errors import (  # noqa: E402
    ERROR_CODE_PERMISSION_DENIED,
    normalize_extension_result_json,
    payload_from_permission_error,
    permission_denied_payload,
)


def _load(result):
    return json.loads(normalize_extension_result_json(result))


def test_stamps_caught_permission_error_json():
    raw = json.dumps(
        {
            "success": False,
            "error": "Access denied: user abc lacks permission 'permission.view'",
        }
    )
    out = _load(raw)
    assert out["error_code"] == ERROR_CODE_PERMISSION_DENIED
    assert out["denied_operation"] == "permission.view"
    assert out["success"] is False


def test_stamps_user_not_found():
    raw = json.dumps({"success": False, "error": "User xyz not found"})
    out = _load(raw)
    assert out["error_code"] == ERROR_CODE_PERMISSION_DENIED
    assert out["denied_operation"] == "authenticated"


def test_leaves_validation_errors_alone():
    raw = json.dumps({"success": False, "error": "Department name is required"})
    out = _load(raw)
    assert "error_code" not in out
    assert out["error"] == "Department name is required"


def test_stamps_legacy_denied_operation():
    raw = {
        "success": False,
        "error": "Access denied: 'access_manager.list_departments' requires access level 'admin'",
        "denied_operation": "admin",
    }
    out = _load(raw)
    assert out["error_code"] == ERROR_CODE_PERMISSION_DENIED
    assert out["denied_operation"] == "admin"


def test_payload_from_permission_error():
    payload = payload_from_permission_error(
        PermissionError("Access denied: user abc lacks permission 'role.assign'")
    )
    assert payload == permission_denied_payload(
        "Access denied: user abc lacks permission 'role.assign'"
    )
    assert payload["denied_operation"] == "role.assign"


def test_successful_payload_unchanged():
    raw = json.dumps({"success": True, "data": {"departments": [1]}})
    assert normalize_extension_result_json(raw) == raw


def test_plain_permission_string():
    out = _load("Access denied: you lack permission 'extension.sync_call'")
    assert out["error_code"] == ERROR_CODE_PERMISSION_DENIED
    assert out["denied_operation"] == "extension.sync_call"
