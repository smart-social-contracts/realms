# Extension Sandboxing — Bridge Protocol v1

Status: Draft (implemented as PoC)
Audience: host frontend developers, extension authors

## 1. Model

Third-party extensions run in a **sandboxed iframe** (`sandbox="allow-scripts"`,
no `allow-same-origin` → opaque origin). The extension never touches the host
DOM, the user's identity/session, or canister agents directly. All interaction
crosses a **message bridge** (`postMessage`) and is mediated by the host.

First-party (in-process) extensions are unaffected and keep loading through the
existing dynamic-import path. The sandboxed path is selected per extension via
its manifest (`runtime: "sandboxed"`).

**Decoupled axes:** frontend `runtime: "sandboxed"` (iframe + bridge) and backend
runtime sandbox modes (`"sandbox"` / `"in_process"`) are independent. Backend
isolation follows the realm's `default_mode` today; the iframe boundary is
enforced entirely in the host frontend regardless of backend mode.

**Privileged tier (in-process):** extensions whose manifest lacks
`runtime: "sandboxed"` mount in-process with full host privileges. The host
consult `isPrivilegedExtension(id)` against `VITE_PRIVILEGED_EXTENSIONS`
(comma-separated allowlist). When the env var is absent the guard is open
(status quo); when set, only listed ids may mount in-process. When the
marketplace lands, install-time enforcement (server-side) plus this list form
the boundary for third-party installs.

```
┌─ Host (SvelteKit app) ─────────────────────────────┐
│  SandboxBridgeService                              │
│   ├─ permission checkpoint (manifest capabilities) │
│   ├─ canister call signing (identity stays here)   │
│   └─ state push channels (locale/theme/principal)  │
│        ▲ postMessage                               │
└────────┼───────────────────────────────────────────┘
         │
┌────────┼───────────────────────────────────────────┐
│  iframe sandbox (opaque origin)                    │
│   referrerpolicy="no-referrer"                     │
│   Extension UI + @realmsgos/extension-bridge client   │
│   + @realmsgos/extension-ui components                │
└────────────────────────────────────────────────────┘
```

## 2. Manifest contract

```jsonc
{
  "name": "hello_sandboxed",
  "version": "1.0.0",
  "runtime": "sandboxed",            // absent or "in_process" = legacy path
  "sdk_version": "1",                // bridge protocol major version required
  "capabilities": [                  // host enforces at the checkpoint
    "call_extension",                // may call its own backend canister
    "navigate",                      // may request in-app navigation
    "notify",                        // may show host toast notifications
    "modal"                          // may open host modal dialogs (typed denial if absent)
  ],
  "entry_access": {                   // required when call_extension is granted
    "functions": { "greet": "member" }
  },
  "...": "all existing fields (sidebar_label, icon, categories, ...) unchanged"
}
```

Rules:
- `runtime: "sandboxed"` selects the iframe loader.
- `sdk_version` must equal `BRIDGE_PROTOCOL_VERSION` major; mismatch → the host
  replies with `hello_nack`, tears down the iframe (no dangling bridge or
  listeners), and shows an error card instead of leaving a running iframe.
- `capabilities` is closed-world: anything not declared is denied with a typed
  `{ code: "denied", message }` error (request/response ops) or silently dropped
  (fire-and-forget ops).
- If `call_extension` is declared, `entry_access.functions` **must** be present.
  When the capability is granted but no allowlist is declared, all function calls
  are denied (fail-closed).

## 3. Wire protocol

All messages are JSON objects with a discriminant. Namespace field
`source: "realm-bridge"` distinguishes bridge traffic from other postMessage
users. The host identifies an extension by `event.source === iframe.contentWindow`
(not by `origin`, which is `null` for opaque origins).

### 3.1 Envelope

```ts
type BridgeMessage =
  | ExtToHost // handshake, requests, events
  | HostToExt // handshake ack, responses, state pushes
```

Every request carries a monotonically increasing `id`; responses echo it.
Errors are typed: `{ code: "denied" | "unsupported" | "failed" | "rate_limited" | "bad_request", message }`.

### 3.2 Handshake

```
ext → host  { source, kind: "hello", sdkVersion: "1" }
host → ext  { source, kind: "hello_ack", sdkVersion: "1", extensionId,
              capabilities: [...], state: HostState }
```

Until `hello_ack` arrives the extension client queues outgoing requests.
On major-version mismatch the host replies with `hello_nack { reason }`, tears
down the iframe, and does not leave a running sandbox. Handshake timeout (30 s)
on either side has the same teardown semantics on the host.

**Iframe reload / self-navigation:** the host attaches a `load` listener on the
sandbox iframe. The first `load` is expected (extension bundle). Any subsequent
`load` means the document inside navigated — the host destroys the current
bridge, treats the new `contentWindow` as untrusted, and re-runs the handshake.
Re-handshake failure applies the same teardown path.

### 3.3 Requests (extension → host)

| kind | payload | reply kind | capability gate |
|---|---|---|---|
| `call_extension` | `{ fn, args }` | `call_result` / `error` | `call_extension` + `entry_access.functions` |
| `navigate` | `{ path }` | none (fire-and-forget) | `navigate` + host path validation |
| `notify` | `{ level: "info"\|"success"\|"error", message }` | none | `notify` |
| `open_modal` | `{ title, body, actions: [{id, label, tone?}] }` | `modal_result { actionId }` / `error` | `modal` |
| `resize` | `{ height }` | none | none |
| `get_state` | — | `state` snapshot | none |

**Navigate path validation (host belt):** in addition to SvelteKit `goto` blocking
external origins, the host validates `path` before navigation: must start with
exactly one `/`, must not start with `//`, must not contain `\`, must not contain
a URL scheme (`/^[a-zA-Z][a-zA-Z0-9+.-]*:/`), and must still pass after one round
of `decodeURIComponent`. Invalid paths are silently dropped with `console.warn`.

### 3.4 Pushes (host → extension, unsolicited)

- `state` — `{ principal, locale, theme, realmInfo }`; sent on `hello_ack` and
  whenever any field changes. Extensions must treat this as the only source of
  truth and must not cache across sessions.
- `modal_result` — resolves a pending `open_modal` request.

### 3.5 Canister call checkpoint

`call_extension` maps to the host's existing extension RPC
(`backend.extension_sync_call` / async equivalent) for **that extension's own
canister only**. The host:

1. verifies the iframe identity (`event.source` match),
2. verifies `call_extension` capability,
3. verifies `fn` against `entry_access.functions` (fail-closed if allowlist missing),
4. performs the call with the host-held identity,
5. returns the JSON-serializable result or a typed error.

Raw actor/agent access is never exposed. This is the security boundary.

### 3.6 Rate limiting (contract)

The bridge enforces sliding-window rate limits (10 s window) and payload bounds:

| operation | limit | notes |
|---|---|---|
| `call_extension` | 30 / 10 s | request/response |
| `open_modal` | 5 / 10 s | request/response |
| `get_state` | 30 / 10 s | request/response |
| `navigate` | 10 / 10 s | fire-and-forget |
| `notify` | 10 / 10 s | fire-and-forget |
| `resize` | 30 / 10 s | fire-and-forget |
| in-flight `call_extension` | 10 concurrent | excess → `rate_limited` |
| inbound message size | 256 KiB | serialized JSON; oversize dropped |

Request/response ops reply with `{ code: "rate_limited", message }`. Fire-and-forget
ops are silently dropped when limited.

## 4. Extension-side client API (`@realmsgos/extension-bridge`)

```ts
import { createExtensionClient } from "@realmsgos/extension-bridge";

const ctx = await createExtensionClient();   // performs handshake
ctx.extensionId: string;
ctx.capabilities: string[];
await ctx.callExtension<T>("greet", { name: "Ada" });
ctx.navigate("/extensions/other");
ctx.notify("success", "Saved");
const { actionId } = await ctx.openModal({ title, body, actions });
ctx.onStateChange((s) => { /* principal, locale, theme, realmInfo */ });
ctx.reportHeight(document.body.scrollHeight); // host resizes iframe
```

Everything is async by design — the contract never exposes synchronous
host state.

## 5. Host integration

- `extension-loader.ts` gains `mountSandboxedExtension(id, version, container, deps)`:
  builds `/ext/{id}/{version}/frontend/dist/index.html` iframe with
  `referrerpolicy="no-referrer"`, creates a `SandboxBridgeService` bound to that
  iframe, returns `{ unmount, ready }`. Handshake failure or timeout tears down
  the iframe before `ready` rejects.
- `extension-bridge-host.ts` wraps `createBridgeServer`, validates navigate paths,
  and wires callbacks to real host capabilities.
- `extension-privileged.ts` exports `isPrivilegedExtension(id)` for the in-process
  allowlist guard.
- The extensions route (`(sidebar)/extensions/[id]/[...subpath]/+page.svelte`)
  branches on the installed manifest's `runtime` field; sandboxed extensions get
  the same breadcrumb/page-shell treatment as in-process ones.
- Loading, error, and access-denied states mirror the in-process path.

## 6. Component package (`@realmsgos/extension-ui`)

Svelte 5 library bundled by each extension (components cannot cross the iframe).
Styled with Tailwind against host design tokens (CSS custom properties), so
host theming/dark mode applies automatically inside the sandbox. v1 exports:
`PageHeader`, `Card`, `Button`, `EmptyState`. `PageHeader` owns the
breadcrumb→title spacing standard (16px under host breadcrumb, no per-page
padding stacking).

## 7. Extension bundle format (sandboxed)

- Vite app build (not lib mode) emitting `dist/index.html` + assets.
- The html file must be self-contained relative to its directory (relative
  asset paths) because it is served from the realm asset canister at
  `/ext/{id}/{version}/frontend/dist/index.html`.
- CSS is bundled by the extension (Tailwind with the shared token preset);
  the host never injects styles into the sandbox.

## 8. Non-goals for v1

- No streaming/binary payloads (JSON-serializable values only).
- No extension-to-extension messaging.
- No shared workers, no storage access (opaque origin has none — by design).
- First-party migration (tracked separately).

## 9. Threat model notes

- A malicious sandboxed extension can still render deceptive UI inside its box;
  review of listed extensions remains necessary.
- It cannot read host memory/DOM, sign canister calls outside its declared
  capabilities, or persist data. Resize/navigate/notify are the only ambient
  authorities and all are rate-limitable at the host.
- Iframe self-navigation resets trust: a navigated document must re-handshake
  before any bridge authority is granted again.
