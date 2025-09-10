"""Database explorer command for interactive Realm database exploration."""

import json
import re
import subprocess
import sys
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import importlib
import inspect

import typer
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from rich.console import Console

from ..utils import get_effective_network_and_canister
from ..utils import get_logger

logger = get_logger("db")

console = Console()


ENTITY_DESCRIPTIONS = {
    "users": "System users and their profiles",
    "humans": "Human entities and identity records",
    "organizations": "Organizational entities and structures",
    "mandates": "Governance mandates and authorizations",
    "tasks": "Scheduled and executed tasks",
    "task_schedules": "Task scheduling configurations",
    "transfers": "Asset transfers between entities",
    "trades": "Completed trading transactions",
    "instruments": "Financial and governance instruments",
    "codexes": "Executable code and logic",
    "disputes": "Conflict resolution records",
    "licenses": "Permissions and authorizations",
    "realms": "Realm configurations and metadata",
    "proposals": "Governance proposals and voting",
    "votes": "Individual voting records",
    "treasuries": "Treasury and vault management",
    "user_profiles": "User profile configurations and permissions",
}


@dataclass
class NavigationState:
    """Tracks current navigation state in the database explorer."""

    entity_type: str = ""
    page_num: int = 0
    page_size: int = 10
    current_items: List[Dict] = None
    selected_item: Optional[Dict] = None
    cursor_position: int = 0
    view_mode: str = "entity_list"
    navigation_stack: List[Dict] = None

    def __post_init__(self):
        if self.current_items is None:
            self.current_items = []
        if self.navigation_stack is None:
            self.navigation_stack = []


class CursorDatabaseExplorer:
    """Interactive database explorer for Realm entities."""

    def __init__(self, network: str, canister: str):
        self.network = network
        self.canister = canister
        self.state = NavigationState()
        self.app = None
        
        # Cache for relationship mappings discovered from GGG models
        self._relationship_cache = None
        self._entity_models_cache = None

        self.entity_types = self._discover_entity_types()

    def call_backend(self, method: str, args: str = "") -> Dict[str, Any]:
        """Call backend canister method and return parsed result."""
        cmd = ["dfx", "canister", "call"]
        if self.network != "local":
            cmd.extend(["--network", self.network])
        cmd.extend(["--query", self.canister, method])
        if args:
            cmd.append(args)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                output = result.stdout.strip()

                if method == "status":
                    return {"success": True, "data": output}

                if output.startswith("(") and output.endswith(")"):
                    output = output[1:-1]

                return self._parse_candid_response(output)
            else:
                return {
                    "items": [],
                    "total_items_count": 0,
                    "total_pages": 1,
                    "page_num": 0,
                    "page_size": 10,
                    "error": result.stderr,
                }
        except Exception as e:
            return {
                "items": [],
                "total_items_count": 0,
                "total_pages": 1,
                "page_num": 0,
                "page_size": 10,
                "error": str(e),
            }

    def _parse_candid_response(self, candid_output: str) -> Dict[str, Any]:
        """Parse Candid response using structured approach instead of fragile regex."""
        try:
            json_strings = []

            vec_start = candid_output.find("vec {")
            if vec_start >= 0:
                brace_count = 0
                vec_content_start = vec_start + 5  # len("vec {")
                vec_content_end = vec_content_start

                for i, char in enumerate(
                    candid_output[vec_content_start:], vec_content_start
                ):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        if brace_count == 0:
                            vec_content_end = i
                            break
                        brace_count -= 1

                vec_content = candid_output[vec_content_start:vec_content_end]

                for item in vec_content.split('";'):
                    item = item.strip()
                    if item.startswith('"'):
                        item = item[1:]
                    if item.endswith('"'):
                        item = item[:-1]
                    if item:
                        try:
                            item = item.replace('\\"', '"')
                            parsed_item = json.loads(item)
                            json_strings.append(parsed_item)
                        except json.JSONDecodeError:
                            continue

            total_items = self._extract_number(candid_output, "total_items_count")
            total_pages = self._extract_number(candid_output, "total_pages")
            page_num = self._extract_number(candid_output, "page_num")
            page_size = self._extract_number(candid_output, "page_size")

            return {
                "items": json_strings,
                "total_items_count": total_items,
                "total_pages": total_pages,
                "page_num": page_num,
                "page_size": page_size,
            }
        except Exception:
            return {
                "items": [],
                "total_items_count": 0,
                "total_pages": 1,
                "page_num": 0,
                "page_size": 10,
            }

    def _extract_number(self, text: str, field_name: str) -> int:
        """Extract a number field from Candid text using simple string operations."""
        try:
            pattern = f"{field_name} = "
            start = text.find(pattern)
            if start >= 0:
                start += len(pattern)
                end = start
                while end < len(text) and (text[end].isdigit() or text[end] == "_"):
                    end += 1
                number_str = text[start:end].replace(
                    "_", ""
                )  # Remove Candid number suffixes
                return int(number_str) if number_str else 0
            return 0
        except (ValueError, IndexError):
            return 0

    def _discover_entity_types(self) -> List[str]:
        """Discover available entity types by checking GGG models and backend API methods."""
        # First, try to get entity types from GGG models
        models = self._discover_ggg_models()
        entity_types_from_models = list(models.keys()) if models else []
        
        # Fallback list for when GGG model discovery fails
        fallback_entities = [
            "users",
            "organizations", 
            "mandates",
            "tasks",
            "transfers",
            "trades",
            "instruments",
            "codexes",
            "disputes",
            "licenses",
            "realms",
            "proposals",
            "votes",
            "treasuries",  # Add missing entities
            "humans",
            "citizens",
            "identities",
            "user_profiles",
            "task_schedules",
        ]
        
        # Use GGG models if available, otherwise use fallback
        candidate_entities = entity_types_from_models if entity_types_from_models else fallback_entities

        available_entities = []
        for entity_type in candidate_entities:
            try:
                result = self.call_backend(f"get_{entity_type}", "(0, 1)")
                if "error" not in result or "method does not exist" not in str(
                    result.get("error", "")
                ):
                    available_entities.append(entity_type)
            except Exception:
                logger.error(f"Error checking entity type {entity_type}")

        return available_entities if available_entities else fallback_entities

    def list_entities(
        self, entity_type: str, page_num: int = 0, page_size: int = 10
    ) -> Dict[str, Any]:
        """List entities of given type with pagination."""
        method = f"get_{entity_type}"
        args = f"({page_num}, {page_size})"
        return self.call_backend(method, args)

    def create_key_bindings(self):
        """Create key bindings for cursor navigation."""
        kb = KeyBindings()

        @kb.add("up")
        def move_up(event):
            if self.state.cursor_position > 0:
                self.state.cursor_position -= 1
                event.app.invalidate()

        @kb.add("down")
        def move_down(event):
            max_pos = len(self.state.current_items) - 1
            if self.state.cursor_position < max_pos:
                self.state.cursor_position += 1
                event.app.invalidate()

        @kb.add("enter")
        def select_item(event):
            self.handle_selection()
            event.app.invalidate()

        @kb.add("left")
        @kb.add("backspace")
        def go_back(event):
            self.handle_back_navigation()
            event.app.invalidate()

        @kb.add("right")
        def drill_into_relationship(event):
            if self.state.view_mode == "record_detail":
                self.handle_relationship_drilling()
                event.app.invalidate()

        @kb.add("pageup")
        def page_up(event):
            if self.state.page_num > 0:
                self.state.page_num -= 1
                self.refresh_data()
                event.app.invalidate()

        @kb.add("pagedown")
        def page_down(event):
            if (
                hasattr(self.state, "total_pages")
                and self.state.page_num < self.state.total_pages - 1
            ):
                self.state.page_num += 1
                self.refresh_data()
                event.app.invalidate()

        @kb.add("q")
        @kb.add("c-c")
        def quit_app(event):
            event.app.exit()

        return kb

    def handle_selection(self):
        """Handle item selection based on current view mode."""
        if self.state.view_mode == "entity_list":
            if self.state.cursor_position < len(self.entity_types):
                selected_entity = self.entity_types[self.state.cursor_position]
                self.state.entity_type = selected_entity
                self.state.view_mode = "record_list"
                self.state.cursor_position = 0
                self.refresh_data()
        elif self.state.view_mode == "record_list":
            if self.state.cursor_position < len(self.state.current_items):
                self.state.selected_item = self.state.current_items[
                    self.state.cursor_position
                ]
                self.state.view_mode = "record_detail"
                self.state.cursor_position = 0
        elif self.state.view_mode == "record_detail":
            self.handle_relationship_drilling()

    def handle_back_navigation(self):
        """Handle back navigation including relationship drilling."""
        if self.state.navigation_stack:
            previous_state = self.state.navigation_stack.pop()
            self.state.entity_type = previous_state["entity_type"]
            self.state.selected_item = previous_state["selected_item"]
            self.state.cursor_position = previous_state["cursor_position"]
            self.state.view_mode = previous_state["view_mode"]
            if "current_items" in previous_state:
                self.state.current_items = previous_state["current_items"]
        else:
            if self.state.view_mode == "record_detail":
                self.state.view_mode = "record_list"
                self.state.selected_item = None
                self.state.cursor_position = 0
            elif self.state.view_mode == "record_list":
                self.state.view_mode = "entity_list"
                self.state.entity_type = ""
                self.state.cursor_position = 0
                self.state.current_items = self.entity_types

    def handle_relationship_drilling(self):
        """Navigate into relationships using cursor keys."""
        if self.state.view_mode != "record_detail" or not self.state.selected_item:
            return

        # Use the new navigable items structure
        if not hasattr(self.state, 'navigable_items') or not self.state.navigable_items:
            return

        if self.state.cursor_position >= len(self.state.navigable_items):
            return

        nav_item = self.state.navigable_items[self.state.cursor_position]
        
        # Only navigate if it's a navigable item
        if nav_item['type'] not in ['relationship_field', 'relationship']:
            return

        # Save current state for back navigation
        self.state.navigation_stack.append({
            "entity_type": self.state.entity_type,
            "selected_item": self.state.selected_item,
            "cursor_position": self.state.cursor_position,
            "view_mode": self.state.view_mode,
            "current_items": self.state.current_items,
        })

        if nav_item['type'] == 'relationship_field':
            # Navigate to a single related entity by ID
            related_entity_type = nav_item['related_type']
            related_id = nav_item['value']
            
            # Try to fetch the related entity
            try:
                result = self.call_backend(f"get_{related_entity_type}", f"(0, 100)")
                if "items" in result:
                    # Find the specific item by ID
                    related_items = [item for item in result["items"] if item.get("_id") == str(related_id)]
                    if related_items:
                        self.state.current_items = related_items
                        self.state.cursor_position = 0
                        self.state.view_mode = "record_list"
                        self.state.entity_type = related_entity_type
                        return
            except Exception:
                pass
            
            # Fallback: create a placeholder item
            placeholder_item = {
                "_id": str(related_id),
                "_type": related_entity_type.rstrip('s').title(),
                "name": f"Referenced {related_entity_type.rstrip('s').title()}",
            }
            self.state.current_items = [placeholder_item]
            self.state.cursor_position = 0
            self.state.view_mode = "record_list"
            self.state.entity_type = related_entity_type
            
        elif nav_item['type'] == 'relationship':
            # Navigate to multiple related entities
            rel_items = nav_item['value']
            if isinstance(rel_items, list) and rel_items:
                self.state.current_items = rel_items
                self.state.cursor_position = 0
                self.state.view_mode = "record_list"
                self.state.entity_type = rel_items[0].get("_type", "Related")

    def _discover_ggg_models(self):
        """Dynamically discover GGG entity models and their relationships."""
        if self._entity_models_cache is not None:
            return self._entity_models_cache
            
        models = {}
        
        # Add the GGG module path to sys.path if not already there
        ggg_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src', 'realm_backend')
        ggg_path = os.path.abspath(ggg_path)
        if ggg_path not in sys.path:
            sys.path.insert(0, ggg_path)
        
        # Also add the project root to handle kybra_simple_db imports
        project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..')
        project_root = os.path.abspath(project_root)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        try:
            # Import the GGG module
            ggg_module = importlib.import_module('ggg')
            
            # Get all exported classes from the __all__ list
            for class_name in getattr(ggg_module, '__all__', []):
                try:
                    cls = getattr(ggg_module, class_name)
                    if inspect.isclass(cls) and hasattr(cls, '__name__'):
                        # Convert class name to entity type (e.g., User -> users)
                        entity_type = self._class_name_to_entity_type(class_name)
                        models[entity_type] = cls
                except AttributeError:
                    continue
                    
        except ImportError as e:
            # Silently fall back to common patterns if GGG models can't be imported
            pass
            
        self._entity_models_cache = models
        return models
    
    def _class_name_to_entity_type(self, class_name: str) -> str:
        """Convert class name to entity type (e.g., User -> users, TaskSchedule -> task_schedules)."""
        # Handle special cases
        if class_name == 'TaskSchedule':
            return 'task_schedules'
        elif class_name == 'UserProfile':
            return 'user_profiles'
        
        # Convert CamelCase to snake_case and pluralize
        import re
        snake_case = re.sub('([A-Z]+)([A-Z][a-z])', r'\1_\2', class_name)
        snake_case = re.sub('([a-z\d])([A-Z])', r'\1_\2', snake_case).lower()
        
        # Simple pluralization
        if snake_case.endswith('y'):
            return snake_case[:-1] + 'ies'
        elif snake_case.endswith(('s', 'sh', 'ch', 'x', 'z')):
            return snake_case + 'es'
        else:
            return snake_case + 's'
    
    def _discover_relationship_fields(self):
        """Discover relationship field mappings from GGG models."""
        if self._relationship_cache is not None:
            return self._relationship_cache
            
        relationship_fields = {}
        models = self._discover_ggg_models()
        
        for entity_type, model_class in models.items():
            try:
                # Inspect the model class for relationship fields
                for attr_name in dir(model_class):
                    attr = getattr(model_class, attr_name, None)
                    if attr is None or attr_name.startswith('_'):
                        continue
                        
                    # Check if it's a relationship field from kybra_simple_db
                    attr_type = type(attr).__name__
                    if attr_type in ['ManyToOne', 'OneToOne', 'OneToMany', 'ManyToMany']:
                        try:
                            # Get the related model name and back reference from the relationship
                            related_model = None
                            back_ref = None
                            
                            # Try different ways to get relationship info
                            if hasattr(attr, '_args') and len(attr._args) >= 1:
                                related_model = attr._args[0]
                                if len(attr._args) >= 2:
                                    back_ref = attr._args[1]
                            elif hasattr(attr, 'args') and len(attr.args) >= 1:
                                related_model = attr.args[0]
                                if len(attr.args) >= 2:
                                    back_ref = attr.args[1]
                            
                            if isinstance(related_model, str):
                                # Convert model name to entity type
                                related_entity_type = self._class_name_to_entity_type(related_model)
                                
                                # Handle different relationship types
                                if attr_type == 'ManyToOne':
                                    # This model has a foreign key to the related model
                                    # e.g., Transfer.from_user -> ManyToOne("User", "transfers_from")
                                    # means Transfer has from_user_id field
                                    field_pattern = f"{attr_name}_id"
                                    relationship_fields[field_pattern] = related_entity_type
                                    
                                elif attr_type == 'OneToOne':
                                    # Similar to ManyToOne for foreign key fields
                                    field_pattern = f"{attr_name}_id"
                                    relationship_fields[field_pattern] = related_entity_type
                                    
                                elif attr_type in ['OneToMany', 'ManyToMany'] and back_ref:
                                    # This is a reverse relationship
                                    # e.g., User.transfers_from -> OneToMany("Transfer", "from_user")
                                    # means Transfer has from_user_id field pointing to User
                                    field_pattern = f"{back_ref}_id"
                                    relationship_fields[field_pattern] = entity_type
                                    
                        except Exception:
                            # Skip problematic relationship definitions
                            continue
                                
            except Exception:
                # Skip problematic models
                continue
        
        # Add some common patterns that might not be captured by introspection
        common_patterns = {
            'user_id': 'users',
            'creator_id': 'users', 
            'owner_id': 'users',
            'from_user_id': 'users',
            'to_user_id': 'users',
            'human_id': 'humans',
            'organization_id': 'organizations',
            'mandate_id': 'mandates',
            'task_id': 'tasks', 
            'task_schedule_id': 'task_schedules',
            'proposal_id': 'proposals',
            'vote_id': 'votes',
            'instrument_id': 'instruments',
            'transfer_id': 'transfers',
            'trade_id': 'trades',
            'dispute_id': 'disputes',
            'license_id': 'licenses',
            'realm_id': 'realms',
            'codex_id': 'codexes',
            'treasury_id': 'treasuries',
            'user_profile_id': 'user_profiles',
        }
        
        # Merge common patterns, but don't override discovered relationships
        for pattern, entity_type in common_patterns.items():
            if pattern not in relationship_fields:
                relationship_fields[pattern] = entity_type
        
        self._relationship_cache = relationship_fields
        return relationship_fields

    def get_all_relationships(self, item):
        """Extract both explicit relations and inferred relationships from ID fields."""
        relations = item.get("relations", {}).copy()

        # Get dynamically discovered relationship fields
        relationship_fields = self._discover_relationship_fields()

        for field_name, entity_type in relationship_fields.items():
            if field_name in item and item[field_name]:
                related_item = {
                    "_id": item[field_name],
                    "_type": entity_type.rstrip("s").title(),
                    "name": f"Referenced {entity_type.rstrip('s').title()}",
                }
                relations[field_name.replace("_id", "")] = [related_item]

        return relations

    def refresh_data(self):
        """Refresh current data based on state."""
        if self.state.view_mode == "entity_list":
            self.state.current_items = self.entity_types
        elif self.state.view_mode == "record_list" and self.state.entity_type:
            logger.info(f"Fetching data for entity type: {self.state.entity_type}")
            result = self.list_entities(
                self.state.entity_type, self.state.page_num, self.state.page_size
            )
            logger.info(f"Backend result: {result}")
            if "error" not in result and "items" in result:
                self.state.current_items = result["items"]
                self.state.total_pages = result.get("total_pages", 1)
                logger.info(f"Loaded {len(result['items'])} items")
            else:
                logger.error(f"Failed to load data: {result}")
                self.state.current_items = []
                self.state.total_pages = 1

    def render_entity_list(self):
        """Render the entity selection menu."""
        lines = []
        lines.append("Realm Database Explorer")
        lines.append("Select an entity type to explore:")
        lines.append("")

        for i, entity_type in enumerate(self.entity_types):
            cursor = "> " if i == self.state.cursor_position else "  "
            desc = ENTITY_DESCRIPTIONS.get(entity_type, "")
            lines.append(f"{cursor}{i + 1:2}. {entity_type.title():<15} - {desc}")

        lines.append("")
        lines.append("Commands: Up/Down navigate | Enter select | q quit")

        return "\n".join(lines)

    def render_record_list(self):
        """Render the record list view."""
        lines = []
        lines.append(f"{self.state.entity_type.title()} List")

        if hasattr(self.state, "total_pages"):
            current_page = self.state.page_num + 1
            lines.append(f"Page {current_page} of {self.state.total_pages}")

        lines.append("")

        for i, item in enumerate(self.state.current_items):
            cursor = "> " if i == self.state.cursor_position else "  "
            if isinstance(item, dict):
                item_id = item.get("_id", "N/A")
                name = (
                    item.get("name") or item.get("title") or item.get("username") or "N/A"
                )
                lines.append(f"{cursor}{i + 1:2}. {item_id:<20} {name}")
            else:
                # Handle string items (entity type names)
                lines.append(f"{cursor}{i + 1:2}. {item}")

        lines.append("")
        lines.append(
            "Commands: Up/Down navigate | Enter view details | Left back | PgUp/PgDn pages | q quit"
        )

        return "\n".join(lines)

    def render_record_detail(self):
        """Render the detailed record view."""
        if not self.state.selected_item:
            return "No item selected"

        lines = []
        item = self.state.selected_item
        item_type = self.state.entity_type.title().rstrip("s")
        item_id = item.get("_id", "N/A")

        lines.append(f"{item_type} Details")
        lines.append(f"ID: {item_id}")
        lines.append("")

        # Get relationship fields for navigation
        relationship_fields = self._discover_relationship_fields()
        
        # Combine properties and navigable relationships
        navigable_items = []
        
        # Add regular properties
        for key, value in item.items():
            if key not in ["_id", "relations"] and not key.startswith("_"):
                if key in relationship_fields and value:
                    # This is a navigable relationship field
                    related_entity_type = relationship_fields[key]
                    navigable_items.append({
                        'type': 'relationship_field',
                        'key': key,
                        'value': value,
                        'related_type': related_entity_type,
                        'display': f"{key}: {value} → {related_entity_type.rstrip('s').title()}"
                    })
                else:
                    # Regular property
                    navigable_items.append({
                        'type': 'property',
                        'key': key,
                        'value': value,
                        'display': f"{key}: {value}"
                    })
        
        # Add explicit relationships
        relations = self.get_all_relationships(item)
        for rel_name, rel_items in relations.items():
            # Skip if this relationship is already shown as a property field
            rel_field_name = f"{rel_name}_id"
            if not any(nav_item['key'] == rel_field_name for nav_item in navigable_items if nav_item['type'] == 'relationship_field'):
                count = len(rel_items) if isinstance(rel_items, list) else 1
                navigable_items.append({
                    'type': 'relationship',
                    'key': rel_name,
                    'value': rel_items,
                    'display': f"{rel_name}: {count} items"
                })

        # Render all items with navigation support
        lines.append("Properties & Relationships:")
        for i, nav_item in enumerate(navigable_items):
            cursor = "> " if i == self.state.cursor_position else "  "
            if nav_item['type'] in ['relationship_field', 'relationship']:
                lines.append(f"{cursor}  {nav_item['display']} [navigable]")
            else:
                lines.append(f"{cursor}  {nav_item['display']}")

        # Store navigable items for navigation
        self.state.navigable_items = navigable_items

        lines.append("")
        lines.append(
            "Commands: Up/Down navigate | Right drill into relationships | Left back | q quit"
        )

        return "\n".join(lines)

    def create_layout(self):
        """Create the prompt_toolkit layout based on current state."""
        if self.state.view_mode == "entity_list":
            content = self.render_entity_list()
        elif self.state.view_mode == "record_list":
            content = self.render_record_list()
        elif self.state.view_mode == "record_detail":
            content = self.render_record_detail()
        else:
            content = "Unknown view mode"

        return Layout(
            HSplit(
                [
                    Window(content=FormattedTextControl(text=content), wrap_lines=True),
                ]
            )
        )

    def run(self):
        """Main interactive loop using prompt_toolkit Application."""
        try:
            self.call_backend("status")
            print("Connected to backend canister\n")
        except Exception:
            print("Could not connect to backend canister")
            return

        self.state.current_items = self.entity_types
        kb = self.create_key_bindings()

        def get_layout():
            return self.create_layout()

        self.app = Application(
            layout=get_layout(),
            key_bindings=kb,
            full_screen=True,
            refresh_interval=0.1,
        )

        original_invalidate = self.app.invalidate

        def invalidate():
            self.app.layout = get_layout()
            original_invalidate()

        self.app.invalidate = invalidate

        self.app.run()


def db_command(
    network: Optional[str] = typer.Option(
        None, "--network", "-n", help="Network to use (overrides context)"
    ),
    canister: Optional[str] = typer.Option(
        None, "--canister", "-c", help="Canister name to connect to (overrides context)"
    ),
) -> None:
    """Explore the Realm database in an interactive text-based interface with cursor navigation."""
    effective_network, effective_canister = get_effective_network_and_canister(
        network, canister
    )

    explorer = CursorDatabaseExplorer(effective_network, effective_canister)
    explorer.run()
