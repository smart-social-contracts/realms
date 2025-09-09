"""Database explorer command for interactive Realm database exploration."""

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import typer
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import confirm
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..utils import get_effective_network_and_canister

console = Console()

ENTITY_TYPES = {
    "users": "Users",
    "organizations": "Organizations",
    "mandates": "Mandates",
    "tasks": "Tasks",
    "codexes": "Codexes",
    "instruments": "Instruments",
    "trades": "Trades",
    "transfers": "Transfers",
    "realms": "Realms",
    "licenses": "Licenses",
    "disputes": "Disputes",
    "proposals": "Proposals",
    "votes": "Votes",
}


@dataclass
class NavigationState:
    """Tracks current navigation state in the database explorer."""

    entity_type: str = ""
    page_num: int = 0
    page_size: int = 10
    current_items: List[Dict] = None
    selected_item: Optional[Dict] = None


class DatabaseExplorer:
    """Interactive database explorer for Realm entities."""

    def __init__(self, network: str, canister: str):
        self.network = network
        self.canister = canister
        self.state = NavigationState()

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

                if "users = vec" in output:
                    start_vec = output.find("users = vec {")
                    if start_vec >= 0:
                        brace_count = 0
                        vec_start = start_vec + len("users = vec {")
                        vec_end = vec_start

                        for i, char in enumerate(output[vec_start:], vec_start):
                            if char == "{":
                                brace_count += 1
                            elif char == "}":
                                brace_count -= 1
                                if brace_count < 0:  # Found the closing brace for vec
                                    vec_end = i
                                    break

                        vec_content = output[vec_start:vec_end]
                        json_strings = []

                        for item in vec_content.split('";'):
                            item = item.strip()
                            if item.startswith('"'):
                                item = item[1:]  # Remove leading quote
                            if item.endswith('"'):
                                item = item[:-1]  # Remove trailing quote
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
                            import re

                            total_match = re.search(
                                r"total_items_count = (\d+)", output
                            )
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
                console.print(f"[red]Error calling backend: {result.stderr}[/red]")
                return {
                    "items": [],
                    "total_items_count": 0,
                    "total_pages": 1,
                    "page_num": 0,
                    "page_size": 10,
                }
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            return {
                "items": [],
                "total_items_count": 0,
                "total_pages": 1,
                "page_num": 0,
                "page_size": 10,
            }

    def list_entities(
        self, entity_type: str, page_num: int = 0, page_size: int = 10
    ) -> Dict[str, Any]:
        """List entities of given type with pagination."""
        method = f"get_{entity_type}"
        args = f"({page_num}, {page_size})"
        return self.call_backend(method, args)

    def show_entity_list_menu(self):
        """Show the main entity type selection menu."""
        console.clear()
        console.print("[bold blue]🏛️  Realm Database Explorer[/bold blue]\n")
        console.print(
            f"[dim]Network: {self.network}, Canister: {self.canister}[/dim]\n"
        )

        table = Table(
            title="Available Entity Types",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Key", style="cyan", width=12)
        table.add_column("Entity Type", style="green")
        table.add_column("Description", style="dim")

        descriptions = {
            "users": "System users with authentication",
            "organizations": "Organizational entities",
            "mandates": "Governance mandates and directives",
            "tasks": "Scheduled and executed tasks",
            "transfers": "Asset transfers between users",
            "trades": "Completed trade transactions",
            "proposals": "Governance proposals",
            "votes": "Voting records",
        }

        for key, name in ENTITY_TYPES.items():
            desc = descriptions.get(key, "")
            table.add_row(key, name, desc)

        console.print(table)
        console.print(
            "\n[dim]Commands: [cyan]<entity_key>[/cyan] to explore, [cyan]q[/cyan] to quit[/dim]"
        )

    def show_entity_records(self, entity_type: str, page_num: int = 0):
        """Show paginated records for an entity type."""
        console.clear()

        data = self.list_entities(entity_type, page_num, self.state.page_size)
        items = data.get("items", [])
        total_count = data.get("total_items_count", 0)
        total_pages = data.get("total_pages", 1)

        self.state.entity_type = entity_type
        self.state.page_num = page_num
        self.state.current_items = items

        console.print(f"[bold blue]{ENTITY_TYPES[entity_type]}[/bold blue]")
        console.print(
            f"[dim]Page {page_num + 1} of {total_pages} | Total: {total_count} records[/dim]\n"
        )

        if not items:
            console.print("[yellow]No records found[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)

        if items:
            first_item = items[0]
            for key in first_item.keys():
                if key not in [
                    "relations",
                    "timestamp_created",
                    "timestamp_updated",
                    "creator",
                    "updater",
                    "owner",
                ]:
                    table.add_column(key.replace("_", " ").title(), style="cyan")

        for i, item in enumerate(items):
            row = [str(i)]
            for key in item.keys():
                if key not in [
                    "relations",
                    "timestamp_created",
                    "timestamp_updated",
                    "creator",
                    "updater",
                    "owner",
                ]:
                    value = str(item.get(key, ""))
                    if len(value) > 30:
                        value = value[:27] + "..."
                    row.append(value)
            table.add_row(*row)

        console.print(table)

        nav_options = []
        if page_num > 0:
            nav_options.append("[cyan]p[/cyan] previous page")
        if page_num < total_pages - 1:
            nav_options.append("[cyan]n[/cyan] next page")
        nav_options.extend(
            [
                "[cyan]<number>[/cyan] view record details",
                "[cyan]b[/cyan] back to entity list",
                "[cyan]q[/cyan] quit",
            ]
        )

        console.print(f"\n[dim]Commands: {' | '.join(nav_options)}[/dim]")

    def show_record_details(self, item: Dict[str, Any]):
        """Show detailed view of a single record with relationships."""
        console.clear()

        entity_type = item.get("_type", "Unknown")
        entity_id = item.get("_id", "Unknown")

        console.print(f"[bold blue]{entity_type} Details[/bold blue]")
        console.print(f"[dim]ID: {entity_id}[/dim]\n")

        props_table = Table(
            title="Properties", show_header=True, header_style="bold magenta"
        )
        props_table.add_column("Property", style="cyan", width=20)
        props_table.add_column("Value", style="green")

        for key, value in item.items():
            if key not in ["relations", "_type"]:
                props_table.add_row(key, str(value))

        console.print(props_table)

        relations = item.get("relations", {})
        if relations:
            console.print("\n")
            rel_table = Table(
                title="Relationships", show_header=True, header_style="bold magenta"
            )
            rel_table.add_column("Relationship", style="cyan", width=20)
            rel_table.add_column("Count", style="yellow", width=8)
            rel_table.add_column("Related Items", style="green")

            for rel_name, rel_items in relations.items():
                if isinstance(rel_items, list):
                    count = len(rel_items)
                    if count > 0:
                        preview = []
                        for rel_item in rel_items[:3]:
                            if isinstance(rel_item, dict):
                                preview.append(
                                    f"{rel_item.get('_type', 'Unknown')}#{rel_item.get('_id', '?')}"
                                )
                        preview_str = ", ".join(preview)
                        if count > 3:
                            preview_str += f" ... (+{count-3} more)"
                        rel_table.add_row(rel_name, str(count), preview_str)
                    else:
                        rel_table.add_row(rel_name, "0", "[dim]None[/dim]")

            console.print(rel_table)

        console.print(
            "\n[dim]Commands: [cyan]b[/cyan] back to list | [cyan]q[/cyan] quit[/dim]"
        )

        self.state.selected_item = item

    def run(self):
        """Main interactive loop."""
        console.print("[bold blue]🚀 Starting Database Explorer[/bold blue]\n")

        try:
            self.call_backend("status")
            console.print("[green]✅ Connected to backend canister[/green]\n")
        except Exception:
            console.print("[red]❌ Could not connect to backend canister[/red]")
            console.print(
                "[yellow]Make sure the canister is running and accessible[/yellow]\n"
            )

        while True:
            try:
                if not self.state.entity_type:
                    self.show_entity_list_menu()
                    choice = prompt("Select entity type: ").strip().lower()

                    if choice == "q":
                        break
                    elif choice in ENTITY_TYPES:
                        self.state.entity_type = choice
                        self.state.page_num = 0
                    else:
                        console.print("[red]Invalid choice. Try again.[/red]")
                        continue

                elif self.state.selected_item is None:
                    self.show_entity_records(
                        self.state.entity_type, self.state.page_num
                    )
                    choice = prompt("Command: ").strip().lower()

                    if choice == "q":
                        break
                    elif choice == "b":
                        self.state.entity_type = ""
                        self.state.selected_item = None
                    elif (
                        choice == "n"
                        and self.state.page_num
                        < len(self.state.current_items) // self.state.page_size
                    ):
                        self.state.page_num += 1
                    elif choice == "p" and self.state.page_num > 0:
                        self.state.page_num -= 1
                    elif choice.isdigit():
                        idx = int(choice)
                        if 0 <= idx < len(self.state.current_items):
                            self.state.selected_item = self.state.current_items[idx]
                        else:
                            console.print("[red]Invalid record number[/red]")
                    else:
                        console.print("[red]Invalid command[/red]")

                else:
                    self.show_record_details(self.state.selected_item)
                    choice = prompt("Command: ").strip().lower()

                    if choice == "q":
                        break
                    elif choice == "b":
                        self.state.selected_item = None
                    else:
                        console.print("[red]Invalid command[/red]")

            except KeyboardInterrupt:
                console.print("\n[dim]Use 'q' to quit[/dim]")
            except EOFError:
                break

        console.print("[bold blue]Goodbye![/bold blue]")


def db_command(
    network: Optional[str] = typer.Option(
        None, "--network", "-n", help="Network to use (overrides context)"
    ),
    canister: Optional[str] = typer.Option(
        None, "--canister", "-c", help="Canister name to connect to (overrides context)"
    ),
) -> None:
    """Explore the Realm database in an interactive text-based interface."""
    effective_network, effective_canister = get_effective_network_and_canister(
        network, canister
    )

    explorer = DatabaseExplorer(effective_network, effective_canister)
    explorer.run()
