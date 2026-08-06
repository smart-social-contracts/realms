# Migrating a first-party extension to the sandboxed runtime

Audience: Realms maintainers moving in-repo `frontend-rt/` extensions to the
sandboxed iframe runtime (`frontend/` + `@realmsgos/extension-bridge`).

Related docs:

- [Extension Sandboxing (bridge protocol)](/reference/EXTENSION_SANDBOXING)
- [Third-Party Extension Authoring Guide](/guide/extension-authoring) — scaffold
  template, bridge API, UI kit, build layout
- Reference pilots (extensions repo): `hello_world`, `system_info`, `member_dashboard`

---

## 1. When to migrate / who this is for

Migrate an extension when its UI should run in the sandboxed iframe like
third-party extensions — same security boundary, same bridge checkpoint, same
bundle format. This checklist is for **first-party extensions in the Realms
monorepo** (`extensions/extensions/*`) that today ship a `frontend-rt/` bundle
mounted in-process. Backend Python (`backend/entry.py`) is unchanged; only the
frontend delivery path moves.

---

## 2. Mechanical migration checklist

Work through in order. Copy patterns from the pilot closest to your extension
(complexity: `hello_world` → `system_info` → `member_dashboard`).

### 2.1 Scaffold `frontend/`

- [ ] Create `extensions/<id>/frontend/` from the **`hello_world/frontend/`**
      template (cleanest monorepo reference) or from `npm create @realmsgos/extension`
      output.
- [ ] Required files (match pilots):
      `index.html`, `package.json`, `vite.config.ts`, `svelte.config.js`,
      `tsconfig.json`, `src/main.ts`, `src/app.css`, `src/App.svelte`.
- [ ] `package.json` dependencies (monorepo checkout):

  ```json
  {
    "dependencies": {
      "@realmsgos/extension-bridge": "file:../../../../packages/extension-bridge",
      "@realmsgos/extension-ui": "file:../../../../packages/extension-ui"
    }
  }
  ```

- [ ] Build bridge + UI packages once if not already built:

  ```bash
  cd packages/extension-bridge && npm install && npm run build
  cd ../extension-ui && npm install && npm run build
  ```

### 2.2 Port UI from `frontend-rt/`

- [ ] Replace in-process mount with a standalone Vite app (`mount(App, …)` in
      `src/main.ts`).
- [ ] Initialize the bridge client on startup:

  ```ts
  import { createExtensionClient, type HostState } from '@realmsgos/extension-bridge';

  const ctx = await createExtensionClient();
  ctx.onStateChange((state: HostState) => {
    document.documentElement.classList.toggle('dark', state.theme === 'dark');
  });
  ctx.reportHeight(document.body.scrollHeight); // + ResizeObserver on body
  ```

- [ ] Replace **`ctx.callSync(fn, args)`** → **`ctx.callExtension(fn, args)`**.
      Handle bridge errors via `err.code === 'denied'` (see pilots).
- [ ] Replace **`ctx.callAsync(fn, args)`** → **`ctx.callExtension(fn, args)`**
      for now. Extensions that rely on **async generator / streaming backend
      functions** must wait for **`callExtensionAsync`** (planned in
      `@realmsgos/extension-bridge` ≥ 0.2.0) or refactor to sync endpoints.
- [ ] Replace host context reads with bridge **`HostState`** pushes:
      `ctx.onStateChange` for `principal`, `locale`, `theme`, `realmInfo`.
      Do not use `ctx.principal`, `ctx.isAuthenticated`, or `ctx.realmInfo` stores.
- [ ] Replace **`ctx.navigate(path)`** — same call shape on `ExtensionClient`
      (fire-and-forget; requires manifest `navigate` capability).
- [ ] Replace host toasts: **`ctx.notify('success' | 'error' | 'info', message)`**
      (requires manifest `notify` capability).
- [ ] Replace host modals: **`ctx.openModal({ title, body, actions })`** — body
      is **plain text only** (host-rendered declarative dialog).
- [ ] Import layout components from **`@realmsgos/extension-ui`** instead of
      `ctx.ui.*` (see mapping table below).
- [ ] Use **`PageHeader`** for page title spacing (`pt-4` under host breadcrumb).
      Do not add extra top padding on the page wrapper.
- [ ] Port helpers into `frontend/src/lib/` as needed (see `member_dashboard`
      `helpers.ts` for envelope unwrapping and formatting utilities).

#### Legacy `ctx.ui` → `@realmsgos/extension-ui` mapping

| Legacy in-process (`ctx.ui` / host DOM) | Sandboxed kit component | Notes |
|----------------------------------------|---------------------------|-------|
| `ctx.ui.AccessDenied` | `AccessDenied` | Props: `operation?`, `message?`. Pilots often use `EmptyState` with a custom message when bridge returns `code: 'denied'`. |
| Host toast / `$lib` toast helpers | `Alert` | Inline status banners inside the iframe. |
| Ad-hoc status pills / tags | `Badge` | |
| Loading spinners (inline SVG) | `Spinner` | |
| Form labels + inputs | `FormField` + `Input` / `Select` | Replace raw `<label>` + `<input>` pairs. |
| Data grids / roster tables | `DataTable` | Columns + rows props; optional `cell` snippet. |
| Monaco read-only code blocks | `CodeBlock` | For simple display. **`ctx.ui.MonacoEditor` / `MonacoDiffEditor` have no kit equivalent** — keep read-only snippets as `CodeBlock` or defer migration. |
| Page title / actions row | `PageHeader` | v1 kit export. |
| Content panels | `Card` | v1 kit export. |
| Primary actions | `Button` | v1 kit export. |
| Empty / error states | `EmptyState` | v1 kit export. |
| `ctx.theme.cn(…)` | `cn` from `@realmsgos/extension-ui` | |

Kit exports at **0.2.0**: `AccessDenied`, `Badge`, `Alert`, `Spinner`,
`FormField`, `Input`, `Select`, `DataTable`, `CodeBlock`, plus v1
`PageHeader`, `Card`, `Button`, `EmptyState`.

#### Response envelope unwrapping

Many legacy frontends unwrap `{ success, data, error }` envelopes after
`callSync`. Keep the same convention with a thin wrapper around `callExtension`:

```ts
type ExtEnvelope<T> = { success: boolean; data?: T; error?: string };

async function callExt<T>(fn: string, args: Record<string, unknown> = {}): Promise<ExtEnvelope<T>> {
  const raw = await ctx.callExtension<ExtEnvelope<T> | T>(fn, args);
  if (raw && typeof raw === 'object' && 'success' in raw) {
    return raw as ExtEnvelope<T>;
  }
  return { success: true, data: raw as T };
}
```

Bridge **`denied`** errors throw before the envelope is returned — catch those
separately from `{ success: false, error: '…' }` backend envelopes.

### 2.3 Update `manifest.json`

- [ ] Add **`"runtime": "sandboxed"`**.
- [ ] Add **`"sdk_version": "1"`** (must match `BRIDGE_PROTOCOL_VERSION`).
- [ ] Add bridge **`capabilities`** array — **closed-world; undeclared ops are
      denied**. Valid v1 bridge capabilities:

  | Capability | Enables |
  |------------|---------|
  | `call_extension` | `ctx.callExtension(fn, args)` to **this extension's own backend** |
  | `navigate` | `ctx.navigate(path)` |
  | `notify` | `ctx.notify(level, message)` |
  | `modal` | `ctx.openModal(…)` |

  **Do not** mix backend permission strings (e.g. `system.snapshot`, `log.write`)
  into this array — those belong in `permissions` / backend config, not bridge
  capabilities.

- [ ] Add or extend **`entry_access.functions`** — **required when
      `call_extension` is declared**. List **every** backend function the frontend
      calls, mapped to its permission string.

  > **Fail-closed warning:** If `call_extension` is granted but
  > `entry_access.functions` is missing or incomplete, the host denies **all**
  > function calls. Copy the full set from `backend/entry.py` / existing
  > `entry_access` and add any newly exposed endpoints.

- [ ] Keep existing metadata (`profiles`, `categories`, `sidebar_label`, etc.)
      unchanged unless intentionally updating.

Example (minimal, from `hello_world`):

```json
{
  "runtime": "sandboxed",
  "sdk_version": "1",
  "capabilities": ["call_extension"],
  "entry_access": {
    "functions": {
      "greet": "member"
    }
  }
}
```

### 2.4 Build requirements

- [ ] **`vite.config.ts`**: `base: './'`, no `@realmsgos/extension-ui` source
      alias — consume the packaged dist (see `hello_world/frontend/vite.config.ts`).

  ```ts
  export default defineConfig({
    plugins: [svelte(), tailwindcss()],
    base: './',
    build: { outDir: 'dist', emptyOutDir: true },
  });
  ```

- [ ] **`src/app.css`** — Tailwind v4 `@source` must scan the UI kit **dist**:

  ```css
  @import "tailwindcss";

  @source "./**/*.{html,js,svelte,ts}";
  @source "../node_modules/@realmsgos/extension-ui/dist/**/*.{html,js,svelte,ts}";
  ```

- [ ] Run **`npm install && npm run build`** in `frontend/`. Build must emit
      `dist/index.html` with **relative** `./assets/…` paths.

### 2.5 Keep `frontend-rt/` as rollback

- [ ] **Do not delete** `frontend-rt/` until the sandboxed path is verified in
      a real realm install.
- [ ] Rollback: remove `"runtime": "sandboxed"` from `manifest.json` (reverts
      to in-process loader) and redeploy the existing `frontend-rt/dist` bundle.

---

## 3. Known bridge limitations — check BEFORE migrating

Review the legacy frontend for patterns that **cannot** be ported mechanically.
If any apply, plan a redesign or defer migration.

| Limitation | Impact | Workaround |
|------------|--------|------------|
| **No cross-extension calls** | `ctx.backend.extension_sync_call('other_ext', …)` (e.g. `access_manager` → `role_manager`) will not work. | Expose needed data from your own backend, add a realm-backend API, or split UI. |
| **No realm-backend RPC beyond own functions** | Raw `ctx.backend.*` actor access is unavailable. | Route all data through your extension's `entry.py` functions via `callExtension`. |
| **Async generator / streaming functions** | `callExtension` is request/response JSON only. | Use `callExtensionAsync` when bridge ≥ 0.2.0 lands, or refactor backend to sync endpoints. |
| **Declarative modal is text-only** | `openModal({ body })` is a plain string — no HTML/components. | Keep complex dialogs inside the iframe; use host modal only for simple confirms. |
| **No `svelte-i18n` in sandbox** | Cannot import host `$lib/i18n` or `svelte-i18n`. | Hardcode strings for now, or read `state.locale` from `onStateChange` and branch locally. Kit i18n story is TBD. |
| **No host `ctx.crypto.*`** | VetKeys decrypt/encrypt helpers are in-process only. | Perform crypto in backend Python, or defer migration for crypto-heavy UIs. |
| **No `ctx.ui.MonacoEditor` / `MonacoDiffEditor`** | No Monaco in iframe bundle today. | Use `CodeBlock` for static display, or embed a lightweight viewer. |
| **No host notification store** | `ctx.notifications.*` unavailable. | Fetch notifications via your backend or omit until a bridge channel exists. |
| **No `ctx.host.*` focus / assistant bridge** | Document focus pub/sub and assistant actions are in-process only. | Omit or reimplement within extension scope. |
| **Response envelope convention** | Backend may return `{ success, data, error }` or bare payloads. | Use a shared `callExt` wrapper (§2.2); do not assume either shape blindly. |

---

## 4. Verification

### 4.1 Production build

```bash
cd extensions/extensions/<id>/frontend
npm install
npm run build
```

Pass criteria:

- Exit code 0.
- `dist/index.html` exists.
- Asset references use **relative** paths:

  ```html
  <script type="module" crossorigin src="./assets/index-*.js"></script>
  <link rel="stylesheet" crossorigin href="./assets/index-*.css">
  ```

- **Not** absolute `/assets/…` (breaks asset-canister serving under
  `/ext/{id}/{version}/frontend/dist/`).

### 4.2 Dev-server smoke test

From the extensions repo:

```bash
cd extensions/dev-server
npm install
node bin/dev.js <extension_id>
```

| Port | Role |
|------|------|
| **5555** | Mock realm host — bridge server, toasts, modal, capability enforcement |
| **5556** | Extension Vite dev server — loaded in sandboxed iframe on 5555 |

Open http://localhost:5555 (not 5556 directly). Verify:

- [ ] Handshake succeeds (no error card).
- [ ] Theme sync (toggle dark mode in mock host if available).
- [ ] Each declared `call_extension` function returns data (or typed `denied`).
- [ ] `navigate` / `notify` work when declared (check bridge log on 5555).
- [ ] iframe height tracks content (`reportHeight` + `ResizeObserver`).

### 4.3 Correct `dist/` layout for upload

```
frontend/dist/
├── index.html
└── assets/
    ├── index-*.js
    └── index-*.css
```

Published to the realm frontend asset canister at:

```
/ext/{id}/{version}/frontend/dist/index.html
/ext/{id}/{version}/frontend/dist/assets/…
```

---

## 5. Pilot commit references

| Extension | Commit | Notes |
|-----------|--------|-------|
| `hello_world` | `abd1eca` | Minimal scaffold; single `call_extension`; no alias workaround |
| `system_info` | `fc38413` | Read-heavy dashboard; multiple backend functions in allowlist |
| `member_dashboard` | `2776b74` | Full port; `navigate` + `notify`; envelope helper; unauthenticated empty state |

Diff inspection:

```bash
git -C extensions show abd1eca   # hello_world
git -C extensions show fc38413   # system_info
git -C extensions show 2776b74   # member_dashboard
```
