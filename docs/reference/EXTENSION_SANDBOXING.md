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
│   Extension UI + @realms/extension-bridge client   │
│   + @realms/extension-ui components                │
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
    "notify"                         // may show host toast notifications
  ],
  "entry_access": {                   // optional fine-grained function allowlist
    "functions": { "greet": "member" }
  },
  "...": "all existing fields (sidebar_label, icon, categories, ...) unchanged"
}
```

Rules:
- `runtime: "sandboxed"` selects the iframe loader.
- `sdk_version` must equal `BRIDGE_PROTOCOL_VERSION` major; mismatch → the host
  shows an error card instead of mounting.
- `capabilities` is closed-world: anything not declared is denied.
- If `entry_access.functions` is present, only listed function names may be
  invoked through `callExtension`.

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
Errors are typed: `{ code: "denied" | "unsupported" | "failed", message }`.

### 3.2 Handshake

```
ext → host  { source, kind: "hello", sdkVersion: "1" }
host → ext  { source, kind: "hello_ack", sdkVersion: "1", extensionId,
              capabilities: [...], state: HostState }
```

Until `hello_ack` arrives the extension client queues outgoing requests.
On major-version mismatch the host replies with `hello_nack { reason }` and
does not mount.

### 3.3 Requests (extension → host)

| kind | payload | reply kind | capability gate |
|---|---|---|---|
| `call_extension` | `{ fn, args }` | `call_result` / `error` | `call_extension` + `entry_access.functions` |
| `navigate` | `{ path }` | none (fire-and-forget) | `navigate` |
| `notify` | `{ level: "info"\|"success"\|"error", message }` | none | `notify` |
| `open_modal` | `{ title, body, actions: [{id, label, tone?}] }` | `modal_result { actionId }` | none (host UI, declarative only) |
| `resize` | `{ height }` | none | none |
| `get_state` | — | `state` snapshot | none |

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
3. verifies `fn` against `entry_access.functions` if present,
4. performs the call with the host-held identity,
5. returns the JSON-serializable result or a typed error.

Raw actor/agent access is never exposed. This is the security boundary.

## 4. Extension-side client API (`@realms/extension-bridge`)

```ts
import { createExtensionClient } from "@realms/extension-bridge";

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
  builds `/ext/{id}/{version}/frontend/dist/index.html` iframe, creates a
  `SandboxBridgeService` bound to that iframe, returns `{ unmount }`.
- The extensions route (`(sidebar)/extensions/[id]/[...subpath]/+page.svelte`)
  branches on the installed manifest's `runtime` field; sandboxed extensions get
  the same breadcrumb/page-shell treatment as in-process ones.
- Loading, error, and access-denied states mirror the in-process path.

## 6. Component package (`@realms/extension-ui`)

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
