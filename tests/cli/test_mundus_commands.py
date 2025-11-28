"""Tests for mundus CLI commands."""

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


def test_mundus_create_generates_structure():
    """Test that mundus create generates the expected folder structure."""
    from cli.realms_cli.commands.mundus import mundus_create_command

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "test_mundus"

        # Mock the create_command and registry_create_command to avoid actual file operations
        with patch("cli.realms_cli.commands.mundus.create_command") as mock_create:
            with patch(
                "cli.realms_cli.commands.mundus.registry_create_command"
            ) as mock_registry:
                with patch("cli.realms_cli.commands.mundus.console"):
                    with patch(
                        "cli.realms_cli.commands.mundus.get_project_root"
                    ) as mock_root:
                        # Set up mock project root with demo manifest
                        mock_root.return_value = Path(__file__).parent.parent.parent

                        try:
                            mundus_create_command(
                                output_dir=str(output_dir),
                                mundus_name="Test Mundus",
                                manifest=None,
                                network="local",
                                deploy=False,
                                identity=None,
                                mode="upgrade",
                            )
                        except SystemExit:
                            pass

                        # Verify create_command was called for each realm
                        assert mock_create.call_count == 3  # realm1, realm2, realm3

                        # Verify registry_create_command was called
                        assert mock_registry.call_count == 1


def test_mundus_create_calls_realm_create_with_correct_args():
    """Test that mundus create calls realm create with correct arguments."""
    from cli.realms_cli.commands.mundus import mundus_create_command

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "test_mundus"

        with patch("cli.realms_cli.commands.mundus.create_command") as mock_create:
            with patch(
                "cli.realms_cli.commands.mundus.registry_create_command"
            ) as mock_registry:
                with patch("cli.realms_cli.commands.mundus.console"):
                    with patch(
                        "cli.realms_cli.commands.mundus.get_project_root"
                    ) as mock_root:
                        mock_root.return_value = Path(__file__).parent.parent.parent

                        try:
                            mundus_create_command(
                                output_dir=str(output_dir),
                                mundus_name="Test Mundus",
                                manifest=None,
                                network="local",
                                deploy=False,
                                identity=None,
                                mode="upgrade",
                            )
                        except SystemExit:
                            pass

                        # Check that create_command was called with deploy=False
                        for call in mock_create.call_args_list:
                            assert call.kwargs.get("deploy") is False


def test_mundus_deploy_calls_realm_deploy():
    """Test that mundus deploy calls realm deploy for each realm."""
    from cli.realms_cli.commands.mundus import mundus_deploy_command

    with tempfile.TemporaryDirectory() as tmpdir:
        mundus_dir = Path(tmpdir) / "test_mundus"
        mundus_dir.mkdir(parents=True)

        # Create a manifest
        manifest = {
            "type": "mundus",
            "name": "Test Mundus",
            "realms": ["realm1", "realm2"],
            "registries": ["registry"],
        }
        with open(mundus_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)

        # Create realm and registry directories
        (mundus_dir / "realm1").mkdir()
        (mundus_dir / "realm2").mkdir()
        (mundus_dir / "registry").mkdir()

        with patch(
            "cli.realms_cli.commands.mundus.realm_deploy_command"
        ) as mock_realm_deploy:
            with patch(
                "cli.realms_cli.commands.mundus.registry_deploy_command"
            ) as mock_registry_deploy:
                with patch("cli.realms_cli.commands.mundus._ensure_dfx_running"):
                    with patch("cli.realms_cli.commands.mundus.console"):
                        try:
                            mundus_deploy_command(
                                mundus_dir=str(mundus_dir),
                                network="local",
                                identity=None,
                                mode="upgrade",
                            )
                        except SystemExit:
                            pass

                        # Verify realm_deploy_command was called for each realm
                        assert mock_realm_deploy.call_count == 2

                        # Verify registry_deploy_command was called
                        assert mock_registry_deploy.call_count == 1


def test_mundus_deploy_missing_manifest():
    """Test that mundus deploy fails gracefully with missing manifest."""
    from cli.realms_cli.commands.mundus import mundus_deploy_command

    with tempfile.TemporaryDirectory() as tmpdir:
        mundus_dir = Path(tmpdir) / "test_mundus"
        mundus_dir.mkdir(parents=True)

        # Don't create manifest - should fail

        with patch("cli.realms_cli.commands.mundus.console"):
            with pytest.raises(SystemExit):
                mundus_deploy_command(
                    mundus_dir=str(mundus_dir),
                    network="local",
                    identity=None,
                    mode="upgrade",
                )


def test_mundus_manifest_structure():
    """Test that mundus creates correct manifest structure."""
    from cli.realms_cli.commands.mundus import mundus_create_command

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "test_mundus"

        with patch("cli.realms_cli.commands.mundus.create_command"):
            with patch("cli.realms_cli.commands.mundus.registry_create_command"):
                with patch("cli.realms_cli.commands.mundus.console"):
                    with patch(
                        "cli.realms_cli.commands.mundus.get_project_root"
                    ) as mock_root:
                        mock_root.return_value = Path(__file__).parent.parent.parent

                        try:
                            mundus_create_command(
                                output_dir=str(output_dir),
                                mundus_name="Manifest Test Mundus",
                                manifest=None,
                                network="local",
                                deploy=False,
                                identity=None,
                                mode="upgrade",
                            )
                        except SystemExit:
                            pass

                        # Verify manifest was created
                        manifest_path = output_dir / "manifest.json"
                        assert manifest_path.exists()

                        with open(manifest_path, "r") as f:
                            manifest = json.load(f)

                        # Verify manifest structure
                        assert manifest["type"] == "mundus"
                        assert manifest["name"] == "Manifest Test Mundus"
                        assert "realms" in manifest
                        assert "registries" in manifest
                        assert isinstance(manifest["realms"], list)
                        assert isinstance(manifest["registries"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
