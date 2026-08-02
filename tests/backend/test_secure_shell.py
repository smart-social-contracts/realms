"""SecureORM wiring and REPL Cedar policy tests (realms#282)."""

import os
import sys
from unittest.mock import MagicMock

import pytest

# test_access_control.py (alphabetically earlier) replaces ic_basilisk_toolkit
# and its dependency modules with MagicMocks at import time and never restores
# them. Evict mocked modules before importing toolkit or core Cedar modules.
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
for _name in ("core.cedar_authz", "core.cedar_entities", "main"):
    sys.modules.pop(_name, None)
for _name in list(sys.modules):
    if _name == "ggg" or _name.startswith("ggg."):
        del sys.modules[_name]

BACKEND = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "realm_backend"
)
sys.path.insert(0, BACKEND)

from core import cedar_authz  # noqa: E402
from core.cedar_policies import POLICIES  # noqa: E402

_main = None


def _sync_orm_engine(orm):
    """Point ORM at the current cedar_authz engine (tests reset the singleton)."""
    orm.engine = cedar_authz._get_engine()
    return orm


def _load_main():
    """Import main once with a minimal _cdk stub; safe when Database already exists."""
    global _main
    if _main is not None:
        return _main
    if "main" in sys.modules:
        _main = sys.modules["main"]
        return _main

    for _name in list(sys.modules):
        if _name == "ggg" or _name.startswith("ggg."):
            del sys.modules[_name]

    from ic_python_db import Database

    db_init = Database.init

    @classmethod
    def _database_init_if_needed(cls, *args, **kwargs):
        if cls._instance is None:
            return db_init(*args, **kwargs)
        return cls._instance

    Database.init = _database_init_if_needed
    import main as main_mod  # noqa: E402

    Database.init = db_init
    _main = main_mod
    return _main


@pytest.fixture(scope="module")
def main_module():
    mod = _load_main()
    assert mod.secure_orm is not None
    assert mod.secure_orm._shell_context == {"repl": True}
    _sync_orm_engine(mod.secure_orm)
    assert mod.secure_orm.engine is cedar_authz._get_engine()
    return mod


class FakeCedar:
    """Stands in for the native module, recording what it was asked."""

    def __init__(self, decision=True, raises=None, warnings=()):
        self.decision = decision
        self.raises = raises
        self.warnings = list(warnings)
        self.requests = []

    def load(self, schema, policies):
        if self.raises:
            raise cedar_authz.CedarError(self.raises)
        return self.warnings

    def is_authorized(self, principal, action, resource, entities, context):
        self.requests.append(
            {
                "principal": principal,
                "action": action,
                "resource": resource,
                "entities": entities,
                "context": context,
            }
        )
        if self.raises:
            raise cedar_authz.CedarError(self.raises)
        return self.decision


@pytest.fixture(autouse=True)
def clean_cedar_state():
    cedar_authz.reset_for_tests()
    yield
    cedar_authz.reset_for_tests()


@pytest.fixture
def loaded(monkeypatch):
    def install(**kwargs):
        fake = FakeCedar(**kwargs)
        monkeypatch.setattr("ic_basilisk_toolkit.cedar_engine._cedar", fake)
        monkeypatch.setitem(sys.modules, "_basilisk_cedar", object())
        cedar_authz.load()
        return fake

    return install


class TestEmbeddedCedarArtifacts:
    def test_schema_declares_repl_in_action_contexts(self):
        schema = cedar_authz.schema()
        assert "repl?: Bool" in schema
        assert schema.count("repl?: Bool") >= 8

    def test_policies_forbid_repl_reads_of_sensitive_types(self):
        assert "context has repl" in POLICIES
        assert "Realm::UserProfile" in POLICIES
        assert "Realm::Permission" in POLICIES
        assert "Realm::RegistrationCode" in POLICIES


class TestSecureOrmWiring:
    def test_secure_orm_shares_engine_and_shell_context(self, main_module):
        assert main_module.secure_orm is not None
        _sync_orm_engine(main_module.secure_orm)
        assert main_module.secure_orm.engine is cedar_authz._get_engine()
        assert main_module.secure_orm._shell_context == {"repl": True}

    def test_actions_cover_crud_for_spot_checked_entities(self, main_module):
        # Generic RPC verbs (the C sandbox gate caps allowed_actions at 32,
        # so per-entity verbs are not feasible); the _entity kwarg selects
        # the class at dispatch time.
        actions = set(main_module.secure_orm.actions())
        assert actions == {
            "orm.create",
            "orm.list",
            "orm.get",
            "orm.update",
            "orm.delete",
            "orm.count",
        }
        for entity in ("User", "Balance", "Proposal"):
            assert entity in main_module.secure_orm._name_map


class TestHandleRpc:
    @staticmethod
    def _fake_balance_row():
        class User:
            _id = "alice"

        class Row:
            _id = "b1"
            amount = 10
            user = User()

        return Row()

    def test_denied_decision_raises_permission_error(self, main_module, loaded, monkeypatch):
        loaded(decision=False)
        orm = _sync_orm_engine(main_module.secure_orm)
        from ggg.finance.balance import Balance

        row = self._fake_balance_row()
        monkeypatch.setattr(Balance, "load", staticmethod(lambda row_id: row if row_id == "b1" else None))
        with pytest.raises(PermissionError, match="denied"):
            orm.handle_rpc("alice", "balance.update", {"id": "b1", "amount": 99})

    def test_allowed_update_flows_with_repl_context(self, main_module, loaded, monkeypatch):
        fake = loaded(decision=True)
        orm = _sync_orm_engine(main_module.secure_orm)

        from ggg.finance.balance import Balance

        row = self._fake_balance_row()
        monkeypatch.setattr(Balance, "load", staticmethod(lambda row_id: row if row_id == "b1" else None))

        result = orm.handle_rpc("alice", "balance.update", {"id": "b1", "amount": 42})
        assert result["id"] == "b1"
        assert result["amount"] == 42
        assert fake.requests
        assert fake.requests[-1]["context"] == {"repl": True}
