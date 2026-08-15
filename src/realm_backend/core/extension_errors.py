"""Structured error envelopes for extension call results.

Inner handlers historically return ``{"success": false, "error": str}`` with no
machine-readable code. The host used to treat that as a successful call and
show empty lists. This module stamps ``error_code: permission_denied`` so the
frontend can handle denials once.

Do not use the ``re`` module here: Basilisk ships only a stub without
``re.compile``.
"""

import json

ERROR_CODE_PERMISSION_DENIED = "permission_denied"


def extract_denied_operation(message: str) -> str:
    if not message:
        return ""
    marker = "permission '"
    start = message.find(marker)
    if start >= 0:
        start += len(marker)
        end = message.find("'", start)
        if end > start:
            return message[start:end]
    lower = message.lower()
    if "user" in lower and "not found" in lower:
        return "authenticated"
    return ""


def is_permission_error_text(message: str) -> bool:
    if not message:
        return False
    lower = message.lower()
    if "access denied" in lower or "lacks permission" in lower:
        return True
    if "permission denied" in lower:
        return True
    if "user" in lower and "not found" in lower:
        return True
    return False


def permission_denied_payload(message: str, operation: str = "") -> dict:
    payload = {
        "success": False,
        "error_code": ERROR_CODE_PERMISSION_DENIED,
        "error": message or "Access denied",
    }
    op = operation or extract_denied_operation(message)
    if op:
        payload["denied_operation"] = op
    return payload


def payload_from_permission_error(exc: BaseException) -> dict:
    return permission_denied_payload(str(exc))


def _stamp_permission_denied(obj: dict) -> dict:
    err = str(obj.get("error") or "")
    stamped = dict(obj)
    stamped["success"] = False
    stamped["error_code"] = ERROR_CODE_PERMISSION_DENIED
    if not stamped.get("error"):
        stamped["error"] = err or "Access denied"
    if not stamped.get("denied_operation"):
        op = extract_denied_operation(err)
        if op:
            stamped["denied_operation"] = op
    return stamped


def normalize_extension_result_json(result) -> str:
    """Return a JSON string, injecting permission_denied when the payload is a denial."""
    if result is None:
        return "null"

    text = None
    if isinstance(result, dict):
        obj = result
    elif isinstance(result, str):
        text = result
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            if is_permission_error_text(text):
                return json.dumps(permission_denied_payload(text))
            return text
    else:
        try:
            text = json.dumps(result)
        except TypeError:
            return json.dumps({"success": False, "error": str(result)})
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return text

    if not isinstance(obj, dict):
        return text if text is not None else json.dumps(obj)

    if obj.get("error_code") == ERROR_CODE_PERMISSION_DENIED or (
        obj.get("success") is False
        and (
            obj.get("denied_operation")
            or is_permission_error_text(str(obj.get("error") or ""))
        )
    ):
        return json.dumps(_stamp_permission_denied(obj))

    return text if text is not None else json.dumps(obj)
