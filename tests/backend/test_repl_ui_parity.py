"""Member-shaped REPL/UI parity (realms#313).

Three locked tests. A controller PEM is not a founder II session — every
principal here is a non-controller member. SHELL_EXECUTE lets them open
the REPL; it must not bypass ``@require`` or ``gate_extension_call``.
"""

import json
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
    "core.extension_access",
    "core.repl_host",
    "core.runtime_extensions",
    "_cdk",
):
    sys.modules.pop(_name, None)

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "realm_backend")
TOOLKIT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ic-basilisk-toolkit")
sys.path.insert(0, BACKEND)
if os.path.isdir(TOOLKIT) and TOOLKIT not in sys.path:
    sys.path.insert(0, TOOLKIT)

# Non-controller Internet Identity. Not a deploy PEM, not is_controller.
MEMBER = "member-ii-not-a-controller"


class _Principal:
    def __init__(self, text):
        self._text = text

    def to_str(self):
        return self._text

    def __str__(self):
        return self._text


_cdk = MagicMock()
_cdk.ic.caller.return_value = _Principal(MEMBER)
_cdk.ic.is_controller.return_value = False
sys.modules["_cdk"] = _cdk

from ggg.system.user_profile import Operations, Profiles  # noqa: E402

from core.access import AccessDenied, require  # noqa: E402
from core.call_origin import current as cedar_origin  # noqa: E402
from core.extension_access import gate_extension_call  # noqa: E402
from core.repl_host import HOST_STUB_APPENDIX, HostSecureORM  # noqa: E402

# Same ops a Profiles.MEMBER row carries, plus SHELL_EXECUTE so they may
# open the REPL client. No realm.admin, no invite.manage, no controller.
MEMBER_OPS = frozenset(Profiles.MEMBER["allowed_to"]) | {Operations.SHELL_EXECUTE}

# Voting 1.4.0 / role_manager 1.4.0 entry_access (realms-extensions).
ROLE_MANAGER_MANIFEST = {
    "name": "role_manager",
    "entry_access": {
        "default": "realm.data_view",
        "functions": {
            "generate_registration_url": "invite.manage",
            "cast_vote": "proposal.vote",
        },
    },
}

STATE: dict = {}


def _member_check(principal: str, operation: str) -> bool:
    """Member RBAC with no controller / trusted / test-mode bypass."""
    if _cdk.ic.is_controller(principal):
        raise AssertionError("denial tests must not use a controller principal")
    if principal != MEMBER:
        return False
    if operation == Operations.ALL:
        return False
    return operation in MEMBER_OPS


def _patch_access(monkeypatch):
    import core.access as access

    monkeypatch.setattr(access, "_check_access", _member_check)
    monkeypatch.setattr(access, "_controller_principal", "")
    _cdk.ic.caller.return_value = _Principal(MEMBER)
    _cdk.ic.is_controller.return_value = False


@require(Operations.SELF_UPDATE_PUBLIC_PROFILE)
def update_my_public_profile(nickname: str, avatar: str = ""):
    STATE["nickname"] = nickname
    STATE["avatar"] = avatar
    STATE["origin"] = dict(cedar_origin())
    return {"ok": True, "nickname": nickname, "avatar": avatar}


@require(Operations.REALM_ADMIN)
def set_canister_config(config: str):
    STATE["config"] = config
    return {"ok": True, "config": config}


def extension_sync_call(extension_name, function_name, args):
    """Same host gates as main.extension_sync_call (minus setup, mocked open)."""
    caller = _cdk.ic.caller().to_str()
    if not _member_check(caller, Operations.EXTENSION_SYNC_CALL):
        from core.extension_errors import permission_denied_payload

        return permission_denied_payload(
            f"Access denied: you lack permission '{Operations.EXTENSION_SYNC_CALL}'",
            Operations.EXTENSION_SYNC_CALL,
        )
    verdict = gate_extension_call(extension_name, function_name, args, caller)
    if verdict is not None:
        return verdict
    STATE.setdefault("ext", []).append(
        (extension_name, function_name, args)
    )
    return {"success": True, "response": json.dumps({"ok": True})}


def _host_module():
    return SimpleNamespace(
        update_my_public_profile=update_my_public_profile,
        set_canister_config=set_canister_config,
        extension_sync_call=extension_sync_call,
    )


def _orm(host):
    return HostSecureORM(
        engine=SimpleNamespace(status=lambda: {}),
        namespace="Realm",
        entities=[],
        schema={},
        host_module=host,
        allowed_methods=[
            "update_my_public_profile",
            "set_canister_config",
            "extension_sync_call",
        ],
    )


def _shell_eval(orm, code):
    """Product surface: ``api.call`` / ``ext.call`` via the injected stubs."""
    import builtins as _builtins

    def rpc(action, **kwargs):
        return orm.handle_rpc(MEMBER, action, kwargs)

    b = dict(vars(_builtins))
    b["rpc"] = rpc
    ns = {"eval_repl": lambda c: "", "__builtins__": b, "rpc": rpc}
    exec(HOST_STUB_APPENDIX, ns)
    return eval(code, ns, ns)


@pytest.fixture(autouse=True)
def _member_session(monkeypatch):
    STATE.clear()
    _patch_access(monkeypatch)
    monkeypatch.setattr(
        "core.runtime_extensions.resolve_extension_id", lambda name: name
    )
    monkeypatch.setattr(
        "core.runtime_extensions._load_manifest",
        lambda ext_id, force=False: ROLE_MANAGER_MANIFEST
        if ext_id == "role_manager"
        else None,
    )
    yield
    assert _cdk.ic.is_controller.return_value is False
    assert MEMBER != ""


class TestReplUiParity:
    def test_member_allow_matches_direct_candid_and_api_call(self):
        """Same member, same host method: Candid and ``api.call`` allow + state."""
        assert _member_check(MEMBER, Operations.SHELL_EXECUTE)
        assert _member_check(MEMBER, Operations.SELF_UPDATE_PUBLIC_PROFILE)
        host = _host_module()
        orm = _orm(host)

        STATE.clear()
        direct = update_my_public_profile("Ada")
        direct_state = dict(STATE)

        STATE.clear()
        via_shell = _shell_eval(
            orm, "api.call('update_my_public_profile', 'Ada')"
        )
        via_state = dict(STATE)

        assert direct == via_shell == {"ok": True, "nickname": "Ada", "avatar": ""}
        assert direct_state == via_state
        assert via_state["nickname"] == "Ada"
        # Host verbs must not inherit Cedar context.repl.
        assert via_state["origin"] == {}

    def test_member_deny_matches_direct_candid_and_api_call(self):
        """SHELL_EXECUTE does not bypass ``@require``; same AccessDenied class."""
        assert _member_check(MEMBER, Operations.SHELL_EXECUTE)
        assert not _member_check(MEMBER, Operations.REALM_ADMIN)
        host = _host_module()
        orm = _orm(host)

        STATE["config"] = None
        with pytest.raises(AccessDenied) as direct:
            set_canister_config("secret")
        assert STATE["config"] is None

        with pytest.raises(AccessDenied) as via_shell:
            _shell_eval(orm, "api.call('set_canister_config', 'secret')")
        assert STATE["config"] is None

        assert type(direct.value) is AccessDenied
        assert type(via_shell.value) is AccessDenied
        assert type(direct.value) is type(via_shell.value)
        assert isinstance(via_shell.value, PermissionError)

    def test_ext_call_matches_extension_sync_call_gate(self):
        """``ext.call`` is the UI button: same ``gate_extension_call`` denial."""
        assert _member_check(MEMBER, Operations.SHELL_EXECUTE)
        assert _member_check(MEMBER, Operations.EXTENSION_SYNC_CALL)
        assert not _member_check(MEMBER, Operations.INVITE_MANAGE)
        host = _host_module()
        orm = _orm(host)

        args = {"label": "invite-1"}
        args_json = json.dumps(args)
        direct = extension_sync_call(
            "role_manager", "generate_registration_url", args_json
        )
        via_shell = _shell_eval(
            orm,
            "ext.call('role_manager', 'generate_registration_url', "
            "{'label': 'invite-1'})",
        )

        assert direct == via_shell
        assert direct["success"] is False
        assert direct["error_code"] == "permission_denied"
        assert direct["denied_operation"] == "invite.manage"
        assert STATE.get("ext") in (None, [])
