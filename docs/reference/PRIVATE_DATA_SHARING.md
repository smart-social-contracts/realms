# Private Data Sharing (Encrypted Extensions)

How an extension stores **end-to-end encrypted** data and shares it with chosen
people. The canister never sees the plaintext, the encryption key, or any
vetKey — all crypto happens in the browser.

## How it works

- Data is encrypted in the browser with a random **DEK** (AES-256-GCM).
- The DEK is **IBE-wrapped** once per recipient and stored as a `KeyEnvelope`
  at a **scope** (a string like `dept:Finance:doc:7`).
- Only a recipient can derive their own vetKey and unwrap the DEK, then decrypt.
- A **scope kind** decides *who may grant/revoke* read access. Reading is always
  self-limited: you can only ever fetch the envelope wrapped for yourself.

The host already provides the crypto engine. An extension only supplies:

1. **a place to store the ciphertext** (its own entity), and
2. **a scope policy** (who can manage sharing).

No host code changes are needed.

## Scope kinds

A scope is `kind:...`. The first segment picks the management policy:

| Scope | Who may grant/revoke | Built-in? |
|---|---|---|
| `user:<principal>:<name>` | that principal (self) | yes |
| `dept:<department>:<name>` | department head or realm admin | yes |
| `realm:<name>` | realm admins | yes |
| your own kind | whatever you register | register it yourself |

Built-in kinds live in `src/realm_backend/core/crypto_scopes.py`. To add your
own, register it from your extension's `entry.py` (see below).

## Steps to add it to an extension

1. **Own an entity** for the opaque ciphertext (via `create_extension_entity_class`).
2. **Register a scope kind** with `@scope_kind` (or reuse a built-in like `dept:`).
3. On the frontend, call the host crypto SDK: `encryptForRecipients` →
   `grantScope` → `decryptScope`.

### Backend skeleton (`backend/entry.py`)

```python
import json
from ic_python_db import String
from core.extensions import create_extension_entity_class
from core.crypto_scopes import scope_kind, ScopeAuthContext

ExtensionEntity = create_extension_entity_class("my_ext")

# 1. Own entity — stored as ext_my_ext::PrivateThing
class PrivateThing(ExtensionEntity):
    __alias__ = "id"
    id = String(max_length=64)
    ciphertext = String()              # enc:v=2:... AES-GCM blob
    scope = String(max_length=512)
    created_by = String(max_length=128)

# Host calls this at canister init.
def register_entities():
    from ic_python_db import Database
    Database.get_instance().register_entity_type(PrivateThing)

# 2. Scope policy — who may grant/revoke for "mykind:<owner>:<id>"
@scope_kind("mykind")
def _manage(parts, caller, ctx: ScopeAuthContext) -> bool:
    if len(parts) < 3 or not parts[1]:
        return False
    return caller == parts[1] or ctx.is_realm_admin(caller)
```

The injected `ScopeAuthContext` offers `is_realm_admin(caller)` and
`is_department_head(department, caller)`. The policy runs in plain CPython, so
it is easy to unit-test with a fake context.

### Frontend skeleton (`frontend-rt/src/*.svelte`)

```javascript
// Create → encrypt → grant
const { id, scope } = (await ctx.callSync('create_thing', {...})).data;
const recipients = [me, ...others];
const { ciphertext, wrappedDeks } = await ctx.crypto.encryptForRecipients(recipients, data);
await ctx.callSync('set_ciphertext', { id, ciphertext });
await ctx.crypto.grantScope(scope, wrappedDeks);

// Read → decrypt (null if you have no key)
const plain = await ctx.crypto.decryptScope(scope, ciphertext);
```

Extensions never bundle `@dfinity/vetkeys` — `ctx.crypto` uses the host's copy.

## Worked examples

- **`department_docs`** — documents shared with a department (`dept:` scope).
- **`justice_litigation`** — private litigations shared only with the submitter
  and the justice department (its own `litigation:` scope kind).

Both are fully self-contained: they define their own entity and (for litigation)
their own scope kind, with zero host edits.

## Notes

- Recipients are wrapped **at share time**. Someone added to a department/group
  *later* won't have a key until a manager re-shares.
- Deleting the payload entity can orphan its `KeyEnvelope`s — harmless, but a
  manager can revoke them with `crypto_revoke_from_scope_batch`.
