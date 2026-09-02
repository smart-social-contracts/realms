"""file_registry resolution prefers canister_ids.json over NETWORK_INFRA."""

from pathlib import Path
from unittest.mock import patch

from realms.cli.commands.files import _resolve_registry, _wasm_type_for_publish


def test_resolve_registry_explicit_wins():
    assert _resolve_registry("demo", "aaaaa-aa") == "aaaaa-aa"


def test_resolve_registry_prefers_canister_ids(tmp_path):
    (tmp_path / "dfx.json").write_text("{}", encoding="utf-8")
    (tmp_path / "canister_ids.json").write_text(
        '{"file_registry": {"demo": "krch6-ryaaa-aaaas-amw3q-cai"}}',
        encoding="utf-8",
    )
    with patch("realms.cli.commands.files._find_project_root", return_value=tmp_path):
        assert _resolve_registry("demo", None) == "krch6-ryaaa-aaaas-amw3q-cai"


def test_wasm_type_for_publish_token_nft_motoko():
    assert _wasm_type_for_publish("token", "backend") == "motoko"
    assert _wasm_type_for_publish("nft", "backend") == "motoko"
    assert _wasm_type_for_publish("marketplace", "backend") == "basilisk"
    assert _wasm_type_for_publish("installer", "backend") == "basilisk"
    assert _wasm_type_for_publish("token", "frontend") == "assets"
