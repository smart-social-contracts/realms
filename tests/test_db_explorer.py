import json
from unittest.mock import Mock, patch

import pytest
from realms_cli.commands.db import CursorDatabaseExplorer, NavigationState


class TestCursorDatabaseExplorer:
    """Test suite for the enhanced database explorer with GGG model discovery."""

    def test_ggg_model_discovery(self):
        """Test that GGG models are discovered dynamically."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")

        models = explorer._discover_ggg_models()
        assert isinstance(models, dict)

        expected_models = ["users", "organizations", "mandates", "tasks", "treasuries"]
        for model in expected_models:
            assert model in models or model in explorer.entity_types

    def test_relationship_field_discovery(self):
        """Test that relationship fields are discovered dynamically."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")

        relationship_fields = explorer._discover_relationship_fields()
        assert isinstance(relationship_fields, dict)

        expected_patterns = ["user_id", "organization_id", "treasury_id"]
        for pattern in expected_patterns:
            assert pattern in relationship_fields

        assert relationship_fields.get("user_id") == "users"
        assert relationship_fields.get("treasury_id") == "treasuries"

    def test_class_name_to_entity_type_conversion(self):
        """Test conversion from class names to entity types."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")

        assert explorer._class_name_to_entity_type("User") == "users"
        assert explorer._class_name_to_entity_type("Organization") == "organizations"
        assert explorer._class_name_to_entity_type("TaskSchedule") == "task_schedules"
        assert explorer._class_name_to_entity_type("UserProfile") == "user_profiles"
        assert explorer._class_name_to_entity_type("Treasury") == "treasuries"

    def test_entity_parsing_users(self):
        """Test that users entity parsing works correctly."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")

        mock_response = """
        (record {
          success = true;
          data = variant {
            UsersList = record {
              users = vec { "{\\"_id\\": \\"user1\\", \\"name\\": \\"Test User\\"}"; };
              pagination = record { page_num = 0; page_size = 10; total_items_count = 1; total_pages = 1; };
            }
          }
        })
        """

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = mock_response

            result = explorer.list_entities("users", 0, 10)
            assert len(result["items"]) == 1
            assert result["items"][0]["_id"] == "user1"

    def test_entity_parsing_organizations(self):
        """Test that organizations entity parsing works correctly."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")

        mock_response = """
        (record {
          success = true;
          data = variant {
            OrganizationsList = record {
              organizations = vec { "{\\"_id\\": \\"org1\\", \\"name\\": \\"Test Org\\"}"; };
              pagination = record { page_num = 0; page_size = 10; total_items_count = 1; total_pages = 1; };
            }
          }
        })
        """

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = mock_response

            result = explorer.list_entities("organizations", 0, 10)
            assert len(result["items"]) == 1
            assert result["items"][0]["_id"] == "org1"

    def test_entity_parsing_mandates(self):
        """Test that mandates entity parsing works correctly."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")

        mock_response = """
        (record {
          success = true;
          data = variant {
            MandatesList = record {
              mandates = vec { "{\\"_id\\": \\"mandate1\\", \\"title\\": \\"Test Mandate\\"}"; };
              pagination = record { page_num = 0; page_size = 10; total_items_count = 1; total_pages = 1; };
            }
          }
        })
        """

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = mock_response

            result = explorer.list_entities("mandates", 0, 10)
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

            assert explorer.state.entity_type == explorer.entity_types[0]
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
        explorer.state.entity_type = "users"
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

                assert len(explorer.state.navigation_stack) == 1
                assert len(explorer.state.current_items) > 0
                assert explorer.state.view_mode == "record_list"
                assert explorer.state.entity_type == "organizations"
                assert explorer.state.cursor_position == 0

    def test_render_entity_list(self):
        """Test entity list rendering."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        explorer.state.cursor_position = 1

        content = explorer.render_entity_list()

        assert "Realm Database Explorer" in content
        assert "> " in content
        assert "Organizations" in content

    def test_render_record_list(self):
        """Test record list rendering."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        explorer.state.entity_type = "users"
        explorer.state.current_items = [
            {"_id": "user1", "name": "Test User 1"},
            {"_id": "user2", "name": "Test User 2"},
        ]
        explorer.state.cursor_position = 0

        content = explorer.render_record_list()

        assert "Users List" in content
        assert "> " in content
        assert "user1" in content
        assert "Test User 1" in content

    def test_render_record_detail(self):
        """Test record detail rendering with navigable items."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        explorer.state.entity_type = "users"
        explorer.state.selected_item = {
            "_id": "user1",
            "name": "Test User",
            "email": "test@example.com",
            "organization_id": "org1",
            "relations": {"votes": [{"_id": "vote1"}]},
        }
        explorer.state.cursor_position = 0

        content = explorer.render_record_detail()

        assert "User Details" in content
        assert "ID: user1" in content
        assert "name: Test User" in content
        assert "email: test@example.com" in content
        assert "organization_id: org1 → Organization [navigable]" in content
        assert "Properties & Relationships:" in content

        assert hasattr(explorer.state, "navigable_items")
        assert len(explorer.state.navigable_items) > 0

        nav_items = explorer.state.navigable_items
        org_nav_item = next(
            (item for item in nav_items if item["key"] == "organization_id"), None
        )
        assert org_nav_item is not None
        assert org_nav_item["type"] == "relationship_field"
        assert org_nav_item["related_type"] == "organizations"

    def test_relationship_drilling_navigation_flow(self):
        """Test the complete relationship drilling navigation flow."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")

        realm_item = {
            "_id": "realm1",
            "name": "Test Realm",
            "treasury_id": "treasury1",
            "description": "A test realm",
        }

        explorer.state.selected_item = realm_item
        explorer.state.entity_type = "realms"
        explorer.state.view_mode = "record_detail"
        explorer.state.current_items = [realm_item]

        explorer.render_record_detail()

        nav_items = explorer.state.navigable_items
        treasury_nav_index = next(
            (i for i, item in enumerate(nav_items) if item["key"] == "treasury_id"),
            None,
        )
        assert treasury_nav_index is not None

        explorer.state.cursor_position = treasury_nav_index

        initial_stack_size = len(explorer.state.navigation_stack)
        explorer.handle_relationship_drilling()

        assert len(explorer.state.navigation_stack) == initial_stack_size + 1
        assert explorer.state.view_mode == "record_list"
        assert explorer.state.entity_type == "treasuries"
        assert len(explorer.state.current_items) > 0

        last_nav_state = explorer.state.navigation_stack[-1]
        assert last_nav_state["entity_type"] == "realms"
        assert last_nav_state["selected_item"] == realm_item

    def test_get_all_relationships_with_discovered_fields(self):
        """Test that get_all_relationships uses discovered relationship fields."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")

        test_item = {
            "_id": "transfer1",
            "amount": 100,
            "from_user_id": "user1",
            "to_user_id": "user2",
            "organization_id": "org1",
            "relations": {"votes": [{"_id": "vote1", "_type": "Vote"}]},
        }

        relationships = explorer.get_all_relationships(test_item)

        assert "votes" in relationships
        assert len(relationships["votes"]) == 1

        assert "from_user" in relationships
        assert "to_user" in relationships
        assert "organization" in relationships

        assert relationships["from_user"][0]["_id"] == "user1"
        assert relationships["from_user"][0]["_type"] == "User"
        assert relationships["to_user"][0]["_id"] == "user2"
        assert relationships["organization"][0]["_id"] == "org1"

    def test_dynamic_entity_discovery(self):
        """Test that entity types are discovered dynamically."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")

        assert len(explorer.entity_types) > 0

        common_entities = ["users", "organizations", "mandates", "treasuries"]
        discovered_entities = set(explorer.entity_types)

        for entity in common_entities:
            assert (
                entity in discovered_entities
            ), f"Entity '{entity}' should be discovered"

    def test_candid_response_parsing(self):
        """Test robust Candid response parsing."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")

        candid_output = """record {
          success = true;
          data = variant {
            UsersList = record {
              users = vec { 
                "{\\"_id\\": \\"user1\\", \\"name\\": \\"Test User\\", \\"organization_id\\": \\"org1\\"}";
                "{\\"_id\\": \\"user2\\", \\"name\\": \\"Another User\\"}";
              };
              pagination = record { 
                page_num = 0; 
                page_size = 10; 
                total_items_count = 2; 
                total_pages = 1; 
              };
            }
          }
        }"""

        result = explorer._parse_candid_response(candid_output)

        assert "items" in result
        assert len(result["items"]) == 2
        assert result["items"][0]["_id"] == "user1"
        assert result["items"][0]["organization_id"] == "org1"
        assert result["items"][1]["_id"] == "user2"
        assert result["page_num"] == 0
        assert result["total_items_count"] == 2
