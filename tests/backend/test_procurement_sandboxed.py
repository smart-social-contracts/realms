"""The real ported ``procurement`` extension, executed in a sandbox (issue #276).

The verb tests in ``test_procurement_bridge.py`` cover the host side of the port.
This covers the other half: that the extension as shipped actually runs under the
sandbox loader, reaches the host only through ``rpc``, and asks for nothing it did
not declare.

Two failures this is here to catch:

* A leftover host import. ``entry.py`` used to ``from ggg import User`` and
  ``from core.crypto_scopes import ...``; a subinterpreter has ``sys.path == []``,
  so anything left behind fails at spawn rather than in review.
* Drift between the code and the manifest. Every verb the module reaches for has
  to be in ``capabilities``, or it will be refused on a live realm — which is a
  runtime error in production and a diff in the manifest here.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "realm_backend"))
sys.modules.setdefault("_cdk", MagicMock())

from core import runtime_sandbox as rs  # noqa: E402

EXT_DIR = REPO_ROOT / "extensions" / "extensions" / "procurement"
MANIFEST = json.loads((EXT_DIR / "manifest.json").read_text())


@pytest.fixture(autouse=True)
def keep_host_modules():
    """The loader registers its own ``ggg_sdk`` in ``sys.modules``. In a real
    subinterpreter that table is private; here it is this process's."""
    names = ("ggg_sdk", rs.SANDBOX_PACKAGE)
    saved = {n: sys.modules.get(n) for n in names}
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is not None:
                sys.modules[name] = value
            else:
                sys.modules.pop(name, None)


@pytest.fixture
def installed(monkeypatch):
    """Point the loader at the shipped sources.

    Installed layout is ``<dir>/<ext_id>/entry.py``; in the repo they sit under
    ``<ext_id>/backend/``. A symlink gives the loader the shape it expects without
    copying the file it is meant to be reading.
    """
    import core.runtime_extensions as rex

    root = Path(tempfile.mkdtemp())
    (root / "procurement").symlink_to(EXT_DIR / "backend")
    monkeypatch.setattr(rex, "EXTENSIONS_DIR", str(root))
    return root


@pytest.fixture
def sandbox(installed):
    """The shipped ``entry.py``, spawned with a recording ``rpc``.

    The returned object exposes the extension's functions and the verbs they
    asked for, which is what the declaration checks read.
    """
    recorded = []
    namespace = _spawn(lambda verb, **params: recorded.append((verb, params)) or {})

    class Sandbox:
        def __init__(self):
            self.calls = recorded

        def call(self, function_name, **params):
            return json.loads(namespace[function_name](json.dumps(params)))

        def last_params(self):
            return self.calls[-1][1]

        def verbs_used(self):
            return [verb for verb, _ in self.calls]

    return Sandbox()


def _spawn(rpc):
    """Execute the shipped ``entry.py`` as the subinterpreter would, with *rpc*.

    ``rpc`` reaches extension code through ``ggg_sdk``'s globals — on a canister
    Basilisk injects it as a builtin, and the module object the loader builds is
    the equivalent seam here.

    Call at most once per test: the exec leaves the sandbox's own ``ggg_sdk`` in
    ``sys.modules``, and ``keep_host_modules`` puts the host's back afterwards.
    """
    source = rs._build_codex_sandbox_source(
        rs._extension_source("procurement"),
        rs._extension_package_modules("procurement"),
    )
    namespace = {}
    exec(compile(source, "<sandbox:procurement>", "exec"), namespace)
    namespace["_ggg_sdk"].__dict__["rpc"] = rpc
    return namespace


# ---------------------------------------------------------------------------
# It loads at all
# ---------------------------------------------------------------------------


def test_the_extension_spawns_with_no_host_imports(sandbox):
    """If any ``ggg`` / ``core`` / ``_cdk`` import were left in the module body,
    the spawn above would already have raised."""
    assert sandbox.call("health")["success"] is True


def test_the_backend_is_a_single_module_now(installed):
    """The six domain modules moved host-side, so there is nothing left to bundle.
    Kept as an assertion because a new sibling file would be sandboxed code doing
    domain work again."""
    assert rs._extension_package_modules("procurement") == []


def test_health_needs_no_host_call(sandbox):
    sandbox.call("health")
    assert sandbox.verbs_used() == []


# ---------------------------------------------------------------------------
# Every call goes through a declared verb
# ---------------------------------------------------------------------------


ENTRY_POINTS = [
    ("list_rfps", {}, "procurement.rfp_list"),
    ("get_rfp", {"rfp_id": "rfp_001"}, "procurement.rfp_get"),
    ("get_rfp_transitions", {"rfp_id": "rfp_001"}, "procurement.transitions"),
    ("create_rfp", {"title": "x", "rubric_json": "[]"}, "procurement.rfp_create"),
    ("update_rfp", {"rfp_id": "rfp_001", "title": "y"}, "procurement.rfp_update"),
    ("publish_rfp", {"rfp_id": "rfp_001"}, "procurement.rfp_publish"),
    ("close_rfp", {"rfp_id": "rfp_001"}, "procurement.rfp_close"),
    ("demo_advance_rfp", {"rfp_id": "rfp_001"}, "procurement.demo_advance"),
    ("create_bid_shell", {"rfp_id": "rfp_001"}, "procurement.bid_create"),
    ("set_bid_payload", {"bid_id": "b1", "ciphertext": "c"},
     "procurement.bid_set_payload"),
    ("list_bids", {"rfp_id": "rfp_001"}, "procurement.bid_list"),
    ("get_bid_payload", {"bid_id": "b1"}, "procurement.bid_payload"),
    ("get_evaluator_principals", {}, "procurement.evaluators"),
    ("submit_scores", {"bid_id": "b1", "scores": {"price": 5}},
     "procurement.scores_submit"),
    ("compute_totals", {"rfp_id": "rfp_001"}, "procurement.totals_compute"),
    ("list_scores", {"rfp_id": "rfp_001"}, "procurement.score_list"),
    ("award_rfp", {"rfp_id": "rfp_001", "winning_bid_id": "b1"},
     "procurement.award"),
    ("execute_contract", {"rfp_id": "rfp_001"}, "procurement.execute"),
    ("flag_vendor", {"vendor_id": "v1", "code": "late"},
     "procurement.vendor_flag"),
    ("get_vendor_record", {"vendor_id": "v1"}, "procurement.vendor_get"),
    ("list_vendor_records", {}, "procurement.vendor_list"),
    ("get_my_roles", {}, "procurement.roles"),
    ("async_task", {}, "procurement.sweep"),
]


@pytest.mark.parametrize("function_name,params,verb", ENTRY_POINTS)
def test_each_entry_point_calls_its_verb(sandbox, function_name, params, verb):
    result = sandbox.call(function_name, **params)
    assert result["success"] is True, result
    assert sandbox.verbs_used() == [verb]


@pytest.mark.parametrize("function_name,params,verb", ENTRY_POINTS)
def test_each_verb_is_declared_in_the_manifest(function_name, params, verb):
    assert verb in MANIFEST["capabilities"]


def test_the_manifest_declares_nothing_unused():
    """A capability nobody calls is authority granted for no reason."""
    reached = {verb for _, _, verb in ENTRY_POINTS}
    assert set(MANIFEST["capabilities"]) == reached


def test_every_entry_point_is_covered():
    """Guards against a new function being added without a case above, which
    would let an undeclared verb through unnoticed."""
    source = (EXT_DIR / "backend" / "entry.py").read_text()
    defined = {
        line.split("(")[0].removeprefix("def ").strip()
        for line in source.splitlines() if line.startswith("def ")
    }
    public = {n for n in defined if not n.startswith("_")}
    covered = {name for name, _, _ in ENTRY_POINTS} | {"health"}
    assert public - covered == set(), f"uncovered entry points: {public - covered}"


# ---------------------------------------------------------------------------
# What crosses the boundary
# ---------------------------------------------------------------------------


def test_identity_is_never_sent(sandbox):
    """The extension has no principal to send and must not invent one. A caller
    who puts ``vendor_id`` in the request must not have it forwarded."""
    sandbox.call("create_bid_shell", rfp_id="rfp_001", vendor_id="someone_else")
    assert sandbox.last_params() == {"rfp_id": "rfp_001"}


def test_an_omitted_edit_field_is_not_sent(sandbox):
    """``rfp_update`` treats an absent key as "leave alone", so sending defaults
    would blank the fields the caller did not touch."""
    sandbox.call("update_rfp", rfp_id="rfp_001", description="revised")
    assert sandbox.last_params()["fields"] == {"description": "revised"}


def test_a_host_refusal_becomes_a_failed_response(installed):
    """The frontend has always read ``{"success": false, "error": ...}``, and a
    refused verb is a normal answer — an evaluator clicking award is UI state."""
    def refuse(verb, **params):
        raise PermissionError("Approver role required")

    namespace = _spawn(refuse)
    result = json.loads(namespace["award_rfp"](
        json.dumps({"rfp_id": "rfp_001", "winning_bid_id": "b1"})
    ))
    assert result["success"] is False
    assert "Approver role" in result["error"]


def test_only_plain_data_crosses(sandbox):
    """Everything sent must survive a JSON round trip — the boundary rejects live
    objects, and a silent ``str()`` of one would be worse than a refusal."""
    sandbox.call("submit_scores", bid_id="b1", scores={"price": 5.5})
    verb, params = sandbox.calls[-1]
    assert json.loads(json.dumps(params)) == params
