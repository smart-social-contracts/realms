"""The call origin must reach every verb dispatched on behalf of a sandbox.

Cedar's guardrails in ``core/cedar/guardrails.cedar`` key on
``context.extension`` to tell a sandboxed extension apart from host code. Both
arrive as the same principal, so a call that loses its origin along the way is
indistinguishable from host code and **passes** guardrails G1 and G2.

That is a fail-open, which is why this is a test rather than a convention. Two
things are checked: that the sanctioned dispatch path carries the origin and
cleans up after itself, and that no new call site quietly bypasses it.
"""

import os
import re
import sys

import pytest

BACKEND = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src",
    "realm_backend",
)
sys.path.insert(0, BACKEND)

from core import call_origin  # noqa: E402


@pytest.fixture(autouse=True)
def clean_origin():
    """No test may leak an origin into the next one."""
    yield
    assert call_origin.current() == {}, "a test leaked a call origin"


class TestAmbientOrigin:
    def test_host_code_has_no_origin(self):
        # The correct reading for host code: nothing to declare, so the
        # guardrails that key on an extension simply do not apply.
        assert call_origin.current() == {}

    def test_origin_is_visible_inside_the_block(self):
        with call_origin.extension_call("procurement"):
            assert call_origin.current() == {"extension": "procurement"}

    def test_origin_is_cleared_on_the_way_out(self):
        with call_origin.extension_call("procurement"):
            pass
        assert call_origin.current() == {}

    def test_origin_is_cleared_even_when_the_body_raises(self):
        # A verb that refuses must not leave the next call wearing its origin.
        with pytest.raises(PermissionError):
            with call_origin.extension_call("procurement"):
                raise PermissionError("denied")
        assert call_origin.current() == {}

    def test_nested_origins_restore_the_outer_one(self):
        with call_origin.extension_call("outer"):
            with call_origin.codex_call("inner"):
                assert call_origin.current() == {"codex": "inner"}
            assert call_origin.current() == {"extension": "outer"}

    def test_empty_identifier_is_not_an_origin(self):
        # An empty ext_id would produce `context.extension == ""`, which reads
        # as present to a policy while identifying nobody.
        with call_origin.origin(extension=""):
            assert call_origin.current() == {}


class TestDispatch:
    def test_verb_sees_the_origin(self):
        seen = {}

        def verb(**kwargs):
            seen.update(call_origin.current())
            return "ok"

        result = call_origin.dispatch(
            {"thing.do": verb}, "thing.do", call_origin.extension_call("procurement")
        )
        assert result == "ok"
        assert seen == {"extension": "procurement"}

    def test_kwargs_are_passed_through(self):
        registry = {"thing.do": lambda **kw: kw}
        out = call_origin.dispatch(
            registry, "thing.do", call_origin.extension_call("x"), a=1, caller="bob"
        )
        assert out == {"a": 1, "caller": "bob"}

    def test_origin_is_required_not_optional(self):
        # The whole point: forgetting it is a TypeError, not a silent
        # fail-open where the call reads as host code.
        with pytest.raises(TypeError):
            call_origin.dispatch({"thing.do": lambda **kw: None}, "thing.do")

    def test_unknown_action_still_clears_the_origin(self):
        with pytest.raises(KeyError):
            call_origin.dispatch({}, "nope", call_origin.extension_call("x"))
        assert call_origin.current() == {}


class TestNoBypass:
    """Catch a *future* dispatch site that indexes a verb registry directly.

    A regex over source is crude, but the failure it guards against is silent
    and security-relevant, and it costs nothing to keep honest.
    """

    # `VERBS[...](` — indexing a registry and calling it in one expression.
    DIRECT_CALL = re.compile(r"\bVERBS\s*\[[^\]]+\]\s*\(")

    def _production_sources(self):
        for root, dirs, files in os.walk(os.path.join(BACKEND, "core")):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in sorted(files):
                if name.endswith(".py"):
                    path = os.path.join(root, name)
                    with open(path, encoding="utf-8") as fh:
                        yield os.path.relpath(path, BACKEND), fh.read()

    def test_no_verb_registry_is_invoked_outside_dispatch(self):
        offenders = []
        for relpath, source in self._production_sources():
            for match in self.DIRECT_CALL.finditer(source):
                line = source[: match.start()].count("\n") + 1
                offenders.append(f"{relpath}:{line}")
        assert not offenders, (
            "these invoke a verb registry directly, so the call origin never "
            "reaches Cedar and guardrails keyed on context.extension pass "
            "silently. Route them through core.call_origin.dispatch:\n  "
            + "\n  ".join(offenders)
        )

    def test_the_detector_actually_detects(self):
        # A guard that cannot fail is not a guard.
        assert self.DIRECT_CALL.search("result = VERBS[action](**kwargs)")
        assert not self.DIRECT_CALL.search(
            "result = dispatch(VERBS, action, extension_call(ext_id), **kwargs)"
        )
