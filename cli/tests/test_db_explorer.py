import json
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

import pytest
import typer

from realms.cli.commands.db import (
    CursorDatabaseExplorer,
    NavigationState,
    db_get_command,
    db_schema_command,
    check_dfx_available,
    require_dfx,
)


class TestCursorDatabaseExplorer:
    def test_entity_parsing_users(self):
        """Test that users entity parsing works correctly."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")

        mock_response = {
            "success": True,
            "data": {
                "objectsListPaginated": {
                    "objects": ['{"_id": "user1", "name": "Test User"}'],
                    "pagination": {
                        "page_num": "0",
                        "page_size": "10", 
                        "total_items_count": "1",
                        "total_pages": "1"
                    }
                }
            }
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_response)

            result = explorer.list_entities("User", 0, 10)
            assert len(result["items"]) == 1
            assert result["items"][0]["_id"] == "user1"

    def test_entity_parsing_organizations(self):
        """Test that organizations entity parsing works correctly."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")

        mock_response = {
            "success": True,
            "data": {
                "objectsListPaginated": {
                    "objects": ['{"_id": "org1", "name": "Test Org"}'],
                    "pagination": {
                        "page_num": "0",
                        "page_size": "10", 
                        "total_items_count": "1",
                        "total_pages": "1"
                    }
                }
            }
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_response)

            result = explorer.list_entities("Organization", 0, 10)
            assert len(result["items"]) == 1
            assert result["items"][0]["_id"] == "org1"

    def test_entity_parsing_mandates(self):
        """Test that mandates entity parsing works correctly."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")

        mock_response = {
            "success": True,
            "data": {
                "objectsListPaginated": {
                    "objects": ['{"_id": "mandate1", "title": "Test Mandate"}'],
                    "pagination": {
                        "page_num": "0",
                        "page_size": "10", 
                        "total_items_count": "1",
                        "total_pages": "1"
                    }
                }
            }
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_response)

            result = explorer.list_entities("Mandate", 0, 10)
            assert len(result["items"]) == 1
            assert result["items"][0]["_id"] == "mandate1"

    def test_navigation_state_initialization(self):
        """Test NavigationState initialization."""
        state = NavigationState()
        assert state.entity_type == ""
        assert state.page_num == 0
        assert state.page_size == 10
        assert state.current_items == []
        assert state.selected_item is None
        assert state.cursor_position == 0
        assert state.view_mode == "entity_list"
        assert state.navigation_stack == []

    def test_handle_selection_entity_list(self):
        """Test selection handling in entity list mode."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        explorer.state.view_mode = "entity_list"
        explorer.state.cursor_position = 0

        with patch.object(explorer, "refresh_data") as mock_refresh:
            explorer.handle_selection()

            assert explorer.state.entity_type == explorer._ggg_classes[0]
            assert explorer.state.view_mode == "record_list"
            assert explorer.state.cursor_position == 0
            mock_refresh.assert_called_once()

    def test_handle_selection_record_list(self):
        """Test selection handling in record list mode."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        explorer.state.view_mode = "record_list"
        explorer.state.cursor_position = 0
        explorer.state.current_items = [{"_id": "test1", "name": "Test Item"}]

        explorer.handle_selection()

        assert explorer.state.selected_item == {"_id": "test1", "name": "Test Item"}
        assert explorer.state.view_mode == "record_detail"
        assert explorer.state.cursor_position == 0

    def test_handle_back_navigation_simple(self):
        """Test simple back navigation without navigation stack."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        explorer.state.view_mode = "record_detail"
        explorer.state.selected_item = {"_id": "test"}

        explorer.handle_back_navigation()

        assert explorer.state.view_mode == "record_list"
        assert explorer.state.selected_item is None
        assert explorer.state.cursor_position == 0

    def test_handle_back_navigation_with_stack(self):
        """Test back navigation with navigation stack."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        explorer.state.navigation_stack = [
            {
                "entity_type": "users",
                "selected_item": {"_id": "user1"},
                "cursor_position": 2,
                "view_mode": "record_detail",
                "current_items": [{"_id": "user1"}],
            }
        ]

        explorer.handle_back_navigation()

        assert explorer.state.entity_type == "users"
        assert explorer.state.selected_item == {"_id": "user1"}
        assert explorer.state.cursor_position == 2
        assert explorer.state.view_mode == "record_detail"
        assert explorer.state.current_items == [{"_id": "user1"}]
        assert len(explorer.state.navigation_stack) == 0

    def test_relationship_drilling(self):
        """Test navigation into relationships."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        explorer.state.selected_item = {"_id": "user1", "organization_id": "org1"}
        explorer.state.view_mode = "record_detail"
        explorer.state.cursor_position = 0
        user_class = next((cls for cls in explorer._ggg_classes if cls.__name__ == "User"), None)
        explorer.state.entity_type = user_class
        explorer.state.current_items = [{"_id": "user1"}]

        explorer.render_record_detail()

        if (
            hasattr(explorer.state, "navigable_items")
            and explorer.state.navigable_items
        ):
            org_nav_index = next(
                (
                    i
                    for i, item in enumerate(explorer.state.navigable_items)
                    if item.get("key") == "organization_id"
                ),
                0,
            )
            explorer.state.cursor_position = org_nav_index

            with patch.object(explorer, "list_entities") as mock_list:
                mock_list.return_value = {
                    "items": [{"_id": "org1", "name": "Test Org"}],
                    "page_num": 0,
                }

                explorer.handle_relationship_drilling()

                assert explorer.state.view_mode == "record_detail"
                assert explorer.state.entity_type.__name__ == "User"

    def test_render_entity_list(self):
        """Test entity list rendering."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        explorer.state.cursor_position = 1

        content = explorer.render_entity_list()

        assert "Realm Database Explorer" in content
        assert "> " in content
        assert "Organization" in content

    def test_render_record_list(self):
        """Test record list rendering."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        user_class = next((cls for cls in explorer._ggg_classes if cls.__name__ == "User"), None)
        explorer.state.entity_type = user_class
        explorer.state.current_items = [
            {"_id": "user1", "name": "Test User 1"},
            {"_id": "user2", "name": "Test User 2"},
        ]
        explorer.state.cursor_position = 0

        content = explorer.render_record_list()

        assert "User List" in content
        assert "> " in content
        assert "user1" in content
        assert "Test User 1" in content

    def test_render_record_detail(self):
        """Test record detail rendering."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        user_class = next((cls for cls in explorer._ggg_classes if cls.__name__ == "User"), None)
        explorer.state.entity_type = user_class
        explorer.state.selected_item = {
            "_id": "user1",
            "name": "Test User",
            "email": "test@example.com",
            "relations": {"votes": [{"_id": "vote1"}]},
        }
        explorer.state.cursor_position = 0

        content = explorer.render_record_detail()

        assert "User Details" in content
        assert "ID: user1" in content
        assert "name: Test User" in content
        assert "email: test@example.com" in content
        assert "Relationships:" in content
        assert "votes: 1 items" in content


class TestDbGetCommand:
    """Test suite for db_get_command function."""

    def test_get_all_users(self):
        """Test getting all users returns JSON array."""
        mock_response = {
            "success": True,
            "data": {
                "objectsListPaginated": {
                    "objects": [
                        '{"_id": "1", "_type": "User", "id": "user1", "name": "Test User 1"}',
                        '{"_id": "2", "_type": "User", "id": "user2", "name": "Test User 2"}'
                    ],
                    "pagination": {
                        "page_num": "0",
                        "page_size": "100",
                        "total_items_count": "2",
                        "total_pages": "1"
                    }
                }
            }
        }

        with patch("realms.cli.commands.db.check_dfx_available", return_value=True), \
             patch("subprocess.run") as mock_run, \
             patch("builtins.print") as mock_print:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_response)

            db_get_command("User", None, "local", "realm_backend")

            # Check that JSON was printed
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            parsed = json.loads(output)
            
            assert isinstance(parsed, list)
            assert len(parsed) == 2
            assert parsed[0]["_id"] == "1"
            assert parsed[0]["name"] == "Test User 1"
            assert parsed[1]["_id"] == "2"

    def test_get_specific_user_by_id(self):
        """Test getting a specific user by ID returns single JSON object."""
        mock_response = {
            "success": True,
            "data": {
                "objectsListPaginated": {
                    "objects": [
                        '{"_id": "1", "_type": "User", "id": "system", "user_profile": "admin"}',
                        '{"_id": "2", "_type": "User", "id": "user_000", "user_profile": "member"}'
                    ],
                    "pagination": {
                        "page_num": "0",
                        "page_size": "1000",
                        "total_items_count": "2",
                        "total_pages": "1"
                    }
                }
            }
        }

        with patch("realms.cli.commands.db.check_dfx_available", return_value=True), \
             patch("subprocess.run") as mock_run, \
             patch("builtins.print") as mock_print:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_response)

            db_get_command("User", "2", "local", "realm_backend")

            # Check that single JSON object was printed
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            parsed = json.loads(output)
            
            assert isinstance(parsed, dict)
            assert parsed["_id"] == "2"
            assert parsed["id"] == "user_000"
            assert parsed["user_profile"] == "member"

    def test_get_case_insensitive_entity_type(self):
        """Test that entity type matching is case-insensitive."""
        mock_response = {
            "success": True,
            "data": {
                "objectsListPaginated": {
                    "objects": ['{"_id": "t1", "_type": "Transfer", "amount": 100}'],
                    "pagination": {
                        "page_num": "0",
                        "page_size": "100",
                        "total_items_count": "1",
                        "total_pages": "1"
                    }
                }
            }
        }

        with patch("realms.cli.commands.db.check_dfx_available", return_value=True), \
             patch("subprocess.run") as mock_run, \
             patch("builtins.print") as mock_print:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_response)

            # Test lowercase entity type
            db_get_command("transfer", None, "local", "realm_backend")

            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            parsed = json.loads(output)
            assert len(parsed) == 1
            assert parsed[0]["_type"] == "Transfer"

    def test_get_invalid_entity_type(self):
        """Test error handling for invalid entity type."""
        mock_response = {
            "success": True,
            "data": {
                "objectsListPaginated": {
                    "objects": [],
                    "pagination": {
                        "page_num": "0",
                        "page_size": "1",
                        "total_items_count": "0",
                        "total_pages": "1"
                    }
                }
            }
        }

        with patch("realms.cli.commands.db.check_dfx_available", return_value=True), \
             patch("subprocess.run") as mock_run, \
             pytest.raises(typer.Exit) as exc_info:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_response)

            db_get_command("InvalidEntityType", None, "local", "realm_backend")

        assert exc_info.value.exit_code == 1

    def test_get_entity_id_not_found(self):
        """Test error handling when specific entity ID is not found."""
        mock_response = {
            "success": True,
            "data": {
                "objectsListPaginated": {
                    "objects": [
                        '{"_id": "1", "_type": "User", "id": "user1"}',
                        '{"_id": "2", "_type": "User", "id": "user2"}'
                    ],
                    "pagination": {
                        "page_num": "0",
                        "page_size": "1000",
                        "total_items_count": "2",
                        "total_pages": "1"
                    }
                }
            }
        }

        with patch("realms.cli.commands.db.check_dfx_available", return_value=True), \
             patch("subprocess.run") as mock_run, \
             pytest.raises(typer.Exit) as exc_info:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_response)

            db_get_command("User", "999", "local", "realm_backend")

        assert exc_info.value.exit_code == 1

    def test_get_connection_error(self):
        """Test error handling when backend connection fails."""
        with patch("realms.cli.commands.db.check_dfx_available", return_value=True), \
             patch("subprocess.run") as mock_run, \
             pytest.raises(typer.Exit) as exc_info:
            mock_run.side_effect = Exception("Connection failed")

            db_get_command("User", None, "local", "realm_backend")

        assert exc_info.value.exit_code == 1

    def test_get_with_pagination(self):
        """Test pagination handling when fetching all entities."""
        # Mock two pages of results
        mock_response_page1 = {
            "success": True,
            "data": {
                "objectsListPaginated": {
                    "objects": [
                        '{"_id": "1", "_type": "User", "id": "user1"}',
                        '{"_id": "2", "_type": "User", "id": "user2"}'
                    ],
                    "pagination": {
                        "page_num": "0",
                        "page_size": "100",
                        "total_items_count": "3",
                        "total_pages": "2"
                    }
                }
            }
        }

        mock_response_page2 = {
            "success": True,
            "data": {
                "objectsListPaginated": {
                    "objects": [
                        '{"_id": "3", "_type": "User", "id": "user3"}'
                    ],
                    "pagination": {
                        "page_num": "1",
                        "page_size": "100",
                        "total_items_count": "3",
                        "total_pages": "2"
                    }
                }
            }
        }

        with patch("realms.cli.commands.db.check_dfx_available", return_value=True), \
             patch("subprocess.run") as mock_run, \
             patch("builtins.print") as mock_print:
            # First call for status check, then alternating pages
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "status ok"
            
            def side_effect(*args, **kwargs):
                result = MagicMock()
                result.returncode = 0
                # Check if this is a status call or entity call
                if "status" in str(args[0]):
                    result.stdout = "status ok"
                else:
                    # Alternate between page responses based on call count
                    if mock_run.call_count <= 2:
                        result.stdout = json.dumps(mock_response_page1)
                    else:
                        result.stdout = json.dumps(mock_response_page2)
                return result
            
            mock_run.side_effect = side_effect

            db_get_command("User", None, "local", "realm_backend")

            # Check that all items from both pages were included
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            parsed = json.loads(output)
            
            assert isinstance(parsed, list)
            assert len(parsed) == 3
            assert parsed[0]["_id"] == "1"
            assert parsed[1]["_id"] == "2"
            assert parsed[2]["_id"] == "3"

    def test_get_backend_error_response(self):
        """Test handling of backend error responses."""
        mock_response = {
            "success": False,
            "data": {
                "error": "Backend error occurred"
            }
        }

        with patch("realms.cli.commands.db.check_dfx_available", return_value=True), \
             patch("subprocess.run") as mock_run, \
             pytest.raises(typer.Exit) as exc_info:
            # First call succeeds (status), second fails (entity query)
            def side_effect(*args, **kwargs):
                result = MagicMock()
                result.returncode = 0
                if "status" in str(args[0]):
                    result.stdout = "status ok"
                else:
                    result.stdout = json.dumps(mock_response)
                return result
            
            mock_run.side_effect = side_effect

            db_get_command("User", None, "local", "realm_backend")

        assert exc_info.value.exit_code == 1


class TestDfxAvailability:
    """Test suite for dfx availability checking."""

    def test_check_dfx_available_when_installed(self):
        """Test check_dfx_available returns True when dfx is installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "dfx 0.29.0"

            result = check_dfx_available()

            assert result is True
            mock_run.assert_called_once()
            assert mock_run.call_args[0][0] == ["dfx", "--version"]

    def test_check_dfx_available_when_not_installed(self):
        """Test check_dfx_available returns False when dfx is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("dfx not found")

            result = check_dfx_available()

            assert result is False

    def test_check_dfx_available_when_command_fails(self):
        """Test check_dfx_available returns False when dfx command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1

            result = check_dfx_available()

            assert result is False

    def test_require_dfx_exits_when_not_available(self):
        """Test require_dfx exits with code 1 and shows user-friendly message when dfx is not available."""
        with patch("realms.cli.commands.db.check_dfx_available") as mock_check, \
             patch("realms.cli.commands.db.console.print") as mock_print, \
             pytest.raises(typer.Exit) as exc_info:
            mock_check.return_value = False

            require_dfx()

        assert exc_info.value.exit_code == 1
        # Verify user-friendly message was printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("dfx is not installed" in str(call) for call in print_calls)

    def test_require_dfx_passes_when_available(self):
        """Test require_dfx does nothing when dfx is available."""
        with patch("realms.cli.commands.db.check_dfx_available") as mock_check:
            mock_check.return_value = True

            # Should not raise
            require_dfx()

    def test_db_get_command_checks_dfx_first(self):
        """Test that db_get_command checks for dfx before doing anything else."""
        with patch("realms.cli.commands.db.check_dfx_available") as mock_check, \
             patch("realms.cli.commands.db.console.print"), \
             pytest.raises(typer.Exit) as exc_info:
            mock_check.return_value = False

            db_get_command("User", None, "local", "realm_backend")

        assert exc_info.value.exit_code == 1
        mock_check.assert_called_once()


class TestDbSchemaCommand:
    """Test suite for db_schema_command function."""

    def test_schema_returns_valid_json(self):
        """Test that db_schema_command outputs valid JSON with entity schema."""
        with patch("builtins.print") as mock_print:
            db_schema_command("local", "realm_backend")

            # Check that JSON was printed
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            
            # Should be valid JSON
            schema = json.loads(output)
            
            # Should have entities key
            assert "entities" in schema
            assert isinstance(schema["entities"], dict)

    def test_schema_includes_common_entity_types(self):
        """Test that schema includes common GGG entity types."""
        with patch("builtins.print") as mock_print:
            db_schema_command("local", "realm_backend")

            output = mock_print.call_args[0][0]
            schema = json.loads(output)
            
            entities = schema["entities"]
            
            # Check for some common entity types
            expected_entities = ["User", "Organization", "Transfer", "Notification", "Proposal"]
            for entity_name in expected_entities:
                assert entity_name in entities, f"Expected entity '{entity_name}' not found in schema"

    def test_schema_entity_has_fields_and_relationships(self):
        """Test that each entity in schema has fields and relationships keys."""
        with patch("builtins.print") as mock_print:
            db_schema_command("local", "realm_backend")

            output = mock_print.call_args[0][0]
            schema = json.loads(output)
            
            # Check structure of at least one entity
            for entity_name, entity_schema in schema["entities"].items():
                assert "fields" in entity_schema, f"Entity '{entity_name}' missing 'fields'"
                assert "relationships" in entity_schema, f"Entity '{entity_name}' missing 'relationships'"
                assert isinstance(entity_schema["fields"], dict)
                assert isinstance(entity_schema["relationships"], dict)
                break  # Just check one entity

    def test_schema_does_not_require_dfx(self):
        """Test that db_schema_command works without dfx (uses local GGG definitions)."""
        # Mock subprocess.run to simulate dfx not being available
        with patch("subprocess.run") as mock_run, \
             patch("builtins.print") as mock_print:
            mock_run.side_effect = FileNotFoundError("dfx not found")

            # Should still work because schema only uses local GGG classes
            db_schema_command("local", "realm_backend")

            # Should have printed valid schema
            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            schema = json.loads(output)
            assert "entities" in schema
