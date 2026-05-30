"""Unit tests for the pluggable crypto-scope authorization registry.

These run in plain CPython with no canister / ggg dependency: the module
under test takes an injected ScopeAuthContext, so we pass a fake one. We load
the module by file path to avoid colliding with other backends' ``core``
package on sys.path.
"""

import importlib.util
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "realm_backend"
    / "core"
    / "crypto_scopes.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("_crypto_scopes_under_test", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


cs = _load()


class FakeCtx:
    def __init__(self, admins=None, heads=None):
        self.admins = set(admins or [])
        self.heads = dict(heads or {})

    def is_realm_admin(self, caller):
        return caller in self.admins

    def is_department_head(self, department, caller):
        return self.heads.get(department) == caller


CTX = FakeCtx(admins={"admin1"}, heads={"Finance": "head1"})


class TestScopeBuilders:
    def test_user_scope_default_name(self):
        assert cs.user_scope("alice") == "user:alice:private"

    def test_user_scope_custom_name(self):
        assert cs.user_scope("alice", "kyc") == "user:alice:kyc"

    def test_dept_scope(self):
        assert cs.dept_scope("Finance", "reports") == "dept:Finance:reports"

    def test_realm_scope(self):
        assert cs.realm_scope("treasury") == "realm:treasury"

    def test_registered_kinds(self):
        assert cs.registered_scope_kinds() == ["dept", "realm", "user"]


class TestUserScopeAuth:
    def test_owner_can_manage(self):
        assert cs.caller_can_manage_scope(cs.user_scope("alice"), "alice", CTX) is True

    def test_non_owner_cannot(self):
        assert cs.caller_can_manage_scope(cs.user_scope("alice"), "bob", CTX) is False

    def test_admin_cannot_manage_someones_user_scope(self):
        # Realm admins are NOT implicitly owners of a member's personal scope.
        assert cs.caller_can_manage_scope(cs.user_scope("alice"), "admin1", CTX) is False

    def test_bare_user_scope_without_name_denied(self):
        assert cs.caller_can_manage_scope("user:alice", "alice", CTX) is False


class TestDeptScopeAuth:
    def test_department_head_can_manage(self):
        assert (
            cs.caller_can_manage_scope(cs.dept_scope("Finance", "reports"), "head1", CTX)
            is True
        )

    def test_realm_admin_can_manage(self):
        assert (
            cs.caller_can_manage_scope(cs.dept_scope("Finance", "reports"), "admin1", CTX)
            is True
        )

    def test_other_member_cannot(self):
        assert (
            cs.caller_can_manage_scope(cs.dept_scope("Finance", "reports"), "bob", CTX)
            is False
        )

    def test_head_of_other_department_cannot(self):
        assert (
            cs.caller_can_manage_scope(cs.dept_scope("Justice", "cases"), "head1", CTX)
            is False
        )


class TestRealmScopeAuth:
    def test_admin_can_manage(self):
        assert cs.caller_can_manage_scope(cs.realm_scope("treasury"), "admin1", CTX) is True

    def test_non_admin_cannot(self):
        assert cs.caller_can_manage_scope(cs.realm_scope("treasury"), "bob", CTX) is False


class TestUnknownAndMalformed:
    def test_unknown_kind_denied(self):
        assert cs.caller_can_manage_scope("widget:x:y", "admin1", CTX) is False

    def test_empty_scope_denied(self):
        assert cs.caller_can_manage_scope("", "admin1", CTX) is False

    def test_empty_caller_denied(self):
        assert cs.caller_can_manage_scope(cs.realm_scope("t"), "", CTX) is False


class TestExtensibility:
    def test_custom_scope_kind_can_be_registered(self):
        # New use cases register their own policy without touching call sites.
        @cs.scope_kind("project")
        def _manage_project(parts, caller, ctx):
            # project:<name>:<...> — only realm admins, for the test.
            return len(parts) >= 3 and ctx.is_realm_admin(caller)

        try:
            assert cs.caller_can_manage_scope("project:apollo:plan", "admin1", CTX) is True
            assert cs.caller_can_manage_scope("project:apollo:plan", "bob", CTX) is False
        finally:
            cs._MANAGERS.pop("project", None)
