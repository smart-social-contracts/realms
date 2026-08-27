"""Package manager: replace-prune, lock deny, owner bypass (issue #351)."""

import json
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))
sys.modules.setdefault("_cdk", MagicMock())
sys.modules.setdefault("ic_python_logging", MagicMock())

import core.package_manager as pm  # noqa: E402
import core.codex_overlay as overlay  # noqa: E402


class FakeRow:
    def __init__(self, store, name, **extra):
        self.name = name
        self.deleted = False
        self._store = store
        for key, value in extra.items():
            setattr(self, key, value)

    def delete(self):
        self.deleted = True
        self._store.pop(self.name, None)


class FakeCodex:
    store = {}

    def __init__(self, name, code=""):
        self.name = name
        self.code = code
        type(self).store[name] = self

    @classmethod
    def reset(cls):
        cls.store = {}

    @classmethod
    def __class_getitem__(cls, name):
        return cls.store.get(name)

    @classmethod
    def instances(cls):
        return list(cls.store.values())


class FakeExtEntity:
    store = {}

    def __init__(self, name="row", **_kwargs):
        self.name = name
        type(self).store[name] = self

    @classmethod
    def reset(cls):
        cls.store = {}

    @classmethod
    def instances(cls):
        return list(cls.store.values())

    def delete(self):
        type(self).store.pop(self.name, None)


@pytest.fixture
def packages(tmp_path, monkeypatch):
    monkeypatch.setattr(pm, "PACKAGES_DIR", str(tmp_path / "packages"))
    monkeypatch.setattr(overlay, "SLOTS_DIR", str(tmp_path / "codex_slots"))
    FakeCodex.reset()
    FakeExtEntity.reset()
    ggg = types.ModuleType("ggg")
    ggg.Codex = FakeCodex
    ggg.User = {}
    monkeypatch.setitem(sys.modules, "ggg", ggg)
    monkeypatch.setattr(pm, "_caller_principal", lambda: "owner-principal")
    monkeypatch.setattr(pm, "_caller_is_bypass", lambda: False)
    monkeypatch.setattr(pm, "_now", lambda: 1_700_000_000)
    yield tmp_path


def _record(package_id="demo_ext", **overrides):
    base = {
        "id": package_id,
        "kind": "extension",
        "version": "1.0.0",
        "hash": "abc",
        "owner": "owner-principal",
        "locked": False,
        "installed_at": 1_700_000_000,
        "claimed": ["KeepEntity"],
    }
    base.update(overrides)
    return pm._write_package(base)


def test_replace_prune_drops_unclaimed_stems(packages, tmp_path):
    FakeCodex.store["leftover_helper"] = FakeRow(FakeCodex.store, "leftover_helper")
    FakeCodex.store["proposal_abc"] = FakeRow(FakeCodex.store, "proposal_abc")
    FakeCodex.store["membership"] = FakeRow(FakeCodex.store, "membership")

    ext_root = tmp_path / "ext" / "demo_ext"
    (ext_root / "modules").mkdir(parents=True)
    (ext_root / "keep.py").write_text("keep")
    (ext_root / "stale.py").write_text("stale")
    (ext_root / "modules" / "gone.py").write_text("gone")

    deleted_files = pm.prune_unclaimed_files(str(ext_root), ["keep.py", "manifest.json"])
    assert "stale.py" in deleted_files
    assert "modules/gone.py" in deleted_files
    assert not (ext_root / "stale.py").exists()
    assert (ext_root / "keep.py").exists()

    pruned = pm.prune_codex_stems(["membership"])
    assert "leftover_helper" in pruned
    assert "leftover_helper" not in FakeCodex.store
    assert "proposal_abc" in FakeCodex.store
    assert "membership" in FakeCodex.store


def test_replace_prune_drops_unclaimed_extension_entities(packages, monkeypatch):
    _record("voting", claimed=["OldConfig", "KeepConfig"])
    FakeExtEntity.store["old"] = FakeRow(FakeExtEntity.store, "old")
    classes = {("voting", "OldConfig"): FakeExtEntity}
    bridge = types.ModuleType("core.extension_bridge")
    bridge._EXT_ENTITY_CLASSES = classes
    monkeypatch.setitem(sys.modules, "core.extension_bridge", bridge)

    deleted = pm.prune_unclaimed_extension_entities("voting", ["KeepConfig"])
    assert "OldConfig" in deleted
    assert "old" not in FakeExtEntity.store


def test_lock_deny_non_owner_replace(packages, monkeypatch):
    _record("voting", locked=True, owner="owner-principal")
    monkeypatch.setattr(pm, "_caller_principal", lambda: "other-principal")
    monkeypatch.setattr(pm, "_caller_is_bypass", lambda: False)
    monkeypatch.setattr(pm, "_is_owner", lambda record, principal=None: False)

    denied = pm.replace_denied("voting")
    assert denied is not None
    assert "locked" in denied
    assert pm.lock_package("voting")["success"] is False
    assert pm.unlock_package("voting")["success"] is False
    assert pm.transfer_package("voting", "someone")["success"] is False


def test_owner_bypass_can_replace_while_locked(packages, monkeypatch):
    _record("voting", locked=True, owner="owner-principal")
    monkeypatch.setattr(pm, "_caller_principal", lambda: "owner-principal")
    monkeypatch.setattr(pm, "_is_owner", lambda record, principal=None: True)

    assert pm.replace_denied("voting") is None
    unlocked = pm.unlock_package("voting")
    assert unlocked["success"] is True
    assert unlocked["package"]["locked"] is False

    locked = pm.lock_package("voting")
    assert locked["success"] is True
    transferred = pm.transfer_package("voting", "congress")
    assert transferred["success"] is True
    assert transferred["package"]["owner"] == "congress"


def test_owner_unlock_then_replace(packages, monkeypatch):
    _record("voting", locked=True, owner="owner-principal")
    monkeypatch.setattr(pm, "_is_owner", lambda record, principal=None: True)
    assert pm.unlock_package("voting")["success"] is True
    assert pm.replace_denied("voting") is None


def test_codex_revert_bypass_can_replace_locked(packages, monkeypatch):
    _record("syntropia", kind="codex", locked=True, owner="someone-else")
    monkeypatch.setattr(pm, "_caller_principal", lambda: "congress-member")
    monkeypatch.setattr(pm, "_is_owner", lambda record, principal=None: False)
    monkeypatch.setattr(pm, "_caller_is_bypass", lambda: True)
    assert pm.replace_denied("syntropia") is None
    assert pm.unlock_package("syntropia")["success"] is True


def test_record_install_keeps_owner_and_lock(packages):
    first = pm.record_install(
        "voting",
        kind="extension",
        version="1.0.0",
        package_hash="h1",
        claimed=["A"],
    )
    assert first["owner"] == "owner-principal"
    assert first["locked"] is False
    pm.lock_package("voting")
    second = pm.record_install(
        "voting",
        kind="extension",
        version="1.1.0",
        package_hash="h2",
        claimed=["B"],
    )
    assert second["owner"] == "owner-principal"
    assert second["locked"] is True
    assert second["version"] == "1.1.0"
    assert second["claimed"] == ["B"]


def test_unlocked_replace_is_allowed(packages, monkeypatch):
    _record("voting", locked=False, owner="owner-principal")
    monkeypatch.setattr(pm, "_caller_principal", lambda: "installer")
    monkeypatch.setattr(pm, "_is_owner", lambda record, principal=None: False)
    assert pm.replace_denied("voting") is None


def test_first_install_has_no_lock_gate(packages):
    assert pm.replace_denied("brand_new") is None


def test_protected_host_types_are_not_claimed():
    claimed = pm.claimed_for_manifest(
        {
            "entities": {
                "User": {"fields": {"id": {"type": "String"}}},
                "AppConfig": {"fields": {"key": {"type": "String"}}},
            }
        }
    )
    assert "User" not in claimed
    assert "AppConfig" in claimed


def test_shell_can_invoke_package_manager():
    did = (src_path / "realm_backend.did").read_text()
    for name in (
        "list_packages",
        "lock_package",
        "unlock_package",
        "transfer_package",
    ):
        assert f'"{name}"' in did
    assert callable(pm.list_packages)
    assert callable(pm.lock_package)
    assert callable(pm.unlock_package)
    assert callable(pm.transfer_package)
    assert callable(pm.replace_denied)


def test_install_extension_prunes_leftover_files(packages, tmp_path, monkeypatch):
    ext_root = tmp_path / "extensions"
    monkeypatch.setattr("core.runtime_extensions.EXTENSIONS_DIR", str(ext_root))
    from core import runtime_extensions as runtime

    runtime._loaded_modules.clear()
    runtime._loaded_manifests.clear()

    leftover = ext_root / "demo_ext"
    leftover.mkdir(parents=True)
    (leftover / "stale.py").write_text("stale leftover")
    (leftover / "manifest.json").write_text("{}")
    monkeypatch.setattr(
        "core.extension_bridge.register_declared_entities",
        lambda ext_id, manifest: list((manifest.get("entities") or {}).keys()),
    )
    monkeypatch.setattr(runtime, "_seed_extension_entity", lambda *a, **k: None)
    monkeypatch.setattr(runtime, "_load_module", lambda *a, **k: None)

    files = {
        "manifest.json": json.dumps(
            {
                "name": "demo_ext",
                "version": "2.0.0",
                "entities": {
                    "AppConfig": {"fields": {"key": {"type": "String"}}},
                },
            }
        ),
    }
    ok = runtime.install_extension("demo_ext", files)
    assert ok is True
    assert not (leftover / "stale.py").exists()
    assert (leftover / "manifest.json").exists()
    record = pm.get_package("demo_ext")
    assert record["version"] == "2.0.0"
    assert record["kind"] == "extension"
    assert "AppConfig" in record["claimed"]


def test_install_extension_lock_deny(packages, tmp_path, monkeypatch):
    _record("locked_ext", locked=True, owner="owner-principal")
    monkeypatch.setattr(pm, "_is_owner", lambda record, principal=None: False)
    monkeypatch.setattr(pm, "_caller_is_bypass", lambda: False)
    ext_root = tmp_path / "extensions"
    monkeypatch.setattr("core.runtime_extensions.EXTENSIONS_DIR", str(ext_root))
    from core import runtime_extensions as runtime

    ok = runtime.install_extension(
        "locked_ext",
        {"manifest.json": json.dumps({"name": "locked_ext", "version": "9.0.0"})},
    )
    assert ok is False
    assert pm.get_package("locked_ext")["version"] == "1.0.0"
