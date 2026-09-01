"""Unit tests for ``realms new`` (issue #389). No replica / live IC."""

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from realms.cli.commands.new import (
    BRANDING_MAX_BYTES,
    DEPLOYMENT_COST_CREDITS,
    StageError,
    _identity_kind_is_web,
    apply_credit_voucher,
    assert_credits_sufficient,
    build_frontend_canister_ids_js,
    build_portal_manifest,
    check_ic_members_policy,
    classify_identity,
    identity_refuse_message,
    load_gaas_config,
    merge_spec_and_flags,
    new_command,
    normalize_deploy_mode,
    parse_subnet,
    poll_installer_until_ready,
    portal_url_for_slug,
    resolve_gos_queue,
    slugify,
    standalone_artifact_urls,
    voucher_credit_amount,
    validate_branding_size,
    validate_merged_spec,
    _parse_jsonish,
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
        assert "can_test_mode" not in manifest

    def test_demo_omits_test_flags(self):
        manifest = build_portal_manifest(
            name="SeedDemo",
            slug="seeddemo",
            network="demo",
            version="main",
            founder="aaaaa-aa",
            subnet={"choice": "automatic"},
        )
        assert manifest["federation"]["portal_url"] == "https://demo.gos.earth/r/seeddemo"
        assert "test_flags" not in manifest
        assert "can_test_mode" not in manifest


class TestCreditsFail:
    def test_assert_credits_shortfall(self):
        with pytest.raises(StageError) as exc:
            assert_credits_sufficient(2, "aaaaa-aa", "staging")
        assert exc.value.stage == "credits"
        assert "add_credits" in exc.value.message
        assert "aaaaa-aa" in exc.value.message
        assert str(DEPLOYMENT_COST_CREDITS) in exc.value.message

    def test_command_credit_fail_mocked(self, tmp_path):
        cfg = tmp_path / "gaas.json"
        cfg.write_text(
            json.dumps(
                {
                    "name": "staging",
                    "domain": "staging.gos.earth",
                    "canisters": {
                        "realm_registry_backend": "7wzxh-wyaaa-aaaau-aggyq-cai",
                        "realm_installer": "lusjm-wqaaa-aaaau-ago7q-cai",
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
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
                    gaas_config=str(cfg),
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


class TestHelp:
    def test_realms_new_help(self):
        result = runner.invoke(app, ["new", "--help"])
        assert result.exit_code == 0
        output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert "--identity" in output
        assert "--network" in output
        assert "--codex" in output
        assert "--resume" in output
        assert "--co-admin" in output
        assert "--log-file" in output
        assert "--gaas-config" in output
        assert "--deploy-mode" in output
        assert "--credit-voucher" in output
        assert "wizard" in output.lower() or "live" in output.lower() or "standalone" in output.lower()


class TestGaasConfig:
    def _write(self, tmp_path: Path, **overrides) -> Path:
        payload = {
            "name": "demo",
            "domain": "demo.gos.earth",
            "canisters": {
                "realm_registry_backend": "5ocwl-eiaaa-aaaah-av2bq-cai",
                "realm_installer": "53fhg-faaaa-aaaah-av2ca-cai",
            },
        }
        payload.update(overrides)
        path = tmp_path / "demo-gaas.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    def test_load_extracts_queue_ids(self, tmp_path: Path):
        path = self._write(tmp_path)
        gaas = load_gaas_config(path)
        assert gaas.env_name == "demo"
        assert gaas.registry_id == "5ocwl-eiaaa-aaaah-av2bq-cai"
        assert gaas.installer_id == "53fhg-faaaa-aaaah-av2ca-cai"
        assert gaas.portal_host == "https://demo.gos.earth"
        assert gaas.billing_url == ""

    def test_load_reads_billing_url(self, tmp_path: Path):
        path = self._write(
            tmp_path,
            services={"billing_url": "https://billing.example.test"},
        )
        gaas = load_gaas_config(path)
        assert gaas.billing_url == "https://billing.example.test"

    def test_resolve_infers_network_from_name(self, tmp_path: Path):
        path = self._write(tmp_path)
        gaas, network = resolve_gos_queue(gaas_config=str(path), network="")
        assert network == "demo"
        assert gaas.registry_id.endswith("-cai")

    def test_resolve_rejects_network_mismatch(self, tmp_path: Path):
        path = self._write(tmp_path)
        with pytest.raises(StageError) as exc:
            resolve_gos_queue(gaas_config=str(path), network="staging")
        assert "does not match" in exc.value.message

    def test_missing_file_is_required(self):
        with pytest.raises(StageError) as exc:
            resolve_gos_queue(gaas_config=None, network="demo")
        assert "--gaas-config is required" in exc.value.message

    def test_command_requires_gaas_config(self):
        with pytest.raises(typer.Exit):
            new_command(
                spec_file=None,
                identity="alice",
                network="demo",
                name="Acme Realm",
                codex="agora",
                yes=True,
            )

    def test_portal_url_uses_config_domain(self, tmp_path: Path):
        path = self._write(tmp_path)
        gaas = load_gaas_config(path)
        url = portal_url_for_slug("acme", "demo", portal_host=gaas.portal_host)
        assert url == "https://demo.gos.earth/r/acme"


class TestDeployMode:
    def test_normalize_defaults_to_gaas(self):
        assert normalize_deploy_mode(None) == "gaas"
        assert normalize_deploy_mode("GAAS") == "gaas"

    def test_normalize_rejects_unknown(self):
        with pytest.raises(StageError) as exc:
            normalize_deploy_mode("casals")
        assert "gaas" in exc.value.message
        assert "standalone" in exc.value.message

    def test_standalone_latest_urls(self):
        backend, frontend = standalone_artifact_urls("latest")
        assert backend.endswith("/releases/latest/download/realm_backend.wasm.gz")
        assert frontend.endswith("/releases/latest/download/realm_frontend.tar.gz")

    def test_standalone_semver_urls(self):
        backend, frontend = standalone_artifact_urls("0.3.5")
        assert "/releases/download/v0.3.5/realm_backend.wasm.gz" in backend
        assert "/releases/download/v0.3.5/realm_frontend.tar.gz" in frontend

    def test_standalone_rejects_build(self):
        with pytest.raises(StageError) as exc:
            standalone_artifact_urls("build")
        assert "build" in exc.value.message.lower()

    def test_standalone_rejects_gaas_config(self, tmp_path: Path):
        path = tmp_path / "demo-gaas.json"
        path.write_text("{}", encoding="utf-8")
        with pytest.raises(typer.Exit):
            new_command(
                spec_file=None,
                identity="alice",
                network="demo",
                name="Acme Realm",
                codex="agora",
                yes=True,
                gaas_config=str(path),
                deploy_mode="standalone",
            )

    @patch("realms.cli.commands.new.join_geister_members", return_value=[])
    @patch("realms.cli.commands.new.import_data_overlay")
    @patch("realms.cli.commands.new.apply_runtime_config")
    @patch("realms.cli.commands.new.register_co_admin_principal")
    @patch("realms.cli.commands.new.run_setup_stage")
    @patch("realms.cli.commands.new.setup_already_complete", return_value=True)
    @patch("realms.cli.commands.new.wait_for_enter_setup")
    @patch("realms.cli.commands.new.wire_live_realm")
    @patch(
        "realms.cli.commands.new.deploy_standalone_realm",
        return_value=("aaaaa-aaaaa-aaaaa-aaaaa-aaa", "bbbbb-bbbbb-bbbbb-bbbbb-bbb"),
    )
    @patch(
        "realms.cli.commands.new.resolve_identity_principal",
        return_value="aaaaa-aaaaa-aaaaa-aaaaa-aaa",
    )
    @patch("realms.cli.commands.new.assert_identity_is_ii_linked")
    def test_standalone_skips_credits_and_installer(
        self,
        _linked,
        _principal,
        mock_deploy,
        mock_wire,
        _wait,
        _complete,
        _setup,
        _co_admin,
        _config,
        _data,
        _members,
        capsys,
    ):
        new_command(
            spec_file=None,
            identity="alice",
            network="demo",
            name="Acme Realm",
            slug="acme",
            codex="agora",
            yes=True,
            deploy_mode="standalone",
            credit_voucher="BETA50",
        )
        mock_deploy.assert_called_once()
        mock_wire.assert_called_once()
        out = capsys.readouterr().out
        assert "standalone" in out
        assert "bbbbb-bbbbb-bbbbb-bbbbb-bbb" in out


class TestCreditVoucher:
    def test_amount_from_trailing_digits(self):
        assert voucher_credit_amount("BETA50") == 50
        assert voucher_credit_amount("beta5") == DEPLOYMENT_COST_CREDITS
        assert voucher_credit_amount("FREE") == DEPLOYMENT_COST_CREDITS

    def test_billing_success_skips_add_credits(self):
        with patch(
            "realms.cli.commands.new.redeem_voucher_via_billing",
            return_value={"success": True, "message": "ok", "data": {"credits": 50}},
        ), patch(
            "realms.cli.commands.new.query_credit_balance", return_value=50
        ), patch("realms.cli.commands.new.grant_registry_credits") as grant:
            apply_credit_voucher(
                code="BETA50",
                registry_id="tmp6q-uiaaa-aaaah-av3bq-cai",
                founder="aaaaa-aa",
                network="demo",
                identity="deployer",
                billing_url="https://billing.example.test",
            )
            grant.assert_not_called()

    def test_falls_back_to_on_chain_add_credits(self):
        with patch(
            "realms.cli.commands.new.redeem_voucher_via_billing",
            side_effect=StageError("credits", "Missing Internet Identity proof"),
        ), patch(
            "realms.cli.commands.new.query_credit_balance", return_value=0
        ), patch(
            "realms.cli.commands.new.grant_registry_credits", return_value={"Ok": {}}
        ) as grant:
            apply_credit_voucher(
                code="BETA50",
                registry_id="tmp6q-uiaaa-aaaah-av3bq-cai",
                founder="aaaaa-aa",
                network="demo",
                identity="deployer",
                billing_url="",
            )
            grant.assert_called_once()
            assert grant.call_args.args[2] == 50

    def test_command_redeems_voucher_before_balance_check(self, tmp_path: Path):
        cfg = tmp_path / "gaas.json"
        cfg.write_text(
            json.dumps(
                {
                    "name": "staging",
                    "domain": "staging.gos.earth",
                    "canisters": {
                        "realm_registry_backend": "7wzxh-wyaaa-aaaau-aggyq-cai",
                        "realm_installer": "lusjm-wqaaa-aaaah-av2ca-cai",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        with patch(
            "realms.cli.commands.new.assert_identity_is_ii_linked", return_value="web"
        ), patch(
            "realms.cli.commands.new.resolve_identity_principal", return_value="aaaaa-aa"
        ), patch(
            "realms.cli.commands.new.apply_credit_voucher"
        ) as redeem, patch(
            "realms.cli.commands.new.query_credit_balance", return_value=1
        ):
            with pytest.raises(typer.Exit):
                new_command(
                    spec_file=None,
                    identity="alice",
                    network="staging",
                    name="Acme Realm",
                    codex="agora",
                    yes=True,
                    gaas_config=str(cfg),
                    credit_voucher="BETA50",
                )
            redeem.assert_called_once()
            assert redeem.call_args.kwargs["code"] == "BETA50"


def test_parse_jsonish_unwraps_dfx_json_string():
    raw = json.dumps('{"success":true,"status":"setup","creator":null}')
    parsed = _parse_jsonish(raw)
    assert parsed["success"] is True
    assert parsed["status"] == "setup"


class TestFrontendCanisterIdsJs:
    def test_includes_backend_and_portal(self):
        js = build_frontend_canister_ids_js(
            backend_id="lvpim-iyaaa-aaaas-amw5q-cai",
            file_registry_id="krch6-ryaaa-aaaas-amw3q-cai",
            derivation_origin="https://demo.realmsgos.org",
            portal_url="https://demo.gos.earth/r/seeddemo",
        )
        assert "globalThis.__CANISTER_IDS" in js
        assert "lvpim-iyaaa-aaaas-amw5q-cai" in js
        assert "https://demo.gos.earth/r/seeddemo" in js
        assert "test_mode_ii_bypass" not in js

    def test_ii_bypass_only_when_requested(self):
        js = build_frontend_canister_ids_js(
            backend_id="aaaaa-aa",
            test_mode_ii_bypass=True,
        )
        assert '"test_mode_ii_bypass": true' in js


class TestPollInstaller:
    def test_failed_job_with_canisters_continues(self):
        payload = {
            "Ok": {
                "status": "failed",
                "error": "set_canister_config_json failed",
                "backend_canister_id": "lvpim-iyaaa-aaaas-amw5q-cai",
                "frontend_canister_id": "laizb-jqaaa-aaaas-amw6a-cai",
            }
        }
        with patch("realms.cli.commands.new._canister_call", return_value=payload):
            info = poll_installer_until_ready(
                "tzip5-vaaaa-aaaah-av3ca-cai",
                "job_1",
                "demo",
                "deployer",
            )
        assert info["backend_canister_id"].startswith("lvpim-")
        assert info["frontend_canister_id"].startswith("laizb-")

    def test_failed_job_without_canisters_raises(self):
        payload = {
            "Ok": {
                "status": "failed",
                "error": "out of cycles",
                "backend_canister_id": "",
                "frontend_canister_id": "",
            }
        }
        with patch("realms.cli.commands.new._canister_call", return_value=payload):
            with pytest.raises(StageError) as exc:
                poll_installer_until_ready(
                    "tzip5-vaaaa-aaaah-av3ca-cai",
                    "job_1",
                    "demo",
                    "deployer",
                )
            assert "out of cycles" in exc.value.message




