"""Host-dispatch REPL: api/ext RPC hits the same Candid surface as the UI.

See realms#313 and docs/issues/repl-ui-parity-spec.md.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace

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
for _name in ("core.cedar_authz", "core.cedar_entities", "core.repl_host", "main"):
    sys.modules.pop(_name, None)

BACKEND = os.path.join(os.path.dirname(__file__), "..", "..", "src", "realm_backend")
TOOLKIT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ic-basilisk-toolkit")
sys.path.insert(0, BACKEND)
if os.path.isdir(TOOLKIT) and TOOLKIT not in sys.path:
    sys.path.insert(0, TOOLKIT)

from ic_basilisk_toolkit.secure_orm import RpcError  # noqa: E402

from core.repl_host import (  # noqa: E402
    BLOCKED_METHODS,
    HOST_ACTIONS,
    HOST_STUB_APPENDIX,
    HostSecureORM,
    json_args,
    load_allowed_methods,
    parse_candid_methods,
)


DID_PATH = Path(BACKEND) / "realm_backend.did"


class AccessDenied(Exception):
    pass


class DummyHost:
    def ping(self):
        return "pong"

    def echo(self, x, y=1):
        return {"x": x, "y": y}

    def boom(self):
        raise AccessDenied("nope")

    def extension_sync_call(self, extension_name, function_name, args):
        return {
            "ok": True,
            "extension_name": extension_name,
            "function_name": function_name,
            "args": args,
        }

    def extension_async_call(self, extension_name, function_name, args):
        return {"async": True, "function_name": function_name}

    def __shell__(self, code):
        return "should never run"

    def status(self):
        return {"ok": True}


def _orm(**overrides):
    allowed = overrides.pop(
        "allowed_methods",
        [
            "ping",
            "echo",
            "boom",
            "status",
            "extension_sync_call",
            "extension_async_call",
            "__shell__",
        ],
    )
    host = overrides.pop("host_module", DummyHost())
    return HostSecureORM(
        engine=SimpleNamespace(status=lambda: {}),
        namespace="Realm",
        entities=[],
        schema={},
        host_module=host,
        allowed_methods=allowed,
        **overrides,
    )


class TestDidAllowlist:
    def test_parses_quoted_service_methods(self):
        methods = parse_candid_methods(DID_PATH.read_text())
        assert "extension_sync_call" in methods
        assert "extension_async_call" in methods
        assert "status" in methods
        assert "__shell__" in methods
        assert "http_request" in methods
        assert "__get_candid_interface_tmp_hack" in methods

    def test_blocked_names_are_the_recursion_and_http_surface(self):
        assert BLOCKED_METHODS == {
            "__shell__",
            "http_request",
            "http_transform",
            "__get_candid_interface_tmp_hack",
        }

    def test_missing_did_uses_injected_candid_hack(self, tmp_path):
        did_text = (
            "service : {\n"
            '  "status" : () -> (text) query;\n'
            '  "__shell__" : (text) -> (text);\n'
            "}\n"
        )
        host = SimpleNamespace(__get_candid_interface_tmp_hack=lambda: did_text)
        names = load_allowed_methods(tmp_path / "missing.did", host_module=host)
        assert "status" in names
        assert "__shell__" not in names

    def test_missing_did_and_hack_raises(self, tmp_path):
        with pytest.raises(RpcError, match="Candid interface not found"):
            load_allowed_methods(tmp_path / "missing.did", host_module=SimpleNamespace())


class TestHostDispatch:
    def test_call_positional_and_keyword(self):
        orm = _orm()
        assert orm.handle_rpc("alice", "host.call", {"method": "ping"}) == "pong"
        assert orm.handle_rpc(
            "alice", "host.call", {"method": "echo", "args": ["hi"]}
        ) == {"x": "hi", "y": 1}
        assert orm.handle_rpc(
            "alice",
            "host.call",
            {"method": "echo", "args": ["hi"], "kwargs": {"y": 9}},
        ) == {"x": "hi", "y": 9}

    def test_list_methods_hides_blocked(self):
        orm = _orm()
        names = orm.handle_rpc("alice", "host.list_methods", {})
        assert "ping" in names
        assert "__shell__" not in names

    def test_blocked_shell_is_permission_error(self):
        orm = _orm()
        with pytest.raises(PermissionError, match="__shell__"):
            orm.handle_rpc(
                "alice", "host.call", {"method": "__shell__", "args": ["1+1"]}
            )

    def test_unknown_method_is_permission_error(self):
        orm = _orm()
        with pytest.raises(PermissionError, match="allowlist"):
            orm.handle_rpc("alice", "host.call", {"method": "not_a_method"})

    def test_access_denied_becomes_permission_error(self):
        orm = _orm()
        with pytest.raises(PermissionError, match="nope"):
            orm.handle_rpc("alice", "host.call", {"method": "boom"})

    def test_ext_sync_json_encodes_dict_like_the_spa(self):
        orm = _orm()
        result = orm.handle_rpc(
            "alice",
            "host.ext_sync",
            {
                "extension_name": "voting",
                "function_name": "cast_vote",
                "args": {"proposal_id": "p1"},
            },
        )
        assert result["extension_name"] == "voting"
        assert result["function_name"] == "cast_vote"
        assert result["args"] == '{"proposal_id": "p1"}'

    def test_ext_sync_passes_through_json_string(self):
        orm = _orm()
        result = orm.handle_rpc(
            "alice",
            "host.ext_sync",
            {
                "extension_name": "voting",
                "function_name": "cast_vote",
                "args": '{"proposal_id": "p1"}',
            },
        )
        assert result["args"] == '{"proposal_id": "p1"}'

    def test_same_args_host_call_and_direct_function(self):
        host = DummyHost()
        orm = _orm(host_module=host)
        via_rpc = orm.handle_rpc(
            "alice",
            "host.call",
            {
                "method": "extension_sync_call",
                "args": ["voting", "cast_vote", json_args({"proposal_id": "p1"})],
            },
        )
        direct = host.extension_sync_call(
            "voting", "cast_vote", json_args({"proposal_id": "p1"})
        )
        assert via_rpc == direct

    def test_unknown_host_action(self):
        orm = _orm()
        with pytest.raises(RpcError, match="unknown action"):
            orm.handle_rpc("alice", "host.explode", {})


class TestSandboxSurface:
    def test_actions_stay_under_cap(self):
        orm = _orm()
        actions = orm.actions()
        assert set(HOST_ACTIONS) <= set(actions)
        assert set(
            ["orm.create", "orm.list", "orm.get", "orm.update", "orm.delete", "orm.count"]
        ) <= set(actions)
        assert len(actions) <= 32

    def test_stub_defines_api_ext_and_wraps_eval_repl(self):
        orm = _orm()
        src = orm.stub_source()
        assert "class api:" in src
        assert "class ext:" in src
        assert "rpc(\"host.call\"" in src
        assert HOST_STUB_APPENDIX.strip() in src
        assert "_eval_repl_inner = eval_repl" in src
        assert 'ns["api"] = api' in src
        assert 'ns["ext"] = ext' in src

    def test_host_appendix_execs_with_rpc_injected(self):
        ns = {"rpc": lambda *a, **k: None, "eval_repl": lambda code: ""}
        exec(HOST_STUB_APPENDIX, ns)
        assert ns["api"].methods() is None
        assert ns["ext"].call("voting", "cast_vote", {"proposal_id": "p1"}) is None

    def test_ensure_sandbox_hash_without_sha256(self, monkeypatch):
        import hashlib
        import types

        approved = []

        class NoSha256:
            def approve_hash(self, h):
                approved.append(h)

        monkeypatch.setitem(sys.modules, "_basilisk_sandbox", NoSha256())
        orm = _orm()
        orm._ensure_sandbox_hash()
        expected = hashlib.sha256(orm._stub_source.encode("utf-8")).hexdigest()
        assert orm._sandbox_hash == expected
        assert approved == [expected]

    def test_json_args_matches_spa(self):
        assert json_args(None) == "{}"
        assert json_args({"a": 1}) == '{"a": 1}'
        assert json_args('{"a": 1}') == '{"a": 1}'
