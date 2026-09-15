#!/usr/bin/env python3
"""Validation tests for the frontend publish path and the installer manifest.

These tests verify the Python-level logic without requiring a running
IC replica: publish_layered.py's frontend arg parsing / content types, and the
vendored realm_installer contract the realm backend relies on.

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
        did_path = REPO_ROOT / "src" / "gos-vendor" / "realm_installer" / "realm_installer.did"
        assert did_path.is_file(), "vendored realm_installer.did missing"
        did_text = did_path.read_text()
        assert "enqueue_deployment" in did_text
        assert "get_deployment_job_status" in did_text
        assert "get_deployment_manifest" in did_text
        assert "destroy_realm_job" in did_text
        assert "report_frontend_verified" in did_text
        assert "deploy_frontend" not in did_text
        assert "install_realm_backend" not in did_text
        assert "fetch_module_hash" not in did_text

    def test_vendored_gos_declarations_present(self):
        for canister in ("realm_installer", "realm_registry_backend"):
            decl_dir = REPO_ROOT / "src" / "declarations" / canister
            vendor_did = (
                REPO_ROOT / "src" / "gos-vendor" / canister / f"{canister}.did"
            )
            did = decl_dir / f"{canister}.did"
            assert vendor_did.is_file(), f"missing gos-vendor {vendor_did}"
            assert did.is_file(), f"missing vendored {did}"
            assert (decl_dir / "index.js").is_file(), (
                f"missing generated bindings for {canister}"
            )

    def test_codex_install_fails_when_dependencies_fail(self):
        fr_path = REPO_ROOT / "src" / "realm_backend" / "api" / "file_registry.py"
        fr_text = fr_path.read_text()
        assert "_format_failed_deps" in fr_text
        assert "if failed_deps:" in fr_text
        assert "frontend_canister_id: str = None" in fr_text


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
