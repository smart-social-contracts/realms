# Entity Method Overrides

Extensions can override methods on core GGG entity classes to customize behavior without modifying the core codebase. This powerful feature enables extensions to deeply integrate with the Realms platform.

## Overview

Entity method overrides allow extensions to:
- Replace or enhance core entity behavior
- Add custom logic to critical system hooks
- Integrate external services (e.g., blockchain transfers, identity verification)
- Customize user onboarding and lifecycle management

## How It Works

1. **Define the override in extension manifest**: Add `entity_method_overrides` array to your extension's `manifest.json`
2. **Implement the method**: Create the override implementation in your extension's backend code
3. **Install the extension**: The platform automatically binds the override to the entity class at runtime

## Configuration

Add the `entity_method_overrides` array to your extension's `manifest.json`:

```json
{
  "name": "my_extension",
  "version": "1.0.0",
  "entity_method_overrides": [
    {
      "entity": "EntityClassName",
      "method": "method_name",
      "type": "method|staticmethod|classmethod",
      "implementation": "module.function_name",
      "description": "Human-readable description"
    }
  ]
}
```

### Configuration Fields

- **entity** (required): Name of the entity class from the `ggg` module (e.g., "User", "Transfer", "Balance")
- **method** (required): Name of the method to override (must exist on the entity class)
- **type** (optional): Method type - `"method"` (instance method, default), `"staticmethod"`, or `"classmethod"`
- **implementation** (required): Path to the implementation function in your extension (e.g., "methods.my_function")
- **description** (optional): Human-readable description of what the override does

## Implementation Path

The `implementation` field uses dot notation relative to your extension's backend package:

- `"methods.user_register_posthook"` → `extensions/{extension_id}/backend/methods.py::user_register_posthook()`
- `"utils.custom_logic"` → `extensions/{extension_id}/backend/utils.py::custom_logic()`

## Method Types

### Instance Methods (default)

Override methods that operate on entity instances:

```python
def execute_transfer(self) -> dict:
    """self is the entity instance (e.g., Transfer object)"""
    logger.info(f"Executing transfer {self.id}")
    # Your custom logic here
    return {"status": "success"}
```

Manifest:
```json
{
  "entity": "Transfer",
  "method": "execute",
  "implementation": "methods.execute_transfer"
}
```

### Static Methods

Override static methods that don't need instance or class context:

```python
def user_register_posthook(user):
    """user is passed as a parameter"""
    logger.info(f"User registered: {user.id}")
    # Custom post-registration logic
    return
```

Manifest:
```json
{
  "entity": "User",
  "method": "user_register_posthook",
  "type": "staticmethod",
  "implementation": "methods.user_register_posthook"
}
```

### Class Methods

Override methods that operate on the class itself:

```python
def refresh_balance(cls, force: bool = False) -> dict:
    """cls is the entity class (e.g., Balance)"""
    logger.info(f"Refreshing all {cls.__name__} instances")
    # Your custom logic here
    return {"refreshed": True}
```

Manifest:
```json
{
  "entity": "Balance",
  "method": "refresh",
  "type": "classmethod",
  "implementation": "methods.refresh_balance"
}
```

## Complete Example: User Registration Hook

This example shows how to override the `user_register_posthook` method to add custom post-registration logic.

### Step 1: Extension Backend Implementation

Create `extensions/my_extension/backend/methods.py`:

```python
"""My Extension Entity Method Implementations."""

from kybra_simple_logging import get_logger

logger = get_logger("my_extension.methods")


def user_register_posthook(user):
    """Custom post-registration hook.
    
    Called after a new user registers on the platform.
    Use this to:
    - Send welcome notifications
    - Initialize user data (wallets, default settings)
    - Log analytics events
    - Trigger onboarding workflows
    
    Args:
        user: The newly registered User entity
    """
    logger.info(f"🎉 New user registered: {user.id}")
    logger.info(f"   Profiles: {[p.name for p in user.profiles]}")
    
    # Example: Create welcome notification
    # from ggg import Notification
    # Notification(
    #     user=user,
    #     message="Welcome to the realm!",
    #     type="welcome"
    # )
    
    return
```

### Step 2: Extension Manifest

Update `extensions/my_extension/manifest.json`:

```json
{
  "name": "my_extension",
  "version": "1.0.0",
  "description": "My custom extension",
  "entity_method_overrides": [
    {
      "entity": "User",
      "method": "user_register_posthook",
      "type": "staticmethod",
      "implementation": "methods.user_register_posthook",
      "description": "Custom post-registration hook with welcome notifications"
    }
  ]
}
```

### Step 3: Install Extension

```bash
./scripts/install_extensions.sh
dfx deploy realm_backend
```

## Real-World Examples

### Vault Extension: Blockchain Transfers

The `vault` extension overrides `Transfer.execute()` to handle external blockchain transfers:

```json
{
  "entity": "Transfer",
  "method": "execute",
  "implementation": "methods.execute_transfer",
  "description": "Execute external blockchain transfer via vault"
}
```

Implementation:
```python
def execute_transfer(self) -> Async[dict]:
    """Execute transfer via blockchain integration."""
    logger.info(f"Executing blockchain transfer: {self.id}")
    vault_response = yield _transfer(self.principal_to, self.amount)
    return vault_response
```

### Vault Extension: Balance Sync

The `vault` extension overrides `Balance.refresh()` to sync with blockchain state:

```json
{
  "entity": "Balance",
  "method": "refresh",
  "type": "classmethod",
  "implementation": "methods.refresh_balance",
  "description": "Sync all balances with vault state"
}
```

Implementation:
```python
def refresh_balance(cls, force: bool = False) -> Async[dict]:
    """Sync all balances with blockchain state."""
    logger.info("Refreshing all balances from vault...")
    vault_response = yield _refresh(force)
    return vault_response
```

## Best Practices

1. **Logging**: Always log when overrides execute for debugging and audit trails
2. **Error Handling**: Wrap custom logic in try-except blocks to prevent crashes
3. **Documentation**: Document what your override does and why
4. **Testing**: Test overrides thoroughly in development before deploying
5. **Backward Compatibility**: Consider existing behavior when overriding core methods
6. **Performance**: Be mindful of performance impact, especially for frequently called methods

## Debugging

When developing overrides:

1. Check backend logs for loading messages:
   ```
   Loading N method override(s) for {extension_id}
   ✓ Entity.method() -> extension.module.function
   ```

2. Add debug logging in your implementation:
   ```python
   logger.info(f"Override called with: {args}")
   ```

3. Test with a single user/entity before enabling for production

## Troubleshooting

### Override Not Loading

- Verify `manifest.json` syntax is valid JSON
- Check entity name matches exactly (case-sensitive)
- Ensure method exists on the entity class
- Verify implementation path is correct

### Runtime Errors

- Check backend logs for error messages
- Ensure all imports are available in extension backend
- Verify method signature matches expected parameters
- Test implementation independently before installing

## Security Considerations

Entity method overrides have full access to the entity and system state. Always:

- Validate inputs thoroughly
- Avoid exposing sensitive data in logs
- Follow principle of least privilege
- Review extension manifests before installing
- Only install extensions from trusted sources
