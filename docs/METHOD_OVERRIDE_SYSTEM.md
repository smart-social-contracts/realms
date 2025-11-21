# Extension Method Override System

## Overview

The Method Override System allows extensions to provide implementations for entity methods through declarative manifest configuration. This enables a clean, modular architecture where core entities define method signatures and extensions provide specialized implementations.

## Architecture

```
Extension Manifest (manifest.json)
          ↓
   Declares Method Overrides
          ↓
Extension Method Loader (runtime)
          ↓
   Dynamically Binds Methods
          ↓
    Entity.method() → extension.implementation()
```

## How It Works

### 1. Extension Declares Override in Manifest

**File**: `/extensions/vault/manifest.json`

```json
{
  "name": "vault",
  "entity_method_overrides": [
    {
      "entity": "Transfer",
      "method": "execute",
      "implementation": "methods.execute_transfer",
      "description": "Execute external blockchain transfer via vault"
    },
    {
      "entity": "Balance",
      "method": "refresh",
      "implementation": "methods.refresh_balance",
      "description": "Sync balance with vault state"
    }
  ]
}
```

### 2. Extension Provides Implementation

**File**: `/extensions/vault/backend/methods.py`

```python
def execute_transfer(self) -> Async[dict]:
    """Execute external blockchain transfer via vault."""
    if self.transfer_type != "external":
        return {"success": True, "type": "internal"}
    
    # Call vault to execute blockchain transfer
    from extension_packages.vault.backend import entry as vault_entry
    
    vault_args = json.dumps({
        "to_principal": self.principal_to,
        "amount": self.amount
    })
    
    vault_response = yield vault_entry.transfer(vault_args)
    # ... handle response ...
    
    return {"success": True, "tx_id": tx_id}


def refresh_balance(self) -> dict:
    """Sync balance with vault state."""
    from extension_packages.vault.backend.vault_lib.entities import VaultBalance
    
    principal = self.id.split("_")[0]
    vault_balance = VaultBalance[principal]
    
    if vault_balance:
        self.amount = vault_balance.amount
        return {"success": True, "synced": True}
    
    return {"success": True, "synced": False}
```

### 3. Core Entity Defines Method Stub

**File**: `/src/realm_backend/ggg/transfer.py`

```python
class Transfer(Entity, TimestampedMixin):
    __alias__ = "id"
    id = String()
    principal_from = String()
    principal_to = String()
    instrument = String()
    amount = Integer()
    timestamp = String()
    transfer_type = String()  # "internal" | "external"
    status = String()
    
    def execute(self):
        """Execute this transfer. Implementation provided by vault extension."""
        pass
```

**File**: `/src/realm_backend/ggg/balance.py`

```python
class Balance(Entity, TimestampedMixin):
    __alias__ = "id"
    id = String()
    user = ManyToOne("User", "balances")
    instrument = String()
    amount = Integer()
    
    def refresh(self):
        """Refresh balance from vault. Implementation provided by vault extension."""
        pass
```

### 4. System Loads and Binds Methods

**File**: `/src/realm_backend/core/extension_methods.py`

The loader:
1. Scans all extension manifests in `extension_packages/`
2. Finds `entity_method_overrides` declarations
3. Imports the implementation functions
4. Dynamically binds them to entity classes

**File**: `/src/realm_backend/main.py` (initialization)

```python
def initialize() -> void:
    # ... register entities ...
    
    # Load and apply extension method overrides
    from core.extension_methods import load_and_apply_extension_methods
    load_and_apply_extension_methods()
    
    # ... initialize extensions ...
```

## Usage Examples

### Example 1: Execute External Transfer

```python
from ggg import Transfer, Instrument
from datetime import datetime

# Create external transfer
transfer = Transfer(
    id="withdrawal_12345",
    principal_from="system",
    principal_to="user_alice",
    instrument="Realm Token",
    amount=5000,
    timestamp=datetime.now().isoformat(),
    transfer_type="external",  # <-- Triggers vault execution
    status="pending"
)

# Execute (async) - calls vault.methods.execute_transfer
result = yield transfer.execute()

print(result)  
# {"success": True, "tx_id": "67890", "type": "external"}
```

### Example 2: Internal Transfer (No Vault)

```python
# Create internal transfer
transfer = Transfer(
    id="tax_12345",
    principal_from="user_alice",
    principal_to="system",
    instrument="Realm Token",
    amount=500,
    transfer_type="internal",  # <-- No vault execution
    status="completed"
)

# Execute (sync) - returns immediately
result = transfer.execute()

print(result)  
# {"success": True, "type": "internal", "message": "Internal transfer..."}
```

### Example 3: Refresh Balance

```python
from ggg import Balance

balance = Balance["user_alice_RealmToken"]

# Refresh from vault - calls vault.methods.refresh_balance
result = balance.refresh()

print(result)  
# {"success": True, "old_amount": 1000, "new_amount": 6000, "synced": True}
```

## Benefits

### ✅ Declarative Configuration
Extensions declare capabilities in manifest, not in code

### ✅ Clean Separation
Core entities don't depend on extensions

### ✅ Hot Reloading
Method implementations can be updated without modifying core

### ✅ Multiple Implementations
Different extensions can override different methods

### ✅ Type Safety
Entity methods have proper signatures in core

### ✅ Discoverable
Manifest documents what an extension provides

### ✅ Testable
Implementations can be tested independently

## System Startup Flow

```
1. System initializes
   ↓
2. Register all entity types
   ↓
3. Load extension manifests
   ↓
4. Find entity_method_overrides
   ↓
5. Import implementation functions
   ↓
6. Bind to entity classes
   ↓
7. Methods are now available!
```

**Console Output:**
```
============================================================
Loading extension method overrides...
============================================================
Scanning extensions in /src/realm_backend/extension_packages...
Extension 'vault' declares 2 method override(s)
Registered override: Transfer.execute -> vault.methods.execute_transfer
Registered override: Balance.refresh -> vault.methods.refresh_balance
✓ Bound Transfer.execute() to vault.methods.execute_transfer
✓ Bound Balance.refresh() to vault.methods.refresh_balance

Successfully loaded 2 method override(s):
  • Transfer.execute() -> vault
  • Balance.refresh() -> vault
============================================================
```

## Adding New Method Overrides

### 1. Update Core Entity

```python
class MyEntity(Entity):
    def my_method(self):
        """Method description. Implementation provided by extension."""
        pass
```

### 2. Add to Extension Manifest

```json
{
  "entity_method_overrides": [
    {
      "entity": "MyEntity",
      "method": "my_method",
      "implementation": "methods.my_implementation",
      "description": "What this method does"
    }
  ]
}
```

### 3. Implement in Extension

```python
# extensions/my_extension/backend/methods.py

def my_implementation(self):
    """Implementation of MyEntity.my_method()."""
    # Your logic here
    return {"success": True}
```

### 4. Restart System

Method will be automatically bound on next initialization.

## Debugging

### Check What's Registered

```python
from core.extension_methods import get_registry

registry = get_registry()
overrides = registry.get_overrides_summary()

for override in overrides:
    print(f"{override['entity']}.{override['method']} -> {override['extension']}")
```

### Test Method Binding

```python
from ggg import Transfer

# Check if method exists
print(hasattr(Transfer, 'execute'))  # Should be True

# Check implementation source
import inspect
print(inspect.getfile(Transfer.execute))
# Should show: .../extension_packages/vault/backend/methods.py
```

### Common Issues

**Method Not Found**
- Check manifest syntax
- Verify extension is installed
- Check entity name spelling

**Import Errors**
- Ensure implementation module path is correct
- Check function name matches

**Method Not Called**
- Verify entity instance is correct type
- Check method signature (async vs sync)

## Comparison: Hooks vs Method Override

### Hook Pattern (Old)
```python
# Callback registered separately
register_transfer_hook(vault_callback)

# Creates coupling between core and extension
```

### Method Override Pattern (New)
```python
# Clean entity definition
class Transfer:
    def execute(self):
        pass

# Extension provides implementation via manifest
# No coupling!
```

## Architecture Advantages

### Modularity
Extensions are truly independent modules

### Testability
Core and extensions can be tested separately

### Documentation
Manifest serves as API documentation

### Versioning
Extensions can declare compatibility

### Discovery
System knows what each extension provides

### Hot Reload
Implementations can be updated without core changes

## Related Documentation

- [Balance Architecture](./BALANCE_ARCHITECTURE.md)
- [Vault Extension](../extensions/vault/README.md)
- [Extension Development Guide](./EXTENSION_GUIDE.md)
- [Entity System](./ENTITY_SYSTEM.md)
