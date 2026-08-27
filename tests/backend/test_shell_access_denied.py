"""Host / REPL AccessDenied is one ``✗`` line (realms#349).

Exact failed permission + the call that caused it. ``shell.execute`` only
when opening ``__shell__``. No principal. No traceback.
"""

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

_MOCKED_PREFIXES = (
    "ic_basilisk_toolkit",
    "ic_python_db",
    "ic_python_logging",
)
for _name in list(sys.modules):
    if any(
        _name == prefix or _name.startswith(prefix + ".")
        for prefix in _MOCKED_PREFIXES
    ):
        if type(sys.modules[_name]).__name__ == "MagicMock":
            del sys.modules[_name]
for _name in (
    "core.access",
    "core.call_origin",
    "core.repl_host",
    "_cdk",
):
    sys.modules.pop(_name, None)

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "realm_backend")
sys.path.insert(0, BACKEND)

MEMBER = "2eqns-member-without-org-create"
STRANGER = "z32zf-no-shell-execute"


class _Principal:
    def __init__(self, text):
        self._text = text

    def to_str(self):
        return self._text

    def __str__(self):
        return self._text


_cdk = MagicMock()
_cdk.ic.caller.return_value = _Principal(STRANGER)
_cdk.ic.is_controller.return_value = False
sys.modules["_cdk"] = _cdk

from ggg.system.user_profile import Operations  # noqa: E402

from core.access import (  # noqa: E402
    AccessDenied,
    format_quiet_denied,
    permission_name,
    product_shell_guard,
    quiet_access_denied,
    quiet_shell_result,
    raise_quiet_access_denied,
    require,
)
from core.repl_host import HOST_STUB_APPENDIX, HostSecureORM  # noqa: E402


def test_quiet_string_shell_execute_only_for_opening_repl():
    exc = AccessDenied(
        f"Access denied: user {STRANGER} lacks permission 'shell.execute'",
        permission="shell.execute",
    )
    out = quiet_access_denied(exc)
    assert out == "✗ access denied: shell.execute"
    assert STRANGER not in out
    assert "Traceback" not in out
    assert "\n" not in out
    assert "api.call" not in out


def test_quiet_string_names_permission_and_api_call():
    out = format_quiet_denied("realm.admin", "api.call('set_canister_config')")
    assert out == "✗ access denied: realm.admin from api.call('set_canister_config')"
    assert "shell.execute" not in out


def test_quiet_string_never_defaults_to_shell_execute():
    assert format_quiet_denied("", "api.call('set_canister_config')") == (
        "✗ access denied: from api.call('set_canister_config')"
    )
    assert "shell.execute" not in format_quiet_denied("realm.admin")
    assert format_quiet_denied("realm.admin") == "✗ access denied: realm.admin"


def test_permission_name_from_long_message():
    assert (
        permission_name(
            f"AccessDenied: Access denied: user {STRANGER} lacks permission 'shell.execute'"
        )
        == "shell.execute"
    )
    assert (
        permission_name(
            "✗ access denied: realm.admin from api.call('set_canister_config')"
        )
        == "realm.admin"
    )


def test_require_shell_execute_denied_is_quiet(monkeypatch):
    import core.access as access

    monkeypatch.setattr(access, "_check_access", lambda *_a, **_k: False)
    _cdk.ic.caller.return_value = _Principal(STRANGER)
    _cdk.ic.is_controller.return_value = False

    @require(Operations.SHELL_EXECUTE)
    def _shell():
        return "should-not-run"

    with pytest.raises(AccessDenied) as denied:
        _shell()
    assert denied.value.permission == "shell.execute"
    out = product_shell_guard(_shell)
    assert out == "✗ access denied: shell.execute"
    assert STRANGER not in out
    assert "Traceback" not in out
    assert "AccessDenied:" not in out
    assert "api.call" not in out


def test_product_shell_guard_does_not_attach_traceback(monkeypatch):
    import core.access as access

    monkeypatch.setattr(access, "_check_access", lambda *_a, **_k: False)
    _cdk.ic.caller.return_value = _Principal(STRANGER)

    @require(Operations.SHELL_EXECUTE)
    def _shell():
        raise RuntimeError("inner should not run")

    out = product_shell_guard(_shell)
    assert out == "✗ access denied: shell.execute"
    assert "RuntimeError" not in out
    assert "Traceback" not in out


def test_raise_quiet_strips_principal_and_keeps_source():
    try:
        raise AccessDenied(
            f"Access denied: user {STRANGER} lacks permission 'realm.admin'",
            permission="realm.admin",
        )
    except AccessDenied as exc:
        with pytest.raises(AccessDenied) as quiet:
            raise_quiet_access_denied(exc, source="api.call('set_canister_config')")
    assert quiet.value.permission == "realm.admin"
    assert quiet.value.source == "api.call('set_canister_config')"
    assert str(quiet.value) == (
        "✗ access denied: realm.admin from api.call('set_canister_config')"
    )
    assert STRANGER not in str(quiet.value)
    assert "shell.execute" not in str(quiet.value)
    assert quiet.value.__cause__ is None


def test_quiet_shell_result_unwraps_leftover_host_pipe():
    leaked = (
        "✗ access denied: call on Host ("
        "✗ access denied: realm.admin from api.call('set_canister_config'))"
    )
    out = quiet_shell_result(leaked)
    assert out == "✗ access denied: realm.admin from api.call('set_canister_config')"
    assert "call on Host" not in out
    assert "shell.execute" not in out

    old = (
        f"✗ access denied: call on Host (Access denied: user {MEMBER} "
        f"lacks permission 'organization.add')"
    )
    out = quiet_shell_result(old)
    assert out == "✗ access denied: organization.add"
    assert MEMBER not in out
    assert "shell.execute" not in out


@require(Operations.ORGANIZATION_ADD)
def create_department(payload: str):
    return {"ok": True, "payload": payload}


@require(Operations.REALM_ADMIN)
def set_canister_config(config: str):
    return {"ok": True, "config": config}


def extension_sync_call(extension_name, function_name, args):
    """Inner entry_access deny — not the ``extension.sync_call`` pipe."""
    raise AccessDenied(
        "inner entry_access",
        permission="invite.manage",
    )


def _member_check(principal: str, operation: str) -> bool:
    if _cdk.ic.is_controller(principal):
        raise AssertionError("denial tests must not use a controller principal")
    if principal != MEMBER:
        return False
    return operation in {Operations.SHELL_EXECUTE, Operations.EXTENSION_SYNC_CALL}


def _eval_api(orm, principal, code):
    import builtins as _builtins

    def rpc(action, **kwargs):
        return orm.handle_rpc(principal, action, kwargs)

    b = dict(vars(_builtins))
    b["rpc"] = rpc
    ns = {"eval_repl": lambda _c: "", "__builtins__": b, "rpc": rpc}
    exec(HOST_STUB_APPENDIX, ns)
    return eval(code, ns, ns), ns


def test_api_call_set_canister_config_names_inner_permission(monkeypatch):
    import core.access as access

    monkeypatch.setattr(access, "_check_access", _member_check)
    _cdk.ic.caller.return_value = _Principal(MEMBER)
    _cdk.ic.is_controller.return_value = False

    orm = HostSecureORM(
        engine=SimpleNamespace(status=lambda: {}),
        namespace="Realm",
        entities=[],
        schema={},
        host_module=SimpleNamespace(set_canister_config=set_canister_config),
        allowed_methods=["set_canister_config"],
    )
    with pytest.raises(AccessDenied) as denied:
        _eval_api(orm, MEMBER, "api.call('set_canister_config', '{}')")
    out = quiet_access_denied(denied.value)
    assert out == "✗ access denied: realm.admin from api.call('set_canister_config')"
    assert "shell.execute" not in out
    assert MEMBER not in out
    assert "Traceback" not in out
    assert "host.call" not in out
    assert "call on Host" not in out


def test_create_department_off_allowlist_is_require_not_allowlist(monkeypatch):
    """Leftover DID allowlist miss must not hide ``organization.add``."""
    import core.access as access

    monkeypatch.setattr(access, "_check_access", _member_check)
    _cdk.ic.caller.return_value = _Principal(MEMBER)
    _cdk.ic.is_controller.return_value = False

    orm = HostSecureORM(
        engine=SimpleNamespace(status=lambda: {}),
        namespace="Realm",
        entities=[],
        schema={},
        host_module=SimpleNamespace(create_department=create_department),
        # Leftover allowlist from an incomplete DID — verb exists with @require.
        allowed_methods=["set_canister_config", "status"],
    )
    with pytest.raises(AccessDenied) as denied:
        _eval_api(orm, MEMBER, "api.call('create_department', '{}')")
    out = quiet_access_denied(denied.value)
    assert out == (
        "✗ access denied: organization.add from api.call('create_department')"
    )
    assert "allowlist" not in out
    assert "allowlist" not in str(denied.value)
    assert "call on Host" not in out
    assert "call on Host" not in str(denied.value)
    assert "shell.execute" not in out
    assert MEMBER not in out

    def _escaped():
        _eval_api(orm, MEMBER, "api.call('create_department', '{}')")

    guarded = product_shell_guard(_escaped)
    assert guarded == (
        "✗ access denied: organization.add from api.call('create_department')"
    )
    assert "allowlist" not in guarded
    assert "call on Host" not in guarded


def test_leftover_query_off_allowlist_still_names_require(monkeypatch):
    """Leftover Query is not callable; still surface the inner ``@require``."""
    import core.access as access

    monkeypatch.setattr(access, "_check_access", _member_check)
    _cdk.ic.caller.return_value = _Principal(MEMBER)
    _cdk.ic.is_controller.return_value = False

    class _LeftoverQuery:
        _require_operation = "organization.add"

    orm = HostSecureORM(
        engine=SimpleNamespace(status=lambda: {}),
        namespace="Realm",
        entities=[],
        schema={},
        host_module=SimpleNamespace(create_department=_LeftoverQuery()),
        allowed_methods=["status"],
    )
    with pytest.raises(AccessDenied) as denied:
        _eval_api(orm, MEMBER, "api.call('create_department', '{}')")
    out = quiet_access_denied(denied.value)
    assert out == (
        "✗ access denied: organization.add from api.call('create_department')"
    )
    assert "allowlist" not in str(denied.value)
    assert "call on Host" not in str(denied.value)


def test_unknown_method_still_allowlist(monkeypatch):
    import core.access as access

    monkeypatch.setattr(access, "_check_access", _member_check)
    _cdk.ic.caller.return_value = _Principal(MEMBER)
    orm = HostSecureORM(
        engine=SimpleNamespace(status=lambda: {}),
        namespace="Realm",
        entities=[],
        schema={},
        host_module=SimpleNamespace(create_department=create_department),
        allowed_methods=["create_department"],
    )
    with pytest.raises(PermissionError, match="allowlist"):
        _eval_api(orm, MEMBER, "api.call('not_a_real_verb', '{}')")


def test_api_call_create_department_is_one_quiet_line(monkeypatch):
    """Member with shell.execute, without organization.add — one ``✗`` line."""
    import core.access as access

    monkeypatch.setattr(access, "_check_access", _member_check)
    _cdk.ic.caller.return_value = _Principal(MEMBER)
    _cdk.ic.is_controller.return_value = False

    orm = HostSecureORM(
        engine=SimpleNamespace(status=lambda: {}),
        namespace="Realm",
        entities=[],
        schema={},
        host_module=SimpleNamespace(create_department=create_department),
        allowed_methods=["create_department"],
    )

    with pytest.raises(AccessDenied) as denied:
        _eval_api(orm, MEMBER, "api.call('create_department', '{}')")

    assert type(denied.value) is AccessDenied
    assert permission_name(denied.value) == "organization.add"
    assert denied.value.source == "api.call('create_department')"
    out = quiet_access_denied(denied.value)
    assert out == "✗ access denied: organization.add from api.call('create_department')"
    assert MEMBER not in out
    assert "shell.execute" not in out
    assert "Traceback" not in out
    assert "\n" not in out

    def _escaped():
        _eval_api(orm, MEMBER, "api.call('create_department', '{}')")

    guarded = product_shell_guard(_escaped)
    assert guarded == (
        "✗ access denied: organization.add from api.call('create_department')"
    )
    assert MEMBER not in guarded
    assert "shell.execute" not in guarded


def test_ext_call_names_inner_permission_not_the_pipe(monkeypatch):
    import core.access as access

    monkeypatch.setattr(access, "_check_access", _member_check)
    _cdk.ic.caller.return_value = _Principal(MEMBER)
    _cdk.ic.is_controller.return_value = False

    orm = HostSecureORM(
        engine=SimpleNamespace(status=lambda: {}),
        namespace="Realm",
        entities=[],
        schema={},
        host_module=SimpleNamespace(extension_sync_call=extension_sync_call),
        allowed_methods=["extension_sync_call"],
    )
    with pytest.raises(AccessDenied) as denied:
        _eval_api(
            orm,
            MEMBER,
            "ext.call('role_manager', 'generate_registration_url', {'label': 'x'})",
        )
    out = quiet_access_denied(denied.value)
    assert out == (
        "✗ access denied: invite.manage from "
        "ext.call('role_manager', 'generate_registration_url')"
    )
    assert "extension.sync_call" not in out
    assert "shell.execute" not in out
    assert MEMBER not in out
    assert "host.ext" not in out
