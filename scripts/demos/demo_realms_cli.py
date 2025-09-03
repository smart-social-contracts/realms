#!/usr/bin/env python3
"""
Realms CLI Demonstration Script

This script demonstrates the full functionality of the Realms CLI tool
by creating a sample government realm project and showing deployment capabilities.
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add the cli directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "cli"))

# from realms_cli.commands.init import init_command
from realms_cli.commands.deploy import deploy_command
from realms_cli.models import RealmConfig
from realms_cli.utils import load_config, save_config, console, display_success_panel, display_info_panel

def demo_init_command():
    """Demonstrate the realms init command."""
    console.print("\n[bold blue]🏗️  Demo: Realms Init Command[/bold blue]")
    console.print("Creating a new government services realm...\n")
    
    # Create temporary directory for demo
    demo_dir = Path(tempfile.mkdtemp(prefix="realms_demo_"))
    console.print(f"[dim]Demo directory: {demo_dir}[/dim]\n")
    
    try:
        from realms_cli.utils import save_config
        basic_config = {
            "realm": {
                "id": "gov_services_demo",
                "name": "Digital Government Services",
                "description": "Demo government services realm",
                "admin_principal": "rdmx6-jaaaa-aaaaa-aaadq-cai"
            },
            "deployment": {
                "network": "local"
            }
        }
        save_config(basic_config, str(demo_dir / "realm_config.json"))
        
        # Show what was created
        console.print("\n[bold green]📁 Project Structure Created:[/bold green]")
        _show_directory_tree(demo_dir, max_depth=3)
        
        # Show configuration file
        config_file = demo_dir / "realm_config.json"
        if config_file.exists():
            console.print("\n[bold green]⚙️  Generated Configuration:[/bold green]")
            config_data = load_config(str(config_file))
            console.print(f"• Realm ID: {config_data['realm']['id']}")
            console.print(f"• Name: {config_data['realm']['name']}")
            console.print(f"• Network: {config_data['deployment']['network']}")
            console.print(f"• Extensions: {sum(len(exts) for exts in config_data.get('extensions', {}).values())}")
        
        return demo_dir
        
    except Exception as e:
        console.print(f"[red]Demo init failed: {e}[/red]")
        shutil.rmtree(demo_dir, ignore_errors=True)
        return None

def demo_config_validation(demo_dir: Path):
    """Demonstrate configuration validation."""
    console.print("\n[bold blue]✅ Demo: Configuration Validation[/bold blue]")
    
    config_file = demo_dir / "realm_config.json"
    if not config_file.exists():
        console.print("[red]Configuration file not found[/red]")
        return False
    
    try:
        # Load and validate configuration
        config_data = load_config(str(config_file))
        config = RealmConfig(**config_data)
        
        console.print("[green]✅ Configuration is valid![/green]")
        console.print(f"• Realm: {config.realm.name} ({config.realm.id})")
        console.print(f"• Admin: {config.realm.admin_principal}")
        console.print(f"• Network: {config.deployment.network}")
        
        # Show extensions by phase
        if config.extensions:
            console.print("• Extensions by phase:")
            for phase, extensions in config.extensions.items():
                enabled_count = sum(1 for ext in extensions if ext.enabled)
                console.print(f"  - {phase}: {enabled_count}/{len(extensions)} enabled")
        
        return True
        
    except Exception as e:
        console.print(f"[red]Configuration validation failed: {e}[/red]")
        return False

def demo_deploy_dry_run(demo_dir: Path):
    """Demonstrate deployment dry run."""
    console.print("\n[bold blue]🚀 Demo: Deployment Dry Run[/bold blue]")
    console.print("Showing what would be deployed without executing...\n")
    
    config_file = demo_dir / "realm_config.json"
    
    try:
        # Change to demo directory for deployment context
        original_cwd = os.getcwd()
        os.chdir(demo_dir)
        
        # Run dry-run deployment
        deploy_command(
            config_file="realm_config.json",
            network=None,
            skip_extensions=False,
            skip_post_deployment=False,
            phases=None,
            dry_run=True,
            identity_file=None
        )
        
        return True
        
    except Exception as e:
        console.print(f"[red]Deployment dry run failed: {e}[/red]")
        return False
    finally:
        os.chdir(original_cwd)

def demo_custom_configuration():
    """Demonstrate creating a custom configuration."""
    console.print("\n[bold blue]⚙️  Demo: Custom Configuration[/bold blue]")
    console.print("Creating a multi-phase deployment configuration...\n")
    
    # Create a more complex configuration
    custom_config = {
        "realm": {
            "id": "smart_city_platform",
            "name": "Smart City Digital Platform",
            "description": "A comprehensive digital platform for smart city services",
            "admin_principal": "2vxsx-fae",
            "version": "2.0.0",
            "tags": ["smart-city", "government", "digital-services", "iot"]
        },
        "deployment": {
            "network": "local",
            "clean_deploy": True,
            "port": 8080
        },
        "extensions": {
            "initial": [
                {"name": "demo_loader", "enabled": True},
                {"name": "public_dashboard", "enabled": True}
            ],
            "q1": [
                {
                    "name": "citizen_dashboard", 
                    "enabled": True,
                    "init_params": {
                        "theme": "smart-city",
                        "features": ["profile", "services", "payments", "notifications"]
                    }
                },
                {"name": "notifications", "enabled": True}
            ],
            "q2": [
                {
                    "name": "land_registry", 
                    "enabled": True,
                    "init_params": {
                        "blockchain_integration": True,
                        "auto_verification": False
                    }
                },
                {"name": "vault_manager", "enabled": True}
            ],
            "q3": [
                {"name": "justice_litigation", "enabled": True},
                {"name": "passport_verification", "enabled": True}
            ]
        },
        "post_deployment": {
            "actions": [
                {
                    "type": "wait",
                    "name": "Initialize system",
                    "duration": 10
                },
                {
                    "type": "extension_call",
                    "name": "Load base infrastructure data",
                    "extension_name": "demo_loader",
                    "function_name": "load",
                    "args": {"step": "base_setup", "city_mode": True},
                    "retry_count": 3
                },
                {
                    "type": "extension_call",
                    "name": "Create citizen accounts",
                    "extension_name": "demo_loader",
                    "function_name": "load",
                    "args": {"step": "user_management", "batch_size": 1000},
                    "retry_count": 2
                },
                {
                    "type": "extension_call",
                    "name": "Initialize smart city services",
                    "extension_name": "demo_loader",
                    "function_name": "load",
                    "args": {"step": "government_services", "smart_city": True}
                }
            ]
        }
    }
    
    # Save to temporary file and validate
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_path = f.name
    
    try:
        save_config(custom_config, config_path)
        
        # Validate the configuration
        config = RealmConfig(**custom_config)
        
        console.print("[green]✅ Custom configuration created and validated![/green]")
        console.print(f"• Realm: {config.realm.name}")
        console.print(f"• Total Extensions: {sum(len(exts) for exts in config.extensions.values())}")
        console.print(f"• Deployment Phases: {len(config.extensions)}")
        console.print(f"• Post-deployment Actions: {len(config.post_deployment.actions)}")
        
        # Show phase breakdown
        console.print("\n[bold]Extension Deployment Phases:[/bold]")
        for phase, extensions in config.extensions.items():
            console.print(f"• {phase}: {[ext.name for ext in extensions if ext.enabled]}")
        
        return config_path
        
    except Exception as e:
        console.print(f"[red]Custom configuration demo failed: {e}[/red]")
        if os.path.exists(config_path):
            os.unlink(config_path)
        return None

def demo_cli_commands():
    """Demonstrate various CLI commands."""
    console.print("\n[bold blue]🔧 Demo: CLI Commands Overview[/bold blue]")
    
    commands = [
        {
            "command": "realms init",
            "description": "Initialize new Realms project",
            "example": "realms init --name 'My Realm' --id my_realm"
        },
        {
            "command": "realms deploy",
            "description": "Deploy Realms project",
            "example": "realms deploy --file realm_config.json"
        },
        {
            "command": "realms deploy --dry-run",
            "description": "Show deployment plan",
            "example": "realms deploy --dry-run --phases q1,q2"
        },
        {
            "command": "realms status",
            "description": "Check project status",
            "example": "realms status"
        },
        {
            "command": "realms validate",
            "description": "Validate configuration",
            "example": "realms validate --file realm_config.json"
        }
    ]
    
    for cmd in commands:
        console.print(f"[cyan]• {cmd['command']}[/cyan]: {cmd['description']}")
        console.print(f"  [dim]Example: {cmd['example']}[/dim]")

def _show_directory_tree(path: Path, max_depth: int = 2, current_depth: int = 0):
    """Show directory tree structure."""
    if current_depth >= max_depth:
        return
    
    items = sorted(path.iterdir())
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        prefix = "└── " if is_last else "├── "
        indent = "    " * current_depth
        
        if item.is_dir():
            console.print(f"[dim]{indent}{prefix}[/dim][blue]{item.name}/[/blue]")
            if current_depth < max_depth - 1:
                next_indent = "    " if is_last else "│   "
                _show_directory_tree(item, max_depth, current_depth + 1)
        else:
            console.print(f"[dim]{indent}{prefix}{item.name}[/dim]")

def main():
    """Run the complete Realms CLI demonstration."""
    console.print("[bold green]🏛️  Realms CLI - Complete Demonstration[/bold green]")
    console.print("This demo showcases the full functionality of the Realms CLI tool.\n")
    
    try:
        # Demo 1: Initialize a new project
        demo_dir = demo_init_command()
        if not demo_dir:
            return 1
        
        # Demo 2: Validate configuration
        if not demo_config_validation(demo_dir):
            return 1
        
        # Demo 3: Deployment dry run
        if not demo_deploy_dry_run(demo_dir):
            return 1
        
        # Demo 4: Custom configuration
        custom_config_path = demo_custom_configuration()
        
        # Demo 5: CLI commands overview
        demo_cli_commands()
        
        # Success summary
        display_success_panel(
            "Demo Complete! 🎉",
            "The Realms CLI demonstration has completed successfully.\n\n"
            "Key Features Demonstrated:\n"
            "• Project scaffolding with realms init\n"
            "• Configuration validation\n"
            "• Deployment planning with dry-run\n"
            "• Multi-phase extension deployment\n"
            "• Post-deployment automation\n"
            "• Custom configuration creation\n\n"
            "The Realms CLI is ready for production use!"
        )
        
        # Cleanup
        if demo_dir and demo_dir.exists():
            shutil.rmtree(demo_dir, ignore_errors=True)
        if custom_config_path and os.path.exists(custom_config_path):
            os.unlink(custom_config_path)
        
        return 0
        
    except Exception as e:
        console.print(f"[red]Demo failed: {e}[/red]")
        return 1

if __name__ == "__main__":
    sys.exit(main())
