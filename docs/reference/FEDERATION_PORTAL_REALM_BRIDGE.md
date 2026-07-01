# Federation portal — realm iframe bridge contract

**Status:** Draft (open during portal implementation)  
**Parent:** [FEDERATION_PORTAL.md](./FEDERATION_PORTAL.md) §6  
**Audience:** Portal shell implementers, Realms `realm_frontend`, third-party GOS frontends

## Purpose

When a realm is embedded in the federation portal, its frontend runs in a **sandboxed iframe** at its own IC origin (`https://{frontend-id}.icp0.io`). The portal and realm cannot share cookies, `localStorage`, or an II session. They communicate through a narrow **`postMessage` + `MessageChannel`** contract.

This contract is part of the **GGG conformance surface**: every realm frontend (Realms-native or third-party) implements the same bridge when `loader_profile` indicates portal embedding.

---

## Security model

| Property | Mechanism |
|---|---|
| Portal session isolation | iframe `sandbox` without `allow-same-origin` |
| Realm cannot log in as portal user | No `AuthClient.login()` in iframe; delegation handoff only |
| Scoped backend access | II delegation `targets` = `[backend_canister_id]` |
| Channel authenticity | One-time `MessageChannel` port transfer at load; no reliance on `event.origin` (opaque `null` in sandbox) |

The portal **never** passes the general-purpose II identity or an unscoped delegation to the iframe.

---

## Handshake (MessageChannel)

Because the sandboxed iframe has an opaque origin, origin-string validation is unreliable. Use this sequence:

```text
1. Portal creates MessageChannel { port1, port2 }
2. Portal sets iframe.src = https://{frontend-id}.icp0.io/?portal=1&slug={slug}
3. Portal listens on port1 for realm-ready
4. On realm-ready, portal posts port2 to iframe.contentWindow via window.postMessage
   with payload { type: 'bridge:init', port: port2 }, targetOrigin '*'
   (port transfer is the trust anchor — only the intended iframe receives port2)
5. All subsequent messages flow on port1 ↔ port2 only
6. Portal ignores unsolicited window-level messages after handshake
```

Realm frontend: on load with `?portal=1`, wait for `bridge:init`, take transferred port, reply `bridge:ready`, then use the port exclusively.

---

## Message envelope

All bridge messages use a common envelope:

```typescript
interface BridgeMessage {
  type: string;       // namespaced, e.g. 'auth:delegation', 'nav:push'
  id?: string;        // correlation id for request/response pairs
  payload?: unknown;
  error?: string;
}
```

Request/response pairs: caller sets `id`; responder echoes `id`.

---

## Message types (v1 draft)

### Portal → realm

| `type` | `payload` | Description |
|---|---|---|
| `auth:delegation` | `{ delegation: SerializedDelegation, backendCanisterId: string, expiresAt: number }` | Scoped II delegation for this realm's backend only |
| `auth:logout` | `{}` | Clear realm-side auth state |
| `nav:sync` | `{ path: string }` | Portal path changed; realm should update internal route |
| `config:realm` | `{ slug, backendCanisterId, frontendCanisterId, env }` | Static realm metadata from `resolve_slug` |

### Realm → portal

| `type` | `payload` | Description |
|---|---|---|
| `bridge:ready` | `{ version: string }` | Realm bridge SDK loaded; triggers port transfer if not yet done |
| `nav:push` | `{ path: string }` | Realm requests portal URL update → `/r/{slug}{path}` |
| `nav:external` | `{ url: string }` | Open URL in new tab (portal validates allowlist) |
| `resize:report` | `{ height: number }` | iframe content height for portal layout |
| `backend:call` | `{ method: string, args: unknown }` | Optional passthrough: portal signs/forwards update to backend (if realm cannot hold delegation) |

> **Note:** Prefer realm holding its own scoped delegation and calling the backend directly from the iframe. `backend:call` passthrough is a fallback for environments where iframe → IC agent setup is constrained.

---

## Auth handoff detail

1. User authenticates on portal origin only (`/join`).
2. Portal calls `resolve_slug` and loads iframe.
3. Portal creates delegation:
   - **Identity:** portal's II identity
   - **Targets:** `[backend_canister_id]` from registry
   - **TTL:** short (e.g. 15–60 minutes; refresh on activity)
4. Portal sends `auth:delegation` over MessageChannel.
5. Realm bridge SDK constructs `@dfinity/agent` `HttpAgent` + `AuthClient` (or equivalent) using the delegation — **no login UI in iframe**.

On delegation expiry, realm sends `auth:refresh-request`; portal re-mints and sends new `auth:delegation` if session still valid.

---

## Navigation sync

Portal owns the browser URL bar:

```text
https://staging.realmsgos.org/r/{slug}/governance/proposals/42
                              └─ realm-internal path ─┘
```

- Portal → realm: `nav:sync` when user uses back/forward or deep-links.
- Realm → portal: `nav:push` when in-app routing changes (portal updates `history.pushState`).

Realm frontend should detect `?portal=1` (or equivalent) and use bridge navigation instead of full page loads.

---

## Loader profiles

| `loader_profile` | Behavior |
|---|---|
| `realms-iframe-v1` | Standard Realms Svelte frontend + bridge SDK |
| `ggg-iframe-v1` | Generic GGG bridge SDK (third-party) |
| `direct-v1` | **Not used in portal context** — direct `{canister-id}.icp0.io` visit only |

Portal dispatch: read `loader_profile` from `resolve_slug` response; default Realms deployments to `realms-iframe-v1`.

---

## GGG conformance (behavioral)

A realm is **GGG-bridge conformant** if it:

1. Accepts MessageChannel handshake when loaded with portal query param.
2. Does not invoke II login when embedded (`portal=1`).
3. Uses scoped delegation only against its registered backend canister.
4. Implements required message types for its declared `loader_profile`.

Conformance is verified by an automated harness (portal test iframe + scripted message exchange), not source inspection.

---

## Implementation locations (planned)

| Component | Repo path (TBD) |
|---|---|
| Portal shell + iframe host | `src/realm_registry_frontend` or dedicated portal canister |
| Realm bridge SDK (Realms) | `src/realm_frontend/src/lib/portal-bridge.ts` |
| Shared types | `packages/portal-bridge-types` or inline in both sides |
| Conformance harness | portal E2E / registry admin tool |

---

## Open questions

- Exact delegation serialization format (match `@dfinity/identity` wire format).
- Whether `backend:call` passthrough is needed for v1 or delegation-only is sufficient.
- iframe refresh strategy on delegation expiry vs. silent refresh.
- Maximum iframe height / resize throttle for performance.
