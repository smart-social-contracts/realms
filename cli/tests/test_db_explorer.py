import json
import pytest
from unittest.mock import Mock, patch

from realms_cli.commands.db import CursorDatabaseExplorer, NavigationState


class TestCursorDatabaseExplorer:
    def test_entity_parsing_users(self):
        """Test that users entity parsing works correctly."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        
        mock_response = '''
        (record {
          success = true;
          data = variant {
            UsersList = record {
              users = vec { "{\\"_id\\": \\"user1\\", \\"name\\": \\"Test User\\"}"; };
              pagination = record { page_num = 0; page_size = 10; total_items_count = 1; total_pages = 1; };
            }
          }
        })
        '''
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = mock_response
            
            result = explorer.list_entities("users", 0, 10)
            assert len(result["items"]) == 1
            assert result["items"][0]["_id"] == "user1"
    
    def test_entity_parsing_organizations(self):
        """Test that organizations entity parsing works correctly."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        
        mock_response = '''
        (record {
          success = true;
          data = variant {
            OrganizationsList = record {
              organizations = vec { "{\\"_id\\": \\"org1\\", \\"name\\": \\"Test Org\\"}"; };
              pagination = record { page_num = 0; page_size = 10; total_items_count = 1; total_pages = 1; };
            }
          }
        })
        '''
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = mock_response
            
            result = explorer.list_entities("organizations", 0, 10)
            assert len(result["items"]) == 1
            assert result["items"][0]["_id"] == "org1"
    
    def test_entity_parsing_mandates(self):
        """Test that mandates entity parsing works correctly."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        
        mock_response = '''
        (record {
          success = true;
          data = variant {
            MandatesList = record {
              mandates = vec { "{\\"_id\\": \\"mandate1\\", \\"title\\": \\"Test Mandate\\"}"; };
              pagination = record { page_num = 0; page_size = 10; total_items_count = 1; total_pages = 1; };
            }
          }
        })
        '''
        
        with patch('subprocess.run') as mock_run:
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
        
        with patch.object(explorer, 'refresh_data') as mock_refresh:
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
        explorer.state.navigation_stack = [{
            'entity_type': 'users',
            'selected_item': {'_id': 'user1'},
            'cursor_position': 2,
            'view_mode': 'record_detail',
            'current_items': [{'_id': 'user1'}]
        }]
        
        explorer.handle_back_navigation()
        
        assert explorer.state.entity_type == 'users'
        assert explorer.state.selected_item == {'_id': 'user1'}
        assert explorer.state.cursor_position == 2
        assert explorer.state.view_mode == 'record_detail'
        assert explorer.state.current_items == [{'_id': 'user1'}]
        assert len(explorer.state.navigation_stack) == 0
    
    def test_relationship_drilling(self):
        """Test navigation into relationships."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        explorer.state.selected_item = {
            "_id": "user1",
            "organization_id": "org1"
        }
        explorer.state.view_mode = "record_detail"
        explorer.state.cursor_position = 0
        explorer.state.entity_type = "users"
        explorer.state.current_items = [{"_id": "user1"}]
        
        explorer.render_record_detail()
        
        if hasattr(explorer.state, 'navigable_items') and explorer.state.navigable_items:
            org_nav_index = next(
                (i for i, item in enumerate(explorer.state.navigable_items) if item.get('key') == 'organization_id'), 
                0
            )
            explorer.state.cursor_position = org_nav_index
            
            with patch.object(explorer, 'list_entities') as mock_list:
                mock_list.return_value = {"items": [{"_id": "org1", "name": "Test Org"}], "page_num": 0}
                
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
        assert "Organization" in content
    
    def test_render_record_list(self):
        """Test record list rendering."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        explorer.state.entity_type = "users"
        explorer.state.current_items = [
            {"_id": "user1", "name": "Test User 1"},
            {"_id": "user2", "name": "Test User 2"}
        ]
        explorer.state.cursor_position = 0
        
        content = explorer.render_record_list()
        
        assert "Users List" in content
        assert "> " in content
        assert "user1" in content
        assert "Test User 1" in content
    
    def test_render_record_detail(self):
        """Test record detail rendering."""
        explorer = CursorDatabaseExplorer("local", "realm_backend")
        explorer.state.entity_type = "users"
        explorer.state.selected_item = {
            "_id": "user1",
            "name": "Test User",
            "email": "test@example.com",
            "relations": {
                "votes": [{"_id": "vote1"}]
            }
        }
        explorer.state.cursor_position = 0
        
        content = explorer.render_record_detail()
        
        assert "User Details" in content
        assert "ID: user1" in content
        assert "name: Test User" in content
        assert "email: test@example.com" in content
        assert "Relationships:" in content
        assert "votes: 1 items" in content
