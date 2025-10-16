# Realms

A framework for building and deploying governance systems on the Internet Computer.

## Table of Contents

- [Extension Development](#extension-development)
- [Running Python Code in Realms](#running-python-code-in-realms)
- [Creating a New Realm](#creating-a-new-realm)
- [Sandbox](#sandbox)

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
# Clone realms at specific version
git clone https://github.com/smart-social-contracts/realms.git
cd realms
git checkout v1.2.3  # Use specific release

# Install realms CLI in development mode
pip install -e cli/

# Install your extension from local path
realms extension install --source /path/to/my-extension/

# Deploy for testing
dfx start --clean --background
realms deploy --network local

# Test your extension
dfx canister call realm_backend extension_call '("my_extension", "my_function", "{\"param\": \"value\"}")'
```

#### For Realm Operators (Production)

```bash
# Install realms CLI
pip install realms-cli

# Create a realm
realms create my-realm --deploy

# Install extension from GitHub release
realms extension install my_extension \
  --from https://github.com/username/my-extension/releases/download/v1.0.0/my_extension-1.0.0.zip

# Or from extension registry (future)
realms extension install my_extension@1.0.0

# Deploy
realms deploy
```

### Managing Extensions

```bash
# List installed extensions
realms extension list

# Uninstall an extension
realms extension uninstall my_extension

# Update an extension
realms extension install my_extension --from <new-url>
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
realms extension package /path/to/my-extension/
# Creates: my_extension-1.0.0.zip
```

### Publishing Extensions

```bash
# Tag release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# Create GitHub release with package
gh release create v1.0.0 my_extension-1.0.0.zip \
  --title "My Extension v1.0.0" \
  --notes "Release notes here"
```

### Extension Examples

- **vault_manager** - Treasury and token management
  - Repository: https://github.com/smart-social-contracts/realms-extension-vault
  - Features: ckBTC balance tracking, transfers, ICRC integration

- More examples available in `extensions/` directory

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
- **ggg entities** - User, Citizen, Treasury, etc.
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
from ggg import Citizen
citizens = Citizen.instances()
result = len(citizens)  # Optional: set result variable
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




## Creating a New Realm

### Quick Start

```bash
# Install Realms CLI
pip install realms-cli  # (future - for now: pip install -e cli/)

# Create a new realm
realms create my-realm --deploy

# Or create with random data for testing
realms create my-realm --random --deploy
```

### Configure Your Realm

Write a JSON configuration file or copy one from the [Realm Registry](https://registry.realmsgos.org).

```bash
# Import realm data
realms realm import cli/example_realm_data.json
```

### Add Extensions

After creating your realm, you can extend its functionality:

```bash
# Install treasury management
realms extension install vault_manager

# Install governance extensions
realms extension install voting

# See all available extensions
realms extension list
```

### Administration

Upload members, codex, and other data:
- Via CLI: `realms realm import <data.json>`
- Via UI: Use the `Administration Dashboard` extension

## Sandbox

[Sandbox Realm](https://sandbox.realmsgos.org).
Decent amount of members (10k) and other objects simulating a production-like environment.
Runs scheduled tasks for payments, tax claculations etc.
Voting of new codex and deployment of it.
Registry in the [Realm Registry](https://registry.realmsgos.org).