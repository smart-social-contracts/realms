"""Codex overlay slots, prune, revert, safe mode, and permission (issue #328)."""

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))
sys.modules.setdefault("_cdk", MagicMock())
sys.modules.setdefault("ic_python_logging", MagicMock())

import core.codex_overlay as overlay  # noqa: E402
import core.codex_hooks as hooks  # noqa: E402


class FakeRow:
    def __init__(self, name, code=""):
        self.name = name
        self.code = code
        self.deleted = False

    def delete(self):
        self.deleted = True
        FakeCodex.store.pop(self.name, None)


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


@pytest.fixture
def slots(tmp_path, monkeypatch):
    monkeypatch.setattr(overlay, "SLOTS_DIR", str(tmp_path / "codex_slots"))
    FakeCodex.reset()
    ggg = types.ModuleType("ggg")
    ggg.Codex = FakeCodex
    monkeypatch.setitem(sys.modules, "ggg", ggg)
    monkeypatch.setattr(overlay, "_apply_to_runtime", lambda ext_id, files: None)
    monkeypatch.setattr(overlay, "_caller_may_revert", lambda: True)
    hooks.invalidate_cache()
    yield tmp_path
    hooks.invalidate_cache()


def _pkg(ext_id, modules, extra_manifest=None):
    files = {
        "manifest.json": json.dumps(
            {"kind": "codex", "name": ext_id, "version": "1.0.0", **(extra_manifest or {})}
        ),
        "entry.py": "def init(args): pass\n",
    }
    for name, body in modules.items():
        files[f"modules/{name}.py"] = body
    return files


def test_replace_not_merge_prunes_leftovers(slots):
    FakeCodex.store["leftover_helper"] = FakeRow("leftover_helper")
    FakeCodex.store["proposal_abc"] = FakeRow("proposal_abc")
    FakeCodex.store["membership"] = FakeRow("membership")

    overlay.activate(
        "syntropia",
        _pkg("syntropia", {"membership": "# membership"}),
        ["membership"],
    )

    assert "leftover_helper" not in FakeCodex.store
    assert "proposal_abc" in FakeCodex.store
    assert "membership" in FakeCodex.store


def test_previous_kept_after_second_activate(slots):
    first = _pkg("syntropia", {"old_mod": "# old"})
    second = _pkg("syntropia", {"new_mod": "# new"})
    overlay.activate("syntropia", first, ["old_mod"])
    first_hash = overlay.status()["current"]["hash"]

    overlay.activate("syntropia", second, ["new_mod"])
    status = overlay.status()
    assert status["current"]["modules"] == ["new_mod"]
    assert status["previous"]["hash"] == first_hash
    assert status["previous"]["modules"] == ["old_mod"]
    assert overlay._slot_files("previous")["modules/old_mod.py"] == "# old"


def test_revert_restores_previous(slots):
    first = _pkg("syntropia", {"old_mod": "# old"})
    second = _pkg("syntropia", {"new_mod": "# new"})
    overlay.activate("syntropia", first, ["old_mod"])
    FakeCodex.store["old_mod"] = FakeRow("old_mod", "# old")
    overlay.activate("syntropia", second, ["new_mod"])
    FakeCodex.store["new_mod"] = FakeRow("new_mod", "# new")

    result = overlay.revert()
    assert result["success"] is True
    assert result["codex_id"] == "syntropia"
    assert result["modules"] == ["old_mod"]
    assert overlay._slot_files("current")["modules/old_mod.py"] == "# old"
    assert overlay.status()["current"]["modules"] == ["old_mod"]
    assert "new_mod" not in FakeCodex.store


def test_safe_mode_skips_hooks(slots, monkeypatch):
    module = MagicMock()
    module.ping = lambda args: json.dumps({"ran": True})
    runtime = MagicMock()
    runtime.get_all_extension_manifests.return_value = {"agora": {"kind": "codex"}}
    runtime._load_module.return_value = module
    monkeypatch.setitem(sys.modules, "core.runtime_extensions", runtime)
    monkeypatch.setitem(
        sys.modules,
        "core.runtime_codex",
        MagicMock(list_installed=lambda: [], get_extension_overrides=lambda: {}),
    )
    hooks.invalidate_cache()
    overlay.activate("agora", _pkg("agora", {"m": "# m"}), ["m"])
    hooks.invalidate_cache()

    overlay.set_safe_mode(True, authorized_by_vote=True)
    assert overlay.is_safe_mode() is True
    assert hooks.call_hook("ping", {}, default="SKIPPED") == "SKIPPED"

    overlay.set_safe_mode(False, authorized_by_vote=True)
    hooks.invalidate_cache()
    assert hooks.call_hook("ping", {}, default="SKIPPED") == {"ran": True}


def test_revert_requires_codex_revert_permission(slots, monkeypatch):
    overlay.activate("syntropia", _pkg("syntropia", {"a": "# a"}), ["a"])
    overlay.activate("syntropia", _pkg("syntropia", {"b": "# b"}), ["b"])
    monkeypatch.setattr(overlay, "_caller_may_revert", lambda: False)
    result = overlay.revert()
    assert result["success"] is False
    assert "codex.revert" in result["error"]
    assert overlay._slot_files("current")["modules/b.py"] == "# b"


def test_shell_can_invoke_revert():
    did = (src_path / "realm_backend.did").read_text()
    assert '"revert_codex"' in did
    assert '"set_codex_safe_mode"' in did
    assert '"get_codex_overlay_status"' in did
    assert callable(overlay.revert)
    assert callable(overlay.set_safe_mode)


def test_protected_overrides_cannot_cover_voting_or_system():
    cleaned = overlay.filter_protected_overrides(
        {
            "voting": "fork_voting",
            "system": "fork_system",
            "system_info": "fork_info",
            "member_dashboard": "agora_dashboard",
        }
    )
    assert cleaned == {"member_dashboard": "agora_dashboard"}
