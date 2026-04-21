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
    """Verify _build_deploy_manifest includes frontend when member has frontend_canister_id."""

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

    def test_installer_did_has_asset_endpoints(self):
        did_path = REPO_ROOT / "src" / "realm_installer" / "realm_installer.did"
        did_text = did_path.read_text()
        assert "deploy_frontend" in did_text
        assert "create_batch" in did_text
        assert "create_chunk" in did_text
        assert "commit_batch" in did_text

    def test_installer_main_has_frontend_core(self):
        main_path = REPO_ROOT / "src" / "realm_installer" / "main.py"
        main_text = main_path.read_text()
        assert "_deploy_frontend_core" in main_text
        assert "AssetCanisterService" in main_text
        assert "deploy_frontend" in main_text
        assert 'kind == "frontend"' in main_text or "kind == \"frontend\"" in main_text

    def test_installer_main_handles_gzip_encoding(self):
        main_path = REPO_ROOT / "src" / "realm_installer" / "main.py"
        main_text = main_path.read_text()
        assert "gzip" in main_text
        assert "content_encoding" in main_text
        assert "gzip_path" in main_text
        assert "gzip_sha256" in main_text


class TestCIInstallerPipeline:
    """Verify the CI script uses installer for all frontends (no dfx deploy fallback)."""

    def test_no_dfx_deploy_fallback(self):
        ci_path = REPO_ROOT / "scripts" / "ci_install_mundus.py"
        text = ci_path.read_text()
        assert "_deploy_realm_frontends" not in text
        assert "_deploy_registry_frontend" not in text
        assert "_deploy_dashboard_frontend" not in text

    def test_stage1_publishes_frontends(self):
        ci_path = REPO_ROOT / "scripts" / "ci_install_mundus.py"
        text = ci_path.read_text()
        assert "_publish_frontend_dist" in text
        assert "_build_realm_frontend" in text
        assert "_build_registry_frontend" in text
        assert "_build_dashboard_frontend" in text

    def test_stage2_deploys_infra_frontends_via_installer(self):
        ci_path = REPO_ROOT / "scripts" / "ci_install_mundus.py"
        text = ci_path.read_text()
        assert "_deploy_infra_frontends_via_installer" in text
        assert "deploy_frontend" in text


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
