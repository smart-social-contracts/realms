"""Tests for Realms CLI utilities."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from realms.cli.utils import (
    create_directory_structure,
    generate_port_from_branch,
    get_current_branch,
    load_config,
    save_config,
)


class TestConfigUtils:
    """Test configuration utilities."""

    def test_load_config_valid(self):
        """Test loading valid configuration."""
        config_data = {
            "realm": {
                "id": "test",
                "name": "Test",
                "description": "Test realm",
                "admin_principal": "2vxsx-fae",
            },
            "deployment": {"network": "local"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            loaded_config = load_config(config_path)
            assert loaded_config["realm"]["id"] == "test"
            assert loaded_config["deployment"]["network"] == "local"
        finally:
            Path(config_path).unlink()

    def test_load_config_not_found(self):
        """Test loading non-existent configuration."""
        with pytest.raises(FileNotFoundError):
            load_config("non_existent_config.json")

    def test_save_config(self):
        """Test saving configuration."""
        config_data = {"test": "data"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_path = f.name

        try:
            save_config(config_data, config_path)

            # Verify file was created and contains correct data
            with open(config_path, "r") as f:
                saved_data = json.load(f)

            assert saved_data["test"] == "data"
        finally:
            Path(config_path).unlink()


class TestPortGeneration:
    """Test port generation utilities."""

    def test_generate_port_main_branch(self):
        """Test port generation for main branch."""
        port = generate_port_from_branch("main")
        assert port == 8000

    def test_generate_port_other_branches(self):
        """Test port generation for other branches."""
        # Test that different branches get different ports
        port1 = generate_port_from_branch("feature/test")
        port2 = generate_port_from_branch("develop")

        assert port1 != port2
        assert 8001 <= port1 <= 8100
        assert 8001 <= port2 <= 8100

    def test_generate_port_consistency(self):
        """Test that same branch always gets same port."""
        branch = "feature/consistent"
        port1 = generate_port_from_branch(branch)
        port2 = generate_port_from_branch(branch)

        assert port1 == port2


class TestGitUtils:
    """Test git utilities."""

    @patch("subprocess.run")
    def test_get_current_branch_success(self, mock_run):
        """Test successful branch detection."""
        mock_run.return_value = MagicMock(stdout="feature/test\n", returncode=0)

        branch = get_current_branch()
        assert branch == "feature/test"

    @patch("subprocess.run")
    def test_get_current_branch_failure(self, mock_run):
        """Test fallback when git fails."""
        mock_run.side_effect = Exception("Git not available")

        branch = get_current_branch()
        assert branch == "main"


class TestDirectoryStructure:
    """Test directory structure creation."""

    def test_create_directory_structure(self):
        """Test creating directory structure."""
        structure = {
            "src": {
                "backend": {"main.py": "# Backend code", "__init__.py": ""},
                "frontend": {"package.json": '{"name": "test"}'},
            },
            "README.md": "# Test Project",
            "config.json": '{"test": true}',
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            create_directory_structure(base_path, structure)

            # Check directories were created
            assert (base_path / "src").is_dir()
            assert (base_path / "src" / "backend").is_dir()
            assert (base_path / "src" / "frontend").is_dir()

            # Check files were created with correct content
            assert (base_path / "README.md").read_text() == "# Test Project"
            assert (base_path / "config.json").read_text() == '{"test": true}'
            assert (
                base_path / "src" / "backend" / "main.py"
            ).read_text() == "# Backend code"
            assert (base_path / "src" / "backend" / "__init__.py").read_text() == ""

    def test_create_nested_structure(self):
        """Test creating deeply nested structure."""
        structure = {
            "level1": {"level2": {"level3": {"deep_file.txt": "Deep content"}}}
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            create_directory_structure(base_path, structure)

            deep_file = base_path / "level1" / "level2" / "level3" / "deep_file.txt"
            assert deep_file.exists()
            assert deep_file.read_text() == "Deep content"
