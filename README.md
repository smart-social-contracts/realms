# Realms

A framework for building and deploying governance systems on the Internet Computer.

## Table of Contents

- [Quick Start](#quick-start)
- [Extension Development](#extension-development)
- [Running Python Code in Realms](#running-python-code-in-realms)
- [Creating a New Realm](#creating-a-new-realm)
- [Multi-Realm Deployment (Mundus)](#multi-realm-deployment-mundus)
- [Sandbox](#sandbox)

---

## Quick Start

```bash
# Install Realms CLI
pip install realms-cli

# or alternatively
pip install -e cli/

# Create a single realm with demo data
realms realm create --random --citizens 50 --deploy

# Or create a multi-realm ecosystem
realms mundus create --deploy

# Your realm is now running!
# Frontend: http://<canister_id>.localhost:8000
```

---

## Extension Development

Realms supports a powerful extension system that allows developers to add custom functionality to realm backends. Extensions are self-contained packages that can be installed into any realm.

### Extension Architecture

Extensions run directly inside the `realm_backend` canister, providing:
- **No inter-canister overhead** - Direct function calls
- **Atomic operations** - Share the same stable memory with realm entities
- **Simple installation** - Copy files, no separate deployment
- **CLI-first workflow** - Easy to develop, test, and distribute

### Creating an Extension

#### 1. Extension Structure

```
my-extension/
├── backend/
│   ├── __init__.py
│   └── entry.py              # Required: Extension entry points
├── frontend/
│   ├── lib/extensions/my_extension/
│   ├── routes/(sidebar)/extensions/my_extension/
│   └── i18n/locales/extensions/my_extension/
├── manifest.json             # Required: Extension metadata
├── requirements.txt          # Python dependencies
├── README.md
├── CHANGELOG.md
├── LICENSE
└── tests/
    └── test_my_extension.py
```

#### 2. Create manifest.json

```json
{
  "name": "my_extension",
  "version": "1.0.0",
  "description": "My awesome extension",
  "author": "Your Name",
  "repository": "https://github.com/username/my-extension",
  "license": "MIT",
  "realms_compatibility": {
    "min_version": "0.1.0",
    "max_version": "0.2.x"
  },
  "entry_points": ["my_function", "another_function"],
  "profiles": ["admin"],
  "categories": ["governance"],
  "icon": "settings",
  "show_in_sidebar": true,
  "python_dependencies": [
    "kybra>=0.10.0"
  ]
}
```

#### 3. Create backend/entry.py

```python
"""My Extension Entry Point"""
import json
from kybra import Async
from kybra_simple_logging import get_logger

logger = get_logger("extensions.my_extension")

def my_function(args: str) -> str:
    """
    Extension function callable from realm_backend.
    
    Args:
        args: JSON string with parameters
    
    Returns:
        JSON string with result
    """
    logger.info(f"my_function called with: {args}")
    
    try:
        params = json.loads(args) if isinstance(args, str) else args
        
        # Your logic here
        result = {"message": "Hello from my extension!"}
        
        return json.dumps({"success": True, "data": result})
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def another_function(args: str) -> Async[str]:
    """Async function example"""
    logger.info("another_function called")
    
    try:
        # Async operations
        result = yield some_async_call()
        
        return json.dumps({"success": True, "data": result})
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})
```

### Installing Extensions

#### For Extension Developers (Local Testing)

```bash
# Clone realms repository
git clone --recurse-submodules https://github.com/smart-social-contracts/realms.git
cd realms

# Install realms CLI in development mode
pip install -e cli/

# Install extensions from source
./scripts/install_extensions.sh

# Deploy for testing
dfx start --clean --background
realms realm create --random --deploy

# Test your extension via frontend or CLI
dfx canister call realm_backend extension_call '("my_extension", "my_function", "{\"param\": \"value\"}")'
```

#### For Realm Operators (Production)

```bash
# Install realms CLI
pip install -e cli/  # (pip install realms-cli when published)

# Create a realm
realms realm create --realm-name "My Realm" --deploy

# Extensions are installed automatically during realm creation
# To update extensions, re-run:
./scripts/install_extensions.sh
dfx deploy realm_frontend

# Deploy
realms realm deploy --network ic --identity prod
```

### Managing Extensions

```bash
# List installed extensions
realms extension list

# Install extensions from source
./scripts/install_extensions.sh

# Uninstall an extension
realms extension uninstall my_extension

# Package an extension for distribution
realms extension package --extension-id my_extension
```

### Testing Extensions

Create tests in `tests/` directory:

```python
# tests/test_my_extension.py
import pytest
import json

def test_my_function():
    """Test extension function"""
    # This requires realms_test_utils (future)
    # from realms_test_utils import RealmTestClient
    
    # client = RealmTestClient()
    # client.install_extension("my_extension")
    # result = client.call_extension("my_extension", "my_function", {})
    # assert result["success"] == True
    pass
```

Run tests:
```bash
pytest tests/ -v
```

### Packaging for Distribution

```bash
# Package extension into distributable zip
realms extension package --extension-id my_extension
# Creates: my_extension-1.0.0.zip in current directory
```

### Publishing Extensions

Extensions are developed in the `extensions/` directory and installed via the install script. For external distribution:

```bash
# Package your extension
realms extension package --extension-id my_extension

# Distribute via GitHub releases or other channels
# Users install by copying to their extensions/ directory
# and running ./scripts/install_extensions.sh
```

### Extension Examples

Available extensions in the repository:

- **admin_dashboard** - Administrative dashboard for realm management
- **citizen_dashboard** - Member-facing dashboard  
- **vault** - Treasury and ICRC-1 token management
- **public_dashboard** - Public-facing statistics and information
- **land_registry** - Property and land management
- **llm_chat** - AI-powered chat assistant
- **notifications** - Notification system
- **passport_verification** - Identity verification
- **justice_litigation** - Legal system management
- **market_place** - Extension marketplace

See `extensions/README.md` for complete documentation

### Extension Best Practices

1. **Use Logging** - Always log important operations
2. **Error Handling** - Catch all exceptions and return JSON errors
3. **JSON API** - All extension functions should accept/return JSON strings
4. **Documentation** - Write comprehensive README with usage examples
5. **Versioning** - Follow semantic versioning
6. **Testing** - Write tests for all functionality
7. **Dependencies** - List all Python dependencies in requirements.txt
8. **Compatibility** - Specify realms version compatibility in manifest.json

### Calling Extensions from Realm Code

```python
# From realm backend code
from core.extensions import extension_async_call

# Call extension function
result = yield extension_async_call("my_extension", "my_function", json.dumps({"key": "value"}))
```

### Extension API Reference

Extensions can access:
- **ggg entities** - User, Member, Treasury, etc.
- **kybra** - IC SDK functions
- **kybra_simple_db** - Database entities
- **kybra_simple_logging** - Logging utilities
- **realm_backend core** - Core realm functionality

---

## Running Python Code in Realms

The `realms shell` command executes Python code inside the realm canister using the unified `execute_code()` function, which automatically detects and handles both synchronous and asynchronous code via the TaskManager.

### Basic Usage

```bash
# Sync code - executes immediately, returns result
realms shell --file examples/sync_example.py

# Async code - schedules task, returns task ID
realms shell --file examples/async_example.py
```

### Response Format

**Sync execution:**
```json
{
  "type": "sync",
  "status": "completed",
  "task_id": "abc123",
  "result": {"count": 5, "names": ["Alice", "Bob"]}
}
```

**Async execution:**
```json
{
  "type": "async",
  "task_id": "def456",
  "status": "pending",
  "message": "Async task scheduled. Check logs or poll status."
}
```

### Code Requirements

**Sync code** - Just write normal Python:
```python
from ggg import Member
members = Member.instances()
result = len(members)  # Optional: set result variable
```

**Async code** - Define an `async_task` function with `yield`:
```python
from kybra import ic

def async_task():
    result = yield some_async_call()
    ic.print(result)
    return result
```

### Implementation Details

- **TaskManager Integration**: Both sync and async code run through the Call → TaskStep → Task → TaskSchedule pipeline
- **Auto-detection**: The presence of `yield` or `async_task` triggers async mode
- **Logging**: Execution logs appear in `dfx.log` or `dfx2.log`, not in CLI output
- **Result Storage**: Results are stored in the `Call._result` attribute for retrieval
- **Status Polling**: Use `dfx canister call realm_backend get_task_status '("task_id")'` to check async task completion

### Examples

See `examples/sync_example.py` and `examples/async_example.py` for working examples.

---

## Scheduled Tasks

Schedule Python code to run automatically at regular intervals.

```bash
# Run a file once
realms run --file examples/my_task.py

# Run every 10 seconds
realms run --file examples/my_task.py --every 10

# Manage tasks
realms ps ls                    # List all tasks
realms ps start <task_id>       # Start a task
realms ps kill <task_id>        # Stop a task
realms ps logs <task_id>        # View execution logs
realms ps logs <task_id> -f     # Follow logs in real-time
```

📖 **Full documentation**: [Scheduled Tasks Reference](./docs/reference/SCHEDULED_TASKS.md)

---

## Creating a New Realm

### Quick Start

```bash
# Install Realms CLI
pip install -e cli/

# Create a new realm with demo data
realms realm create --random --citizens 100 --organizations 10 --deploy

# Or create with custom configuration
realms realm create \
  --realm-name "My Government Realm" \
  --citizens 50 \
  --organizations 5 \
  --transactions 200 \
  --seed 12345 \
  --deploy
```

### Import Existing Data

```bash
# Create realm structure
realms realm create --realm-name "My Realm"

# Import data
cd generated_realm
realms import ../my_realm_data.json

# Deploy
realms realm deploy
```

### Administration

Manage realm data:
- **Via CLI**: `realms import <data.json>` or `realms import <codex.py> --type codex`
- **Via UI**: Use the Admin Dashboard extension (admin-only access)
- **Via Extensions**: Extensions can provide custom data management interfaces

---

## Multi-Realm Deployment (Mundus)

Mundus allows you to deploy multiple realm instances with a shared registry on a single dfx instance.

### Quick Start

```bash
# Create mundus with 3 realms + registry
realms mundus create --deploy

# Access realms at different URLs
# Realm 1: http://<realm1_frontend_id>.localhost:8000
# Realm 2: http://<realm2_frontend_id>.localhost:8000
# Realm 3: http://<realm3_frontend_id>.localhost:8000
# Registry: http://<registry_frontend_id>.localhost:8000
```

### Features

- **Single dfx Instance**: All realms share one dfx process
- **Unique Canister Names**: Each realm has unique canister IDs
- **Shared Registry**: Central registry tracks all realms
- **Independent Data**: Each realm has its own entities and state
- **Customizable**: Configure each realm independently via manifests

### Use Cases

- **Development**: Test multi-realm interactions locally
- **Demos**: Showcase multiple realm configurations
- **Testing**: Integration testing across realms
- **Staging**: Multi-tenant staging environment

### Customization

Edit realm manifests in `examples/demo/realm{N}/manifest.json`:

```json
{
  "type": "realm",
  "name": "My Custom Realm",
  "options": {
    "random": {
      "members": 100,
      "organizations": 10,
      "transactions": 200,
      "disputes": 15,
      "seed": 42
    }
  }
}
```

Then create with your custom manifest:
```bash
realms mundus create --manifest examples/demo/manifest.json --deploy
```

See [Deployment Guide](./docs/DEPLOYMENT_GUIDE.md#multi-realm-deployment-mundus) for details.

---

## Sandbox

[Sandbox Realm](https://sandbox.realmsgos.org).
Decent amount of members (10k) and other objects simulating a production-like environment.
Runs scheduled tasks for payments, tax claculations etc.
Voting of new codex and deployment of it.
Registry in the [Realm Registry](https://registry.realmsgos.org).