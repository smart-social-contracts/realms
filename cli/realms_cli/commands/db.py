"""Database explorer command for interactive Realm database exploration."""

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import typer
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from rich.console import Console

from ..utils import get_effective_network_and_canister

console = Console()


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

        self.entity_types = [
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
        ]

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

                entity_patterns = [
                    r"users = vec \{",
                    r"organizations = vec \{",
                    r"mandates = vec \{",
                    r"tasks = vec \{",
                    r"transfers = vec \{",
                    r"trades = vec \{",
                    r"instruments = vec \{",
                    r"codexes = vec \{",
                    r"disputes = vec \{",
                    r"licenses = vec \{",
                    r"realms = vec \{",
                    r"proposals = vec \{",
                    r"votes = vec \{",
                ]

                vec_field = None
                start_vec = -1

                for pattern in entity_patterns:
                    match = re.search(pattern, output)
                    if match:
                        vec_field = pattern.split(" = vec")[0]
                        start_vec = match.start()
                        break

                if start_vec >= 0:
                    brace_count = 0
                    vec_start = start_vec + len(f"{vec_field} = vec {{")
                    vec_end = vec_start

                    for i, char in enumerate(output[vec_start:], vec_start):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count < 0:
                                vec_end = i
                                break

                    vec_content = output[vec_start:vec_end]
                    json_strings = []

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

                    total_items = 0
                    total_pages = 1
                    page_num = 0
                    page_size = 10

                    if "total_items_count" in output:
                        total_match = re.search(r"total_items_count = (\d+)", output)
                        if total_match:
                            total_items = int(total_match.group(1))

                    if "total_pages" in output:
                        pages_match = re.search(r"total_pages = (\d+)", output)
                        if pages_match:
                            total_pages = int(pages_match.group(1))

                    if "page_num" in output:
                        page_match = re.search(r"page_num = (\d+)", output)
                        if page_match:
                            page_num = int(page_match.group(1))

                    if "page_size" in output:
                        size_match = re.search(r"page_size = (\d+)", output)
                        if size_match:
                            page_size = int(size_match.group(1))

                    return {
                        "items": json_strings,
                        "total_items_count": total_items,
                        "total_pages": total_pages,
                        "page_num": page_num,
                        "page_size": page_size,
                    }

                return {
                    "items": [],
                    "total_items_count": 0,
                    "total_pages": 1,
                    "page_num": 0,
                    "page_size": 10,
                }
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

        relations = self.state.selected_item.get("relations", {})

        if not relations:
            return

        rel_names = list(relations.keys())
        if self.state.cursor_position < len(rel_names):
            rel_name = rel_names[self.state.cursor_position]
            rel_items = relations[rel_name]

            if isinstance(rel_items, list) and rel_items:
                self.state.navigation_stack.append(
                    {
                        "entity_type": self.state.entity_type,
                        "selected_item": self.state.selected_item,
                        "cursor_position": self.state.cursor_position,
                        "view_mode": self.state.view_mode,
                        "current_items": self.state.current_items,
                    }
                )

                self.state.current_items = rel_items
                self.state.cursor_position = 0
                self.state.view_mode = "record_list"
                self.state.entity_type = rel_items[0].get("_type", "Related")

    def refresh_data(self):
        """Refresh current data based on state."""
        if self.state.view_mode == "entity_list":
            self.state.current_items = self.entity_types
        elif self.state.view_mode == "record_list" and self.state.entity_type:
            result = self.list_entities(
                self.state.entity_type, self.state.page_num, self.state.page_size
            )
            if "error" not in result:
                self.state.current_items = result["items"]
                self.state.total_pages = result.get("total_pages", 1)

    def render_entity_list(self):
        """Render the entity selection menu."""
        lines = []
        lines.append("Realm Database Explorer")
        lines.append("Select an entity type to explore:")
        lines.append("")

        descriptions = {
            "users": "System users and their profiles",
            "organizations": "Organizational entities and structures",
            "mandates": "Governance mandates and authorizations",
            "tasks": "Scheduled and executed tasks",
            "transfers": "Asset transfers between entities",
            "trades": "Completed trading transactions",
            "instruments": "Financial and governance instruments",
            "codexes": "Executable code and logic",
            "disputes": "Conflict resolution records",
            "licenses": "Permissions and authorizations",
            "realms": "Realm configurations and metadata",
            "proposals": "Governance proposals and voting",
            "votes": "Individual voting records",
        }

        for i, entity_type in enumerate(self.entity_types):
            cursor = "> " if i == self.state.cursor_position else "  "
            desc = descriptions.get(entity_type, "")
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
            item_id = item.get("_id", "N/A")
            name = (
                item.get("name") or item.get("title") or item.get("username") or "N/A"
            )
            lines.append(f"{cursor}{i + 1:2}. {item_id:<20} {name}")

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

        lines.append("Properties:")
        for key, value in item.items():
            if key not in ["_id", "relations"] and not key.startswith("_"):
                lines.append(f"  {key}: {value}")

        relations = item.get("relations", {})
        if relations:
            lines.append("")
            lines.append("Relationships:")
            rel_names = list(relations.keys())
            for i, rel_name in enumerate(rel_names):
                cursor = "> " if i == self.state.cursor_position else "  "
                rel_items = relations[rel_name]
                count = len(rel_items) if isinstance(rel_items, list) else 1
                lines.append(f"{cursor}  {rel_name}: {count} items")

        lines.append("")
        lines.append(
            "Commands: Up/Down navigate relationships | Right drill into | Left back | q quit"
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
