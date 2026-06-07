## What's new in v0.4.0

This is a major feature release, the largest since the platform launch. It introduces
on-chain orchestrated deployments via Casals, a complete sidebar and navigation
overhaul, department-level permissions, a rich messaging API, and a major wave of
new and updated extensions.

---

### 🎛️ On-chain orchestration with Casals

Realm deployment and upgrades are now driven by
[Casals](https://github.com/smart-social-contracts/casals), a generic on-chain
canister orchestrator running on the Internet Computer. Key changes:

- **Dedicated per-realm frontend canisters** — each realm gets its own certified-asset
  canister; no shared host.
- **`realm_installer` ↔ Casals integration** — the installer can now create a Casals
  Stand (backend + frontend canisters) and hand off lifecycle management. Controlled
  by the `provision_via_casals` feature flag (off by default for safe coexistence with
  the legacy path).
- **New CI/CD workflows** — `publish-build.yml`, `rollout.yml`, `publish-main.yml`,
  `wire-casals.yml` — covering artifact publishing, canister rollout, and infrastructure
  wiring for all environments (test / demo / staging).
- **Dedicated `CASALS_CI_PEM` key** — Casals-related CI calls use a purpose-built
  controller identity, separate from the general infrastructure key.
- **Incremental file uploads** — large uploads (e.g. the backend WASM) now use
  `finalize_chunked_file_step` to avoid the IC 40 B-instruction per-message limit.
- **`set_canister_controllers` endpoint on Casals** — allows controller-safe rotation
  of managed canister controller lists from within the orchestrator.
- **Casals link in registry footer** — the Realm Registry frontend now links to the
  Casals dashboard for the current environment.

---

### 🔧 Backend

- **Pre-upgrade canister snapshots** (`realm_installer`) — automatic snapshots before
  any realm backend upgrade, enabling safe one-click rollback.
- **Messaging API** — new `send_message`, `get_messages`, `get_inbox` endpoints and
  `Message` / `Conversation` models; notifications integration.
- **Department-level permission enforcement** — permissions are now checked at the
  department boundary, not just at the realm level; new `add_permission`,
  `remove_permission`, and permission-management endpoints.
- **`directory_list` query** — returns entity lists suitable for autocomplete / entity
  pickers in UI components.
- **Backend-driven sidebar menu config** — extensions declare their sidebar items in
  their manifests; the backend aggregates and serves the merged config.
- **Role assignment proposals** — inline proposal creation for role changes without
  leaving the current context.
- **Registry & marketplace configurable by realm admins** — `set_registry_canister`
  and `set_marketplace_canister` endpoints allow admins to point realms at custom
  instances.
- **File registry / marketplace fields in `StatusRecord`** — surfaces canister IDs in
  the standard status response.
- **Registration code improvements** — IC-safe timestamps, test-mode invite shortcut,
  `already joined` check skip in `TEST_MODE_II_BYPASS`.
- **`department_id` in `directory_list`** — for entity pickers that scope to a
  department.
- **`DeploymentJob.snapshot_id` default** — unblocks upgrades on realms that were
  installed before the snapshot field was added.

---

### 🖥️ Frontend & UI

- **Sidebar reorganisation** — two top-level sections: **MY REALM** (realm-specific
  items) and **MY MUNDUS** (cross-realm / platform items); collapsible categories with
  visual hierarchy.
- **Navbar label reveal on hover** — labels appear alongside icons when hovering on
  medium+ screens, keeping the layout compact by default.
- **Global page breadcrumbs** — consistent breadcrumb trail across all pages, without
  a redundant "Home" item.
- **AI assistant panel overhaul** — cleaner layout, model label + settings moved into
  the panel header, sidebar auto-detect.
- **Improved test-mode banner** — full-width dark bar, shown correctly after realm info
  loads; profile selection during test-mode sign-in.
- **ICP logo grayscale in footer** — subtler visual weight.
- **Zone selector map** — interactive Leaflet map for geographic entity selection
  (zone_selector v1.1.2).
- **Identities page** — sections reordered (public → private → connected).
- **Permission-denied UX** — user-friendly message instead of raw error.
- **Extension links** — removed spurious `data-sveltekit-reload` that broke SPA
  navigation.

---

### 📦 Extensions (bundled updates)

| Extension | Version | Notes |
|---|---|---|
| `zone_selector` | 1.1.2 | Leaflet map, static imports, bundle, public query fix |
| `justice_litigation` | 0.3.6 | Case model, notification/scenario tests |
| `land_registry` | 1.1.1 | CDN fix |
| `vault` | 0.2.1 | Bug fixes |
| `notifications` | 1.1.0 | Messaging integration |
| `public_dashboard` | 1.3.4 | Hero gradient, lifecycle status, hero background |
| `llm_chat` | 1.0.1 | Sidebar conversation controls, message metadata |
| `mundus_explorer` | 1.0.0 | Registry discovery, CDK & sync fixes |
| `role_manager` | — | Permission-aware UI, manage permissions |
| `access_manager` | 1.0.0 | New — access control management |
| `member_manager` | 1.0.0 | New — member administration |
| `realm_settings` | 1.0.2 | Patch manifest data args |
| `extensions_manager` | 1.0.0 | New — in-realm extension management |
| `census` | 1.0.0 | New |

---

### 📚 Codices

- **Agora** and **Syntropia** codices rewritten from scratch (ultra-lightweight
  `init.py`, IC-safe, instruction-limit hardened).
- **Westminster** removed.
- Common init infrastructure extracted to `codex/common`.

---

### 🛠️ Developer tooling & CI

- **`ic-basilisk` upgraded to 0.14.2** — ships a pre-built CPython-to-WASM template;
  no Rust toolchain, `wasm32-wasip1`, `wasm32-wasi2`, or `candid-extractor` install
  at build time. Eliminates the multi-minute prerequisite step in CI.
- **`ic-basilisk-toolkit` upgraded to 0.4.0**.
- **`realms files publish-release` CLI command** — one-shot publishing of backend WASM
  + frontend bundle into `file_registry`, with Casals authorization.
- **`realms rollout` CLI command** — matrix-style upgrade orchestrator (environment ×
  target × scope × version), dry-run by default with `--execute` to apply.
- **`realms files build` CLI command** — builds bundles locally for inspection or
  offline upload.
- **`publish_build.py` main-snapshot mode** (`--from-main`) — auto-versioned as
  `main.<ts>.<sha>` for rapid continuous deployment from the `main` branch.
- **File registry chunk size** reduced to 200 KB to stay within IC ingress limits.

---

### 🐛 Bug fixes

- IC-safe timestamps throughout (`ic.time()` / `_now_dt()`) — removes `datetime.utcnow()` and `time.time()` calls that returned 0 or wrong values inside canisters.
- Candid declaration sync before frontend builds (fixes `$lib/declarations/realm_backend` not found in CI).
- JSON quote escaping in `set_canister_config` Candid argument.
- Frontend IDL declarations regenerated for new `StatusRecord` fields.
- Registry frontend loads branding from `/custom/` (not `/images/`).
- Profile selection restored to step 3 of the registration flow.
- `.save()` calls removed from `RegistrationCode` (entities auto-persist).

---

### ⬆️ Upgrading

Existing realms continue to use the legacy installer path unchanged
(`provision_via_casals` defaults to `false`). No action needed for running realms.

To opt in to Casals-managed deployments for an environment, follow the
[CASALS_ROLLOUT.md](docs/reference/CASALS_ROLLOUT.md) runbook.

```bash
# Update the CLI
pip install --upgrade realms-gos==0.4.0
```
