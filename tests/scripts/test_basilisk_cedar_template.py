"""Cedar is the only realm_backend pack path.

The plain CPython template is not selectable. These tests pin the leftover-free
recipe, dfx/CLI build lines, and docker setup to
``cpython_canister_template_cedar.wasm``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import basilisk_cedar_template as bct  # noqa: E402
import pack_realm_backend as pack  # noqa: E402


def _write_fake_cedar(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-wasm " + bct._SANDBOX_SHA256_SYMBOL + b" cedar")
    return path


def test_plain_template_name_is_detected():
    assert bct.is_plain_cpython_template("/tmp/cpython_canister_template.wasm")
    assert not bct.is_plain_cpython_template(
        "/tmp/cpython_canister_template_cedar.wasm"
    )


def test_require_cedar_rejects_plain_template(tmp_path):
    plain = tmp_path / bct.PLAIN_TEMPLATE_NAME
    plain.write_bytes(bct._SANDBOX_SHA256_SYMBOL)
    with pytest.raises(SystemExit, match="not a realm_backend pack path"):
        bct._require_cedar_template(plain)


def test_require_cedar_rejects_other_template_name(tmp_path):
    other = tmp_path / "some_other_template.wasm"
    other.write_bytes(bct._SANDBOX_SHA256_SYMBOL)
    with pytest.raises(SystemExit, match="must pack with"):
        bct._require_cedar_template(other)


def test_apply_cedar_overwrites_plain_template_env(tmp_path, monkeypatch):
    dest = _write_fake_cedar(tmp_path / bct.CEDAR_TEMPLATE_NAME)
    monkeypatch.setattr(bct, "cedar_template_cache_path", lambda: dest)
    env = bct.apply_cedar_template_env(
        {"BASILISK_TEMPLATE_WASM": str(tmp_path / bct.PLAIN_TEMPLATE_NAME)}
    )
    assert env["BASILISK_TEMPLATE_WASM"] == str(dest)
    assert Path(env["BASILISK_TEMPLATE_WASM"]).name == bct.CEDAR_TEMPLATE_NAME
    assert not bct.is_plain_cpython_template(env["BASILISK_TEMPLATE_WASM"])


def test_leftover_free_pack_forces_cedar(tmp_path, monkeypatch):
    dest = _write_fake_cedar(tmp_path / bct.CEDAR_TEMPLATE_NAME)
    monkeypatch.setattr(bct, "cedar_template_cache_path", lambda: dest)
    monkeypatch.setenv("BASILISK_TEMPLATE_WASM", str(tmp_path / bct.PLAIN_TEMPLATE_NAME))

    captured = {}

    def fake_run(cmd, cwd=None, env=None):
        captured["cmd"] = cmd
        captured["env"] = env

        class _R:
            returncode = 0

        return _R()

    monkeypatch.setattr(pack.subprocess, "run", fake_run)
    assert pack.pack_realm_backend(REPO_ROOT) == 0
    assert captured["cmd"][-2:] == ["realm_backend", str(REPO_ROOT / "src" / "realm_backend" / "main.py")]
    assert captured["env"]["BASILISK_TEMPLATE_WASM"] == str(dest)
    assert Path(captured["env"]["BASILISK_TEMPLATE_WASM"]).name == bct.CEDAR_TEMPLATE_NAME
    assert captured["env"]["CANISTER_CANDID_PATH"].endswith("src/realm_backend/realm_backend.did")


def test_dfx_json_realm_backend_uses_cedar_pack():
    dfx = json.loads((REPO_ROOT / "dfx.json").read_text())
    build = dfx["canisters"]["realm_backend"]["build"]
    assert build == "python3 scripts/pack_realm_backend.py"
    assert "python -m basilisk realm_backend" not in build


def test_dfx_templates_use_cedar_pack():
    for rel in ("dfx.template.json", "cli/realms/cli/dfx.template.json"):
        dfx = json.loads((REPO_ROOT / rel).read_text())
        build = dfx["canisters"]["realm_backend"]["build"]
        assert build == "python3 scripts/pack_realm_backend.py", rel


def test_setup_docker_dev_env_downloads_cedar_not_plain():
    text = (REPO_ROOT / "scripts" / "setup_docker_dev_env.sh").read_text()
    assert 'TEMPLATE="cpython_canister_template_cedar.wasm"' in text
    assert 'TEMPLATE="cpython_canister_template.wasm"' not in text
    assert "cpython-wasm-3.13.0-ic1" in text


def test_mundus_leftover_free_uses_pack_script():
    text = (REPO_ROOT / "cli" / "realms" / "cli" / "commands" / "mundus.py").read_text()
    assert "pack_realm_backend.py" in text
    assert '["python", "-m", "basilisk", "realm_backend"' not in text


def test_agents_leftover_free_recipe_uses_cedar_pack():
    text = (REPO_ROOT / "AGENTS.md").read_text()
    leftover = text.split("### Direct runtime install")[1]
    leftover = leftover.split("## Environment Setup")[0]
    assert leftover.count("python3 scripts/pack_realm_backend.py") == 2
    assert "python -m basilisk realm_backend" not in leftover


def test_build_base_wasm_dry_run_still_pins_cedar(tmp_path, monkeypatch):
    dest = _write_fake_cedar(tmp_path / bct.CEDAR_TEMPLATE_NAME)
    monkeypatch.setattr(bct, "cedar_template_cache_path", lambda: dest)
    monkeypatch.setenv("BASILISK_TEMPLATE_WASM", str(tmp_path / bct.PLAIN_TEMPLATE_NAME))

    import build_base_wasm as bbw

    monkeypatch.setattr(bbw, "apply_cedar_template_env", bct.apply_cedar_template_env)
    out = bbw._run_basilisk(REPO_ROOT, dry_run=True)
    assert out.name == "realm_backend.wasm"
