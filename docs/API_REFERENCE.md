# Backend API Reference

Complete reference for Realms backend canister endpoints.

---

## Entity Operations

### `get_objects_paginated`
Get paginated list of entities with ordering.

**Type:** Query

```candid
get_objects_paginated: (class_name: text, page_num: nat, page_size: nat, order: text) -> (RealmResponse)
```

**Example:**
```bash
# Get first page of users (ascending)
dfx canister call realm_backend get_objects_paginated '("User", 0, 10, "asc")'

# Get latest proposals (descending)
dfx canister call realm_backend get_objects_paginated '("Proposal", 0, 20, "desc")'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "objectsListPaginated": {
      "objects": ["...", "..."],
      "pagination": {
        "page_num": "0",
        "page_size": "10",
        "total_items_count": "150",
        "total_pages": "15"
      }
    }
  }
}
```

**Supported Classes:**
`User`, `Citizen`, `Human`, `Organization`, `Proposal`, `Vote`, `Mandate`, `Codex`, `Task`, `TaskSchedule`, `Transfer`, `Balance`, `Treasury`, `Instrument`, `Trade`, `Dispute`, `License`, `Realm`, `Registry`, `Service`, `Permission`, `UserProfile`, `Notification`, `Land`, `Contract`, `TaxRecord`

---

### `get_objects`
Get multiple specific entities by ID.

**Type:** Query

```candid
get_objects: (vec { record { text; text } }) -> (RealmResponse)
```

**Example:**
```bash
dfx canister call realm_backend get_objects '(
  vec { 
    record { "User"; "1" };
    record { "Realm"; "1" };
  }
)'
```

---

## User Management

### `join_realm`
Register new user in the realm.

**Type:** Update

```candid
join_realm: (profile: text) -> (RealmResponse)
```

**Example:**
```bash
dfx canister call realm_backend join_realm '("member")'
```

---

### `get_my_user_status`
Get current user's authentication status and profiles.

**Type:** Query

```candid
get_my_user_status: () -> (RealmResponse)
```

**Example:**
```bash
dfx canister call realm_backend get_my_user_status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "userGet": {
      "principal": "2ibo7-dia...",
      "profiles": ["member", "admin"],
      "profile_picture_url": "https://..."
    }
  }
}
```

---

### `get_my_principal`
Get caller's principal ID.

**Type:** Query

```candid
get_my_principal: () -> (text)
```

**Example:**
```bash
dfx canister call realm_backend get_my_principal
```

---

### `update_my_profile_picture`
Update current user's profile picture.

**Type:** Update

```candid
update_my_profile_picture: (profile_picture_url: text) -> (RealmResponse)
```

---

## Extension System

### `extension_sync_call`
Call extension function synchronously.

**Type:** Update

```candid
extension_sync_call: (ExtensionCallArgs) -> (ExtensionCallResponse)

type ExtensionCallArgs = record {
  extension_name: text;
  function_name: text;
  args: text;  // JSON string
}
```

**Example:**
```bash
dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "vault";
    function_name = "get_balance";
    args = "{\"user_id\": \"alice_2024\"}";
  }
)'
```

---

### `extension_async_call`
Call extension function asynchronously.

**Type:** Update (async)

```candid
extension_async_call: (ExtensionCallArgs) -> (ExtensionCallResponse)
```

---

### `get_extensions`
List all available extensions.

**Type:** Query

```candid
get_extensions: () -> (RealmResponse)
```

**Example:**
```bash
dfx canister call realm_backend get_extensions
```

---

## Task Management

### `list_scheduled_tasks`
List all scheduled tasks with status.

**Type:** Query

```candid
list_scheduled_tasks: () -> (text)
```

**Example:**
```bash
dfx canister call realm_backend list_scheduled_tasks
```

**Response:**
```json
[
  {
    "task_id": "abc123",
    "name": "daily_tax_collection",
    "status": "running",
    "last_run": "2024-11-20T10:00:00Z",
    "next_run": "2024-11-21T10:00:00Z",
    "interval": 86400
  }
]
```

---

### `stop_task`
Stop a scheduled task.

**Type:** Update

```candid
stop_task: (task_id: text) -> (text)
```

**Example:**
```bash
dfx canister call realm_backend stop_task '("abc123")'
```

---

### `get_task_logs`
Get execution logs for a task.

**Type:** Query

```candid
get_task_logs: (task_id: text, limit: nat) -> (text)
```

**Example:**
```bash
dfx canister call realm_backend get_task_logs '("abc123", 20)'
```

---

### `create_multi_step_scheduled_task`
Create task with multiple execution steps.

**Type:** Update

```candid
create_multi_step_scheduled_task: (
  name: text,
  steps_config: text,  // JSON array
  repeat_every: nat,
  run_after: nat
) -> (text)
```

**Example:**
```bash
dfx canister call realm_backend create_multi_step_scheduled_task '(
  "data_pipeline",
  "[{\"code\": \"<base64>\", \"run_next_after\": 0}]",
  3600,
  10
)'
```

---

## Code Execution

### `execute_code`
Execute Python code (sync or async auto-detected).

**Type:** Update

```candid
execute_code: (source_code: text) -> (text)
```

**Example:**
```bash
# Sync code
dfx canister call realm_backend execute_code '(
  "from ggg import User\nresult = User.count()"
)'

# Async code
dfx canister call realm_backend execute_code '(
  "def async_task():\n    result = yield some_call()\n    return result"
)'
```

**Response (sync):**
```json
{
  "type": "sync",
  "status": "completed",
  "result": {"count": 150}
}
```

**Response (async):**
```json
{
  "type": "async",
  "task_id": "task_xyz",
  "status": "pending"
}
```

---

## Realm Information

### `status`
Get realm health and statistics.

**Type:** Query

```candid
status: () -> (RealmResponse)
```

**Example:**
```bash
dfx canister call realm_backend status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": {
      "realm_name": "Demo Realm",
      "version": "1.0.0",
      "user_count": 150,
      "task_count": 5,
      "extensions_loaded": 15
    }
  }
}
```

---

### `get_canister_id`
Get this canister's principal ID.

**Type:** Query

```candid
get_canister_id: () -> (text)
```

---

### `initialize`
Initialize realm with foundational entities.

**Type:** Update (one-time)

```candid
initialize: () -> (void)
```

**Example:**
```bash
dfx canister call realm_backend initialize
```

Creates: System user, admin/member profiles, realm, treasury.

---

## Registry Operations

### `register_realm`
Register this realm with central registry.

**Type:** Update

```candid
register_realm: (realm_id: text, realm_name: text, frontend_url: text) -> (text)
```

**Example:**
```bash
dfx canister call realm_backend register_realm '(
  "demo_realm_001",
  "Demo Governance Realm",
  "abc123-cai.icp0.io"
)'
```

---

### `get_registry_info`
Get realm registry information.

**Type:** Query

```candid
get_registry_info: () -> (text)
```

---

## Data Import/Export

### Import via Extension
Bulk data import through admin_dashboard extension.

**Example:**
```bash
# Import JSON entities
realms import realm_data.json

# Import codex
realms import tax_codex.py --type codex
```

### Export via CLI
```bash
# Export all data
realms export --output-dir exported_realm

# Export specific entities
realms export --entity-types User,Proposal,Vote
```

---

## Response Types

### RealmResponse
Standard response wrapper.

```candid
type RealmResponse = record {
  success: bool;
  data: RealmResponseData;
}

type RealmResponseData = variant {
  status: StatusRecord;
  userGet: UserGetRecord;
  objectsList: ObjectsListRecord;
  objectsListPaginated: ObjectsListRecordPaginated;
  error: text;
}
```

---

## Error Handling

All endpoints return structured errors:

```json
{
  "success": false,
  "data": {
    "error": "User not found: alice_2024"
  }
}
```

Common error codes:
- `Not found` - Entity doesn't exist
- `Permission denied` - Insufficient permissions
- `Invalid arguments` - Malformed request
- `Extension error` - Extension function failed

---

## Rate Limits

- **Query calls:** Unlimited
- **Update calls:** Limited by ICP cycles
- **Batch operations:** Use pagination (max 100 items/call)
- **Code execution:** 10-second timeout for sync, no limit for async

---

## Usage Examples

### Frontend Integration
```typescript
import { callBackend } from '$lib/api/backend';

// Get users
const response = await callBackend('get_objects_paginated', [
  'User', 0, 10, 'desc'
]);

// Call extension
const result = await callBackend('extension_sync_call', [{
  extension_name: 'vault',
  function_name: 'get_balance',
  args: JSON.stringify({ user_id: 'alice_2024' })
}]);
```

### CLI Integration
```bash
# Using dfx directly
dfx canister call realm_backend status

# Using realms CLI
realms shell --file my_code.py
realms ps ls
realms import data.json
```

### Extension Backend
```python
from core.extensions import extension_async_call

# Call another extension
result = yield extension_async_call(
    "vault", 
    "transfer", 
    json.dumps({"to": "bob_2024", "amount": 100})
)
```

---

## See Also

- [Core Entities](./CORE_ENTITIES.md) - Entity data model
- [Extension Guide](../extensions/README.md) - Building extensions
- [CLI Reference](./CLI_REFERENCE.md) - Command-line tools
- [Task System](./TASK_ENTITY.md) - Batch processing
