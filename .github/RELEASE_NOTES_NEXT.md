## What's new in v0.5.0

This release moves the whole product onto the Casals v2 orchestration model,
adds production/test build variants, ships the `realms new` / `realms seed`
CLI wizards, and adopts a faster storage layer for realm backends.

---

### ⚡ Faster realm backends (ic-basilisk 0.15.1, ic-python-db 0.12.0)

- Entity listing now reads pages with `StableBTreeMap.range()` instead of one
  storage read per id, and deleted ids no longer cost anything. Measured on a
  canister: `instances()` over 500 entities −30 %, with half the ids deleted
  −41 %, a `load_some` page of 50 −29 %, single `load` −12 % (instructions).
- The Cedar template realm backends pack with is pinned to the versioned
  Basilisk release (`v0.15.1`) and cached per version, so an old cached
  template can no longer be picked up silently.
- Repeated full-table scans removed from quarter registration, quarter
  directory sync (was O(n²) per peer sync) and delegation lookups.

### 🎛️ Casals v2 orchestration

- The product orchestra is a single `casals.json` sheet; realm deployment,
  quarter auto-scaling (`create_stand`) and governance handover all go through
  Casals. The v1 rollout slice, the realms deploy-CLI (`casals_product`,
  `casals_governance`, `seed`/`env` commands, Cloudflare/DNS helpers,
  `scripts/deploy.py`, `ci_install_mundus.py`, `environments/*.json`) are gone.
- No per-network tables anywhere: backend, frontend and CLI read the
  shared-ledger catalog and installer configuration from the realm
  (`get_setup_state()` / `status().shared_tokens`) instead of baked maps.
- Production governance multisig `i7hog-cyaaa-aaaai-rasxa-cai` (1-of-3);
  `realms seed` mints the multisig from `orchestration-multisig@1.4.0` and
  drives controller handover through icp-cli.
- Quarters are handed to the stand baton; the broker path is dropped.
- New `OPERATIONS.md`; `scripts/local_up.sh` builds and brings up the whole
  orchestra on a local replica (`--gaas` births a realm through the portal
  path).

### 🔒 Production vs test build variants

- Backend WASM and frontend are built per variant. Test identities and the
  auth-bypass sentinel are compiled out of production builds; the build
  verifies the artifact matches the variant it asked for
  (`scripts/check_frontend_variant.py`, `verify_build_variant`), and the demo
  stand's `converged_when` asserts the deployed variant.
- Runtime test flags hardened for production safety; `skip_authentication`
  removed in favour of a central test-flag mapping.

### 🧭 CLI

- `realms new`: live wizard-path create, `--deploy-mode`, `--co-admin` (dfx
  founder + Internet Identity admin), imported II session as founder, host
  chrome install, GaaS-only flow with Agora init split off the install message.
- `realms seed`: destroy-and-recreate Casals, union sheet with token/nft in
  the product stack, resumable catalog publishing, IC canister creation on
  the european application subnet capped at 1.8 T cycles.

### 🖥️ Frontend and marketplace

- Setup wizard stepper fits phones; Test Mode banner is dismissable; leftover
  `/ggg` Admin Dashboard and System sidebar items removed; portal URL and
  sidebar stay in sync across iframe reloads.
- Marketplace: canvas capitol landing, civic mosaic assets, `/about` as an
  Ashoka conversation, Verified-only catalog by default.
- `GET /version` on realm and marketplace canisters (sha, build time, version).

### 🔧 Backend and extensions

- Department table JSON apply with cascade delete.
- `enter_setup` exported; installer first boot allowed without IC control;
  live GOS installer recognised as bootstrap principal.
- Codex: seed `backend/modules` on legacy catalog install.
- Extensions submodule bumped (dev-server test identity).

### 🔑 Key ceremony

- Air-gapped YubiKey provisioning and offline verification tooling was added
  and then moved to its own private repository.

### 🛠️ CI / release

- `realms-e2e.yml`: `casals up` from an empty replica plus the cross-quarter
  live suite, replacing the dfx-driven `ci_install_mundus.py` stages.
- Release workflow installs `ic-wasm` and builds the frontend from the npm
  workspace root.
