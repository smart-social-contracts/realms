"""Unit tests for the install-time marketplace approval gate (issue #267).

Covers api/file_registry.py:
  - _trust_policy: what the realm requires and whose approvals it honours
  - _check_marketplace_approval: the refusal decision itself

The gate is the thing standing between a realm and unreviewed code, so the
cases that matter most here are the ones where it must say no: content that
changed after review, an approval from someone the realm does not trust, and
a registry that cannot answer the question at all.
"""

import json
import sys
import types
from pathlib import Path

import pytest

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))


# ---------------------------------------------------------------------------
# _cdk stub
#
# A MagicMock will not do: api/file_registry.py subclasses Service and
# subscripts Opt/Async at import time, so these have to be real objects.
# ---------------------------------------------------------------------------


def _build_cdk_stub():
    cdk = types.ModuleType("_cdk")

    class _Subscriptable:
        def __class_getitem__(cls, item):
            return cls

    class Service:
        def __init__(self, principal=None):
            self.principal = principal

    class Record:
        pass

    class Principal:
        def __init__(self, text_value=""):
            self.text_value = text_value

        @staticmethod
        def from_str(value):
            return Principal(value)

        def to_str(self):
            return self.text_value

    def _identity_decorator(fn):
        return fn

    class _IC:
        @staticmethod
        def caller():
            return Principal("test-caller")

        @staticmethod
        def id():
            return Principal("self-cai")

        @staticmethod
        def time():
            return 1_000_000

    cdk.Async = _Subscriptable
    cdk.CallResult = _Subscriptable
    cdk.Opt = _Subscriptable
    cdk.Vec = _Subscriptable
    cdk.Principal = Principal
    cdk.Record = Record
    cdk.Service = Service
    cdk.blob = bytes
    cdk.text = str
    cdk.void = None
    cdk.nat = int
    cdk.ic = _IC
    cdk.service_query = _identity_decorator
    cdk.service_update = _identity_decorator

    # Importing api.file_registry pulls in api/__init__, and so every sibling
    # api module and the candid type declarations they use. Rather than
    # enumerate the whole CDK surface, hand back a benign subscriptable type
    # for anything not modelled above (PEP 562 module __getattr__).
    cdk.__getattr__ = lambda name: _Subscriptable

    return cdk


def _load_file_registry_module():
    """Load api/file_registry.py on its own, against a throwaway _cdk.

    Importing it as ``api.file_registry`` would run ``api/__init__``, which
    pulls in every sibling module and the whole ggg entity graph. The module
    under test only needs _cdk and a logger, and it imports ggg lazily inside
    the functions — which is exactly where the tests want to substitute it.

    The _cdk stub is removed again afterwards: sibling test modules install
    their own (a MagicMock, via setdefault) and would otherwise inherit this
    one and fail on the CDK surface it does not model.
    """
    import importlib.util

    previous = sys.modules.get("_cdk")
    sys.modules["_cdk"] = _build_cdk_stub()
    try:
        path = src_path / "api" / "file_registry.py"
        spec = importlib.util.spec_from_file_location("realm_api_file_registry", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is None:
            sys.modules.pop("_cdk", None)
        else:
            sys.modules["_cdk"] = previous


fr = _load_file_registry_module()


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

MARKETPLACE = "l5qpy-wqaaa-aaaah-qu2mq-cai"
OTHER_APPROVER = "aaaaa-bbbbb-ccccc-ddddd-cai"


class FakeRealm:
    """Stands in for the single ggg.Realm row the policy is read from."""

    _rows = []
    _explode = False

    def __init__(self, **kwargs):
        self.require_marketplace_approval = kwargs.get(
            "require_marketplace_approval", True
        )
        self.trusted_approvers = kwargs.get("trusted_approvers", "")
        self.marketplace_canister_id = kwargs.get(
            "marketplace_canister_id", MARKETPLACE
        )

    @classmethod
    def instances(cls):
        if cls._explode:
            raise RuntimeError("database unavailable")
        return list(cls._rows)


@pytest.fixture(autouse=True)
def ggg_module():
    """Expose FakeRealm as `ggg.Realm`, which _trust_policy imports lazily."""
    module = types.ModuleType("ggg")
    module.Realm = FakeRealm
    sys.modules["ggg"] = module
    FakeRealm._rows = [FakeRealm()]
    FakeRealm._explode = False
    yield module
    sys.modules.pop("ggg", None)


def set_policy(**kwargs):
    FakeRealm._rows = [FakeRealm(**kwargs)]


class FakeRegistry:
    """Records the namespaces the gate asked about."""

    def __init__(self):
        self.asked = []

    def get_namespace_approval_icc(self, namespace):
        self.asked.append(namespace)
        return ("call", namespace)


def run_async(generator, responses):
    """Drive a basilisk Async generator, feeding it canned ICC responses."""
    pending = list(responses)
    to_send = None
    while True:
        try:
            generator.send(to_send)
        except StopIteration as stop:
            return stop.value
        assert pending, "generator made more calls than the test provided answers for"
        to_send = pending.pop(0)


def check(namespace="ext/voting/1.0.0", responses=()):
    registry = FakeRegistry()
    verdict = run_async(fr._check_marketplace_approval(registry, namespace), responses)
    return verdict, registry


def approval(**overrides):
    payload = {
        "namespace": "ext/voting/1.0.0",
        "approved": True,
        "status": "approved",
        "approver": MARKETPLACE,
        "content_matches": True,
        "file_count": 3,
    }
    payload.update(overrides)
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# _trust_policy
# ---------------------------------------------------------------------------


def test_default_policy_enforces_and_trusts_the_configured_marketplace():
    require, trusted = fr._trust_policy()
    assert require is True
    assert trusted == [MARKETPLACE]


def test_explicit_trusted_approvers_replace_the_marketplace_default():
    set_policy(trusted_approvers=f"{OTHER_APPROVER}, {MARKETPLACE}")
    require, trusted = fr._trust_policy()
    assert require is True
    assert trusted == [OTHER_APPROVER, MARKETPLACE]


def test_policy_can_be_switched_off():
    set_policy(require_marketplace_approval=False)
    require, _ = fr._trust_policy()
    assert require is False


def test_unreadable_policy_enforces():
    # Not being able to read the policy is not evidence that the realm opted
    # out of it.
    FakeRealm._explode = True
    require, trusted = fr._trust_policy()
    assert require is True
    assert trusted == []


def test_realm_without_a_row_enforces():
    FakeRealm._rows = []
    require, trusted = fr._trust_policy()
    assert require is True
    assert trusted == []


# ---------------------------------------------------------------------------
# The gate: allowed
# ---------------------------------------------------------------------------


def test_approved_by_the_trusted_marketplace_is_allowed():
    verdict, registry = check(responses=[approval()])
    assert verdict == ""
    assert registry.asked == ["ext/voting/1.0.0"]


def test_enforcement_off_skips_the_check_entirely():
    set_policy(require_marketplace_approval=False)
    verdict, registry = check(responses=[])
    assert verdict == ""
    # No point paying for an inter-canister call whose answer is ignored.
    assert registry.asked == []


def test_approver_on_the_explicit_trust_list_is_allowed():
    set_policy(trusted_approvers=OTHER_APPROVER)
    verdict, _ = check(responses=[approval(approver=OTHER_APPROVER)])
    assert verdict == ""


# ---------------------------------------------------------------------------
# The gate: refused
# ---------------------------------------------------------------------------


def test_unapproved_content_is_refused():
    verdict, _ = check(
        responses=[
            json.dumps(
                {
                    "namespace": "ext/voting/1.0.0",
                    "approved": False,
                    "status": "unapproved",
                }
            )
        ]
    )
    assert "has not been approved" in verdict
    assert "unapproved" in verdict


def test_rejected_content_is_refused_and_says_so():
    verdict, _ = check(responses=[approval(approved=False, status="rejected")])
    assert "has not been approved" in verdict
    assert "rejected" in verdict


def test_content_changed_after_approval_is_refused():
    # The approve-then-swap case: the registry still holds a decision, but not
    # for these bytes.
    verdict, _ = check(responses=[approval(approved=False, content_matches=False)])
    assert "files have changed since" in verdict


def test_approval_by_an_untrusted_principal_is_refused():
    verdict, _ = check(responses=[approval(approver=OTHER_APPROVER)])
    assert "does not trust" in verdict
    assert OTHER_APPROVER in verdict


def test_approval_is_refused_when_the_realm_trusts_nobody():
    set_policy(marketplace_canister_id="")
    verdict, _ = check(responses=[approval()])
    assert "trusts no approver" in verdict


def test_setup_allows_approved_content_when_no_marketplace_is_configured():
    set_policy(marketplace_canister_id="")
    FakeRealm._rows[0].status = "setup"
    verdict, _ = check(responses=[approval()])
    assert verdict == ""
    assert FakeRealm._rows[0].trusted_approvers == MARKETPLACE


def test_setup_still_refuses_unapproved_content_without_a_marketplace():
    set_policy(marketplace_canister_id="")
    FakeRealm._rows[0].status = "setup"
    verdict, _ = check(
        responses=[
            json.dumps(
                {
                    "namespace": "ext/voting/1.0.0",
                    "approved": False,
                    "status": "unapproved",
                }
            )
        ]
    )
    assert "has not been approved" in verdict


def test_registry_without_approval_support_is_refused():
    # An older registry rejects the call; basilisk hands back an Err variant,
    # which is not the JSON the gate expects.
    verdict, _ = check(responses=[{"Err": "Canister has no query method"}])
    assert "did not answer" in verdict
    assert "cannot verify marketplace approval" in verdict


def test_registry_error_response_is_refused():
    verdict, _ = check(
        responses=[json.dumps({"error": "Namespace 'ext/voting/1.0.0' not found"})]
    )
    assert "cannot verify marketplace approval" in verdict
    assert "not found" in verdict


def test_nonsense_response_is_refused():
    verdict, _ = check(responses=[json.dumps(["not", "an", "object"])])
    assert "unexpected response" in verdict


def test_every_refusal_points_at_the_way_out():
    # An operator hitting this needs to know it is a policy decision they can
    # change, not a broken deployment.
    for responses in (
        [json.dumps({"approved": False, "status": "unapproved"})],
        [approval(approved=False, content_matches=False)],
        [approval(approver=OTHER_APPROVER)],
        [{"Err": "no such method"}],
    ):
        verdict, _ = check(responses=responses)
        assert "realm.configure.trust_policy" in verdict, verdict


# ---------------------------------------------------------------------------
# entity_method_overrides are refused at install time (issue #265)
# ---------------------------------------------------------------------------
#
# The mechanism let a codex replace core GGG methods with exec()'d code running
# as the host. Removing it silently would be worse than leaving it: a realm
# would install a codex, see success, and run without the governance policy the
# codex was written to enforce.


def test_a_manifest_without_overrides_installs():
    assert fr._entity_method_override_error("agora", {}) == ""
    assert fr._entity_method_override_error("agora", {"entity_method_overrides": []}) == ""


def test_declaring_an_override_refuses_the_install():
    error = fr._entity_method_override_error("legacy", {
        "entity_method_overrides": [
            {"entity": "Treasury", "method": "send",
             "implementation": "Codex.treasury_send_hook.send_hook"},
        ],
    })
    assert error
    assert "Treasury.send()" in error


def test_the_refusal_names_every_override_and_the_way_forward():
    error = fr._entity_method_override_error("legacy", {
        "entity_method_overrides": [
            {"entity": "User", "method": "user_register_posthook"},
            {"entity": "Treasury", "method": "send"},
        ],
    })
    assert "User.user_register_posthook()" in error
    assert "Treasury.send()" in error
    assert "sandboxed hooks" in error


def test_a_malformed_override_entry_still_refuses():
    # Garbage in the list is not a reason to let the install through.
    error = fr._entity_method_override_error("legacy", {
        "entity_method_overrides": ["not-an-object"],
    })
    assert error


# ---------------------------------------------------------------------------
# Legacy init.py is refused at install time (issue #265)
# ---------------------------------------------------------------------------


def test_a_package_without_init_py_is_fine(tmp_path, monkeypatch):
    from core import runtime_codex

    monkeypatch.setattr(runtime_codex, "_pkg_dir", lambda cid: str(tmp_path / cid))
    assert runtime_codex.legacy_init_py_error("agora", {"manifest.json": "{}"}) == ""
    assert runtime_codex.legacy_init_py_error("agora") == ""


def test_init_py_in_the_file_dict_refuses_install():
    from core import runtime_codex

    error = runtime_codex.legacy_init_py_error(
        "legacy", {"manifest.json": "{}", "init.py": "print('hi')"}
    )
    assert error
    assert "init.py" in error
    assert "init hook" in error


def test_nested_init_py_path_is_also_refused():
    from core import runtime_codex

    error = runtime_codex.legacy_init_py_error(
        "legacy", {"backend/init.py": "print('hi')"}
    )
    assert error


# ---------------------------------------------------------------------------
# Extension frontend resync guard
# ---------------------------------------------------------------------------


def test_copy_frontend_to_asset_canister_errors_on_empty_registry_namespace():
    original_pull = fr._pull_extension_frontend_files
    original_resolve = fr._resolve_registry_namespace
    original_frs = fr.FileRegistryService

    def fake_pull(registry, ext_id, version):
        if False:
            yield
        return {}, "1.3.9", None

    def fake_resolve(registry, category, item_id, version):
        if False:
            yield
        return "ext/public_dashboard/1.3.9", "1.3.9", None

    fr._pull_extension_frontend_files = fake_pull
    fr._resolve_registry_namespace = fake_resolve
    fr.FileRegistryService = lambda principal: object()

    try:
        err = run_async(
            fr._copy_frontend_to_asset_canister(
                "registry-id",
                "public_dashboard",
                "1.3.9",
                "frontend-id",
            ),
            [],
        )
        assert err == (
            "no frontend files found in registry namespace ext/public_dashboard/1.3.9"
        )
    finally:
        fr._pull_extension_frontend_files = original_pull
        fr._resolve_registry_namespace = original_resolve
        fr.FileRegistryService = original_frs


def test_run_codex_init_never_executes(tmp_path, monkeypatch):
    """Even a leftover call site must not exec the file."""
    from core import runtime_codex

    pkg = tmp_path / "legacy"
    pkg.mkdir()
    (pkg / "init.py").write_text("raise SystemExit('executed')")
    monkeypatch.setattr(runtime_codex, "_pkg_dir", lambda cid: str(pkg))

    error = runtime_codex.run_codex_init("legacy")
    assert error
    assert "init.py" in error
