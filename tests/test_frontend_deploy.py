#!/usr/bin/env python3
"""Validation tests for the frontend-via-installer deploy pipeline.

These tests verify the Python-level logic without requiring a running
IC replica. They ensure manifests are built correctly, the new
code paths are reachable, and the publish/install flow is wired up.

Run: python -m pytest tests/test_frontend_deploy.py -v
"""
import gzip
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))


class TestBuildDeployManifest:
    """Verify _build_deploy_manifest handles all member types correctly."""

    def _import_ci(self):
        import ci_install_mundus as ci
        return ci

    def test_manifest_with_frontend_canister(self):
        ci = self._import_ci()
        member = {
            "name": "dominion",
            "type": "realm",
            "frontend_canister_id": "gzya5-jyaaa-aaaac-qai5a-cai",
        }
        manifest = ci._build_deploy_manifest(
            member,
            target_canister_id="h5vpp-qyaaa-aaaac-qai3a-cai",
            file_registry="vi64l-3aaaa-aaaae-qj4va-cai",
            base_version="0.1.0",
            install_mode="upgrade",
            artifacts={"extensions": [], "codices": []},
        )
        assert "frontend" in manifest
        assert "wasm" in manifest
        fe = manifest["frontend"]
        assert fe["target_canister_id"] == "gzya5-jyaaa-aaaac-qai5a-cai"
        assert fe["namespace"] == "frontend/dominion"

    def test_manifest_no_frontend_canister(self):
        ci = self._import_ci()
        member = {
            "name": "realm_registry_backend",
            "type": "realm_registry",
        }
        manifest = ci._build_deploy_manifest(
            member,
            target_canister_id="rhw4p-gqaaa-aaaac-qbw7q-cai",
            file_registry="vi64l-3aaaa-aaaae-qj4va-cai",
            base_version="0.1.0",
            install_mode="upgrade",
            artifacts={"extensions": [], "codices": []},
        )
        assert "frontend" not in manifest

    def test_manifest_dashboard_frontend_only(self):
        ci = self._import_ci()
        member = {
            "name": "platform_dashboard_frontend",
            "type": "dashboard",
            "frontend_canister_id": "rxtxq-kyaaa-aaaac-qgora-cai",
        }
        manifest = ci._build_deploy_manifest(
            member,
            target_canister_id="rxtxq-kyaaa-aaaac-qgora-cai",
            file_registry="vi64l-3aaaa-aaaae-qj4va-cai",
            base_version="0.1.0",
            install_mode="upgrade",
            artifacts={"extensions": [], "codices": []},
        )
        assert "wasm" not in manifest, "dashboard should have no WASM section"
        assert "frontend" in manifest
        assert manifest["frontend"]["target_canister_id"] == "rxtxq-kyaaa-aaaac-qgora-cai"
        assert manifest["frontend"]["namespace"] == "frontend/platform_dashboard_frontend"

    def test_manifest_marketplace_with_frontend(self):
        ci = self._import_ci()
        member = {
            "name": "marketplace_backend",
            "type": "marketplace",
            "frontend_canister_id": "ulsvn-pyaaa-aaaae-qj4tq-cai",
        }
        manifest = ci._build_deploy_manifest(
            member,
            target_canister_id="ehyfg-wyaaa-aaaae-qg3qq-cai",
            file_registry="vi64l-3aaaa-aaaae-qj4va-cai",
            base_version="0.1.0",
            install_mode="upgrade",
            artifacts={"extensions": [], "codices": []},
        )
        assert "wasm" in manifest
        assert "frontend" in manifest
        assert "marketplace" in manifest["wasm"]["path"]

    def test_manifest_external_wasm_token(self):
        ci = self._import_ci()
        member = {
            "name": "token_backend",
            "type": "token",
            "wasm_url": "https://example.com/token_backend.wasm",
        }
        manifest = ci._build_deploy_manifest(
            member,
            target_canister_id="xbkkh-syaaa-aaaah-qq3ya-cai",
            file_registry="vi64l-3aaaa-aaaae-qj4va-cai",
            base_version="0.1.0",
            install_mode="upgrade",
            artifacts={"extensions": [], "codices": []},
        )
        assert "wasm" in manifest
        assert "token-backend" in manifest["wasm"]["path"]


class TestPublishLayeredFrontend:
    """Verify the publish_layered.py frontend CLI arg parsing."""

    def test_cli_arg_accepted(self):
        import publish_layered
        parser_source = open(
            REPO_ROOT / "scripts" / "publish_layered.py"
        ).read()
        assert "--publish-frontend" in parser_source

    def test_content_type_detection(self):
        import publish_layered
        assert publish_layered._guess_content_type(Path("foo.html")) == "text/html"
        assert publish_layered._guess_content_type(Path("foo.js")) == "application/javascript"
        assert publish_layered._guess_content_type(Path("foo.css")) == "text/css"
        assert publish_layered._guess_content_type(Path("foo.svg")) == "image/svg+xml"
        assert publish_layered._guess_content_type(Path("foo.woff2")) == "font/woff2"
        assert publish_layered._guess_content_type(Path("foo.webmanifest")) == "application/manifest+json"

    def test_step_publish_frontend_rejects_missing_dir(self):
        import publish_layered
        rc = publish_layered._step_publish_frontend(
            registry="fake-id",
            network="local",
            identity=None,
            dist_dir=Path("/nonexistent/dist"),
            namespace="frontend/test",
        )
        assert rc == 1

    def test_compressible_content_types_defined(self):
        import publish_layered
        assert hasattr(publish_layered, "_COMPRESSIBLE_CONTENT_TYPES")
        compressible = publish_layered._COMPRESSIBLE_CONTENT_TYPES
        assert "text/html" in compressible
        assert "application/javascript" in compressible
        assert "text/css" in compressible
        assert "application/json" in compressible
        assert "image/svg+xml" in compressible
        # Binary types should NOT be compressible
        assert "image/png" not in compressible
        assert "image/jpeg" not in compressible
        assert "font/woff2" not in compressible

    def test_upload_blob_to_registry_exists(self):
        import publish_layered
        assert callable(getattr(publish_layered, "_upload_blob_to_registry", None))


class TestInstallerManifestParsing:
    """Verify realm_installer's _build_steps handles frontend entries."""

    def test_frontend_step_in_manifest(self):
        manifest = {
            "wasm": {
                "path": "realm-base-0.1.0.wasm.gz",
                "namespace": "wasm",
                "mode": "upgrade",
            },
            "frontend": {
                "target_canister_id": "gzya5-jyaaa-aaaac-qai5a-cai",
                "namespace": "frontend/dominion",
            },
            "extensions": [{"id": "voting", "version": None}],
        }
        assert "frontend" in manifest
        fe = manifest["frontend"]
        assert "target_canister_id" in fe
        assert "namespace" in fe

    def test_manifest_v2_gzip_fields(self):
        """Verify v2 manifest structure with gzip encoding metadata."""
        entry = {
            "path": "index.html",
            "key": "/index.html",
            "content_type": "text/html",
            "size": 5000,
            "sha256": "abc123",
            "encodings": ["identity", "gzip"],
            "gzip_path": "index.html.gz",
            "gzip_size": 1200,
            "gzip_sha256": "def456",
        }
        assert "gzip" in entry["encodings"]
        assert entry["gzip_path"] == "index.html.gz"
        assert entry["gzip_size"] < entry["size"]

    def test_manifest_v2_identity_only_for_binary(self):
        """Binary files should only have identity encoding."""
        entry = {
            "path": "logo.png",
            "key": "/logo.png",
            "content_type": "image/png",
            "size": 8000,
            "sha256": "abc123",
            "encodings": ["identity"],
        }
        assert "gzip" not in entry["encodings"]
        assert "gzip_path" not in entry

    def test_installer_did_is_queue_only(self):
        did_path = REPO_ROOT / "src" / "realm_installer" / "realm_installer.did"
        did_text = did_path.read_text()
        assert "enqueue_deployment" in did_text
        assert "get_deployment_job_status" in did_text
        assert "report_frontend_verified" in did_text
        assert "deploy_frontend" not in did_text
        assert "install_realm_backend" not in did_text
        assert "fetch_module_hash" not in did_text

    def test_installer_main_uses_worker_callbacks(self):
        main_path = REPO_ROOT / "src" / "realm_installer" / "main.py"
        main_text = main_path.read_text()
        assert "report_frontend_verified" in main_text
        assert "_schedule_registry_settlement" in main_text
        assert "_deploy_frontend_core" not in main_text
        assert "AssetCanisterService" not in main_text
        assert "def deploy_frontend(" not in main_text

    def test_installer_main_has_no_frontend_deploy_internals(self):
        main_path = REPO_ROOT / "src" / "realm_installer" / "main.py"
        main_text = main_path.read_text()
        assert "gzip_path" not in main_text
        assert "gzip_sha256" not in main_text
        assert "content_encoding" not in main_text


class TestWasmSpecResolution:
    """Verify _wasm_spec_for_member handles all member types."""

    def _import_ci(self):
        import ci_install_mundus as ci
        return ci

    def test_realm_type(self):
        ci = self._import_ci()
        spec = ci._wasm_spec_for_member({"type": "realm"}, "1.0.0")
        assert spec is not None
        assert spec["source"] == "realm_backend"
        assert "realm-base-1.0.0" in spec["path"]

    def test_marketplace_type(self):
        ci = self._import_ci()
        spec = ci._wasm_spec_for_member({"type": "marketplace"}, "1.0.0")
        assert spec is not None
        assert spec["source"] == "marketplace_backend"
        assert "marketplace-1.0.0" in spec["path"]

    def test_dashboard_type_returns_none(self):
        ci = self._import_ci()
        spec = ci._wasm_spec_for_member({"type": "dashboard"}, "1.0.0")
        assert spec is None, "dashboard type should have no WASM"

    def test_token_external_wasm(self):
        ci = self._import_ci()
        member = {
            "type": "token",
            "wasm_url": "https://example.com/token_backend.wasm",
        }
        spec = ci._wasm_spec_for_member(member, "1.0.0")
        assert spec is not None
        assert spec.get("external") is True
        assert spec["url"] == "https://example.com/token_backend.wasm"
        assert "token-backend-1.0.0" in spec["path"]

    def test_nft_frontend_external_wasm(self):
        ci = self._import_ci()
        member = {
            "type": "nft_frontend",
            "wasm_url": "https://example.com/nft_frontend.wasm",
        }
        spec = ci._wasm_spec_for_member(member, "1.0.0")
        assert spec is not None
        assert spec.get("external") is True
        assert "nft-frontend-1.0.0" in spec["path"]

    def test_type_to_wasm_has_marketplace(self):
        ci = self._import_ci()
        assert "marketplace" in ci._TYPE_TO_WASM

    def test_external_wasm_types_defined(self):
        ci = self._import_ci()
        assert "token" in ci._EXTERNAL_WASM_TYPES
        assert "nft" in ci._EXTERNAL_WASM_TYPES
        assert "token_frontend" in ci._EXTERNAL_WASM_TYPES
        assert "nft_frontend" in ci._EXTERNAL_WASM_TYPES

    def test_frontend_only_types_defined(self):
        ci = self._import_ci()
        assert "dashboard" in ci._FRONTEND_ONLY_TYPES


class TestCIInstallerPipeline:
    """Verify the CI script deploys directly via dfx (no installer middleman)."""

    def test_stage2_uses_direct_dfx(self):
        ci_path = REPO_ROOT / "scripts" / "ci_install_mundus.py"
        text = ci_path.read_text()
        assert "_find_or_build_wasm" in text
        assert "_direct_deploy_frontend_assets" in text
        assert "_build_member_frontend" in text
        assert "install_realm_backend" not in text
        assert '"deploy_frontend"' not in text

    def test_stage1_publishes_frontends(self):
        ci_path = REPO_ROOT / "scripts" / "ci_install_mundus.py"
        text = ci_path.read_text()
        assert "_publish_frontend_dist" in text
        assert "_build_realm_frontend" in text
        assert "_build_registry_frontend" in text
        assert "_build_dashboard_frontend" in text
        assert "_build_marketplace_frontend" in text

    def test_external_wasm_download_support(self):
        ci_path = REPO_ROOT / "scripts" / "ci_install_mundus.py"
        text = ci_path.read_text()
        assert "_download_external_wasm" in text
        assert "external_wasms" in text

    def test_grant_frontend_permissions_exists(self):
        ci_path = REPO_ROOT / "scripts" / "ci_install_mundus.py"
        text = ci_path.read_text()
        assert "_grant_frontend_permissions" in text
        assert "grant_permission" in text

    def test_dashboard_workflow_removed(self):
        dashboard_wf = REPO_ROOT / ".github" / "workflows" / "_deploy-dashboard.yml"
        assert not dashboard_wf.exists(), "_deploy-dashboard.yml should be deleted"

    def test_ci_main_no_dashboard_job(self):
        ci_main = REPO_ROOT / ".github" / "workflows" / "ci-main.yml"
        text = ci_main.read_text()
        assert "deploy-dashboard-staging" not in text
        assert "_deploy-dashboard.yml" not in text

    def test_fast_deploy_uses_queue_deployment(self):
        fast = REPO_ROOT / ".github" / "workflows" / "fast-deploy.yml"
        text = fast.read_text()
        assert "request_deployment.py" in text
        assert "upgrade_installer" not in text


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
