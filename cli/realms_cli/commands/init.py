"""Init command for creating new Realms projects."""

import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.prompt import Prompt, Confirm
from rich.table import Table

from ..models import RealmConfig, RealmMetadata, DeploymentConfig
from ..utils import (
    console, 
    save_config, 
    create_directory_structure, 
    display_success_panel,
    display_info_panel
)


def init_command(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Realm name"),
    realm_id: Optional[str] = typer.Option(None, "--id", help="Realm ID"),
    admin_principal: Optional[str] = typer.Option(None, "--admin", help="Admin principal ID"),
    network: str = typer.Option("local", "--network", help="Target network"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Interactive mode"),
    output_dir: str = typer.Option(".", "--output", "-o", help="Output directory")
) -> None:
    """Initialize a new Realms project with scaffolding and configuration."""
    
    console.print("[bold blue]🏛️  Realms Project Initialization[/bold blue]\n")
    
    output_path = Path(output_dir)
    
    # Interactive prompts if not provided
    if interactive:
        if not name:
            name = Prompt.ask("Enter realm name", default="My Realm")
        
        if not realm_id:
            suggested_id = name.lower().replace(" ", "_").replace("-", "_")
            realm_id = Prompt.ask("Enter realm ID", default=suggested_id)
        
        if not admin_principal:
            admin_principal = Prompt.ask("Enter admin principal ID", default="2vxsx-fae")
        
        network = Prompt.ask(
            "Select target network", 
            choices=["local", "local2", "staging", "ic"],
            default=network
        )
        
        # Ask about extensions to include
        console.print("\n[bold]Available extensions:[/bold]")
        available_extensions = [
            "demo_loader", "public_dashboard", "citizen_dashboard", 
            "vault_manager", "land_registry", "justice_litigation",
            "notifications", "llm_chat", "passport_verification"
        ]
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Extension", style="cyan")
        table.add_column("Description", style="white")
        
        extension_descriptions = {
            "demo_loader": "Loads demo data for testing",
            "public_dashboard": "Public-facing dashboard",
            "citizen_dashboard": "Citizen services dashboard",
            "vault_manager": "Digital asset management",
            "land_registry": "Land ownership registry",
            "justice_litigation": "Legal case management",
            "notifications": "Notification system",
            "llm_chat": "AI chat interface",
            "passport_verification": "Identity verification"
        }
        
        for ext in available_extensions:
            table.add_row(ext, extension_descriptions.get(ext, ""))
        
        console.print(table)
        
        selected_extensions = []
        if Confirm.ask("\nWould you like to select extensions to include?", default=True):
            for ext in available_extensions:
                if Confirm.ask(f"Include {ext}?", default=ext in ["demo_loader", "public_dashboard"]):
                    selected_extensions.append(ext)
    else:
        # Non-interactive mode - use defaults or provided values
        if not name:
            name = "My Realm"
        if not realm_id:
            realm_id = "my_realm"
        if not admin_principal:
            admin_principal = "2vxsx-fae"
        selected_extensions = ["demo_loader", "public_dashboard"]
    
    # Create realm configuration
    realm_metadata = RealmMetadata(
        id=realm_id,
        name=name,
        description=f"A digital realm for {name}",
        admin_principal=admin_principal,
        version="1.0.0",
        tags=["government", "digital-services"]
    )
    
    deployment_config = DeploymentConfig(
        network=network,
        clean_deploy=True
    )
    
    # Organize extensions by phases
    extensions = {}
    if selected_extensions:
        initial_extensions = []
        for ext in selected_extensions:
            initial_extensions.append({
                "name": ext,
                "source": "local",
                "enabled": True
            })
        extensions["initial"] = initial_extensions
    
    # Create post-deployment actions for demo data
    post_deployment_actions = []
    if "demo_loader" in selected_extensions:
        post_deployment_actions = [
            {
                "type": "wait",
                "name": "Wait for canisters to initialize",
                "duration": 5
            },
            {
                "type": "extension_call",
                "name": "Load base demo data",
                "extension_name": "demo_loader",
                "function_name": "load",
                "args": {"step": "base_setup"},
                "retry_count": 2
            },
            {
                "type": "extension_call",
                "name": "Load user management data",
                "extension_name": "demo_loader",
                "function_name": "load",
                "args": {"step": "user_management", "batch": 0},
                "retry_count": 1
            }
        ]
    
    # Create full configuration
    config_data = {
        "realm": realm_metadata.dict(),
        "deployment": deployment_config.dict(),
        "extensions": extensions,
        "post_deployment": {
            "actions": post_deployment_actions
        } if post_deployment_actions else None
    }
    
    # Create project structure
    project_structure = {
        "src": {
            "realm_backend": {
                "main.py": _get_backend_template(),
                "realm_backend.did": _get_candid_template(),
                "__init__.py": ""
            },
            "realm_frontend": {
                "package.json": _get_frontend_package_json(realm_id),
                "src": {
                    "app.html": _get_app_html_template(name),
                    "app.css": _get_app_css_template(),
                    "routes": {
                        "+layout.svelte": _get_layout_template(name)
                    }
                }
            }
        },
        "extensions": {},
        "scripts": {
            "deploy_local.sh": _get_deploy_script_template(),
            "install_extensions.sh": _get_install_extensions_script()
        },
        "dfx.json": _get_dfx_json_template(realm_id),
        "package.json": _get_root_package_json(realm_id),
        "requirements.txt": _get_requirements_txt(),
        "README.md": _get_readme_template(name, realm_id),
        ".gitignore": _get_gitignore_template(),
        "realm_config.json": json.dumps(config_data, indent=2)
    }
    
    # Create the project
    console.print(f"\n[bold]Creating project structure in: {output_path.absolute()}[/bold]")
    
    try:
        create_directory_structure(output_path, project_structure)
        
        # Make scripts executable
        scripts_dir = output_path / "scripts"
        for script_file in scripts_dir.glob("*.sh"):
            script_file.chmod(0o755)
        
        display_success_panel(
            "Project Created Successfully!",
            f"Your new Realms project '{name}' has been created.\n\n"
            f"📁 Location: {output_path.absolute()}\n"
            f"🆔 Realm ID: {realm_id}\n"
            f"🌐 Network: {network}\n"
            f"📦 Extensions: {len(selected_extensions)} selected\n\n"
            "Next steps:\n"
            f"1. cd {output_path.name if output_path != Path('.') else '.'}\n"
            "2. realms deploy --file realm_config.json\n"
            "3. Open http://localhost:8000 in your browser"
        )
        
    except Exception as e:
        console.print(f"[red]Failed to create project: {e}[/red]")
        raise typer.Exit(1)


def _get_backend_template() -> str:
    """Get the backend main.py template."""
    return '''"""Main backend module for Realms."""

from kybra import (
    Canister,
    query,
    update,
    init,
    Principal,
    Record,
    text,
    nat64,
    Opt,
    Vec
)
from typing import Dict, Any, Optional, List


# Type definitions
class RealmInfo(Record):
    id: text
    name: text
    description: text
    admin_principal: Principal
    version: text
    created_at: nat64


class ExtensionCall(Record):
    extension_name: text
    function_name: text
    args: text


# Global state
realm_info: Opt[RealmInfo] = None
extensions: Dict[text, Any] = {}


class RealmCanister(Canister):
    
    @init
    def init_canister(self, realm_id: text, name: text, description: text, admin: Principal):
        """Initialize the realm canister."""
        global realm_info
        realm_info = RealmInfo(
            id=realm_id,
            name=name,
            description=description,
            admin_principal=admin,
            version="1.0.0",
            created_at=0  # TODO: Add proper timestamp
        )
    
    @query
    def get_realm_info(self) -> Opt[RealmInfo]:
        """Get realm information."""
        return realm_info
    
    @query
    def get_status(self) -> text:
        """Get canister status."""
        return "running"
    
    @update
    def extension_sync_call(self, call: ExtensionCall) -> text:
        """Call an extension function synchronously."""
        # This is a placeholder - actual extension calls would be implemented here
        return f"Called {call.extension_name}.{call.function_name} with args: {call.args}"
    
    @query
    def list_extensions(self) -> Vec[text]:
        """List available extensions."""
        return list(extensions.keys())


# Create canister instance
canister = RealmCanister()
'''

def _get_candid_template() -> str:
    """Get the Candid interface template."""
    return '''type RealmInfo = record {
    id : text;
    name : text;
    description : text;
    admin_principal : principal;
    version : text;
    created_at : nat64;
};

type ExtensionCall = record {
    extension_name : text;
    function_name : text;
    args : text;
};

service : (text, text, text, principal) -> {
    get_realm_info : () -> (opt RealmInfo) query;
    get_status : () -> (text) query;
    extension_sync_call : (ExtensionCall) -> (text);
    list_extensions : () -> (vec text) query;
}
'''

def _get_frontend_package_json(realm_id: str) -> str:
    """Get frontend package.json template."""
    return json.dumps({
        "name": f"{realm_id}-frontend",
        "version": "0.0.1",
        "private": True,
        "scripts": {
            "build": "vite build",
            "dev": "vite dev",
            "preview": "vite preview",
            "check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json",
            "check:watch": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json --watch"
        },
        "devDependencies": {
            "@sveltejs/adapter-static": "^2.0.3",
            "@sveltejs/kit": "^1.20.4",
            "svelte": "^4.0.5",
            "svelte-check": "^3.4.3",
            "typescript": "^5.0.0",
            "vite": "^4.4.2"
        },
        "type": "module"
    }, indent=2)

def _get_app_html_template(realm_name: str) -> str:
    """Get app.html template."""
    return f'''<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <link rel="icon" href="%sveltekit.assets%/favicon.png" />
        <meta name="viewport" content="width=device-width" />
        <title>{realm_name}</title>
        %sveltekit.head%
    </head>
    <body data-sveltekit-preload-data="hover">
        <div style="display: contents">%sveltekit.body%</div>
    </body>
</html>
'''

def _get_app_css_template() -> str:
    """Get app.css template."""
    return '''/* Global styles */
body {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background-color: #f8f9fa;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.header {
    background-color: #2563eb;
    color: white;
    padding: 1rem 0;
    margin-bottom: 2rem;
}

.header h1 {
    margin: 0;
    text-align: center;
}
'''

def _get_layout_template(realm_name: str) -> str:
    """Get layout template."""
    return f'''<script lang="ts">
    import '../app.css';
</script>

<div class="header">
    <div class="container">
        <h1>{realm_name}</h1>
    </div>
</div>

<div class="container">
    <slot />
</div>
'''

def _get_dfx_json_template(realm_id: str) -> str:
    """Get dfx.json template."""
    return json.dumps({
        "dfx": "0.29.0",
        "canisters": {
            "realm_backend": {
                "build": f"python -m kybra realm_backend src/realm_backend/main.py",
                "candid": "src/realm_backend/realm_backend.did",
                "declarations": {"node_compatibility": True},
                "gzip": True,
                "metadata": [{"name": "candid:service"}],
                "tech_stack": {
                    "cdk": {"kybra": {}},
                    "language": {"python": {}}
                },
                "type": "custom",
                "wasm": ".kybra/realm_backend/realm_backend.wasm"
            },
            "realm_frontend": {
                "source": ["src/realm_frontend/dist"],
                "type": "assets",
                "workspace": "realm_frontend"
            }
        },
        "defaults": {
            "build": {"args": "", "packtool": ""}
        },
        "networks": {
            "local": {"bind": "127.0.0.1:8000", "type": "ephemeral"},
            "ic": {"providers": ["https://icp0.io"], "type": "persistent"}
        },
        "output_env_file": ".env",
        "version": 1
    }, indent=2)

def _get_root_package_json(realm_id: str) -> str:
    """Get root package.json template."""
    return json.dumps({
        "name": realm_id,
        "version": "1.0.0",
        "workspaces": ["src/realm_frontend"],
        "scripts": {
            "dev": "npm run dev --workspace realm_frontend",
            "build": "npm run build --workspace realm_frontend"
        }
    }, indent=2)

def _get_requirements_txt() -> str:
    """Get requirements.txt template."""
    return '''kybra==0.7.*
kybra-simple-logging==0.2.*
kybra-simple-db>=0.2.1
'''

def _get_deploy_script_template() -> str:
    """Get deploy script template."""
    return '''#!/bin/bash

set -e
set -x

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    if [ -d "venv" ]; then
        echo "Activating virtual environment..."
        source venv/bin/activate
    else
        echo "Creating virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    fi
fi

# Stop and start dfx
dfx stop 2>/dev/null || true
dfx start --clean --background

# Install extensions if directory exists
if [ -d "extensions" ]; then
    ./scripts/install_extensions.sh
fi

# Deploy backend
dfx deploy realm_backend --yes
dfx generate realm_backend

# Build and deploy frontend
npm install --legacy-peer-deps
npm run build --workspace realm_frontend
dfx deploy realm_frontend

echo "Deployment complete! Visit http://localhost:8000"
'''

def _get_install_extensions_script() -> str:
    """Get install extensions script template."""
    return '''#!/bin/bash

set -e

echo "Installing extensions..."

# Check if extensions directory exists
if [ ! -d "extensions" ]; then
    echo "No extensions directory found, skipping extension installation"
    exit 0
fi

# Check if realm-extension-cli.py exists
if [ ! -f "scripts/realm-extension-cli.py" ]; then
    echo "Extension CLI not found, skipping extension installation"
    exit 0
fi

# Install all extensions
python scripts/realm-extension-cli.py install --all

echo "Extensions installed successfully"
'''

def _get_readme_template(realm_name: str, realm_id: str) -> str:
    """Get README template."""
    return f'''# {realm_name}

A Realms-based digital government platform.

## Quick Start

1. **Deploy locally:**
   ```bash
   realms deploy --file realm_config.json
   ```

2. **Visit your realm:**
   Open http://localhost:8000 in your browser

## Configuration

The realm is configured via `realm_config.json`. Key settings:

- **Realm ID:** `{realm_id}`
- **Network:** Local development
- **Extensions:** Configured in phases

## Development

### Prerequisites

- Python 3.8+
- Node.js 16+
- dfx (Internet Computer SDK)

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt
npm install

# Start local development
./scripts/deploy_local.sh
```

### Adding Extensions

Extensions are managed through the `extensions/` directory and deployed via:

```bash
./scripts/install_extensions.sh
```

## Project Structure

```
{realm_id}/
├── src/
│   ├── realm_backend/     # Python backend canister
│   └── realm_frontend/    # SvelteKit frontend
├── extensions/            # Extension source code
├── scripts/              # Deployment and utility scripts
├── realm_config.json     # Realm configuration
└── dfx.json             # Internet Computer configuration
```

## Deployment

### Local
```bash
realms deploy --file realm_config.json
```

### Production
```bash
realms deploy --file realm_config.json --network ic
```

## License

MIT License - see LICENSE file for details.
'''

def _get_gitignore_template() -> str:
    """Get .gitignore template."""
    return '''# Dependencies
node_modules/
venv/
.venv/

# Build outputs
.dfx/
.kybra/
dist/
build/

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Extension deployment artifacts
src/realm_backend/extension_packages/
src/realm_frontend/src/lib/extensions/
src/realm_frontend/src/routes/(sidebar)/extensions/
src/realm_frontend/src/lib/i18n/locales/extensions/

# Logs
*.log
dfx.log

# Temporary files
*.tmp
*.temp
'''
