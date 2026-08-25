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

def _default_did_path() -> Path:
    """DID path for tests. Basilisk execs modules with no ``__file__``."""
    here = globals().get("__file__")
    if here:
        return Path(here).parent.parent / "realm_backend.did"
    try:
        return Path(__file__).parent.parent / "realm_backend.did"
    except Exception:
        return Path("realm_backend.did")


_DID_PATH = _default_did_path()

# Appended to the SecureORM stub. ``rpc`` is a sandbox builtin, not a global,
# and basilisk may bind the first ``eval_repl`` — so ``api``/``ext`` go in
# ``__builtins__`` and ``rpc`` is resolved at call time.
HOST_STUB_APPENDIX = r'''
def _host_rpc(action, **kwargs):
    b = __builtins__
    fn = b.get("rpc") if isinstance(b, dict) else getattr(b, "rpc", None)
    if fn is None:
        fn = globals().get("rpc")
    if not callable(fn):
        raise RuntimeError("rpc is not available")
    return fn(action, **kwargs)

class api:
    @staticmethod
    def call(method, *args, **kwargs):
        return _host_rpc("host.call", method=method, args=list(args), kwargs=dict(kwargs))

    @staticmethod
    def methods():
        return _host_rpc("host.list_methods")

class ext:
    @staticmethod
    def call(extension_name, function_name, args=None):
        return _host_rpc("host.ext_sync", extension_name=extension_name, function_name=function_name, args=args)

    @staticmethod
    def call_async(extension_name, function_name, args=None):
        return _host_rpc("host.ext_async", extension_name=extension_name, function_name=function_name, args=args)

def _install_host_names():
    b = __builtins__
    if isinstance(b, dict):
        b["api"] = api
        b["ext"] = ext
    else:
        b.api = api
        b.ext = ext
    ns = globals().get("_repl_ns")
    if isinstance(ns, dict):
        ns["api"] = api
        ns["ext"] = ext
        if not callable(ns.get("rpc")):
            fn = b.get("rpc") if isinstance(b, dict) else getattr(b, "rpc", None)
            if callable(fn):
                ns["rpc"] = fn

_install_host_names()
_eval_repl_inner = eval_repl
def eval_repl(code):
    _install_host_names()
    return _eval_repl_inner(code)
'''


def parse_candid_methods(did_text: str) -> FrozenSet[str]:
    """Quoted method names from the last ``service :`` block. No ``re`` module.

    Handles both multiline DID files and the one-line form basilisk embeds
    in ``__get_candid_interface_tmp_hack``.
    """
    marker = "service :"
    idx = did_text.rfind(marker)
    body = did_text[idx:] if idx >= 0 else did_text
    names = []
    i = 0
    while True:
        q = body.find('"', i)
        if q < 0:
            break
        end = body.find('"', q + 1)
        if end < 0:
            break
        name = body[q + 1 : end]
        rest = body[end + 1 :].lstrip()
        if rest.startswith(":") and name:
            names.append(name)
        i = end + 1
    return frozenset(names)


def _resolve_host_module(host_module: Any = None) -> Any:
    if host_module is not None:
        return host_module
    mod = sys.modules.get("main") or sys.modules.get("__main__")
    if mod is not None:
        return mod
    try:
        import main as mod  # type: ignore
        return mod
    except Exception:
        return None


def load_allowed_methods(
    did_path: Optional[Path] = None,
    blocked: Iterable[str] = BLOCKED_METHODS,
    host_module: Any = None,
) -> FrozenSet[str]:
    """Allowlist from the DID file, or from the injected Candid hack on-canister."""
    blocked_set = frozenset(blocked)
    path = Path(did_path) if did_path is not None else _DID_PATH
    did_text = None
    try:
        if path.is_file():
            did_text = path.read_text()
    except OSError:
        did_text = None
    if not did_text:
        module = _resolve_host_module(host_module)
        hack = getattr(module, "__get_candid_interface_tmp_hack", None) if module else None
        if callable(hack):
            did_text = hack()
    if did_text:
        names = parse_candid_methods(did_text) - blocked_set
        if names:
            return names
    raise RpcError("Candid interface not found; host RPC disabled")


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
        if not self._allowed_methods:
            self._allowed_methods = load_allowed_methods(
                self._did_path,
                self._blocked_methods,
                host_module=self.host_module(),
            )
        return self._allowed_methods - self._blocked_methods

    def host_module(self) -> Any:
        if self._host_module is not None:
            return self._host_module
        resolved = _resolve_host_module()
        if resolved is not None:
            self._host_module = resolved
        return resolved

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
        # The Candid surface *is* the decorated function. Do not unwrap
        # ``@require`` / ``@update`` — that would skip the same gates the UI
        # hits. SHELL_EXECUTE is not a superuser bit on these verbs.
        fn = getattr(module, method, None)
        if not callable(fn):
            raise RpcError(f"host method {method!r} is not defined")
        try:
            bound = inspect.signature(fn).bind(*args, **call_kwargs)
            bound.apply_defaults()
        except TypeError as exc:
            raise RpcError(f"{method}: {exc}") from exc
        from core.call_origin import host_call

        try:
            # Host verbs must not run Cedar with context.repl. Empty origin
            # matches a browser Candid ingress; extension_sync_call then
            # sets context.extension on the bridge like the UI does.
            with host_call():
                return drive_result(fn(*bound.args, **bound.kwargs))
        except PermissionError:
            raise
        except Exception as exc:
            if type(exc).__name__ == "AccessDenied":
                raise _as_permission(exc) from exc
            raise
