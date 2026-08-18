"""``core.extension_errors`` — structured codes set at the source."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "realm_backend"))
sys.modules.setdefault("_cdk", MagicMock())

from core.extension_errors import (  # noqa: E402
    ERROR_CODE_NOT_FOUND,
    ERROR_CODE_PERMISSION_DENIED,
    ERROR_CODE_UNAUTHENTICATED,
    ERROR_CODE_VALIDATION,
    PermissionDenied,
    Unauthenticated,
    normalize_extension_result_json,
    not_found_payload,
    payload_from_permission_error,
    permission_denied_payload,
    validation_payload,
)


def _load(result):
    return json.loads(normalize_extension_result_json(result))


def test_serializes_coded_payload():
    payload = permission_denied_payload(
        "Access denied: user abc lacks permission 'permission.view'",
        operation="permission.view",
    )
    out = _load(payload)
    assert out["error_code"] == ERROR_CODE_PERMISSION_DENIED
    assert out["denied_operation"] == "permission.view"
    assert out["success"] is False


def test_does_not_infer_code_from_english():
    raw = json.dumps(
        {
            "success": False,
            "error": "Access denied: user abc lacks permission 'permission.view'",
        }
    )
    out = _load(raw)
    assert "error_code" not in out
    assert out["error"].startswith("Access denied")


def test_does_not_treat_user_not_found_as_permission():
    raw = json.dumps({"success": False, "error": "User xyz not found"})
    out = _load(raw)
    assert "error_code" not in out


def test_leaves_validation_errors_alone():
    raw = json.dumps({"success": False, "error": "Department name is required"})
    out = _load(raw)
    assert "error_code" not in out
    assert out["error"] == "Department name is required"


def test_payload_from_permission_denied():
    payload = payload_from_permission_error(
        PermissionDenied(
            "Access denied: user abc lacks permission 'role.assign'",
            operation="role.assign",
        )
    )
    assert payload == permission_denied_payload(
        "Access denied: user abc lacks permission 'role.assign'",
        operation="role.assign",
    )
    assert payload["denied_operation"] == "role.assign"


def test_payload_from_unauthenticated():
    payload = payload_from_permission_error(Unauthenticated("User xyz not found"))
    assert payload["error_code"] == ERROR_CODE_UNAUTHENTICATED
    assert "denied_operation" not in payload


def test_not_found_and_validation_helpers():
    missing = not_found_payload("No realm member with principal 'xyz'", entity="user")
    assert missing["error_code"] == ERROR_CODE_NOT_FOUND
    assert missing["entity"] == "user"
    bad = validation_payload("department is required")
    assert bad["error_code"] == ERROR_CODE_VALIDATION


def test_successful_payload_unchanged():
    raw = json.dumps({"success": True, "data": {"departments": [1]}})
    assert normalize_extension_result_json(raw) == raw


def test_plain_permission_string_not_stamped():
    out = normalize_extension_result_json(
        "Access denied: you lack permission 'extension.sync_call'"
    )
    assert out == "Access denied: you lack permission 'extension.sync_call'"
