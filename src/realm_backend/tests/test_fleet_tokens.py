"""The published Realms-token map is environment names, not canister ids baked into GaaS."""

import json
from pathlib import Path

_MAP = Path(__file__).resolve().parents[3] / "fleet-tokens.json"

_STAGING = "r6dmi-3yaaa-aaaak-qzgka-cai"
_PRODUCTION = "qah7x-liaaa-aaaag-azbza-cai"


def test_fleet_tokens_map_names_environments():
    data = json.loads(_MAP.read_text())
    assert data["staging"]["ledger"] == _STAGING
    assert data["staging"]["symbol"] == "RLM"
    assert data["production"]["ledger"] == _PRODUCTION
    assert "ckBTC" not in data
    assert "ckUSDC" not in data
    for key in data:
        if str(key).startswith("_"):
            continue
        assert isinstance(data[key], dict)
        assert data[key]["ledger"].endswith("-cai")
