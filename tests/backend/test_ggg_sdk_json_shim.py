"""The in-sandbox ``json`` shim must behave like the real thing.

A subinterpreter has only builtin C modules, so ``import json`` fails there —
verified against the staging canister, where ``json``, ``re`` and ``math`` are
all absent while ``sys`` is present.

That matters more than it first looks. Every extension entry point is
``f(args: str) -> str`` with JSON on both sides, so without ``json`` each
ported extension would hand-roll serialization, which is both tedious and a
good way to introduce escaping bugs. ``ggg_sdk`` therefore ships a pure-Python
implementation and registers it as ``sys.modules["json"]`` when the real one is
missing.

Since it silently replaces the stdlib inside the sandbox, it has to agree with
the stdlib. These tests build the shim by forcing the ImportError branch, then
compare it against ``json`` directly.
"""

import builtins
import json as stdlib_json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "realm_backend"))

import ggg_sdk  # noqa: E402


@pytest.fixture(scope="module")
def shim():
    """The shim the sandbox would get, built with ``json`` unimportable."""
    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "json":
            raise ImportError("no json in the sandbox")
        return real_import(name, *args, **kwargs)

    namespace = {}
    saved = sys.modules.pop("json")
    builtins.__import__ = blocked
    try:
        exec(compile(ggg_sdk.GGG_SDK_SOURCE, "ggg_sdk.py", "exec"), namespace)
    finally:
        builtins.__import__ = real_import
        sys.modules["json"] = saved
    return namespace["json"]


VALUES = [
    None, True, False,
    0, -17, 1234567890123,
    3.5, -0.25,
    "", "plain",
    'quote" backslash\\ newline\n tab\t',
    "unicode: \u00f1 \u65e5\u672c \u20ac",
    "control\x01char",
    [], [1, [2, [3, []]]],
    {}, {"a": 1, "b": [True, None, "x"], "c": {"d": 2.25}},
    {"success": True, "data": [], "error": None},
]


@pytest.mark.parametrize("value", VALUES, ids=lambda v: repr(v)[:34])
def test_dumps_is_parseable_and_lossless(shim, value):
    assert stdlib_json.loads(shim.dumps(value)) == value


@pytest.mark.parametrize("value", VALUES, ids=lambda v: repr(v)[:34])
def test_loads_matches_stdlib(shim, value):
    assert shim.loads(stdlib_json.dumps(value)) == value


@pytest.mark.parametrize("text", [
    '{"a":1e3}', '{"a":1E-3}', '[1,2,3]', '"\\u00e9"', '  {"k" : [ ] } ',
    '-0.5', 'null', 'true', '[{"nested":[{"deep":true}]}]', '"\\/slash"',
])
def test_parser_matches_stdlib(shim, text):
    assert shim.loads(text) == stdlib_json.loads(text)


@pytest.mark.parametrize("text", [
    '{"a":1}extra', '{', '[1,', '"unterminated', '{"a" 1}', '', '{"a":}',
    '[1 2]', '"\\q"',
])
def test_malformed_input_is_rejected(shim, text):
    """Silently accepting junk is worse than failing: the extension would
    return a plausible-looking wrong answer."""
    with pytest.raises(ValueError):
        shim.loads(text)


def test_unserializable_types_raise(shim):
    """Matches the host-side serializer: refuse rather than coerce."""
    with pytest.raises(TypeError):
        shim.dumps({1, 2, 3})
    with pytest.raises(TypeError):
        shim.dumps(object())


def test_non_finite_floats_raise(shim):
    """JSON has no Infinity/NaN; stdlib emits them, which no parser accepts."""
    for value in (float("inf"), float("-inf"), float("nan")):
        with pytest.raises(ValueError):
            shim.dumps(value)


def test_shim_is_registered_as_the_json_module(shim):
    """``import json`` inside a ported extension has to keep working."""
    assert hasattr(shim, "dumps") and hasattr(shim, "loads")
    assert shim.JSONDecodeError is ValueError


def test_real_json_is_preferred_when_available():
    """Host-side (and any future sandbox that gains json) uses the real one."""
    assert ggg_sdk.json is stdlib_json
