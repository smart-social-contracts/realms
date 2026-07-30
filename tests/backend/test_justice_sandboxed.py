"""The real ported ``justice_litigation`` extension, executed in a sandbox (#272).

``test_justice_bridge.py`` covers the host side. This covers the other half: that
the extension as shipped runs under the sandbox loader, reaches the host only
through ``rpc``, and asks for nothing it did not declare.

The failure this is really here to catch is a forwarded identity. The in-process
version took ``plaintiff_id``, ``judge_id``, ``appellant_id`` and ``executor_id``
off the request; the host now derives all four from the caller, so any of them
still being passed along would be a parameter the host is right to ignore but the
extension is wrong to send.
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

EXT_ID = "justice_litigation"
EXT_DIR = REPO_ROOT / "extensions" / "extensions" / EXT_ID
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

    Installed layout is ``<dir>/<ext_id>/entry.py``; in the repo it sits under
    ``<ext_id>/backend/``. A symlink gives the loader the shape it expects without
    copying the file it is meant to be reading.
    """
    import core.runtime_extensions as rex

    root = Path(tempfile.mkdtemp())
    (root / EXT_ID).symlink_to(EXT_DIR / "backend")
    monkeypatch.setattr(rex, "EXTENSIONS_DIR", str(root))
    return root


def _spawn(rpc):
    """Execute the shipped ``entry.py`` as the subinterpreter would, with *rpc*.

    ``rpc`` reaches extension code through ``ggg_sdk``'s globals — on a canister
    Basilisk injects it as a builtin, and the module object the loader builds is
    the equivalent seam here.
    """
    host_sdk = sys.modules.get("ggg_sdk")
    try:
        source = rs._build_codex_sandbox_source(
            rs._extension_source(EXT_ID),
            rs._extension_package_modules(EXT_ID),
        )
    finally:
        if host_sdk is not None:
            sys.modules["ggg_sdk"] = host_sdk
    namespace = {}
    exec(compile(source, f"<sandbox:{EXT_ID}>", "exec"), namespace)
    namespace["_ggg_sdk"].__dict__["rpc"] = rpc
    return namespace


@pytest.fixture
def sandbox(installed):
    """The shipped ``entry.py``, spawned with a recording ``rpc``."""
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


# ---------------------------------------------------------------------------
# It loads at all
# ---------------------------------------------------------------------------


def test_the_extension_spawns_with_no_host_imports(sandbox):
    """The old module body imported ``ggg``, ``core.crypto_scopes`` and
    ``core.numbers``. A subinterpreter has ``sys.path == []``, so anything left
    behind fails here at spawn rather than on a live realm."""
    assert sandbox.call("get_my_roles")["success"] is True


def test_the_backend_is_a_single_module(installed):
    """1754 lines of domain logic moved host-side into ``core.justice``. A new
    sibling file here would be sandboxed code doing domain work again."""
    assert rs._extension_package_modules(EXT_ID) == []


def test_the_module_is_a_thin_shell():
    """Not a line count for its own sake: anything much bigger than argument
    shaping means a decision is being made on the wrong side of the boundary."""
    lines = (EXT_DIR / "backend" / "entry.py").read_text().splitlines()
    code = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    assert len(code) < 300, f"{len(code)} lines of code in a shell"


# ---------------------------------------------------------------------------
# Every call goes through a declared verb
# ---------------------------------------------------------------------------


ENTRY_POINTS = [
    ("get_my_roles", {}, "justice.roles"),
    ("get_justice_audience", {}, "justice.audience"),
    ("initialize", {}, "justice.initialize"),
    ("get_justice_systems", {}, "justice.justice_systems"),
    ("get_courts", {}, "justice.courts"),
    ("create_court", {"name": "High Court"}, "justice.create_court"),
    ("seed_default_courts", {}, "justice.seed_courts"),
    ("get_judges", {}, "justice.judges"),
    ("get_cases", {}, "justice.cases"),
    ("get_case", {"case_id": "1"}, "justice.case"),
    ("file_case", {"court_id": "c1", "defendant_id": "d1", "title": "x"},
     "justice.file_case"),
    ("assign_judge", {"case_id": "1", "judge_id": "j1"}, "justice.assign_judge"),
    ("get_litigations", {}, "justice.litigations"),
    ("create_litigation", {"defendant_principal": "d1"},
     "justice.create_litigation"),
    ("set_litigation_content", {"case_id": "1", "ciphertext": "enc:v=2:x"},
     "justice.set_litigation_content"),
    ("get_verdicts", {}, "justice.verdicts"),
    ("issue_verdict", {"case_id": "1", "decision": "dismissed"},
     "justice.issue_verdict"),
    ("get_penalties", {}, "justice.penalties"),
    ("execute_penalty", {"penalty_id": "p1"}, "justice.execute_penalty"),
    ("waive_penalty", {"penalty_id": "p1"}, "justice.waive_penalty"),
    ("get_appeals", {}, "justice.appeals"),
    ("file_appeal", {"case_id": "1", "grounds": "unfair"}, "justice.file_appeal"),
    ("decide_appeal", {"appeal_id": "a1", "decision": "upheld"},
     "justice.decide_appeal"),
    ("get_statistics", {}, "justice.statistics"),
]


@pytest.mark.parametrize("function_name,params,verb", ENTRY_POINTS)
def test_each_entry_point_calls_its_verb(sandbox, function_name, params, verb):
    result = sandbox.call(function_name, **params)
    assert result["success"] is True, result
    assert sandbox.verbs_used() == [verb]


def test_the_manifest_declares_exactly_the_verbs_reached():
    """A capability nobody calls is authority granted for no reason; one that is
    called but undeclared is refused on a live realm."""
    assert set(MANIFEST["capabilities"]) == {verb for _, _, verb in ENTRY_POINTS}


def test_the_manifest_declares_exactly_the_entry_points_defined():
    declared = set(MANIFEST["entry_points"])
    defined = _public_functions()
    assert declared == defined, (
        f"manifest-only: {declared - defined}, code-only: {defined - declared}"
    )


def test_every_entry_point_is_covered():
    """Guards against a new function arriving without a case above, which would
    let an undeclared verb through unnoticed."""
    covered = {name for name, _, _ in ENTRY_POINTS}
    assert _public_functions() - covered == set()


def _public_functions():
    source = (EXT_DIR / "backend" / "entry.py").read_text()
    return {
        line.split("(")[0].removeprefix("def ").strip()
        for line in source.splitlines()
        if line.startswith("def ") and not line.startswith("def _")
    }


# ---------------------------------------------------------------------------
# What crosses the boundary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("function_name,params,forged", [
    ("file_case", {"court_id": "c1", "defendant_id": "d1", "title": "x"},
     "plaintiff_id"),
    ("create_litigation", {"defendant_principal": "d1"}, "requester_principal"),
    ("issue_verdict", {"case_id": "1", "decision": "dismissed"}, "judge_id"),
    ("file_appeal", {"case_id": "1", "grounds": "unfair"}, "appellant_id"),
    ("execute_penalty", {"penalty_id": "p1"}, "executor_id"),
    ("waive_penalty", {"penalty_id": "p1"}, "waived_by"),
    ("decide_appeal", {"appeal_id": "a1", "decision": "upheld"}, "decided_by"),
])
def test_a_forged_identity_is_not_forwarded(sandbox, function_name, params, forged):
    """Each of these was a real parameter in the in-process version. The host
    derives them from the caller now, and the extension must not pass them on —
    a forwarded value that the host happens to ignore is one refactor away from
    being trusted again."""
    sandbox.call(function_name, **params, **{forged: "someone_else"})
    assert forged not in sandbox.last_params()


def test_no_plaintext_is_sent_when_opening_a_litigation(sandbox):
    """The title and description are encrypted client-side; the canister must not
    receive them even by accident."""
    sandbox.call(
        "create_litigation", defendant_principal="d1",
        title="my dispute", description="the details",
    )
    params = sandbox.last_params()
    assert "title" not in params and "description" not in params


def test_ciphertext_is_attached_in_its_own_call(sandbox):
    sandbox.call("set_litigation_content", case_id="1", ciphertext="enc:v=2:blob")
    verb, params = sandbox.calls[-1]
    assert verb == "justice.set_litigation_content"
    assert params == {"case_id": "1", "ciphertext": "enc:v=2:blob"}


def test_an_omitted_litigation_field_is_not_sent(sandbox):
    """The host reads an absent key as "not specified" and falls back to a
    default court and an individual defendant."""
    sandbox.call("create_litigation", defendant_principal="d1")
    assert sandbox.last_params() == {"defendant_principal": "d1"}


def test_a_legacy_defendant_id_still_works(sandbox):
    """The frontend sent ``defendant_id`` before the department-defendant work;
    accepted as an alias so an older bundle keeps filing."""
    sandbox.call("create_litigation", defendant_id="d1")
    assert sandbox.last_params() == {"defendant_principal": "d1"}


# The two shapes ``JusticeLitigation.svelte`` actually sends. Pinned because the
# frontend and the extension version independently, and a renamed key here is a
# silent failure to file rather than an error anyone sees.


def test_the_frontend_shape_for_an_individual_defendant(sandbox):
    sandbox.call(
        "create_litigation", defendant_kind="user",
        defendant_principal="d1", court_id="court1",
    )
    assert sandbox.last_params() == {
        "defendant_kind": "user", "defendant_principal": "d1",
        "court_id": "court1",
    }


def test_the_frontend_shape_for_a_department_defendant(sandbox):
    sandbox.call(
        "create_litigation", defendant_kind="department",
        defendant_department="Sanitation", defendant_department_id="7",
    )
    assert sandbox.last_params() == {
        "defendant_kind": "department", "defendant_department": "Sanitation",
        "defendant_department_id": "7",
    }


def test_the_frontend_may_name_the_case_id_id(sandbox):
    """``create_litigation`` returns ``id``, and the frontend passes it straight
    back to ``set_litigation_content`` under that name."""
    sandbox.call("set_litigation_content", id="1", ciphertext="enc:v=2:blob")
    assert sandbox.last_params() == {"case_id": "1", "ciphertext": "enc:v=2:blob"}


def test_a_host_refusal_becomes_a_failed_response(installed):
    """The frontend reads ``{"success": false, "error": ...}``, and a refused verb
    is a normal answer — a member who is not a judge opening the verdict form is
    UI state, not a fault."""
    def refuse(verb, **params):
        raise PermissionError("Caller is not a judge assigned to case 1")

    namespace = _spawn(refuse)
    result = json.loads(namespace["issue_verdict"](
        json.dumps({"case_id": "1", "decision": "dismissed"})
    ))
    assert result["success"] is False
    assert "not a judge" in result["error"]


def test_only_plain_data_crosses(sandbox):
    """Everything sent must survive a JSON round trip — the boundary rejects live
    objects, and a silent ``str()`` of one would be worse than a refusal."""
    sandbox.call(
        "issue_verdict", case_id="1", decision="for the plaintiff",
        penalties=[{"type": "fine", "amount": 100.5, "target_user_id": "d1"}],
    )
    _, params = sandbox.calls[-1]
    assert json.loads(json.dumps(params)) == params


def test_malformed_arguments_are_a_failed_response_not_a_crash(installed):
    """Arguments arrive as a JSON string from the canister entry point, so a
    truncated body is a client error rather than a trap."""
    namespace = _spawn(lambda verb, **params: {})
    result = json.loads(namespace["get_cases"]("{not json"))
    assert result["success"] is False
