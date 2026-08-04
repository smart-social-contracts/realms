"""In-process Kybra Async extension functions must suspend via extension_async_call."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))

sys.modules.setdefault("_cdk", MagicMock())


def _make_yielding_extension(monkeypatch):
    from core import extensions as core_extensions

    def _fake_func(_args):
        def _gen():
            yield "http-outcall"
            return "done"

        return _gen()

    monkeypatch.setattr(
        "core.runtime_sandbox.should_sandbox", lambda _id: False
    )
    monkeypatch.setattr(
        "core.runtime_extensions.get_func", lambda _ext, _fn: _fake_func
    )
    monkeypatch.setattr(
        "core.runtime_extensions.resolve_extension_id", lambda name: name
    )
    return core_extensions


def test_sync_call_rejects_suspending_generator(monkeypatch):
    core_extensions = _make_yielding_extension(monkeypatch)

    with pytest.raises(RuntimeError, match="invoke it via extension_async_call"):
        core_extensions.call_extension_function("passport_verification", "get_verification_link", "{}")


def test_async_call_returns_suspending_generator(monkeypatch):
    core_extensions = _make_yielding_extension(monkeypatch)

    gen = core_extensions.call_extension_function(
        "passport_verification",
        "get_verification_link",
        "{}",
        allow_suspend=True,
    )
    assert hasattr(gen, "__next__")
    assert next(gen) == "http-outcall"


def test_extension_async_call_uses_allow_suspend(monkeypatch):
    core_extensions = _make_yielding_extension(monkeypatch)

    gen = core_extensions.extension_async_call(
        "passport_verification", "get_verification_link", "{}"
    )
    assert hasattr(gen, "__next__")
    assert next(gen) == "http-outcall"
