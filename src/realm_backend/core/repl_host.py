"""Host-dispatch REPL: UI and shell share the same Candid surface.

The product REPL is a client of host methods (``api.call`` / ``ext.call``),
not a second ORM back door. SecureORM entity stubs remain available as an
optional Cedar-gated debug surface.

See ``docs/issues/repl-ui-parity-spec.md``.
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from typing import Any, FrozenSet, Iterable, Optional

from ic_basilisk_toolkit.secure_orm import RpcError, SecureORM

HOST_ACTIONS = (
    "host.call",
    "host.ext_sync",
    "host.ext_async",
    "host.list_methods",
)

BLOCKED_METHODS = frozenset(
    {
        "__shell__",
        "http_request",
        "http_transform",
        "__get_candid_interface_tmp_hack",
    }
)

# Do not Path.resolve() here: WASI realpath can fail at import, which would
# take down HostSecureORM (and therefore __shell__) for the whole process.
_DID_PATH = Path(__file__).parent.parent / "realm_backend.did"

# Appended to the SecureORM stub module. ``rpc`` is injected by the sandbox.
# ``eval_repl`` is redefined so ``api`` / ``ext`` survive in ``_repl_ns``.
HOST_STUB_APPENDIX = r'''
class api:
    @staticmethod
    def call(method, *args, **kwargs):
        return rpc("host.call", method=method, args=list(args), kwargs=dict(kwargs))

    @staticmethod
    def methods():
        return rpc("host.list_methods")

class ext:
    @staticmethod
    def call(extension_name, function_name, args=None):
        return rpc("host.ext_sync", extension_name=extension_name, function_name=function_name, args=args)

    @staticmethod
    def call_async(extension_name, function_name, args=None):
        return rpc("host.ext_async", extension_name=extension_name, function_name=function_name, args=args)

_eval_repl_inner = eval_repl
def eval_repl(code):
    ns = globals().get("_repl_ns")
    if ns is None:
        ns = {"rpc": globals().get("rpc"), "__builtins__": __builtins__}
        for _name, _val in list(globals().items()):
            if isinstance(_val, type) and _name[:1].isupper():
                ns[_name] = _val
        ns["api"] = api
        ns["ext"] = ext
        globals()["_repl_ns"] = ns
    else:
        ns["api"] = api
        ns["ext"] = ext
    return _eval_repl_inner(code)
'''


def parse_candid_methods(did_text: str) -> FrozenSet[str]:
    """Quoted method names from the last ``service :`` block. No ``re`` module."""
    marker = "service :"
    idx = did_text.rfind(marker)
    body = did_text[idx:] if idx >= 0 else did_text
    names = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith('"'):
            continue
        end = stripped.find('"', 1)
        if end <= 1:
            continue
        name = stripped[1:end]
        rest = stripped[end + 1 :].lstrip()
        if rest.startswith(":"):
            names.append(name)
    return frozenset(names)


def _candid_text_from_host_module() -> str:
    """Basilisk injects ``__get_candid_interface_tmp_hack`` returning the .did.

    The WASM image does not ship ``realm_backend.did`` as a file, so host RPC
    falls back to that embedded string once ``main`` is loaded.
    """
    module = sys.modules.get("main")
    if module is None:
        return ""
    hack = getattr(module, "__get_candid_interface_tmp_hack", None)
    if not callable(hack):
        return ""
    try:
        text = hack()
    except Exception:
        return ""
    return text if isinstance(text, str) else ""


def load_allowed_methods(
    did_path: Optional[Path] = None,
    blocked: Iterable[str] = BLOCKED_METHODS,
) -> FrozenSet[str]:
    path = Path(did_path) if did_path is not None else _DID_PATH
    text = ""
    try:
        if path.is_file():
            text = path.read_text()
    except OSError:
        text = ""
    if not text:
        text = _candid_text_from_host_module()
    if not text:
        raise RpcError(f"Candid interface not found at {path}; host RPC disabled")
    return parse_candid_methods(text) - frozenset(blocked)


def json_args(args: Any) -> str:
    """Match the SPA: ``JSON.stringify(args)`` into ``extension_sync_call``."""
    if args is None:
        return "{}"
    if isinstance(args, str):
        return args
    return json.dumps(args)


def drive_result(result: Any) -> Any:
    """Consume a Basilisk ``Async`` generator that does not yield IC calls."""
    if not inspect.isgenerator(result):
        return result
    try:
        yielded = next(result)
        while True:
            if isinstance(yielded, tuple) and yielded and yielded[0] == "call":
                raise RuntimeError(
                    "async host method yielded an inter-canister call; "
                    "the REPL cannot drive IC calls yet"
                )
            yielded = result.send(None)
    except StopIteration as done:
        return done.value


def _as_permission(exc: BaseException) -> PermissionError:
    return PermissionError(str(exc))


class HostSecureORM(SecureORM):
    """SecureORM plus host-method RPCs (``api`` / ``ext`` in the REPL)."""

    def __init__(
        self,
        *args: Any,
        host_module: Any = None,
        allowed_methods: Optional[Iterable[str]] = None,
        blocked_methods: Optional[Iterable[str]] = None,
        did_path: Optional[Path] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._host_module = host_module
        self._blocked_methods = (
            frozenset(blocked_methods)
            if blocked_methods is not None
            else BLOCKED_METHODS
        )
        self._allowed_methods: Optional[FrozenSet[str]] = (
            frozenset(allowed_methods) if allowed_methods is not None else None
        )
        self._did_path = Path(did_path) if did_path is not None else _DID_PATH
        self._stub_source = self._stub_source + "\n" + HOST_STUB_APPENDIX
        self._sandbox_hash = ""

    def actions(self) -> list:
        return list(super().actions()) + list(HOST_ACTIONS)

    def allowed_methods(self) -> FrozenSet[str]:
        if self._allowed_methods is not None:
            return self._allowed_methods - self._blocked_methods
        return load_allowed_methods(self._did_path, self._blocked_methods)

    def host_module(self) -> Any:
        if self._host_module is not None:
            return self._host_module
        return sys.modules.get("main")

    def handle_rpc(self, principal_id: str, action: str, kwargs: dict) -> Any:
        kwargs = dict(kwargs or {})
        if action.startswith("host."):
            return self._handle_host(action, kwargs)
        return super().handle_rpc(principal_id, action, kwargs)

    def _handle_host(self, action: str, kwargs: dict) -> Any:
        if action == "host.list_methods":
            return sorted(self.allowed_methods())
        if action == "host.call":
            method = kwargs.get("method")
            args = list(kwargs.get("args") or [])
            call_kwargs = dict(kwargs.get("kwargs") or {})
            return self._call_host(method, args, call_kwargs)
        if action == "host.ext_sync":
            return self._call_host(
                "extension_sync_call",
                [
                    kwargs.get("extension_name"),
                    kwargs.get("function_name"),
                    json_args(kwargs.get("args")),
                ],
                {},
            )
        if action == "host.ext_async":
            return self._call_host(
                "extension_async_call",
                [
                    kwargs.get("extension_name"),
                    kwargs.get("function_name"),
                    json_args(kwargs.get("args")),
                ],
                {},
            )
        raise RpcError(f"unknown action {action!r}")

    def _call_host(self, method: Any, args: list, call_kwargs: dict) -> Any:
        if not isinstance(method, str) or not method:
            raise RpcError("host.call requires a method name")
        if method in self._blocked_methods:
            raise PermissionError(
                f"host method {method!r} is not callable from the REPL"
            )
        allowed = self.allowed_methods()
        if method not in allowed:
            raise PermissionError(f"host method {method!r} is not on the allowlist")
        module = self.host_module()
        if module is None:
            raise RpcError("host module is not loaded")
        fn = getattr(module, method, None)
        if not callable(fn):
            raise RpcError(f"host method {method!r} is not defined")
        try:
            bound = inspect.signature(fn).bind(*args, **call_kwargs)
            bound.apply_defaults()
        except TypeError as exc:
            raise RpcError(f"{method}: {exc}") from exc
        try:
            return drive_result(fn(*bound.args, **bound.kwargs))
        except PermissionError:
            raise
        except Exception as exc:
            if type(exc).__name__ == "AccessDenied":
                raise _as_permission(exc) from exc
            raise
