# Realms CLI

A powerful command-line tool for managing Realms project lifecycle on the Internet Computer.

## Features

- **🏗️ Project Scaffolding**: Initialize complete Realms projects with proper structure
- **🚀 Automated Deployment**: Deploy backend + frontend + extensions with single command
- **📦 Extension Management**: Phased rollouts (q1-q4) with dependency management
- **⚙️ Post-Deployment Actions**: Automated setup and data population
- **🔧 Configuration Validation**: Schema validation with helpful error messages
- **📊 Project Status**: Check project health and deployment status

## Prerequisites

Before installing realms-cli, ensure you have the following dependencies:

### 1. DFX (DFINITY Canister SDK)
```bash
sh -ci "$(curl -fsSL https://internetcomputer.org/install.sh)"
```
- **Required for**: Canister deployment, local replica management
- **Used by**: `realms deploy` command for backend/frontend deployment
- **Verify installation**: `dfx --version`

### 2. Node.js (v16 or later)
```bash
# Option 1: Download from https://nodejs.org
# Option 2: Via package manager (Ubuntu/Debian)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Option 3: Via nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18
```
- **Required for**: Frontend building, npm package management
- **Used by**: Frontend canister builds during deployment
- **Verify installation**: `node --version && npm --version`

## Installation

```bash
pip install realms-cli
```

### From Source

```bash
git clone https://github.com/smartsocialcontracts/realms
cd realms/cli
pip install -e .
```

## Prerequisites

- Python 3.8+
- [dfx](https://internetcomputer.org/docs/current/developer-docs/setup/install/) (Internet Computer SDK)
- Node.js 16+
- Git

## Quick Start

### 1. Initialize a New Realm

```bash
realms init --name "My Government Realm" --id my_gov_realm
```

This creates a complete project structure with:
- Backend canister (Python/Kybra)
- Frontend canister (SvelteKit)
- Extension system
- Configuration files
- Deployment scripts

### 2. Deploy Your Realm

```bash
cd my_gov_realm
realms deploy --file realm_config.json
```

Your realm will be available at `http://localhost:8000`

## Commands

### `realms init`

Initialize a new Realms project with scaffolding.

```bash
realms init [OPTIONS]

Options:
  -n, --name TEXT           Realm name
  --id TEXT                 Realm ID (lowercase, underscores)
  --admin TEXT              Admin principal ID
  --network TEXT            Target network [local|staging|ic]
  --interactive/--no-interactive  Interactive mode (default: true)
  -o, --output TEXT         Output directory (default: current)
```

**Example:**
```bash
realms init --name "City Services" --id city_services --admin "2vxsx-fae"
```

### `realms deploy`

Deploy a Realms project based on configuration.

```bash
realms deploy [OPTIONS]

Options:
  -f, --file TEXT           Configuration file (default: realm_config.json)
  -n, --network TEXT        Override network from config
  --skip-extensions         Skip extension deployment
  --skip-post-deployment    Skip post-deployment actions
  --phases TEXT             Deploy specific phases only
  --dry-run                 Show deployment plan without executing
  --identity TEXT           Identity file for authentication
```

**Examples:**
```bash
# Basic deployment
realms deploy

# Deploy to IC mainnet
realms deploy --network ic --identity ~/.config/dfx/identity/production/identity.pem

# Deploy only specific extension phases
realms deploy --phases q1,q2

# Dry run to see what would be deployed
realms deploy --dry-run
```

### `realms status`

Show the current status of your Realms project.

```bash
realms status
```

### `realms validate`

Validate a realm configuration file.

```bash
realms validate [--file realm_config.json]
```

## Configuration

Realms projects are configured via `realm_config.json`:

```json
{
  "realm": {
    "id": "my_government_realm",
    "name": "My Government Realm",
    "description": "A digital government platform",
    "admin_principal": "2vxsx-fae",
    "version": "1.0.0"
  },
  "deployment": {
    "network": "local",
    "clean_deploy": true
  },
  "extensions": {
    "initial": [
      {"name": "public_dashboard", "enabled": true},
      {"name": "citizen_dashboard", "enabled": true}
    ],
    "q1": [
      {"name": "vault_manager", "enabled": true}
    ]
  },
  "post_deployment": {
    "actions": [
      {
        "type": "extension_call",
        "name": "Load demo data",
        "extension_name": "demo_loader",
        "function_name": "load",
        "args": {"step": "base_setup"}
      }
    ]
  }
}
```

### Configuration Schema

- **realm**: Basic realm metadata (id, name, admin, etc.)
- **deployment**: Deployment settings (network, port, identity)
- **extensions**: Extensions organized by deployment phases
- **post_deployment**: Actions to run after deployment

## Extension Phases

Extensions can be organized into deployment phases:

- `initial`: Core extensions deployed first
- `q1`, `q2`, `q3`, `q4`: Quarterly rollout phases
- `phase_1`, `phase_2`, etc.: Custom phases

## Post-Deployment Actions

Automate setup tasks after deployment:

- **extension_call**: Call extension functions
- **script**: Run shell scripts
- **wait**: Add delays between actions

## Installation

### Recommended: Using pipx (Isolated Environment)

The easiest way to install the Realms CLI is using `pipx`, which automatically manages isolated Python environments:

```bash
# Install pipx if you don't have it
pip install pipx

# Install realms-cli in an isolated environment
pipx install realms-cli

# Use the CLI tool (no venv activation needed)
realms --help
realms create --citizens 50
```

### Alternative: Using pip with venv

If you prefer manual environment management:

```bash
python -m venv realms-env
source realms-env/bin/activate  # On Windows: realms-env\Scripts\activate
pip install realms-cli
```

### Development Setup

For contributing to the CLI tool:

```bash
git clone https://github.com/smartsocialcontracts/realms
cd realms/cli
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black realms_cli/
isort realms_cli/
```

## Examples

### Government Services Platform

```bash
realms init \
  --name "Digital Government Services" \
  --id gov_services \
  --admin "rdmx6-jaaaa-aaaaa-aaadq-cai"

cd gov_services
realms deploy
```

### Multi-Phase Deployment

```json
{
  "extensions": {
    "initial": [
      {"name": "public_dashboard", "enabled": true}
    ],
    "q1": [
      {"name": "citizen_dashboard", "enabled": true},
      {"name": "notifications", "enabled": true}
    ],
    "q2": [
      {"name": "land_registry", "enabled": true},
      {"name": "justice_litigation", "enabled": true}
    ]
  }
}
```

Deploy phases incrementally:
```bash
realms deploy --phases initial
realms deploy --phases q1
realms deploy --phases q2
```

## Troubleshooting

### Common Issues

**dfx not found**
```bash
# Install dfx
sh -ci "$(curl -fsSL https://internetcomputer.org/install.sh)"
```

**Port already in use**
```bash
# Kill existing dfx processes
dfx stop
pkill dfx
```

**Extension deployment fails**
```bash
# Check extension directory exists
ls extensions/
# Reinstall extensions
./scripts/install_extensions.sh
```

### Getting Help

- Check project status: `realms status`
- Validate configuration: `realms validate`
- Use dry-run mode: `realms deploy --dry-run`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- 📖 [Documentation](https://docs.realms.dev)
- 🐛 [Issue Tracker](https://github.com/smartsocialcontracts/realms/issues)
- 💬 [Discord Community](https://discord.gg/realms)
