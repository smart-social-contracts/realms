# Third-Party Extension Authoring Guide

Audience: external developers building Realms extensions that run in the sandboxed iframe runtime.

Related specs:

- [Extension Sandboxing (bridge protocol)](/reference/EXTENSION_SANDBOXING)
- Start a new extension: `npm create @realmsgos/extension my-extension` (scaffolder package `@realmsgos/create-extension`)
- Reference implementation: `extensions/extensions/hello_sandboxed/` in the Realms monorepo

---

## 1. Overview

Realms supports two extension frontends:

| Runtime | Manifest | Trust model | Frontend delivery |
|---------|----------|-------------|-------------------|
| **In-process** | `runtime` absent or `"in_process"` | First-party, trusted | ES module at `/ext/{id}/{version}/frontend/dist/index.js`, mounted directly into the host DOM |
| **Sandboxed** | `"runtime": "sandboxed"` | Third-party, untrusted | Self-contained Vite app at `/ext/{id}/{version}/frontend/dist/index.html`, loaded in an iframe with `sandbox="allow-scripts"` (opaque origin) |

Third-party extensions must use the sandboxed runtime. The extension never touches the host DOM, the user's identity/session, or canister agents directly. All host interaction crosses a **postMessage bridge** mediated by the host permission checkpoint. See [Extension Sandboxing](/reference/EXTENSION_SANDBOXING) for the full protocol contract and threat model: a malicious extension cannot read host memory, sign canister calls outside declared capabilities, or persist data across sessions, but it can still render deceptive UI inside its iframe — marketplace listing and review remain necessary.

First-party extensions are being migrated to the sandboxed runtime; see [Migrating a first-party extension to the sandboxed runtime](/guide/extension-migration).

---

## 2. Quick start

### Scaffold a new extension

```bash
npm create @realmsgos/extension my-ext
```

This downloads `@realmsgos/create-extension` (published on npm at **0.1.0**, alongside `@realmsgos/extension-bridge` and `@realmsgos/extension-ui` at the same version) and generates a sandboxed project with `manifest.json`, `frontend/`, and `backend/entry.py`.

Non-interactive flags:

```bash
npm create @realmsgos/extension my-ext -- \
  --id my_extension \
  --name "My Extension" \
  --description "Does something useful"
```

```bash
cd my-ext/frontend
npm install
npm run build   # emits dist/index.html with relative ./assets/ paths
```

The scaffold template declares a minimal capability set (`call_extension` + `notify`); the monorepo reference extension `hello_sandboxed` adds `navigate` and demonstrates host modal UI via `openModal`.

### Alternative: copy the reference extension

In a monorepo checkout, copy `hello_sandboxed` instead:

```bash
cp -r extensions/extensions/hello_sandboxed extensions/extensions/my_extension
cd extensions/extensions/my_extension/frontend
```

Edit `../manifest.json` (`name`, `version`, labels, capabilities, `entry_access`).

### Install dependencies

**Scaffolded projects (npm):** dependencies on `@realmsgos/extension-bridge` and `@realmsgos/extension-ui` are resolved from npm when you run `npm install` in `frontend/`.

**Monorepo checkout:** build the bridge and UI packages locally first:

```bash
cd packages/extension-bridge && npm install && npm run build
cd ../extension-ui && npm install && npm run build
```

Then install the extension frontend:

```bash
cd extensions/extensions/my_extension/frontend
npm install
npm run build   # emits dist/index.html with relative ./assets/ paths
```

In a monorepo checkout, `package.json` depends on the packages via `file:` paths:

```json
{
  "dependencies": {
    "@realmsgos/extension-bridge": "file:../../../../packages/extension-bridge",
    "@realmsgos/extension-ui": "file:../../../../packages/extension-ui"
  }
}
```

### Local dev loop (mock host + iframe)

From the extensions repo:

```bash
cd extensions/dev-server
npm install
node bin/dev.js my_extension
```

Or, from the extension frontend directory after installing dev-server deps:

```bash
cd extensions/dev-server && npm install
node bin/dev.js hello_sandboxed
```

| Port | Role |
|------|------|
| **5555** | Mock realm host page — bridge server, toast area, confirm modal, bridge log |
| **5556** | Extension Vite dev server — loaded inside a sandboxed iframe on port 5555 |

Open http://localhost:5555. The mock host enforces manifest `capabilities` and `entry_access.functions`, returns mock results for declared functions (e.g. `greet`), and logs all bridge traffic. In a real realm install, those calls instead reach your extension's `backend/entry.py` on the canister.

Alternative entry point (same script):

```bash
npx realms-ext-dev hello_sandboxed
```

Run from `extensions/dev-server/` or pass the extension id explicitly.

### Where artifacts land in production

After install, the realm frontend asset canister serves:

```
/ext/{id}/{version}/frontend/dist/index.html
/ext/{id}/{version}/frontend/dist/assets/...
```

The host iframe loader (`mountSandboxedExtension`) sets `iframe.src` to the `index.html` path above.

---

## 3. Manifest reference

`manifest.json` lives at the extension root (sibling of `frontend/`).

### Sandboxed-specific fields

| Field | Required | Description |
|-------|----------|-------------|
| `runtime` | Yes (sandboxed) | Must be `"sandboxed"` to select the iframe loader. Absent or `"in_process"` uses the legacy in-process path. |
| `sdk_version` | Yes (sandboxed) | Bridge protocol major version the extension was built for (currently `"1"`). Must match `BRIDGE_PROTOCOL_VERSION` from `@realmsgos/extension-bridge`. Mismatch → host sends `hello_nack` and shows an error card instead of mounting. |
| `capabilities` | Yes (sandboxed) | Bridge capability allowlist. **Closed-world rule:** anything not listed is denied at the host checkpoint. Valid v1 values: `call_extension`, `navigate`, `notify`. |
| `entry_access` | Recommended | Fine-grained backend function allowlist. When `entry_access.functions` is present, only listed function names may be invoked through `callExtension`. Values are role/permission strings (e.g. `"member"`, `"proposal.create"`). |

Example (from `hello_sandboxed`):

```json
{
  "name": "hello_sandboxed",
  "version": "1.0.0",
  "runtime": "sandboxed",
  "sdk_version": "1",
  "capabilities": [
    "call_extension",
    "navigate",
    "notify"
  ],
  "entry_access": {
    "functions": {
      "greet": "member"
    }
  }
}
```

### Shared metadata fields

These fields apply to all extensions (in-process and sandboxed):

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Extension identifier (directory name, canister routing key). |
| `version` | Yes | Semver string; must match the uploaded bundle version. |
| `description` | No | Human-readable summary. |
| `author` | No | Author or organization name. |
| `permissions` | No | Backend permission strings (empty array is common). Distinct from bridge `capabilities`. |
| `profiles` | No | Profiles that may see the extension in the sidebar (e.g. `["member", "admin"]`). Empty or omitted → public. |
| `categories` | No | Sidebar grouping: `public_services`, `finances`, `oversight`, `system`, `governance`, `other`, etc. |
| `icon` | No | Sidebar icon key (e.g. `"wand"`, `"gavel"`). |
| `show_in_sidebar` | No | Default `true`. Set `false` to hide from sidebar. |
| `sidebar_label` | No | Localized labels, e.g. `{ "en": "Hello (Sandboxed)" }`. |
| `doc_url` | No | Link to external documentation. |
| `path` | No | Custom route prefix. `null` hides from default routing. Default: `/extensions/{id}`. |
| `entry_access.default` | No | Default access level for backend functions not listed in `entry_access.functions`. |
| `entry_points` | No | Backend only — list of Python entry functions in `backend/entry.py`. Not used by the sandboxed frontend directly. |
| `screenshots` | No | Package-relative image paths for the marketplace listing, e.g. `["screenshots/01-overview.png", "screenshots/02-detail.png"]`. Files live under `screenshots/` in the extension repo. The first entry is the marketplace card thumbnail; the rest form the detail-page gallery. On release, CI captures these automatically via Playwright — authors normally do not hand-place them. Recommended: PNG, 16:9, 1280×720. |

---

## 4. Bridge API reference

Install:

```bash
npm install @realmsgos/extension-bridge
```

Import and create the client at app startup:

```ts
import { createExtensionClient, BRIDGE_PROTOCOL_VERSION } from '@realmsgos/extension-bridge';

const ctx = await createExtensionClient();
```

`createExtensionClient` performs the handshake (`hello` → `hello_ack`), queues outgoing requests until the handshake completes, and throws on timeout (30 s) or `hello_nack`.

### `createExtensionClient(options?)`

```ts
interface ExtensionClientOptions {
  /** Bridge protocol version the extension was built for. Defaults to BRIDGE_PROTOCOL_VERSION. */
  sdkVersion?: string;
  /** Override postMessage target (defaults to window.parent). */
  target?: Window;
}

function createExtensionClient(
  options?: ExtensionClientOptions,
): Promise<ExtensionClient>;
```

### `ExtensionClient`

| Member | Signature | Capability gate | Description |
|--------|-----------|-----------------|-------------|
| `extensionId` | `string` (readonly) | — | Set by host in `hello_ack`. |
| `capabilities` | `string[]` (readonly) | — | Declared manifest capabilities echoed by host. |
| `callExtension` | `<T>(fn: string, args?: Record<string, unknown>) => Promise<T>` | `call_extension` + `entry_access.functions` | Call the extension's own backend canister via host RPC. JSON-serializable args and results only. |
| `navigate` | `(path: string) => void` | `navigate` | Request in-app navigation (fire-and-forget). |
| `notify` | `(level: NotifyLevel, message: string) => void` | `notify` | Show a host toast. `NotifyLevel`: `'info' \| 'success' \| 'error'`. |
| `openModal` | `(options: OpenModalOptions) => Promise<{ actionId: string }>` | `modal` | Declarative confirm dialog rendered by the host. |
| `callExtensionAsync` | `<T>(fn: string, args?: Record<string, unknown>, opts?: { timeoutMs?: number }) => Promise<T>` | `call_extension` + `entry_access.functions` | Async backend functions (generators with `yield`). Host acknowledges with a task id and pushes the settled result. Bridge ≥ 0.2.0. |
| `onStateChange` | `(listener: (state: HostState) => void) => () => void` | none | Subscribe to host state pushes. Returns unsubscribe function. |
| `reportHeight` | `(height: number) => void` | none | Tell the host to resize the iframe. |
| `destroy` | `() => void` | — | Remove listeners and cancel pending work. Call on unmount. |

```ts
interface OpenModalOptions {
  title: string;
  body: string;
  actions: ModalAction[];
}

interface ModalAction {
  id: string;
  label: string;
  tone?: 'primary' | 'secondary' | 'danger';
}
```

### `HostState`

Pushed on `hello_ack` and whenever any field changes. Treat as the only source of truth; do not cache across sessions.

```ts
interface HostState {
  principal: string;
  locale: string;
  theme: 'light' | 'dark';
  realmInfo: HostRealmInfo;
}

interface HostRealmInfo {
  name: string;
  welcomeMessage: string;
  manifesto: string;
  isQuarter: boolean;
  parentRealmCanisterId: string;
  logoUrl?: string;
}
```

### Examples

**Initialize, theme sync, and backend call:**

```ts
import { createExtensionClient, type HostState } from '@realmsgos/extension-bridge';

const ctx = await createExtensionClient();

ctx.onStateChange((state: HostState) => {
  document.documentElement.classList.toggle('dark', state.theme === 'dark');
  document.documentElement.dataset.theme = state.theme;
});

const data = await ctx.callExtension('greet', { name: 'Ada' });
```

**Navigation and notification:**

```ts
ctx.navigate('/extensions/other');
ctx.notify('success', 'Saved');
```

**Host-rendered modal:**

```ts
const { actionId } = await ctx.openModal({
  title: 'Confirm',
  body: 'Delete this item?',
  actions: [
    { id: 'cancel', label: 'Cancel', tone: 'secondary' },
    { id: 'delete', label: 'Delete', tone: 'danger' },
  ],
});
```

**Iframe height:**

```ts
ctx.reportHeight(document.body.scrollHeight);

const observer = new ResizeObserver(() => ctx.reportHeight(document.body.scrollHeight));
observer.observe(document.body);
```

**Cleanup (Svelte `onMount` return):**

```ts
return () => {
  observer.disconnect();
  ctx.destroy();
};
```

**Handling typed errors from `callExtension`:**

Bridge errors carry a `code` property: `'denied' | 'unsupported' | 'failed'`.

```ts
try {
  await ctx.callExtension('greet', { name: 'Ada' });
} catch (e) {
  if (e instanceof Error) {
    const code = (e as Error & { code?: string }).code ?? 'failed';
    console.error(code, e.message);
  }
}
```

Protocol constant:

```ts
import { BRIDGE_PROTOCOL_VERSION } from '@realmsgos/extension-bridge';
// '1' — must match manifest sdk_version major
```

See [Extension Sandboxing](/reference/EXTENSION_SANDBOXING) for wire-level message shapes.

---

## 5. UI components (`@realmsgos/extension-ui`)

Sandboxed extensions bundle their own copy of shared Svelte 5 components. The host does not inject components or styles across the iframe boundary.

Install:

```bash
npm install @realmsgos/extension-ui
```

v1 exports: `PageHeader`, `Card`, `Button`, `EmptyState`.

```svelte
<script lang="ts">
  import { PageHeader, Card, Button, EmptyState } from '@realmsgos/extension-ui';
</script>

<PageHeader title="Members" subtitle="Manage realm membership.">
  {#snippet actions()}
    <Button onclick={() => refresh()}>Refresh</Button>
  {/snippet}
</PageHeader>

<Card title="Roster">
  {#snippet children()}
    <!-- content -->
  {/snippet}
</Card>

<EmptyState title="No members yet" message="Invite someone to get started.">
  {#snippet actions()}
    <Button>Invite member</Button>
  {/snippet}
</EmptyState>
```

### Page spacing standard

Built-in Realms pages place breadcrumbs in the host shell with a fixed gap to the page title. **`PageHeader` owns the standard: `pt-4` (16px) under the host breadcrumb.** Do not wrap the page in additional top padding (`p-4`, `pt-8`, `py-6`, etc.) — that stacks with host padding and produces inconsistent spacing.

Horizontal padding on the content wrapper (e.g. `px-4`) is fine; see `hello_sandboxed/frontend/src/App.svelte`.

### Tailwind content scan (required)

`@realmsgos/extension-ui` ships Tailwind utility class names only. Your build must scan the package so those classes are emitted.

**Tailwind v4** (as used in `hello_sandboxed`):

```css
/* frontend/src/app.css */
@import "tailwindcss";

@source "./**/*.{html,js,svelte,ts}";
@source "../node_modules/@realmsgos/extension-ui/dist/**/*.{html,js,svelte,ts}";
```

**Tailwind v3** (`tailwind.config.js`):

```js
export default {
  darkMode: 'selector',
  content: [
    './src/**/*.{html,js,svelte,ts}',
    './node_modules/@realmsgos/extension-ui/dist/**/*.{html,js,svelte,ts}',
  ],
};
```

Set `darkMode: 'selector'` (or `@custom-variant dark` equivalent) so dark mode follows a `.dark` ancestor.

### Design tokens

Components read host theme CSS custom properties with light-mode fallbacks:

| Token | Fallback | Usage |
|-------|----------|--------|
| `--color-text-primary` | `#111827` | Headings, body text |
| `--color-text-secondary` | `#6b7280` | Subtitles, muted copy |
| `--color-text-inverse` | `#ffffff` | Text on filled buttons |
| `--color-bg-primary` | `#ffffff` | Card surfaces |
| `--color-bg-secondary` | `#f9fafb` | Reserved |
| `--color-border-primary` | `#e5e7eb` | Card borders, dividers |
| `--color-primary-600` | `#2563eb` | Primary actions |
| `--color-error-600` | `#dc2626` | Danger actions |

The host sets these on `document.documentElement`. Apply bridge `theme` state in the iframe the same way:

```ts
document.documentElement.classList.toggle('dark', state.theme === 'dark');
```

---

## 6. Styling and theming

- The extension **bundles its own CSS**. The host never injects styles into the sandbox.
- Use Tailwind with the shared token names above so light/dark mode tracks the host automatically.
- Use Tailwind `dark:` variants (with `darkMode: 'selector'`) for any custom styles beyond the component library.
- Do not rely on host Svelte components, global CSS, or design-system imports from `realm_frontend`.

Recommended Vite config (`frontend/vite.config.ts`):

```ts
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [svelte(), tailwindcss()],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
```

`base: './'` is required so asset URLs in `dist/index.html` are relative (`./assets/...`), not absolute (`/assets/...`).

---

## 7. Packaging and publishing

### Release channels

`@realmsgos/extension-bridge`, `@realmsgos/extension-ui`, and `@realmsgos/create-extension` are published to npm on two dist-tags:

| Dist-tag | Channel | Source | Install |
|----------|---------|--------|---------|
| **`latest`** | Official | Manual release by a maintainer via `scripts/publish_extension_packages.sh` (npm token stays off CI) | `npm install @realmsgos/extension-bridge` |
| **`next`** | Experimental | CI on every push to `main` that touches `packages/extension-*` | `npm install @realmsgos/extension-bridge@next` |

Experimental builds use semver pre-release versions derived from the `package.json` base version plus the GitHub Actions run number, e.g. `0.1.0-next.42`. Pin `@next` only for early testing against main; use `@latest` (or an explicit semver) for production extension work.

### Build output layout

```bash
cd frontend
npm run build
```

Produces:

```
frontend/dist/
├── index.html          # entry point loaded by host iframe
└── assets/
    ├── index-*.js
    └── index-*.css
```

Built `index.html` must reference assets with relative paths:

```html
<script type="module" crossorigin src="./assets/index-BE6mO-tc.js"></script>
<link rel="stylesheet" crossorigin href="./assets/index-CRW7cn3p.css">
```

### Upload path

Publish the `frontend/dist/` tree to the realm asset canister under:

```
/ext/{id}/{version}/frontend/dist/
```

The file_registry namespace for marketplace listings follows `ext/{extension_id}/{version}`.

### Install flow

1. Upload extension artifacts (backend Python modules + frontend bundle) to the file registry or bundle them in a marketplace listing. See [Marketplace](/reference/MARKETPLACE).
2. Install on a realm via `install_extension` / `install_extension_from_registry` (realm admin or governance proposal through the package manager extension).
3. On install, the realm copies the frontend bundle to its own frontend asset canister at the `/ext/{id}/{version}/...` prefix.
4. The extensions route reads the installed manifest's `runtime` field and calls `mountSandboxedExtension` for sandboxed extensions.

CLI helpers (monorepo):

```bash
realms extension list
realms extension runtime-install --canister <backend_id> --source-dir extensions/extensions/<ext_id>
```

For staging/runtime deploy details, see [Runtime Extension Staging Deploy](/reference/RUNTIME_EXTENSION_STAGING_DEPLOY).

---

## 8. Permission model

The host **permission checkpoint** (`SandboxBridgeService` / `createBridgeServer`) enforces:

1. **Iframe identity** — messages accepted only when `event.source === iframe.contentWindow`.
2. **Handshake** — `sdk_version` major must match `BRIDGE_PROTOCOL_VERSION`.
3. **Closed-world capabilities** — each bridge request kind checks the manifest `capabilities` array.
4. **`entry_access.functions`** — when present, `callExtension(fn, …)` is denied unless `fn` is listed.
5. **Canister signing** — `call_extension` is routed to the host's existing extension RPC for **that extension's own canister only**; raw actor/agent access is never exposed.

### Denied error shape

Failed requests return `{ code, message }` where `code` is one of:

| Code | Typical cause |
|------|---------------|
| `denied` | Missing capability, function not in allowlist, handshake incomplete |
| `unsupported` | Host handler not configured for this request kind |
| `failed` | Backend call threw or returned an error |

Example denial messages from the bridge server:

- `Capability 'call_extension' not declared`
- `Function 'not_allowed_fn' not in entry_access.functions allowlist`
- `SDK version mismatch: extension requires 2, host supports 1` (via `hello_nack` at handshake)

`navigate` and `notify` without the declared capability are silently dropped (no error reply — fire-and-forget).

### Review requirement

Checkpoint enforcement does not prevent a sandboxed extension from drawing misleading buttons or impersonating host chrome **inside its iframe**. Extensions listed in a marketplace or installed on a realm should go through human review.

---

## 9. Troubleshooting

### `hello_nack` / SDK version mismatch

**Symptom:** Error card instead of extension UI; handshake reason mentions SDK version.

**Fix:** Set manifest `sdk_version` to match `BRIDGE_PROTOCOL_VERSION` (`"1"` today). Rebuild and redeploy. Import `BRIDGE_PROTOCOL_VERSION` in dev to verify.

### Blank iframe

**Symptom:** iframe loads but shows nothing or 404 for assets.

**Fix:** Confirm `vite.config.ts` has `base: './'`. Rebuild and verify `dist/index.html` uses `./assets/...` paths, not `/assets/...`. Confirm files exist at `/ext/{id}/{version}/frontend/dist/index.html` on the realm frontend canister.

### `call_extension` denied

**Symptom:** `{ code: 'denied', message: '...' }`.

**Fix:**

- Add `"call_extension"` to manifest `capabilities`.
- Add the function name to `entry_access.functions`.
- Ensure the extension backend is installed and exposes the function in `backend/entry.py`.

### Tailwind classes missing on UI components

**Symptom:** Unstyled `PageHeader` / `Button` / `Card`.

**Fix:** Add `@realmsgos/extension-ui/dist/**` to Tailwind content/`@source` scan paths (see section 5).

### iframe height too small or clipped

**Symptom:** Scrollbar inside iframe or content cut off.

**Fix:** Call `ctx.reportHeight(document.body.scrollHeight)` after render and on content changes. Use a `ResizeObserver` on `document.body` (see `hello_sandboxed/frontend/src/App.svelte`).

### Bridge handshake timeout

**Symptom:** `Bridge handshake timed out` after 30 s.

**Fix:** Extension must run inside the host iframe (dev-server port 5555 loads port 5556). Opening the Vite dev URL (5556) directly has no bridge parent.

---

## 10. Current limitations and roadmap

| Limitation | Status |
|------------|--------|
| `@realmsgos/extension-bridge`, `@realmsgos/extension-ui`, and `@realmsgos/create-extension` on npm | Published at **0.1.0** (0.x semver); monorepo checkouts still use `file:` paths |
| JSON-serializable payloads only (no streaming/binary) | v1 |
| No extension-to-extension messaging | v1 |
| No shared workers or storage (opaque origin) | By design |
| First-party extensions still on in-process path | [Migration in progress](/guide/extension-migration) — pilots done |
| `open_modal` gated behind the `modal` capability (bridge ≥ 0.1.1) | Done |

Spec and protocol details: [Extension Sandboxing](/reference/EXTENSION_SANDBOXING).

Legacy in-process frontend architecture (superseded for third-party frontends): [Extension Architecture](/reference/EXTENSION_ARCHITECTURE).
