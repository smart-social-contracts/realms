"""Unit tests for ``realms new`` (issue #389). No replica / live IC."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from realms.cli.commands.new import (
    BRANDING_MAX_BYTES,
    DEPLOYMENT_COST_CREDITS,
    WIZARD_DEFAULT_TOKEN_CANISTER,
    WIZARD_DEFAULT_TOKEN_SYMBOL,
    StageError,
    _identity_kind_is_web,
    _parse_jsonish,
    assert_credits_sufficient,
    build_portal_manifest,
    check_ic_members_policy,
    classify_identity,
    identity_refuse_message,
    load_gaas_env_canisters,
    merge_spec_and_flags,
    new_command,
    parse_env_config,
    parse_subnet,
    registry_id_for,
    slugify,
    validate_branding_size,
    validate_merged_spec,
    wait_for_enter_setup,
)
from realms.cli.main import app


runner = CliRunner()


def _merged(**overrides):
    spec = {
        "name": "Acme Realm",
        "slug": "acme",
        "gos": "realms-gos",
        "version": "main",
        "subnet": {"choice": "automatic"},
        "codex": {"package": "agora", "version": None},
        "members": 0,
        "open_registration": False,
    }
    spec.update(overrides)
    return merge_spec_and_flags(spec, spec_dir=None)


class TestSlugify:
    def test_basic(self):
        assert slugify("Acme Realm") == "acme-realm"

    def test_strips_punctuation_and_caps_length(self):
        assert slugify("Hello, World!!!") == "hello-world"
        long_name = "a" * 80
        assert len(slugify(long_name)) == 48

    def test_empty_falls_back(self):
        assert slugify("") == "realm"
        assert slugify("---") == "realm"


class TestSpecFlagMerge:
    def test_flags_override_spec(self, tmp_path: Path):
        spec = {
            "name": "FromSpec",
            "codex": {"package": "dominion", "version": "1.0.0"},
            "members": 2,
        }
        merged = merge_spec_and_flags(
            spec,
            spec_dir=tmp_path,
            name="FromFlag",
            codex="agora",
            members=0,
        )
        assert merged["name"] == "FromFlag"
        assert merged["codex"]["package"] == "agora"
        assert merged["members"] == 0
        assert merged["slug"] == "fromflag"

    def test_slug_defaults_from_name(self):
        merged = merge_spec_and_flags({"name": "Hello World"}, spec_dir=None)
        assert merged["slug"] == "hello-world"

    def test_paths_relative_to_spec_file(self, tmp_path: Path):
        logo = tmp_path / "logo.png"
        logo.write_bytes(b"\x89PNG")
        spec = {"name": "Acme Realm", "branding": {"logo": "./logo.png"}, "codex": {"package": "agora"}}
        merged = merge_spec_and_flags(spec, spec_dir=tmp_path)
        assert merged["branding"]["logo"] == str(logo.resolve())

    def test_missing_required_fields(self):
        merged = merge_spec_and_flags({}, spec_dir=None)
        with pytest.raises(StageError) as exc:
            validate_merged_spec(merged, network="staging", identity="alice")
        assert "name" in exc.value.message.lower()
        assert "codex" in exc.value.message.lower()

    def test_token_defaults_to_catalog_ckeurc(self):
        merged = merge_spec_and_flags(
            {"name": "Acme Realm", "codex": {"package": "agora"}}, spec_dir=None
        )
        assert merged["token"] == {
            "symbol": WIZARD_DEFAULT_TOKEN_SYMBOL,
            "canister": WIZARD_DEFAULT_TOKEN_CANISTER,
        }

    def test_token_flags_override_catalog_default(self):
        merged = merge_spec_and_flags(
            {"name": "Acme Realm", "codex": {"package": "agora"}},
            spec_dir=None,
            token_symbol="ckUSDC",
            token_canister="xevnm-gaaaa-aaaar-qafnq-cai",
        )
        assert merged["token"] == {
            "symbol": "ckUSDC",
            "canister": "xevnm-gaaaa-aaaar-qafnq-cai",
        }

    def test_gos_must_be_realms_gos(self):
        merged = _merged()
        merged["gos"] = "monad-gos"
        with pytest.raises(StageError) as exc:
            validate_merged_spec(merged, network="staging", identity="alice")
        assert "realms-gos" in exc.value.message


class TestSubnet:
    def test_automatic_default(self):
        assert parse_subnet(None, None) == {"choice": "automatic"}

    def test_european_flag(self):
        assert parse_subnet({"choice": "automatic"}, "european")["choice"] == "european"

    def test_other_requires_id(self):
        with pytest.raises(StageError) as exc:
            parse_subnet({"choice": "other"}, None)
        assert "subnet.id" in exc.value.message

    def test_subnet_id_flag(self):
        subnet_id = "o57es-2iaaa-aaaaa-qaaaa-yai"
        block = parse_subnet(None, subnet_id)
        assert block == {"choice": "other", "id": subnet_id}

    def test_casals_block_automatic_omits_subnet(self):
        manifest = build_portal_manifest(
            name="Acme",
            slug="acme",
            network="staging",
            version="main",
            founder="aaaaa-aa",
            subnet={"choice": "automatic"},
        )
        assert "subnet" not in manifest["casals"]
        assert "subnet_type" not in manifest["casals"]

    def test_casals_block_european_and_other(self):
        eu = build_portal_manifest(
            name="Acme",
            slug="acme",
            network="staging",
            version="v0.4.0",
            founder="aaaaa-aa",
            subnet={"choice": "european"},
        )
        assert eu["casals"]["subnet_type"] == "european"
        assert eu["casals"]["backend_wasm_key"] == "realm-backend@0.4.0"
        other = build_portal_manifest(
            name="Acme",
            slug="acme",
            network="test",
            version="main",
            founder="aaaaa-aa",
            subnet={"choice": "other", "id": "o57es-2iaaa-aaaaa-qaaaa-yai"},
        )
        assert other["casals"]["subnet"] == "o57es-2iaaa-aaaaa-qaaaa-yai"


class TestPortalManifest:
    def test_includes_casals_federation_founder_not_github_urls(self):
        manifest = build_portal_manifest(
            name="Acme",
            slug="acme",
            network="staging",
            version="main",
            founder="2eqns-rmzes-7npxw-dxpw2-qdy2s-mw6ix-svdo2-oya7o-a6ldc-sqgwh-bqe",
            subnet={"choice": "automatic"},
        )
        assert manifest["casals"]["backend_wasm_key"] == "realm-backend@main"
        assert manifest["casals"]["frontend_wasm_key"] == "realm-assets@main"
        assert manifest["federation"]["slug"] == "acme"
        assert manifest["federation"]["portal_url"] == "https://staging.gos.earth/r/acme"
        assert manifest["founder"].startswith("2eqns-")
        assert "artifacts" not in manifest
        assert "github.com" not in json.dumps(manifest)
        assert manifest["gos"]["implementation"] == "realms-gos"
        assert manifest["test_flags"]["user_self_registration"] is True

    def test_ic_portal_host_and_no_test_flags(self):
        manifest = build_portal_manifest(
            name="Acme",
            slug="acme",
            network="ic",
            version="latest",
            founder="aaaaa-aa",
            subnet={"choice": "automatic"},
        )
        assert manifest["federation"]["portal_url"] == "https://registry.realmsgos.org/r/acme"
        assert manifest["deploy_version"] == "main"
        assert "test_flags" not in manifest


class TestCreditsFail:
    def test_assert_credits_shortfall(self):
        with pytest.raises(StageError) as exc:
            assert_credits_sufficient(2, "aaaaa-aa", "staging")
        assert exc.value.stage == "credits"
        assert "add_credits" in exc.value.message
        assert "aaaaa-aa" in exc.value.message
        assert str(DEPLOYMENT_COST_CREDITS) in exc.value.message

    def test_command_credit_fail_mocked(self):
        with patch("realms.cli.commands.new.assert_identity_is_ii_linked", return_value="web"), patch(
            "realms.cli.commands.new.resolve_identity_principal", return_value="aaaaa-aa"
        ), patch("realms.cli.commands.new.query_registry_env_config", return_value={}), patch(
            "realms.cli.commands.new.query_credit_balance", return_value=1
        ):
            with pytest.raises(typer.Exit) as exc:
                new_command(
                    spec_file=None,
                    identity="alice",
                    network="staging",
                    name="Acme Realm",
                    codex="agora",
                    yes=True,
                )
            assert exc.value.exit_code == 1


class TestIcMembersRefused:
    def test_ic_members_without_open_registration(self):
        err = check_ic_members_policy("ic", 3, False, [])
        assert err is not None
        assert "open-registration" in err

    def test_ic_members_allowed_with_flag_or_codes(self):
        assert check_ic_members_policy("ic", 3, True, []) is None
        assert check_ic_members_policy("ic", 3, False, ["deadbeef"]) is None
        assert check_ic_members_policy("staging", 3, False, []) is None
        assert check_ic_members_policy("ic", 0, False, []) is None

    def test_validate_rejects_ic_members(self):
        merged = _merged()
        merged["members"] = 2
        with pytest.raises(StageError) as exc:
            validate_merged_spec(merged, network="ic", identity="alice")
        assert "open-registration" in exc.value.message


class TestBrandingSize:
    def test_reject_oversize_file(self, tmp_path: Path):
        huge = tmp_path / "bg.png"
        huge.write_bytes(b"x" * (BRANDING_MAX_BYTES + 1))
        with pytest.raises(StageError) as exc:
            validate_branding_size(str(huge), "background")
        assert "1.5 MiB" in exc.value.message

    def test_accept_small_file(self, tmp_path: Path):
        small = tmp_path / "logo.png"
        small.write_bytes(b"\x89PNG")
        validate_branding_size(str(small), "logo")

    def test_validate_merged_rejects_huge_logo(self, tmp_path: Path):
        huge = tmp_path / "logo.png"
        huge.write_bytes(b"x" * (BRANDING_MAX_BYTES + 8))
        merged = _merged()
        merged["branding"]["logo"] = str(huge)
        with pytest.raises(StageError) as exc:
            validate_merged_spec(merged, network="staging", identity="alice")
        assert "1.5 MiB" in exc.value.message


class TestIdentityClassification:
    def test_known_pem_deploy_keys(self):
        assert classify_identity("deployer") == "pem_deploy"
        assert classify_identity("my_dev_identity_1") == "pem_deploy"

    def test_web_linked(self):
        assert classify_identity("alice", web_linked=True) == "web"

    def test_imported_ii_session_pem_is_not_refused(self):
        """Cloud agents import ``demo_identity1`` as a plaintext PEM + delegation."""
        assert classify_identity("demo_identity1", pem_file_exists=True) == "unknown"
        assert classify_identity("demo_identity1", web_linked=False) == "unknown"
        assert classify_identity("demo_identity1", web_linked=True) == "web"

    def test_web_auth_kind_counts_as_linked(self):
        assert _identity_kind_is_web("web-auth") is True
        assert _identity_kind_is_web("web") is True
        assert _identity_kind_is_web("pem") is False

    def test_refuse_message_shows_link_web(self):
        msg = identity_refuse_message("deployer", "staging")
        assert "icp identity link web deployer --app https://staging.realmsgos.org" in msg
        assert "--co-admin" in msg

    def test_command_refuses_pem_deploy_identity(self):
        with pytest.raises(typer.Exit) as exc:
            new_command(
                spec_file=None,
                identity="deployer",
                network="staging",
                name="Acme Realm",
                codex="agora",
                yes=True,
            )
        assert exc.value.exit_code == 1


class TestCoAdmin:
    SAMPLE = "2eqns-rmzes-7npxw-dxpw2-qdy2s-mw6ix-svdo2-oya7o-a6ldc-sqgwh-bqe"

    def test_deployer_refused_without_co_admin(self):
        merged = _merged()
        with pytest.raises(StageError) as exc:
            validate_merged_spec(merged, network="demo", identity="deployer")
        assert "co-admin" in exc.value.message.lower()

    def test_deployer_ok_with_co_admin(self):
        merged = _merged()
        merged["co_admin"] = self.SAMPLE
        validate_merged_spec(merged, network="demo", identity="deployer")

    def test_flag_overrides_spec(self):
        merged = merge_spec_and_flags(
            {"name": "Acme Realm", "codex": {"package": "agora"}, "co_admin": "old-id"},
            spec_dir=None,
            co_admin=self.SAMPLE,
        )
        assert merged["co_admin"] == self.SAMPLE

    def test_rejects_anonymous(self):
        merged = _merged()
        merged["co_admin"] = "2vxsx-fae"
        with pytest.raises(StageError) as exc:
            validate_merged_spec(merged, network="demo", identity="deployer")
        assert "anonymous" in exc.value.message.lower()

    def test_rejects_short_principal(self):
        merged = _merged()
        merged["co_admin"] = "not-a-principal"
        with pytest.raises(StageError) as exc:
            validate_merged_spec(merged, network="demo", identity="deployer")
        assert "principal" in exc.value.message.lower()


class TestGaasEnvDiscovery:
    def test_registry_id_from_descriptor(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        path = tmp_path / "demo.json"
        path.write_text(
            json.dumps(
                {
                    "canisters": {
                        "realm_registry_backend": "aaaaa-aaaaa-aaaaa-aaaaa-cai",
                        "realm_installer": "bbbbb-bbbbb-bbbbb-bbbbb-cai",
                    }
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("GAAS_DESCRIPTOR", str(path))
        assert load_gaas_env_canisters("demo")["realm_registry_backend"] == (
            "aaaaa-aaaaa-aaaaa-aaaaa-cai"
        )
        assert registry_id_for("demo") == "aaaaa-aaaaa-aaaaa-aaaaa-cai"

    def test_demo_without_descriptor_has_no_hardcoded_id(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("GAAS_DESCRIPTOR", raising=False)
        monkeypatch.delenv("GAAS_ENV", raising=False)
        with patch("realms.cli.commands.new.load_gaas_env_canisters", return_value={}):
            with pytest.raises(StageError) as exc:
                registry_id_for("demo")
            assert exc.value.stage == "deploy"
            assert "GAAS_DESCRIPTOR" in exc.value.message

    def test_wait_for_enter_setup_ignores_default_setup_without_creator(self):
        replies = [
            {"success": True, "status": "setup", "creator": None},
            {"success": True, "status": "setup", "creator": "ah6ac-founder"},
        ]

        def _call(*_a, **_k):
            return replies.pop(0)

        with patch("realms.cli.commands.new._canister_call", side_effect=_call), patch(
            "realms.cli.commands.new.time.sleep"
        ), patch("realms.cli.commands.new.time.time", side_effect=[0, 1, 2, 3, 4]):
            state = wait_for_enter_setup("backend-id", "demo", "deployer", timeout_s=30)
        assert state["creator"] == "ah6ac-founder"

    def test_parse_jsonish_unwraps_dfx_text_json(self):
        inner = {
            "success": True,
            "status": "setup",
            "creator": "ah6ac-founder",
        }
        parsed = _parse_jsonish(json.dumps(json.dumps(inner)))
        assert parsed["creator"] == "ah6ac-founder"
        assert parsed["success"] is True

    def test_wait_for_enter_setup_accepts_json_string(self):
        payload = json.dumps(
            {"success": True, "status": "setup", "creator": "ah6ac-founder"}
        )
        with patch(
            "realms.cli.commands.new._canister_call", return_value=payload
        ), patch("realms.cli.commands.new.time.sleep"), patch(
            "realms.cli.commands.new.time.time", side_effect=[0, 1, 2]
        ):
            state = wait_for_enter_setup("backend-id", "demo", "deployer", timeout_s=30)
        assert state["creator"] == "ah6ac-founder"

    def test_parse_env_config_can_test_mode(self):
        assert parse_env_config('{"success": true, "can_test_mode": true}')[
            "can_test_mode"
        ] is True
        assert parse_env_config({"Ok": '{"can_test_mode": true, "installer_id": "x"}'})[
            "installer_id"
        ] == "x"


class TestHelp:
    def test_realms_new_help(self):
        result = runner.invoke(app, ["new", "--help"])
        assert result.exit_code == 0
        import re

        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert "identity" in plain
        assert "network" in plain
        assert "codex" in plain
        assert "resume" in plain
        assert "co-admin" in plain or "co" in plain
        assert "wizard" in plain.lower() or "live" in plain.lower()
