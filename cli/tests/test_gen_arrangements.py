"""Tests for casals-config/_gen_arrangements.py."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN_PATH = ROOT / "casals-config" / "_gen_arrangements.py"


def _load_gen():
    spec = importlib.util.spec_from_file_location("_gen_arrangements", GEN_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_test_flags_from_staging_descriptor():
    gen = _load_gen()
    desc = gen._load_descriptor("staging")
    flags = gen.test_flags_from_parameters(desc.get("parameters"))
    assert flags == {
        "test_mode": True,
        "ii_bypass": True,
        "user_self_registration": True,
        "demo_data": False,
        "skip_terms": False,
        "skip_passport_zkproof": False,
        "disable_monetary_tokens": True,
        "demo_notice": True,
    }


def test_test_flags_from_test_descriptor():
    gen = _load_gen()
    desc = gen._load_descriptor("test")
    flags = gen.test_flags_from_parameters(desc.get("parameters"))
    assert flags["test_mode"] is True
    assert flags["ii_bypass"] is True
    assert flags["user_self_registration"] is True
    assert flags["demo_data"] is True
    assert flags["skip_terms"] is True
    assert flags["disable_monetary_tokens"] is True
    assert flags["demo_notice"] is False


def test_staging_parameters_include_host_go_live_flags():
    gen = _load_gen()
    canister_ids = gen._load_canister_ids()
    _steps, parameters, _realms = gen.generate_env_arrangement("staging", canister_ids)
    assert parameters["network"] == "staging"
    assert parameters["test_flags"]["disable_monetary_tokens"] is True
    assert parameters["test_flags"]["demo_notice"] is True
    assert parameters["test_flags"]["user_self_registration"] is True


def test_all_env_arrangement_files_exist_after_generation():
    gen = _load_gen()
    gen.main()
    for name in ("test.json", "staging.json", "demo.json"):
        path = ROOT / "casals-config" / "arrangements" / name
        assert path.is_file(), name
        doc = json.loads(path.read_text())
        assert doc["name"] in ("test", "staging", "demo")
        assert doc["active"] is True
        if name != "staging.json":
            assert doc["steps"], name
        assert doc["parameters"]["test_flags"], name
        flags = doc["parameters"]["test_flags"]
        assert "disable_monetary_tokens" in flags
        assert "demo_notice" in flags
