"""Create command for generating new Realms projects."""

import json
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..utils import (
    console,
    display_error_panel,
    display_success_panel,
    get_project_root,
)
from .deploy import deploy_command


def create_command(
    random: bool,
    citizens: int,
    organizations: int,
    transactions: int,
    disputes: int,
    seed: Optional[int],
    output_dir: str,
    realm_name: str,
    network: str,
    deploy: bool,
) -> None:
    """Create a new realm with optional random data generation."""

    try:
        if random:
            console.print("[bold blue]🏗️  Creating Random Realm[/bold blue]\n")

            realm_data = _generate_random_realm_data(
                citizens=citizens,
                organizations=organizations,
                transactions=transactions,
                disputes=disputes,
                seed=seed,
                realm_name=realm_name,
            )

            output_path = Path(output_dir)
            _create_realm_folder_structure(output_path, realm_data, network, realm_name)

            console.print(
                f"[green]✅ Random realm created successfully in: {output_path.absolute()}[/green]"
            )

            success_message = (
                f"Random realm '{realm_name}' has been created successfully.\n\n"
                f"📁 Location: {output_path.absolute()}\n"
                f"👥 Citizens: {citizens}\n"
                f"🏢 Organizations: {organizations}\n"
                f"💰 Transactions: {transactions}\n"
                f"⚖️  Disputes: {disputes}\n\n"
                f"Next steps:\n"
                f"1. Review the generated configuration in realm_config.json\n"
                f"2. Deploy with: realms deploy --file {output_dir}/realm_config.json\n"
                f"3. The realm will be automatically populated with demo data"
            )
        else:
            console.print("[bold blue]🏗️  Creating Basic Realm[/bold blue]\n")

            output_path = Path(output_dir)
            _create_basic_realm_structure(output_path, network, realm_name)

            console.print(
                f"[green]✅ Basic realm created successfully in: {output_path.absolute()}[/green]"
            )

            success_message = (
                f"Basic realm '{realm_name}' has been created successfully.\n\n"
                f"📁 Location: {output_path.absolute()}\n\n"
                f"Next steps:\n"
                f"1. Review the generated configuration in realm_config.json\n"
                f"2. Deploy with: realms deploy --file {output_dir}/realm_config.json\n"
                f"3. Manually add data or use extensions to populate the realm"
            )

        if deploy:
            console.print("\n[bold blue]🚀 Deploying Realm[/bold blue]")
            config_file = str(output_path / "realm_config.json")
            deploy_command(config_file, network, False, False, None, False, None)

        display_success_panel(
            "Realm Creation Complete! 🎉",
            success_message,
        )

    except Exception as e:
        display_error_panel("Realm Creation Failed", str(e))
        raise typer.Exit(1)


def _generate_random_realm_data(
    citizens: int,
    organizations: int,
    transactions: int,
    disputes: int,
    seed: Optional[int],
    realm_name: str,
) -> dict:
    """Generate random realm data using existing realm_generator logic."""

    console.print("🎲 Generating random realm data...")

    project_root = get_project_root()
    sys.path.append(str(project_root / "scripts"))

    import realm_generator  # type: ignore

    generator = realm_generator.RealmGenerator(seed)
    realm_data = generator.generate_realm_data(
        citizens=citizens,
        organizations=organizations,
        transactions=transactions,
        disputes=disputes,
        realm_name=realm_name,
    )

    # Generate codex files and add them to realm_data
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        codex_files = generator.generate_codex_files(temp_path)

        # Read the generated codex files and store their content
        codex_content = {}
        for codex_file_path in codex_files:
            file_path = Path(codex_file_path)
            with open(file_path, "r") as f:
                codex_content[file_path.name] = f.read()

        realm_data["codex_files"] = codex_content

    console.print(
        f"✅ Generated data for {len(realm_data['users'])} users, {len(realm_data['organizations'])} organizations"
    )

    return realm_data


def _create_realm_folder_structure(
    output_path: Path, realm_data: dict, network: str, realm_name: str
) -> None:
    """Create the complete realm folder structure."""

    console.print(f"📁 Creating realm folder structure in {output_path}...")

    output_path.mkdir(exist_ok=True)

    data_dir = output_path / "data"
    codexes_dir = output_path / "codexes"
    data_dir.mkdir(exist_ok=True)
    codexes_dir.mkdir(exist_ok=True)

    _create_realm_config(output_path, realm_data, network, realm_name)

    _create_json_data_files(data_dir, realm_data)

    _create_codex_files(codexes_dir, realm_data)

    console.print("✅ Folder structure created successfully")


def _create_realm_config(
    output_path: Path, realm_data: dict, network: str, realm_name: str
) -> None:
    """Create the main realm configuration file."""

    realm_info = realm_data.get(
        "realm",
        {"name": realm_name, "description": f"Random generated realm: {realm_name}"},
    )

    config = {
        "realm": {
            "id": realm_info["name"].lower().replace(" ", "_").replace("-", "_"),
            "name": realm_info["name"],
            "description": realm_info["description"],
            "admin_principal": "2vxsx-fae",
            "version": "1.0.0",
            "tags": ["demo", "random-generated", "governance"],
        },
        "deployment": {"network": network, "clean_deploy": True},
        "extensions": {
            "initial": [
                {"name": "admin_dashboard", "source": "local", "enabled": True},
                {"name": "citizen_dashboard", "source": "local", "enabled": True},
                {"name": "voting", "source": "local", "enabled": True},
            ]
        },
        "post_deployment": {
            "actions": [
                {
                    "type": "extension_call",
                    "name": "Import User Profiles",
                    "extension_name": "admin_dashboard",
                    "function_name": "import_data",
                    "args": {
                        "file_path": "data/user_profiles.json",
                        "data_type": "user_profiles",
                    },
                },
                {
                    "type": "extension_call",
                    "name": "Import Users",
                    "extension_name": "admin_dashboard",
                    "function_name": "import_data",
                    "args": {"file_path": "data/users.json", "data_type": "users"},
                },
                {
                    "type": "extension_call",
                    "name": "Import Organizations",
                    "extension_name": "admin_dashboard",
                    "function_name": "import_data",
                    "args": {
                        "file_path": "data/organizations.json",
                        "data_type": "organizations",
                    },
                },
                {
                    "type": "extension_call",
                    "name": "Import Transfers",
                    "extension_name": "admin_dashboard",
                    "function_name": "import_data",
                    "args": {
                        "file_path": "data/transfers.json",
                        "data_type": "transfers",
                    },
                },
                {
                    "type": "extension_call",
                    "name": "Import Instruments",
                    "extension_name": "admin_dashboard",
                    "function_name": "import_data",
                    "args": {
                        "file_path": "data/instruments.json",
                        "data_type": "instruments",
                    },
                },
                {
                    "type": "extension_call",
                    "name": "Import Mandates",
                    "extension_name": "admin_dashboard",
                    "function_name": "import_data",
                    "args": {
                        "file_path": "data/mandates.json",
                        "data_type": "mandates",
                    },
                },
            ]
        },
    }

    config_file = output_path / "realm_config.json"
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    console.print(f"✅ Created realm configuration: {config_file}")


def _create_json_data_files(data_dir: Path, realm_data: dict) -> None:
    """Create JSON data files for each entity type."""

    entity_mappings = {
        "users.json": realm_data.get("users", []),
        "humans.json": realm_data.get("humans", []),
        "user_profiles.json": realm_data.get("user_profiles", []),
        "organizations.json": realm_data.get("organizations", []),
        "instruments.json": realm_data.get("instruments", []),
        "transfers.json": realm_data.get("transfers", []),
        "mandates.json": realm_data.get("mandates", []),
    }

    for filename, data in entity_mappings.items():
        if data:
            file_path = data_dir / filename
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            console.print(f"✅ Created {filename} with {len(data)} records")


def _create_codex_files(codexes_dir: Path, realm_data: dict) -> None:
    """Create Python codex files."""

    codex_files = realm_data.get("codex_files", {})

    for filename, content in codex_files.items():
        file_path = codexes_dir / filename
        with open(file_path, "w") as f:
            f.write(content)
        console.print(f"✅ Created codex file: {filename}")


def _create_basic_realm_structure(
    output_path: Path, network: str, realm_name: str
) -> None:
    """Create a basic realm folder structure without demo data."""

    console.print(f"📁 Creating basic realm folder structure in {output_path}...")

    output_path.mkdir(exist_ok=True)

    # Create basic realm configuration
    config = {
        "realm": {
            "id": realm_name.lower().replace(" ", "_").replace("-", "_"),
            "name": realm_name,
            "description": f"Basic realm: {realm_name}",
            "admin_principal": "2vxsx-fae",
            "version": "1.0.0",
            "tags": ["basic", "empty"],
        },
        "deployment": {"network": network, "clean_deploy": True},
        "extensions": {
            "initial": [
                {"name": "admin_dashboard", "source": "local", "enabled": True},
                {"name": "citizen_dashboard", "source": "local", "enabled": True},
            ]
        },
        "post_deployment": {"actions": []},
    }

    config_file = output_path / "realm_config.json"
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    console.print(f"✅ Created basic realm configuration: {config_file}")
    console.print("✅ Basic folder structure created successfully")
