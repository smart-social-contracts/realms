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
    StageError,
    assert_credits_sufficient,
    build_portal_manifest,
    check_ic_members_policy,
    classify_identity,
    identity_refuse_message,
    merge_spec_and_flags,
    new_command,
    parse_subnet,
    slugify,
    validate_branding_size,
    validate_merged_spec,
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
        ), patch("realms.cli.commands.new.query_credit_balance", return_value=1):
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

    def test_pem_file_without_web_link(self):
        assert classify_identity("alice", pem_file_exists=True) == "pem_deploy"

    def test_refuse_message_shows_link_web(self):
        msg = identity_refuse_message("deployer", "staging")
        assert "icp identity link web deployer --app https://staging.realmsgos.org" in msg

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


class TestHelp:
    def test_realms_new_help(self):
        result = runner.invoke(app, ["new", "--help"])
        assert result.exit_code == 0
        assert "--identity" in result.output
        assert "--network" in result.output
        assert "--codex" in result.output
        assert "--resume" in result.output
        assert "wizard" in result.output.lower() or "live" in result.output.lower()
