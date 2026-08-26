"""SecureORM wiring and REPL Cedar policy tests (realms#282, realms#313)."""

import os
import sys
import types
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
        assert isinstance(main_module.secure_orm, main_module.HostSecureORM)
        _sync_orm_engine(main_module.secure_orm)
        assert main_module.secure_orm.engine is cedar_authz._get_engine()
        assert main_module.secure_orm._shell_context == {"repl": True}

    def test_actions_cover_crud_for_spot_checked_entities(self, main_module):
        # Generic RPC verbs (the C sandbox gate caps allowed_actions at 32,
        # so per-entity verbs are not feasible); the _entity kwarg selects
        # the class at dispatch time.
        actions = set(main_module.secure_orm.actions())
        assert {
            "orm.create",
            "orm.list",
            "orm.get",
            "orm.update",
            "orm.delete",
            "orm.count",
        } <= actions
        assert {
            "host.call",
            "host.ext_sync",
            "host.ext_async",
            "host.list_methods",
        } <= actions
        assert len(actions) <= 32
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


class TestSecureOrmLazyInit:
    def test_retries_after_import_time_failure(self, main_module, monkeypatch):
        saved = main_module.secure_orm
        saved_err = main_module._secure_orm_error

        class FakeOrm:
            def shell(self, code):
                return "ok\n"

        try:
            main_module.secure_orm = None
            main_module._secure_orm_error = "ImportError: earlier"
            monkeypatch.setattr(main_module, "_init_secure_orm", FakeOrm)
            assert main_module._try_init_secure_orm() is not None
            assert main_module.secure_orm is not None
            assert main_module._secure_orm_error == ""
        finally:
            main_module.secure_orm = saved
            main_module._secure_orm_error = saved_err

    def test_shell_surfaces_init_error(self, main_module, monkeypatch):
        saved = main_module.secure_orm
        saved_err = main_module._secure_orm_error
        try:
            main_module.secure_orm = None
            main_module._secure_orm_error = ""

            def fail():
                raise ValueError("principal type 'User' is not among the entity types")

            monkeypatch.setattr(main_module, "_init_secure_orm", fail)
            assert main_module._try_init_secure_orm() is None
            assert "ValueError: principal type" in main_module._secure_orm_error
        finally:
            main_module.secure_orm = saved
            main_module._secure_orm_error = saved_err


def _leftover_repl_host_lazymod():
    """Live leftover: no HostSecureORM on instance or type; ``_bload`` crashes."""
    _bMT = type(sys)
    crash_src = "raise RuntimeError('Database instance already exists')\n"

    class _LazyMod(_bMT):
        def __init__(self, name):
            super().__init__(name)
            self.__dict__["_bsrc"] = crash_src
            self.__dict__["_bloaded"] = True
            self.__dict__["_bloading"] = False
            self.__dict__["_bload_count"] = 0

        def _bload(self):
            self.__dict__["_bload_count"] = self.__dict__.get("_bload_count", 0) + 1
            if self.__dict__.get("_bloading") or self.__dict__.get("_bloaded"):
                return
            raise RuntimeError("Database instance already exists")

        def __getattribute__(self, name):
            ns = object.__getattribute__(self, "__dict__")
            if name in ns:
                return ns[name]
            if name in {"__getattr__", "__getattribute__", "_bload"} or (
                name.startswith("__") and name.endswith("__")
            ):
                return object.__getattribute__(self, name)
            return object.__getattribute__(self, "__getattr__")(name)

        def __getattr__(self, name):
            object.__getattribute__(self, "_bload")()
            ns = object.__getattribute__(self, "__dict__")
            try:
                return ns[name]
            except KeyError:
                raise AttributeError(
                    f"module '{self.__name__}' has no attribute '{name}'"
                )

    leftover = _LazyMod("core.repl_host")
    assert "HostSecureORM" not in leftover.__dict__
    assert "HostSecureORM" not in type(leftover).__dict__
    return leftover


def _leftover_executed_main():
    """Live leftover: packed ``__main__`` has no leftover verb attributes.

    Leftover Candid ingress looks leftover verbs up by NAME in leftover-
    executed ``__main__`` globals (``get_global``), not leftover packed
    ``__main__`` attrs. Instance and type dict omit ``get_sandbox_config``.
    No Candid hack. ``_bload`` cannot run. Leftover ``_bsrc`` still lists
    leftover public ``def`` names for leftover allowlist.
    """
    _bMT = type(sys)

    class _LazyMod(_bMT):
        def __init__(self, name):
            super().__init__(name)
            self.__dict__["_bsrc"] = (
                "def get_sandbox_config():\n    pass\n"
                "def extension_sync_call(a, b, c):\n    pass\n"
            )
            self.__dict__["_bloaded"] = True
            self.__dict__["_bloading"] = False
            self.__dict__["_bload_count"] = 0

        def _bload(self):
            self.__dict__["_bload_count"] = self.__dict__.get("_bload_count", 0) + 1
            raise RuntimeError("Database instance already exists")

        def __getattr__(self, name):
            self._bload()

    executed = _LazyMod("__main__")
    assert "get_sandbox_config" not in executed.__dict__
    assert "get_sandbox_config" not in type(executed).__dict__
    assert "extension_sync_call" not in executed.__dict__
    assert "extension_sync_call" not in type(executed).__dict__
    assert "__get_candid_interface_tmp_hack" not in executed.__dict__
    assert not any(
        str(key).endswith("__get_candid_interface_tmp_hack")
        for key in type(executed).__dict__
    )
    assert "HostSecureORM" not in executed.__dict__
    return executed


def _leftover_inspect_without_signature():
    """Live leftover WASI inspect is a stub: no leftover ``signature``."""
    import inspect as real

    stub = types.ModuleType("inspect")
    stub.__dict__.update(
        {
            name: value
            for name, value in vars(real).items()
            if name not in {"signature", "Parameter", "BoundArguments"}
        }
    )
    assert not hasattr(stub, "signature")
    with pytest.raises(AttributeError, match="signature"):
        stub.signature
    return stub


def _leftover_api_eval(orm, appendix, code, principal="2eqns"):
    """Product ``api.call`` / ``ext.call`` via leftover-executed stub."""
    import builtins as _builtins

    def rpc(action, **kwargs):
        return orm.handle_rpc(principal, action, kwargs)

    b = dict(vars(_builtins))
    b["rpc"] = rpc
    ns = {"eval_repl": lambda _c: "", "__builtins__": b, "rpc": rpc}
    exec(appendix, ns)
    return eval(code, ns, ns)


class TestLeftoverReplHostShell:
    def test_shell_starts_when_repl_host_is_leftover_lazymod(
        self, main_module, monkeypatch, tmp_path
    ):
        """Leftover ``core.repl_host``: from-import / ``_bload`` die; ``__shell__`` starts."""
        import types as types_mod

        stub = type(sys)("types")
        stub.__dict__.update(
            {
                name: value
                for name, value in vars(types_mod).items()
                if name != "ModuleType"
            }
        )
        monkeypatch.setitem(sys.modules, "types", stub)
        leftover = _leftover_repl_host_lazymod()
        # Honest leftover image: leftover packed ``__main__`` has no leftover
        # verb attrs. Leftover Candid globals do. No planted Candid hack.
        # No repo DID.
        executed = _leftover_executed_main()
        executed.__dict__["HostSecureORM"] = main_module.HostSecureORM
        saved_mod = sys.modules.get("core.repl_host")
        saved_main = sys.modules.get("main")
        saved_dunder = sys.modules.get("__main__")
        saved_orm = main_module.secure_orm
        saved_err = main_module._secure_orm_error
        saved_gsc = None
        saved_esc = None
        missing_did = tmp_path / "missing.did"
        repo_did = os.path.join(BACKEND, "realm_backend.did")
        assert os.path.isfile(repo_did)
        assert not missing_did.exists()
        try:
            sys.modules["core.repl_host"] = leftover
            sys.modules["main"] = executed
            sys.modules["__main__"] = executed
            assert "HostSecureORM" not in leftover.__dict__
            assert "__get_candid_interface_tmp_hack" not in leftover.__dict__
            assert "__get_candid_interface_tmp_hack" not in executed.__dict__
            assert not any(
                str(key).endswith("__get_candid_interface_tmp_hack")
                for key in type(executed).__dict__
            )
            with pytest.raises(ImportError, match="unknown location"):
                exec(
                    "from core.repl_host import HostSecureORM",
                    {"__name__": "leftover_import"},
                )
            leftover.__dict__["_bloaded"] = False
            with pytest.raises(RuntimeError, match="Database instance already exists"):
                leftover._bload()
            leftover.__dict__["_bloaded"] = True
            leftover.__dict__["_bload_count"] = 0

            main_module.secure_orm = None
            main_module._secure_orm_error = ""
            orm = main_module._try_init_secure_orm()
            assert orm is not None
            assert main_module._secure_orm_error == ""
            assert leftover._bload_count == 0
            assert isinstance(orm, main_module.HostSecureORM)

            started = {"n": 0}

            def _started(code):
                started["n"] += 1
                return "started\n"

            orm.shell = _started

            def _start_shell(code):
                bound = main_module._try_init_secure_orm()
                if bound is None:
                    raise RuntimeError(
                        f"secure_orm is not available: "
                        f"{main_module._secure_orm_error or 'unknown init failure'}"
                    )
                return bound.shell(code)

            out = _start_shell("1")
            assert out == "started\n"
            assert started["n"] == 1
            assert leftover._bload_count == 0

            # Live leftover has no DID file and no Candid hack. Point the
            # leftover-executed HostSecureORM at this host + missing DID.
            orm = main_module.HostSecureORM(
                engine=orm.engine,
                namespace="Realm",
                entities=[],
                schema={},
                principal_type="User",
                host_module=executed,
                did_path=missing_did,
            )
            names = main_module._host_load_allowed(
                missing_did, host_module=executed
            )
            assert "get_sandbox_config" in names
            assert "extension_sync_call" in names
            assert "__shell__" not in names
            assert leftover._bload_count == 0
            assert executed._bload_count == 0
            # Live leftover: leftover packed ``__main__`` has no leftover
            # verb attr. Leftover Candid globals (this leftover-executed
            # ``main`` module) do. Slot unwrap on leftover packed
            # ``__main__`` cannot bind leftover-executed host verbs.
            assert (
                main_module._host_module_attr(executed, "get_sandbox_config")
                is None
            )
            assert (
                main_module._host_module_attr(executed, "extension_sync_call")
                is None
            )
            saved_gsc = main_module.get_sandbox_config
            saved_esc = main_module.extension_sync_call
            leftover_inspect = _leftover_inspect_without_signature()
            monkeypatch.setattr(main_module, "_host_inspect", leftover_inspect)
            main_module.get_sandbox_config = lambda: {
                "available": True,
                "default_mode": "sandbox",
            }
            main_module.extension_sync_call = (
                lambda extension_name, function_name, args: {
                    "success": True,
                    "extension_name": extension_name,
                    "function_name": function_name,
                    "args": args,
                }
            )

            assert _leftover_api_eval(
                orm,
                main_module._HOST_STUB_APPENDIX,
                "api.call('get_sandbox_config')",
            ) == {"available": True, "default_mode": "sandbox"}
            assert _leftover_api_eval(
                orm,
                main_module._HOST_STUB_APPENDIX,
                "ext.call('department_docs', 'list_documents', {})",
            ) == {
                "success": True,
                "extension_name": "department_docs",
                "function_name": "list_documents",
                "args": "{}",
            }
            with pytest.raises(PermissionError, match="__shell__"):
                _leftover_api_eval(
                    orm,
                    main_module._HOST_STUB_APPENDIX,
                    "api.call('__shell__', '1')",
                )
            assert leftover._bload_count == 0
            assert executed._bload_count == 0
        finally:
            if saved_gsc is not None:
                main_module.get_sandbox_config = saved_gsc
            if saved_esc is not None:
                main_module.extension_sync_call = saved_esc
            main_module.secure_orm = saved_orm
            main_module._secure_orm_error = saved_err
            if saved_mod is None:
                sys.modules.pop("core.repl_host", None)
            else:
                sys.modules["core.repl_host"] = saved_mod
            if saved_main is None:
                sys.modules.pop("main", None)
            else:
                sys.modules["main"] = saved_main
            if saved_dunder is None:
                sys.modules.pop("__main__", None)
            else:
                sys.modules["__main__"] = saved_dunder
