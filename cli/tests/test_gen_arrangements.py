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
        "ii_bypass": False,
        "user_self_registration": True,
        "demo_data": False,
        "skip_terms": False,
        "skip_passport_zkproof": False,
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


def test_staging_agora_canister_in_generated_steps():
    gen = _load_gen()
    canister_ids = gen._load_canister_ids()
    steps, parameters, realms = gen.generate_env_arrangement("staging", canister_ids)
    agora = next(r for r in realms if r["slug"] == "agora")
    assert agora["backend"] == "ihbn6-yiaaa-aaaac-beh3a-cai"
    config_steps = [
        s for s in steps
        if s["method"] == "set_canister_config_json" and s["target"] == agora["backend"]
    ]
    assert len(config_steps) == 1
    assert config_steps[0]["args"]["test_flags"]["user_self_registration"] is True
    assert parameters["network"] == "staging"


def test_all_env_arrangement_files_exist_after_generation():
    gen = _load_gen()
    gen.main()
    for name in ("test.json", "staging.json", "demo.json"):
        path = ROOT / "casals-config" / "arrangements" / name
        assert path.is_file(), name
        doc = json.loads(path.read_text())
        assert doc["name"] in ("test", "staging", "demo")
        assert doc["active"] is True
        assert doc["steps"], name
        assert doc["parameters"]["test_flags"], name
