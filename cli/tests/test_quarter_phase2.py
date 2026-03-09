"""Tests for Quarter Phase 2: backend endpoints, CLI commands, and status integration."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# realm_backend is not an installable package; add src/ to path for direct import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from ic_python_db import Database

from realm_backend.ggg import Quarter, QuarterStatus, Realm, Codex


@pytest.fixture(autouse=True)
def clean_db():
    """Clear the database before each test."""
    Database.get_instance().clear()
    yield
    Database.get_instance().clear()


# ---------------------------------------------------------------------------
# Backend logic tests (simulating what the endpoints do without Candid layer)
# ---------------------------------------------------------------------------


class TestRegisterQuarter:
    """Tests for the register_quarter backend logic."""

    def test_register_quarter_creates_entity(self):
        """Test that registering a quarter creates a Quarter entity linked to the realm."""
        realm = Realm(name="Arcadia")
        quarter = Quarter(name="North", canister_id="can-north-123")
        quarter.federation = realm

        assert quarter.name == "North"
        assert quarter.canister_id == "can-north-123"
        assert quarter.federation == realm
        assert quarter in realm.quarter_ids

    def test_register_multiple_quarters(self):
        """Test registering multiple quarters under a single realm."""
        realm = Realm(name="Arcadia")
        q1 = Quarter(name="North", canister_id="can-1")
        q1.federation = realm
        q2 = Quarter(name="South", canister_id="can-2")
        q2.federation = realm
        q3 = Quarter(name="East", canister_id="can-3")
        q3.federation = realm

        assert len(realm.quarter_ids) == 3

    def test_duplicate_canister_id_detection(self):
        """Test that duplicate canister IDs can be detected."""
        realm = Realm(name="Arcadia")
        q1 = Quarter(name="North", canister_id="can-dup")
        q1.federation = realm

        # Check for duplicate
        existing_ids = [q.canister_id for q in Quarter.instances()]
        assert "can-dup" in existing_ids

    def test_quarter_default_values_on_register(self):
        """Test that newly registered quarters have correct defaults."""
        realm = Realm(name="Arcadia")
        q = Quarter(name="Central", canister_id="can-central")
        q.federation = realm

        assert q.population == 0
        assert q.status == QuarterStatus.ACTIVE


class TestDeregisterQuarter:
    """Tests for the deregister_quarter backend logic."""

    def test_deregister_quarter_removes_entity(self):
        """Test that deregistering removes the quarter."""
        realm = Realm(name="Arcadia")
        q = Quarter(name="North", canister_id="can-north")
        q.federation = realm

        assert len(realm.quarter_ids) == 1

        # Simulate deregister (just delete; ic_python_db cleans up on DB clear)
        q.delete()

        assert Quarter.count() == 0

    def test_deregister_by_canister_id(self):
        """Test finding and deregistering a quarter by canister ID."""
        realm = Realm(name="Arcadia")
        q1 = Quarter(name="North", canister_id="can-1")
        q1.federation = realm
        q2 = Quarter(name="South", canister_id="can-2")
        q2.federation = realm

        # Find by canister ID and remove
        target_id = "can-1"
        for q in Quarter.instances():
            if q.canister_id == target_id:
                q.delete()
                break

        assert Quarter.count() == 1
        remaining = list(Quarter.instances())
        assert remaining[0].canister_id == "can-2"


class TestSetQuarterConfig:
    """Tests for the set_quarter_config backend logic."""

    def test_set_quarter_config_marks_realm(self):
        """Test that set_quarter_config sets is_quarter and parent ID."""
        realm = Realm(name="North Quarter Backend")
        assert realm.is_quarter is False

        realm.is_quarter = True
        realm.federation_realm_id = "parent-can-id"
        realm._save()

        # Reload and verify
        loaded = Realm.load(realm._id)
        assert loaded.is_quarter is True
        assert loaded.federation_realm_id == "parent-can-id"

    def test_standalone_realm_unaffected(self):
        """Test that unconfigured realms remain standalone."""
        realm = Realm(name="Standalone Realm")
        assert realm.is_quarter is False
        assert not realm.federation_realm_id


class TestStatusQuarterInfo:
    """Tests for quarter info in status response."""

    def test_status_includes_quarters(self):
        """Test that quarter data can be serialized for status response."""
        realm = Realm(name="Arcadia")
        q1 = Quarter(name="North", canister_id="can-1", population=100)
        q1.federation = realm
        q2 = Quarter(name="South", canister_id="can-2", population=200)
        q2.federation = realm

        # Simulate what status.py does
        quarters = []
        for q in Quarter.instances():
            quarters.append({
                "name": q.name or "",
                "canister_id": q.canister_id or "",
                "population": q.population or 0,
                "status": q.status or "active",
            })

        assert len(quarters) == 2
        assert quarters[0]["population"] == 100
        assert quarters[1]["canister_id"] == "can-2"

    def test_status_empty_quarters_for_standalone(self):
        """Test that standalone realms return empty quarters list."""
        realm = Realm(name="Standalone")

        quarters = []
        for q in Quarter.instances():
            quarters.append({
                "name": q.name,
                "canister_id": q.canister_id,
                "population": q.population,
                "status": q.status,
            })

        assert quarters == []

    def test_status_quarter_mode_fields(self):
        """Test that quarter mode fields are correctly reported."""
        realm = Realm(name="Quarter Backend")
        realm.is_quarter = True
        realm.federation_realm_id = "parent-abc"

        is_quarter = getattr(realm, 'is_quarter', False) or False
        parent_id = getattr(realm, 'federation_realm_id', '') or ''

        assert is_quarter is True
        assert parent_id == "parent-abc"


# ---------------------------------------------------------------------------
# CLI command tests (mock subprocess calls to dfx)
# ---------------------------------------------------------------------------


class TestQuarterCLIList:
    """Tests for quarter list CLI command."""

    @patch("realms.cli.commands.quarter._call_canister")
    @patch("realms.cli.commands.quarter.resolve_realm_ref_to_canister_id")
    @patch("realms.cli.commands.quarter.get_effective_network_and_canister")
    def test_list_parses_status_response(self, mock_network, mock_resolve, mock_call):
        """Test that quarter list correctly parses the status response."""
        from realms.cli.commands.quarter import quarter_list_command

        mock_network.return_value = ("local", "realm_backend")
        mock_resolve.return_value = ("can-parent", "Arcadia")
        mock_call.return_value = {
            "data": {
                "status": {
                    "quarters": [
                        {"name": "North", "canister_id": "can-1", "population": 50, "status": "active"},
                        {"name": "South", "canister_id": "can-2", "population": 30, "status": "active"},
                    ]
                }
            }
        }

        # Should not raise
        quarter_list_command("Arcadia", "local")

        mock_call.assert_called_once_with("can-parent", "status", "()", "local")

    @patch("realms.cli.commands.quarter._call_canister")
    @patch("realms.cli.commands.quarter.resolve_realm_ref_to_canister_id")
    @patch("realms.cli.commands.quarter.get_effective_network_and_canister")
    def test_list_empty_quarters(self, mock_network, mock_resolve, mock_call):
        """Test list output when no quarters exist."""
        from realms.cli.commands.quarter import quarter_list_command

        mock_network.return_value = ("local", "realm_backend")
        mock_resolve.return_value = ("can-parent", "Arcadia")
        mock_call.return_value = {
            "data": {
                "status": {
                    "quarters": []
                }
            }
        }

        # Should not raise
        quarter_list_command("Arcadia", "local")


class TestQuarterCLIRegister:
    """Tests for quarter register CLI command."""

    @patch("realms.cli.commands.quarter._call_canister")
    @patch("realms.cli.commands.quarter.resolve_realm_ref_to_canister_id")
    @patch("realms.cli.commands.quarter.get_effective_network_and_canister")
    def test_register_calls_both_endpoints(self, mock_network, mock_resolve, mock_call):
        """Test that register calls both set_quarter_config and register_quarter."""
        from realms.cli.commands.quarter import quarter_register_command

        mock_network.return_value = ("local", "realm_backend")
        mock_resolve.return_value = ("can-parent", "Arcadia")
        mock_call.return_value = {"success": True}

        quarter_register_command("Arcadia", "North", "can-quarter", "local")

        assert mock_call.call_count == 2
        # First call: set_quarter_config on the quarter
        mock_call.assert_any_call(
            "can-quarter", "set_quarter_config", '("can-parent")', "local"
        )
        # Second call: register_quarter on the parent
        mock_call.assert_any_call(
            "can-parent", "register_quarter", '("North", "can-quarter")', "local"
        )


class TestQuarterCLIRemove:
    """Tests for quarter remove CLI command."""

    @patch("realms.cli.commands.quarter._call_canister")
    @patch("realms.cli.commands.quarter.resolve_realm_ref_to_canister_id")
    @patch("realms.cli.commands.quarter.get_effective_network_and_canister")
    def test_remove_calls_deregister(self, mock_network, mock_resolve, mock_call):
        """Test that remove finds the quarter and calls deregister."""
        from realms.cli.commands.quarter import quarter_remove_command

        mock_network.return_value = ("local", "realm_backend")
        mock_resolve.return_value = ("can-parent", "Arcadia")

        # First call returns status with quarters, second call does deregister
        mock_call.side_effect = [
            {
                "data": {
                    "status": {
                        "quarters": [
                            {"name": "North", "canister_id": "can-1", "population": 50, "status": "active"},
                        ]
                    }
                }
            },
            {"success": True},
        ]

        quarter_remove_command("Arcadia", "North", "local")

        assert mock_call.call_count == 2
        mock_call.assert_any_call("can-parent", "deregister_quarter", '("can-1")', "local")


class TestQuarterCLIStatus:
    """Tests for quarter status CLI command."""

    @patch("realms.cli.commands.quarter._call_canister")
    @patch("realms.cli.commands.quarter.resolve_realm_ref_to_canister_id")
    @patch("realms.cli.commands.quarter.get_effective_network_and_canister")
    def test_status_queries_both_parent_and_quarter(self, mock_network, mock_resolve, mock_call):
        """Test that status queries both parent (for quarter list) and the quarter itself."""
        from realms.cli.commands.quarter import quarter_status_command

        mock_network.return_value = ("local", "realm_backend")
        mock_resolve.return_value = ("can-parent", "Arcadia")

        mock_call.side_effect = [
            # Parent status
            {
                "data": {
                    "status": {
                        "quarters": [
                            {"name": "North", "canister_id": "can-1", "population": 50, "status": "active"},
                        ]
                    }
                }
            },
            # Quarter's own status
            {
                "data": {
                    "status": {
                        "users_count": 50,
                        "transfers_count": 120,
                        "proposals_count": 3,
                        "version": "0.1.0",
                        "is_quarter": True,
                        "parent_realm_canister_id": "can-parent",
                    }
                }
            },
        ]

        quarter_status_command("Arcadia", "North", "local")

        assert mock_call.call_count == 2
        # First: parent status to find the quarter
        mock_call.assert_any_call("can-parent", "status", "()", "local")
        # Second: quarter's own status
        mock_call.assert_any_call("can-1", "status", "()", "local")
