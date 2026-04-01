"""Main CLI application for Realms."""

from typing import Optional

import typer
from rich.console import Console

from .commands.create import create_command
from .commands.deploy import deploy_command, deploy_from_descriptor
from .commands.import_data import import_data_command
from .commands.export_data import export_data_command
from .commands.extension import extension_command
from .commands.marketplace import marketplace_create_command, marketplace_deploy_command
from .commands.mundus import mundus_create_command, mundus_deploy_command
from .commands.quarter import (
    quarter_create_command,
    quarter_list_command,
    quarter_register_command,
    quarter_remove_command,
    quarter_status_command,
)
from .commands.registry import (
    billing_add_credits_command,
    billing_balance_command,
    billing_deduct_credits_command,
    billing_redeem_voucher_command,
    billing_status_command,
    realm_deploy_realm_command,
    realm_deploy_status_command,
    registry_count_command,
    registry_create_command,
    registry_deploy_command,
    registry_get_command,
    registry_list_command,
    registry_remove_command,
    registry_search_command,
    registry_status_command,
)
from .commands.test import test_command
from .constants import MAX_BATCH_SIZE, REALM_FOLDER

console = Console()

app = typer.Typer(
    name="realms",
    help="CLI tool for deploying and managing Realms",
    add_completion=False,
    rich_markup_mode="rich",
    invoke_without_command=True,
)




@app.command("import", hidden=True)
def import_data(
    file_path: str = typer.Argument(..., help="Path to JSON data file"),
    entity_type: Optional[str] = typer.Option(
        None, "--type", help="Entity type (codex for Python files, or json entity type)"
    ),
    format: str = typer.Option("json", "--format", help="Data format (json)"),
    batch_size: int = typer.Option(
        MAX_BATCH_SIZE, "--batch-size", help="Batch size for import"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be imported without executing"
    ),
    network: str = typer.Option("local", "--network", help="Network to use for import"),
    identity: Optional[str] = typer.Option(
        None, "--identity", help="Path to identity PEM file or identity name"
    ),
    canister: str = typer.Option(
        "realm_backend", "--canister", "-c", help="Canister name to import data to (e.g. realm1_backend for mundus)"
    ),
    folder: Optional[str] = typer.Option(
        None, "--folder", "-f", help="Realm folder containing deployment config (uses current realm context if not specified)"
    ),
) -> None:
    """Import data into the realm. Supports JSON data and Python codex files."""
    import_data_command(file_path, entity_type, format, batch_size, dry_run, network, identity, canister, folder)


@app.command("extension", hidden=True)
def extension(
    action: str = typer.Argument(..., help="Action to perform"),
    extension_id: Optional[str] = typer.Option(None, "--extension-id", help="Extension ID"),
    package_path: Optional[str] = typer.Option(None, "--package-path", help="Package path"),
    source_dir: str = typer.Option("extensions", "--source-dir", help="Source directory"),
    all_extensions: bool = typer.Option(False, "--all", help="All extensions"),
) -> None:
    """Manage Realm extensions."""
    extension_command(action, extension_id, package_path, source_dir, all_extensions)


@app.command("export", hidden=True)
def export_data(
    output_dir: str = typer.Option(
        "exported_realm", "--output-dir", help="Output directory for exported data"
    ),
    entity_types: Optional[str] = typer.Option(
        None, "--entity-types", help="Comma-separated list of entity types to export (default: all)"
    ),
    network: str = typer.Option("local", "--network", help="Network to use for export"),
    identity: Optional[str] = typer.Option(
        None, "--identity", help="Path to identity PEM file or identity name"
    ),
    include_codexes: bool = typer.Option(
        True, "--include-codexes/--no-codexes", help="Include codexes in export (default: True)"
    ),
) -> None:
    """Export data from the realm. Saves JSON data and Python codex files."""
    export_data_command(output_dir, entity_types, network, identity, include_codexes)


@app.command("deploy", rich_help_panel="Lifecycle")
def deploy(
    descriptor: Optional[str] = typer.Argument(
        None,
        help="Path to deployment descriptor YAML file (e.g. deployments/staging-mundus.yml)",
    ),
    subtypes: Optional[str] = typer.Option(
        None, "--subtypes", "-s",
        help="Override subtypes: backend, frontend, all, token, nft, marketplace",
    ),
    mode: Optional[str] = typer.Option(
        None, "--mode", "-m",
        help="Override deploy mode: upgrade, reinstall",
    ),
    network: Optional[str] = typer.Option(
        None, "--network", "-n",
        help="Override target network: local, staging, demo, ic",
    ),
    identity: Optional[str] = typer.Option(
        None, "--identity", "-i",
        help="Identity name or PEM file path for deployment",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Print deployment plan without executing",
    ),
    folder: Optional[str] = typer.Option(
        None, "--folder", "-f",
        help="[Classic mode] Path to realm folder (used when no descriptor given)",
    ),
    clean: bool = typer.Option(
        False, "--clean",
        help="[Classic mode] Clean deployment (wipes state)",
    ),
    plain_logs: bool = typer.Option(
        False, "--plain-logs",
        help="[Classic mode] Show full verbose output instead of progress UI",
    ),
    registry: Optional[str] = typer.Option(
        None, "--registry",
        help="[Classic mode] Registry canister ID for realm registration",
    ),
) -> None:
    """Deploy realms using a deployment descriptor or classic folder-based deploy.

    \b
    DESCRIPTOR MODE (recommended):
      realms deploy <descriptor.yml> [--subtypes X] [--mode X] [--identity X]
    \b
    CLASSIC MODE (legacy):
      realms deploy --folder <path> --network <net> [--mode X] [--identity X]
    \b
    EXAMPLES:
    \b
      # Full mundus deploy to staging
      realms deploy deployments/staging-mundus.yml
    \b
      # Backend-only hotfix for Agora
      realms deploy deployments/staging-realm2-backend.yml
    \b
      # Frontend-only redeploy for Dominion
      realms deploy deployments/staging-realm1-frontend.yml
    \b
      # Override subtypes at deploy time
      realms deploy deployments/staging-mundus.yml --subtypes backend
    \b
      # Dry run (print plan without executing)
      realms deploy deployments/staging-mundus.yml --dry-run
    \b
      # Force reinstall instead of upgrade
      realms deploy deployments/staging-realm1-backend.yml --mode reinstall
    \b
      # Classic folder-based deploy (legacy)
      realms deploy --folder ./my_realms/realm_dominion --network staging
    \b
    DESCRIPTORS:
      YAML files in deployments/ define what to deploy declaratively.
      See deployment_file_example.yml for the full schema.
      Create new descriptors by copying an existing one and adjusting fields.
    \b
    AVAILABLE DESCRIPTORS:
      staging-mundus.yml            Full mundus (all realms + registry) to staging
      demo-mundus.yml               Full mundus to demo
      staging-realm1-backend.yml    Backend hotfix for Dominion (realm1) on staging
      staging-realm2-backend.yml    Backend hotfix for Agora (realm2) on staging
      staging-realm3-backend.yml    Backend hotfix for Syntropia (realm3) on staging
      staging-realm1-frontend.yml   Frontend fix for Dominion (realm1) on staging
      staging-registry.yml          Registry deployment to staging
    \b
    See: https://github.com/smart-social-contracts/realms/issues/160
    """
    if descriptor:
        deploy_from_descriptor(
            descriptor_path=descriptor,
            subtypes_override=subtypes,
            network_override=network,
            mode_override=mode,
            identity=identity,
            dry_run=dry_run,
        )
        return
    # Classic mode fallback
    deploy_command(
        config_file=None,
        folder=folder,
        network=network or "local",
        clean=clean,
        identity=identity,
        mode=mode or "auto",
        plain_logs=plain_logs,
        registry=registry,
    )


@app.command("test", rich_help_panel="Development")
def test(
    path: str = typer.Argument(".", help="Path to codices directory, realm directory, or test file"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show verbose output including passing test details"
    ),
) -> None:
    """Run codex tests locally using the mock ggg framework.

    Examples:
        realms test codices/agora
        realms test codices/
        realms test codices/agora/tests/test_financial_setup.py
    """
    test_command(path, verbose)


# Create mundus subcommand group
mundus_app = typer.Typer(name="mundus", help="Multi-realm mundus operations")
app.add_typer(mundus_app, name="mundus", rich_help_panel="Lifecycle")


@mundus_app.command("create")
def mundus_create(
    output_dir: str = typer.Option(
        ".realms/mundus", "--output-dir", help="Output directory for mundus"
    ),
    mundus_name: str = typer.Option(
        "Demo Mundus", "--mundus-name", help="Name of the mundus"
    ),
    manifest: Optional[str] = typer.Option(
        None, "--manifest", help="Path to mundus manifest.json (default: examples/demo/manifest.json)"
    ),
    network: str = typer.Option(
        "local", "--network", help="Target network for deployment"
    ),
    deploy: bool = typer.Option(
        False, "--deploy", help="Deploy the mundus after creation"
    ),
    identity: Optional[str] = typer.Option(
        None, "--identity", help="Path to identity PEM file or identity name"
    ),
    mode: str = typer.Option(
        "auto", "--mode", "-m", help="Deploy mode: 'auto', 'upgrade' or 'reinstall' (auto picks install/upgrade)"
    ),
    no_demo_data: bool = typer.Option(
        False, "--no-demo-data", help="Skip generating demo/fake data (users, orgs, accounting). Extensions and codex files are still included."
    ),
) -> None:
    """Create a new multi-realm mundus from a manifest."""
    mundus_create_command(
        output_dir,
        mundus_name,
        manifest,
        network,
        deploy,
        identity,
        mode,
        no_demo_data=no_demo_data,
    )


@mundus_app.command("deploy")
def mundus_deploy(
    mundus_dir: str = typer.Option(
        ".realms/mundus", "--mundus-dir", help="Path to mundus directory"
    ),
    network: str = typer.Option(
        "local", "--network", help="Target network for deployment"
    ),
    identity: Optional[str] = typer.Option(
        None, "--identity", help="Path to identity PEM file or identity name"
    ),
    mode: str = typer.Option(
        "auto", "--mode", "-m", help="Deploy mode: 'auto', 'upgrade' or 'reinstall'"
    ),
    no_demo_data: bool = typer.Option(
        False, "--no-demo-data", help="Skip generating demo/fake data (users, orgs, accounting). Extensions and codex files are still included."
    ),
) -> None:
    """Deploy all realms and registry in an existing mundus."""
    mundus_deploy_command(mundus_dir, network, identity, mode, no_demo_data=no_demo_data)


# Create realm subcommand group
realm_app = typer.Typer(name="realm", help="Realm-specific operations")
app.add_typer(realm_app, name="realm", rich_help_panel="Lifecycle")


@realm_app.command("create")
def realm_create(
    output_dir: str = typer.Option(
        REALM_FOLDER, "--output-dir", help="Output directory"
    ),
    realm_name: str = typer.Option(
        "Generated Demo Realm", "--realm-name", help="Name of the realm"
    ),
    manifest: Optional[str] = typer.Option(
        "examples/demo/realm1/manifest.json", "--manifest", help="Path to realm manifest.json (defaults to realm1 template)"
    ),
    random: bool = typer.Option(
        False, "--random/--no-random", help="Generate random realm data"
    ),
    members: Optional[int] = typer.Option(
        None, "--members", help="Number of members to generate (overrides manifest)"
    ),
    organizations: Optional[int] = typer.Option(
        None, "--organizations", help="Number of organizations to generate (overrides manifest)"
    ),
    transactions: Optional[int] = typer.Option(
        None, "--transactions", help="Number of transactions to generate (overrides manifest)"
    ),
    disputes: Optional[int] = typer.Option(
        None, "--disputes", help="Number of disputes to generate (overrides manifest)"
    ),
    seed: Optional[int] = typer.Option(
        None, "--seed", help="Random seed for reproducible generation (overrides manifest)"
    ),
    network: str = typer.Option(
        "local", "--network", help="Target network for deployment"
    ),
    deploy: bool = typer.Option(
        False, "--deploy", help="Deploy the realm after creation"
    ),
    identity: Optional[str] = typer.Option(
        None, "--identity", help="Path to identity PEM file or identity name"
    ),
    mode: str = typer.Option(
        "auto", "--mode", "-m", help="Deploy mode: 'auto', 'upgrade' or 'reinstall' (auto picks install/upgrade)"
    ),
    bare: bool = typer.Option(
        False, "--bare", help="Create minimal realm (canisters only, no extensions or data)"
    ),
    no_demo_data: bool = typer.Option(
        False, "--no-demo-data", help="Skip generating demo/fake data (users, orgs, accounting). Extensions and codex files are still included."
    ),
    plain_logs: bool = typer.Option(
        False, "--plain-logs", help="Show full verbose output instead of progress UI during deployment"
    ),
    registry: Optional[str] = typer.Option(
        None, "--registry", help="Registry canister ID for realm registration during deployment"
    ),
) -> None:
    """Create a new realm. Use --manifest for template or flags for custom configuration."""
    create_command(
        output_dir,
        realm_name,
        manifest,
        random,
        members,
        organizations,
        transactions,
        disputes,
        seed,
        network,
        deploy,
        identity,
        mode,
        bare,
        no_demo_data,
        plain_logs,
        registry=registry,
    )


@realm_app.command("deploy")
def realm_deploy(
    folder: Optional[str] = typer.Option(
        None, "--folder", "-f", help="Path to realm folder to deploy"
    ),
    config_file: Optional[str] = typer.Option(
        None, "--config-file", help="Path to custom deployment config"
    ),
    network: str = typer.Option(
        "local", "--network", "-n", help="Network to deploy to"
    ),
    clean: bool = typer.Option(
        False, "--clean", help="Clean deployment (wipes state)"
    ),
    identity: Optional[str] = typer.Option(
        None, "--identity", help="Identity file or name for IC deployment"
    ),
    mode: str = typer.Option(
        "auto", "--mode", "-m", help="Deployment mode (auto, upgrade, reinstall)"
    ),
    plain_logs: bool = typer.Option(
        False, "--plain-logs", help="Show full verbose output instead of progress UI"
    ),
    registry: Optional[str] = typer.Option(
        None, "--registry", help="Registry canister ID for realm registration"
    ),
    descriptor: Optional[str] = typer.Option(
        None, "--descriptor", "-d",
        help="Path to deployment descriptor YAML (see issue #160)"
    ),
    subtypes: Optional[str] = typer.Option(
        None, "--subtypes",
        help="Override subtypes from descriptor (e.g. 'backend', 'frontend', 'all')"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Print deployment plan without executing (descriptor mode only)"
    ),
) -> None:
    """Deploy a realm to the specified network.
    
    Two modes:
      1. Classic: realms realm deploy --folder <path> --network <net>
      2. Descriptor: realms realm deploy --descriptor deployments/staging-realm2-backend.yml
    
    See: https://github.com/smart-social-contracts/realms/issues/160
    """
    if descriptor:
        deploy_from_descriptor(
            descriptor_path=descriptor,
            subtypes_override=subtypes,
            network_override=network if network != "local" else None,
            mode_override=mode if mode != "auto" else None,
            identity=identity,
            dry_run=dry_run,
        )
        return
    deploy_command(config_file, folder, network, clean, identity, mode, plain_logs, registry=registry)


# Create quarter subcommand group under realm
quarter_app = typer.Typer(name="quarter", help="Manage quarters within a realm")
realm_app.add_typer(quarter_app, name="quarter")


@quarter_app.command("create")
def realm_quarter_create(
    realm_ref: str = typer.Argument(help="Parent realm canister ID or name"),
    quarter_name: str = typer.Option(..., "--quarter-name", help="Name for the new quarter"),
    output_dir: str = typer.Option(
        REALM_FOLDER, "--output-dir", help="Output directory for quarter files"
    ),
    network: str = typer.Option("local", "--network", "-n", help="Network to deploy to"),
    deploy: bool = typer.Option(
        False, "--deploy", help="Deploy the quarter after creation"
    ),
    identity: Optional[str] = typer.Option(
        None, "--identity", help="Identity for IC deployment"
    ),
    mode: str = typer.Option(
        "auto", "--mode", "-m", help="Deploy mode: auto, upgrade, or reinstall"
    ),
    manifest: Optional[str] = typer.Option(
        None, "--manifest", help="Path to realm manifest.json for the quarter"
    ),
    bare: bool = typer.Option(
        False, "--bare", help="Create minimal quarter (canisters only, no extensions or data)"
    ),
    plain_logs: bool = typer.Option(
        False, "--plain-logs", help="Show full verbose output instead of progress UI"
    ),
    capital: bool = typer.Option(
        False, "--capital", help="Designate this quarter as the federation capital"
    ),
) -> None:
    """Create a new quarter backend and register it with a parent realm."""
    quarter_create_command(
        realm_ref, quarter_name, network, identity, mode,
        output_dir, deploy, manifest, bare, plain_logs, capital,
    )


@quarter_app.command("register")
def realm_quarter_register(
    realm_ref: str = typer.Argument(help="Parent realm canister ID or name"),
    quarter_name: str = typer.Option(..., "--quarter-name", help="Name for the quarter"),
    canister_id: str = typer.Option(..., "--canister-id", help="Canister ID of the quarter backend"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
) -> None:
    """Register an existing deployed canister as a quarter of a realm."""
    quarter_register_command(realm_ref, quarter_name, canister_id, network)


@quarter_app.command("list")
def realm_quarter_list(
    realm_ref: str = typer.Argument(help="Realm canister ID or name"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
) -> None:
    """List all quarters under a realm."""
    quarter_list_command(realm_ref, network)


@quarter_app.command("status")
def realm_quarter_status(
    realm_ref: str = typer.Argument(help="Realm canister ID or name"),
    quarter_ref: str = typer.Argument(help="Quarter name or canister ID"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
) -> None:
    """Show detailed status of a specific quarter."""
    quarter_status_command(realm_ref, quarter_ref, network)


@quarter_app.command("remove")
def realm_quarter_remove(
    realm_ref: str = typer.Argument(help="Realm canister ID or name"),
    quarter_ref: str = typer.Argument(help="Quarter name or canister ID to remove"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
) -> None:
    """Remove a quarter from a realm."""
    quarter_remove_command(realm_ref, quarter_ref, network)


@quarter_app.command("secede")
def realm_quarter_secede(
    quarter_ref: str = typer.Argument(help="Quarter canister ID to declare independence"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
) -> None:
    """Declare independence — secede a quarter from its federation."""
    from .commands.quarter import quarter_secede_command
    quarter_secede_command(quarter_ref, network)


@quarter_app.command("join-federation")
def realm_quarter_join_federation(
    quarter_ref: str = typer.Argument(help="Quarter canister ID to join a federation"),
    capital_canister_id: str = typer.Option(..., "--capital", help="Capital canister ID of the target federation"),
    as_capital: bool = typer.Option(False, "--as-capital", help="Join as the capital of the federation"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
) -> None:
    """Join an existing federation as a quarter."""
    from .commands.quarter import quarter_join_federation_command
    quarter_join_federation_command(quarter_ref, capital_canister_id, as_capital, network)


# Create registry subcommand group
registry_app = typer.Typer(name="registry", help="Realm registry operations")
app.add_typer(registry_app, name="registry", rich_help_panel="Lifecycle")

# Create registry realm subgroup
registry_realm_app = typer.Typer(name="realm", help="Manage realms in registry")
registry_app.add_typer(registry_realm_app, name="realm")

# Create registry billing subgroup
registry_billing_app = typer.Typer(name="billing", help="Manage credits and billing")
registry_app.add_typer(registry_billing_app, name="billing")


@registry_realm_app.command("list")
def registry_list(
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """List all realms in the registry."""
    registry_list_command(network, canister_id)


@registry_realm_app.command("get")
def registry_get(
    realm_id: str = typer.Option(..., "--id", help="Realm ID to retrieve"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """Get a specific realm by ID."""
    registry_get_command(realm_id, network, canister_id)


@registry_realm_app.command("remove")
def registry_remove(
    realm_id: str = typer.Option(..., "--id", help="Realm ID to remove"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """Remove a realm from the registry."""
    registry_remove_command(realm_id, network, canister_id)


@registry_realm_app.command("search")
def registry_search(
    query: str = typer.Option(..., "--query", help="Search query"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """Search realms by name or ID."""
    registry_search_command(query, network, canister_id)


@registry_realm_app.command("count")
def registry_count(
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """Get the total number of realms."""
    registry_count_command(network, canister_id)


@registry_app.command("create")
def registry_create(
    registry_name: Optional[str] = typer.Option(None, "--name", help="Registry name"),
    output_dir: str = typer.Option(".realms", "--output-dir", "-o", help="Base output directory"),
    network: str = typer.Option("local", "--network", "-n", help="Network to deploy to"),
    deploy: bool = typer.Option(
        False, "--deploy", help="Deploy the registry after creation"
    ),
    identity: Optional[str] = typer.Option(
        None, "--identity", help="Path to identity PEM file or identity name"
    ),
    mode: str = typer.Option(
        "auto", "--mode", "-m", help="Deploy mode: 'auto', 'upgrade' or 'reinstall' (auto picks install/upgrade)"
    ),
) -> None:
    """Create a new registry instance."""
    registry_create_command(registry_name, output_dir, network, deploy, identity, mode)


@registry_app.command("deploy")
def registry_deploy(
    folder: str = typer.Option(..., "--folder", "-f", help="Path to registry directory"),
    network: str = typer.Option("local", "--network", "-n", help="Network to deploy to"),
    mode: str = typer.Option("auto", "--mode", "-m", help="Deployment mode (auto, upgrade, reinstall)"),
    identity: Optional[str] = typer.Option(None, "--identity", help="Identity file for IC deployment"),
) -> None:
    """Deploy a registry instance."""
    registry_deploy_command(folder, network, mode, identity)


@registry_app.command("status")
def registry_status(
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """Get the status of the registry backend canister."""
    registry_status_command(network, canister_id)


# ============== Marketplace Commands ==============

marketplace_app = typer.Typer(name="marketplace", help="Extension marketplace operations")
app.add_typer(marketplace_app, name="marketplace", rich_help_panel="Lifecycle")


@marketplace_app.command("create")
def marketplace_create(
    marketplace_name: Optional[str] = typer.Option(None, "--name", help="Marketplace name"),
    output_dir: str = typer.Option(".realms", "--output-dir", "-o", help="Base output directory"),
    network: str = typer.Option("local", "--network", "-n", help="Network to deploy to"),
    deploy: bool = typer.Option(
        False, "--deploy", help="Deploy the marketplace after creation"
    ),
    identity: Optional[str] = typer.Option(
        None, "--identity", help="Path to identity PEM file or identity name"
    ),
    mode: str = typer.Option(
        "auto", "--mode", "-m", help="Deploy mode: 'auto', 'upgrade' or 'reinstall'"
    ),
) -> None:
    """Create a new marketplace instance."""
    marketplace_create_command(marketplace_name, output_dir, network, deploy, identity, mode)


@marketplace_app.command("deploy")
def marketplace_deploy(
    folder: str = typer.Option(..., "--folder", "-f", help="Path to marketplace directory"),
    network: str = typer.Option("local", "--network", "-n", help="Network to deploy to"),
    mode: str = typer.Option("auto", "--mode", "-m", help="Deployment mode (auto, upgrade, reinstall)"),
    identity: Optional[str] = typer.Option(None, "--identity", help="Identity file for IC deployment"),
) -> None:
    """Deploy a marketplace instance."""
    marketplace_deploy_command(folder, network, mode, identity)


# ============== Billing Commands ==============

@registry_billing_app.command("balance")
def billing_balance(
    principal_id: str = typer.Option(..., "--principal", "-p", help="User principal ID"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """Get a user's credit balance."""
    billing_balance_command(principal_id, network, canister_id)


@registry_billing_app.command("add_credits")
def billing_add_credits(
    principal_id: str = typer.Option(..., "--principal", "-p", help="User principal ID"),
    amount: int = typer.Option(..., "--amount", "-a", help="Amount of credits to add"),
    stripe_session_id: str = typer.Option("", "--stripe-session", help="Stripe session ID"),
    description: str = typer.Option("Manual top-up", "--description", "-d", help="Transaction description"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """Add credits to a user's balance."""
    billing_add_credits_command(principal_id, amount, stripe_session_id, description, network, canister_id)


@registry_billing_app.command("deduct_credits")
def billing_deduct_credits(
    principal_id: str = typer.Option(..., "--principal", "-p", help="User principal ID"),
    amount: int = typer.Option(..., "--amount", "-a", help="Amount of credits to deduct"),
    description: str = typer.Option("Manual deduction", "--description", "-d", help="Transaction description"),
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """Deduct credits from a user's balance."""
    billing_deduct_credits_command(principal_id, amount, description, network, canister_id)


@registry_billing_app.command("status")
def billing_status(
    network: str = typer.Option("local", "--network", "-n", help="Network to use"),
    canister_id: Optional[str] = typer.Option(
        None, "--canister-id", help="Registry canister ID"
    ),
) -> None:
    """Get overall billing status across all users."""
    billing_status_command(network, canister_id)


@registry_billing_app.command("redeem_voucher")
def billing_redeem_voucher(
    principal_id: str = typer.Option(..., "--principal", "-p", help="User principal ID"),
    code: str = typer.Option(..., "--code", "-c", help="Voucher code to redeem"),
    billing_url: str = typer.Option(
        "https://billing.realmsgos.dev", "--billing-url", help="Billing service URL"
    ),
) -> None:
    """Redeem a voucher code to add credits to a user's balance."""
    billing_redeem_voucher_command(principal_id, code, billing_url)


@registry_realm_app.command("deploy-realm")
def registry_deploy_realm(
    principal_id: str = typer.Option(..., "--principal", "-p", help="User principal ID"),
    realm_name: str = typer.Option(..., "--name", "-n", help="Name for the new realm"),
    management_url: str = typer.Option(
        "https://management.realmsgos.dev", "--management-url", help="Management service URL"
    ),
) -> None:
    """Deploy a new realm via the management service (appears in dashboard)."""
    realm_deploy_realm_command(principal_id, realm_name, management_url)


@registry_realm_app.command("deploy-status")
def registry_deploy_status(
    deployment_id: str = typer.Option(..., "--deployment-id", "-d", help="Deployment ID to check"),
    management_url: str = typer.Option(
        "https://management.realmsgos.dev", "--management-url", help="Management service URL"
    ),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for deployment to complete (polls periodically)"),
    poll_interval: int = typer.Option(10, "--poll-interval", help="Seconds between status polls (with --wait)"),
    max_wait: int = typer.Option(900, "--max-wait", help="Maximum seconds to wait (with --wait)"),
) -> None:
    """Check deployment status, optionally waiting for completion."""
    realm_deploy_status_command(deployment_id, management_url, wait, poll_interval, max_wait)


@app.command("version", hidden=True)
def version() -> None:
    """Show version information."""
    import subprocess
    from pathlib import Path
    from . import __version__
    
    try:
        from . import __commit__, __commit_date__
        print(f"{__version__}+{__commit__}")
        print(__commit_date__)
        return
    except ImportError:
        pass
    
    try:
        cli_dir = Path(__file__).parent.parent.parent
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=cli_dir,
            stderr=subprocess.DEVNULL
        ).decode().strip()
        commit_date = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI"],
            cwd=cli_dir,
            stderr=subprocess.DEVNULL
        ).decode().strip()
        print(f"{__version__}+{commit_hash}")
        print(commit_date)
    except Exception:
        print(__version__)


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    version_flag: bool = typer.Option(False, "--version", help="Show version and exit"),
) -> None:
    """
    Realms CLI - Deploy and manage Realms projects.

    🏛️ Build and deploy digital government platforms on the Internet Computer.

    Quick start:
    1. Copy and modify example_realm_config.json
    2. realms realm deploy --file your_config.json
    3. realms status
    """
    if version_flag:
        version()
        raise typer.Exit()

    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")
    
    # If no command was provided, show error and help suggestion
    if ctx.invoked_subcommand is None:
        console.print("[red]Error: No command provided.[/red]")
        console.print("\n💡 Try running [cyan]realms --help[/cyan] to see available commands.")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
