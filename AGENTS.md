# Agents Guide — Realms

## Project Structure

```
realms/
├── extensions/ (submodule → realms-extensions)
│   └── extensions/<ext_id>/
│       ├── manifest.json
│       ├── backend/entry.py          # Python RPC handler (optional)
│       └── frontend-rt/              # Svelte 5 ESM bundle
│           ├── src/
│           └── vite.config.ts        # Lib-mode build
├── src/realm_frontend/               # Main SvelteKit frontend
├── src/realm_backend/                # Python canister backend
├── .github/workflows/
│   ├── deploy-infra.yml              # Infra canisters (legacy path)
│   ├── deploy-files.yml              # Publish extensions/codices (legacy path)
│   ├── deploy-mundus.yml            # Deploy realm canisters (legacy path)
│   ├── publish-build.yml            # Build + publish a semver release into Casals
│   ├── publish-main.yml             # Build + publish current main checkout (no release)
│   └── rollout.yml                   # Upgrade/reinstall canisters via Casals
├── scripts/
│   └── publish_build.py              # Build+publish engine used by publish-build.yml
├── deployment-descriptors/           # Network topology (YAML)
└── docs/reference/
```

`extensions/` is a git submodule. Commit/push there first, then update the ref in `realms`.

---

## Deploying Code Changes

### Decision: What Changed?

| What changed | Command |
|---|---|
| **Frontend only** (`src/realm_frontend/`) | Fast deploy (see below) |
| **Backend** (`src/realm_backend/`) | Full deploy with `canister=both` |
| **Extension frontend** (`extensions/`) | `deploy-files` → `deploy-mundus` |
| **Extension backend** (`entry.py`) | `deploy-files` → `deploy-mundus` with `canister=both` |

### Fast Frontend Deploy (~40s)

For changes to `src/realm_frontend/` only. **Always scope to the realm you're testing.**

```bash
git add . && git commit -m "fix: describe change" && git push origin main

gh workflow run deploy-mundus.yml \
  -f descriptor=deployment-descriptors/test-mundus-layered.yml \
  -f deploy_mode=upgrade \
  -f canister=frontend \
  -f extensions=none \
  -f codices=none \
  -f realm=agora
```

Why each flag matters:
- `canister=frontend` — skips backend WASM build/install/verification
- `extensions=none` / `codices=none` — skips extension and codex installation
- `realm=agora` — deploys one realm instead of all three (3x faster)
- `deploy_mode=upgrade` — preserves all on-chain state

### Full Deploy (~5min)

When backend code changed, or when deploying all realms:

```bash
gh workflow run deploy-mundus.yml \
  -f descriptor=deployment-descriptors/test-mundus-layered.yml \
  -f deploy_mode=upgrade \
  -f canister=both \
  -f artifact_version=build
```

### Descriptors by Environment

| Environment | Descriptor | Domain |
|---|---|---|
| Test | `test-mundus-layered.yml` | `<canister_id>.icp0.io` |
| Demo | `demo-mundus-layered.yml` | `<canister_id>.cp0.io` |
| Staging | `staging-mundus-layered.yml` | `<canister_id>.icp0.io` |

---

## `deploy-mundus.yml` Parameters

| Parameter | Options | Default | Notes |
|---|---|---|---|
| `descriptor` | YAML path in `deployment-descriptors/` | staging | Target environment |
| `deploy_mode` | `reinstall`, `upgrade`, `install` | `reinstall` | **Use `upgrade` unless resetting** |
| `realm` | realm name or blank | blank (all) | **Always scope for testing** |
| `canister` | `both`, `backend`, `frontend` | `both` | `frontend` is fastest for UI changes |
| `extensions` | `all`, `none`, or comma-separated IDs | `all` | e.g. `voting,vault,admin_dashboard` |
| `codices` | `all`, `none`, or comma-separated IDs | `all` | e.g. `dominion,agora` |
| `artifact_version` | `build`, `latest`, semver | `build` | `latest` = skip source build |

---

## Deploying Extension Changes

```bash
# 1. Build
cd extensions/extensions/<ext_id>/frontend-rt && npm run build && cd -

# 2. Push submodule
cd extensions && git add -A && git commit -m "feat(<ext_id>): change" && git push origin main && cd ..

# 3. Update submodule ref
git add extensions && git commit -m "chore: bump extensions" && git push origin main

# 4. Publish to file_registry (specific extension, or omit --extensions for all)
gh workflow run deploy-files.yml -f scope=extensions-only -f environment=test -f extensions=<ext_id>

# 5. Deploy realm (wait for step 4 to complete first)
gh workflow run deploy-mundus.yml \
  -f descriptor=deployment-descriptors/test-mundus-layered.yml \
  -f deploy_mode=upgrade \
  -f canister=both \
  -f realm=agora \
  -f extensions=<ext_id>
```

### `deploy-files.yml` Parameters

| Parameter | Options | Default | Notes |
|---|---|---|---|
| `environment` | `test`, `staging`, `demo` | `staging` | |
| `scope` | `all`, `extensions-only`, `codices-only` | `all` | |
| `extensions` | comma-separated IDs or blank | blank (all) | e.g. `voting,vault` |
| `codices` | comma-separated IDs or blank | blank (all) | e.g. `dominion` |
| `reinstall` | `true`/`false` | `false` | Destructive if true |

---

## Creating a Release

Bump the version and produce release artifacts (WASM, frontend tarball, CLI on PyPI, GitHub release):

```bash
gh workflow run release.yml -f release_type=patch   # or minor, major
```

This will:
1. Bump `version.txt` (e.g. 0.3.4 → 0.3.5)
2. Build `realm_backend.wasm.gz` and `realm_frontend.tar.gz`
3. Publish the CLI to PyPI
4. Create a GitHub release `v0.3.5` with all artifacts + checksums
5. Commit and push the version bump

Takes ~5 minutes. The version file determines the current version; the workflow computes the next one automatically.

### `release.yml` Parameters

| Parameter | Options | Default | Notes |
|---|---|---|---|
| `release_type` | `patch`, `minor`, `major` | `patch` | Follows semver |

---

## Casals — On-Chain Deploy & Upgrade (preferred path)

> **Always use the Casals path whenever possible.** This means `publish-build.yml` /
> `publish-main.yml` to publish artifacts and `rollout.yml` (or `realms rollout`)
> to deploy them. The legacy `deploy-infra`/`deploy-files`/`deploy-mundus` workflows
> exist only for anything Casals does not yet cover (mainly: the initial infra
> bootstrap and new-realm provisioning while `provision_via_casals` is still off).
> When in doubt, use Casals.

Casals is an **on-chain orchestrator** that owns the realm canisters and upgrades
them for us. Instead of an off-chain CI job installing WASMs, Casals pulls the
artifacts from `file_registry` and installs them itself, with **automatic
snapshot → install → verify-hash → rollback-on-failure** built in.

There are exactly **two steps**:

1. **Publish Build** — build the artifacts, upload them into `file_registry`, and
   register ("authorize") them in Casals. Nothing is deployed yet.
2. **Rollout** — tell Casals to upgrade (or reinstall) the chosen canisters to a
   published version.

This path **coexists** with the legacy `deploy-infra`/`deploy-files`/`deploy-mundus`
path. Pick per environment (see "Coexistence" below). **Casals is deployed and
wired on all three environments** (`test`, `demo`, `staging`): each one's realm and
infra canisters are registered in Casals and have `[Casals, CycleOps]` as their
only controllers. Provisioning of new realms still flows through the legacy path
until the installer's `provision_via_casals` flag is turned on per environment
(default off) — but publishing builds and rolling out upgrades already go through
Casals everywhere.

### How Casals organizes things

```
Section "Deployments"  → one Stand per realm (agora, dominion, syntropia, …)
Section "Infra"        → one Stand per infra piece (installer, realm-registry, …)
each Stand             → backend + frontend Canister(s)
```

Artifacts are named `<family>-backend@<version>` (backend WASM) and
`<family>-assets@<version>` (frontend bundle). Realms use the family `realm`;
infra stands map to families `installer`, `registry`, `file-registry`,
`dashboard`, `marketplace`. (`token`/`nft` are external canisters — managed in
Casals but not built here.)

### Step 1 — Publish Build

Builds the WASM/bundle, uploads to `file_registry`, authorizes in Casals.

```bash
# Manual workflow (preferred)
gh workflow run publish-build.yml \
  -f environment=test -f family=realm -f component=both -f version=0.4.0

# Or locally (same engine the workflow runs)
python3 scripts/publish_build.py \
  --environment test --family realm --component both \
  --version 0.4.0 --identity deployer
```

| `publish-build.yml` param | Options | Default | Notes |
|---|---|---|---|
| `environment` | `test`, `staging`, `demo` | `test` | |
| `family` | `realm`, `installer`, `registry`, `file-registry`, `dashboard`, `marketplace` | `realm` | |
| `component` | `both`, `backend`, `frontend` | `both` | |
| `version` | semver, e.g. `0.4.0` | — | required unless `from_main` |
| `from_main` | `true`/`false` | `false` | Publish as `main.<ts>.<sha>` instead of semver |
| `update_catalog` | `true`/`false` | `false` | Only for Casals-only envs (see Coexistence) |

### Main-branch snapshots (no release)

For day-to-day work on `main`, you do **not** need to cut a semver release. Publish
the current checkout and roll out with `-v main`:

```bash
# CI: runs automatically on push to main (realm/infra source paths) → test
# Or trigger manually:
gh workflow run publish-main.yml -f environment=test -f family=realm -f component=both

# Locally
python3 scripts/publish_build.py --environment test --family realm \
  --component both --from-main --identity deployer

# Roll out the newest main snapshot
realms rollout -e test -t all-realms -s both -v main --identity deployer --execute --yes
```

Version label format: `main.<unix_timestamp>.<git_sha>` (e.g. `main.1749254400.a1b2c3d`).
`-v main` always picks the newest one in that channel. `-v latest` still means the
newest **semver** release (Casals `latest` flag), not main.

### Step 2 — Rollout

Upgrades/reinstalls any mix of environments × realms/infra × backend/frontend.
**Dry-run by default** — it prints the plan and changes nothing until `--execute`.

```bash
# Preview (no changes): all realm backends in test
realms rollout -e test -t all-realms -s backend -v 0.4.0

# Apply: one realm, backend only
realms rollout -e test -t agora -s backend -v 0.4.0 --identity deployer --execute --yes

# Apply: all realms, backend + frontend
realms rollout -e test -t all-realms -s both -v 0.4.0 --identity deployer --execute --yes

# Reinstall all infra (state-wiping infra needs an explicit opt-in)
realms rollout -e test -t all-infra -m reinstall --include-infra-reinstall --execute --yes
```

Same inputs are available as a manual workflow:

```bash
gh workflow run rollout.yml \
  -f environments=test -f targets=all-realms -f scope=both \
  -f mode=upgrade -f version=0.4.0 -f execute=true
```

| `rollout` flag / `rollout.yml` input | Options | Default | Notes |
|---|---|---|---|
| `-e` / `environments` | comma list or `all` | `test` | Skips envs with no Casals |
| `-t` / `targets` | stand names, `all-realms`, `all-infra`, `all` | — | required |
| `-s` / `scope` | `backend`, `frontend`, `both` | `both` | |
| `-m` / `mode` | `upgrade`, `reinstall` | `upgrade` | `reinstall` **wipes state** |
| `-v` / `version` | `main`, `latest`, or semver | `latest` | `main` = newest main snapshot |
| `--execute` / `execute` | flag / bool | off | Off = dry-run plan only |
| `--include-infra-reinstall` | flag / bool | off | Required to reinstall `file-registry`/`realm-registry` |
| `--yes` / (always in CI) | flag | off | Skip confirmation prompts |

### Upgrading Casals itself (the orchestrator canisters)

> **Different from rollout.** `rollout.yml` upgrades the realm/infra canisters
> Casals *manages*. `casals-upgrade.yml` upgrades the **Casals orchestrator
> canisters themselves** (`casals_backend` / `casals_frontend`) — i.e. when a new
> version of the [Casals](https://github.com/smart-social-contracts/Casals)
> project ships and we want this environment's Casals brought up to it.

`casals-upgrade.yml` checks out the Casals repo at a chosen ref, builds it from
source (`make build`), points the deploy at this environment's Casals canister IDs
(from `canister_ids.json`), and runs `icp deploy --mode upgrade` with the
`CASALS_CI_PEM` identity (a controller of all three Casals). `upgrade` preserves
Casals' on-chain state (orchestra tree, pool, sheet, authorized-WASM catalog).

```bash
gh workflow run casals-upgrade.yml \
  -f environment=test -f casals_ref=main -f components=backend,frontend
```

| `casals-upgrade.yml` param | Options | Default | Notes |
|---|---|---|---|
| `environment` | `test`, `demo`, `staging` | `test` | Which env's Casals to upgrade |
| `casals_ref` | git ref/tag/sha | blank (`main`) | Casals version to build |
| `components` | `backend`, `frontend`, `file-registry` (comma list) | `backend,frontend` | See file-registry note |
| `mode` | `upgrade`, `reinstall` | `upgrade` | `reinstall` **wipes Casals state** |
| `i_understand_reinstall_wipes_casals` | `true`/`false` | `false` | Required to allow `reinstall` |

- **`file-registry` is special here.** This project's Casals instances **reuse the
  realms `file_registry`** (there is no separate `ic_file_registry`); that canister
  is realms-managed infra with its own upgrade path (`publish-build.yml`
  `family=file-registry` + `rollout.yml`). Prefer that path. Only add
  `file-registry` to `components` if you deliberately want to push the Casals-repo
  file_registry WASM onto it.
- Needs the `CASALS_CI_PEM` secret (the only secret required — the Casals repo is public).

### Casals canister IDs

| Env | Casals backend | Casals frontend | file_registry |
|---|---|---|---|
| Test | `qthgp-3yaaa-aaaae-agveq-cai` | `qic2k-baaaa-aaaae-agvga-cai` | `uq2mu-kaaaa-aaaah-avqcq-cai` |
| Demo | `jo3cj-faaaa-aaaac-bffea-cai` | `hvwpv-aiaaa-aaaam-ajddq-cai` | `vi64l-3aaaa-aaaae-qj4va-cai` |
| Staging | `jj2e5-iyaaa-aaaac-bffeq-cai` | `mcqbx-hyaaa-aaaaj-qsarq-cai` | `iebdk-kqaaa-aaaau-agoxq-cai` |

These are also in `_CASALS_IDS` (`cli/realms/cli/commands/rollout.py`) and
`canister_ids.json` (`casals_backend`/`casals_frontend`). Add new env IDs there.

### Who controls what

- **Orchestra canisters** (every realm + infra canister Casals manages): controlled
  only by **Casals itself** plus **CycleOps** (`cpbhu-5iaaa-aaaad-aalta-cai`, for
  cycle top-ups). Casals does the upgrades; no human key is a controller.
- **Casals canisters**: controlled by `ah6ac-cc73l-...` (the `my_dev_identity_1` /
  `deployer` key), the dedicated CI key, and a conductor Internet Identity.
- **CI identity**: workflows use the **`CASALS_CI_PEM`** secret (a controller of all
  three Casals), falling back to `IC_IDENTITY_PEM` if it is unset. To change a
  controller list, call Casals' admin-only `set_canister_controllers` (it refuses to
  drop Casals from the list unless you pass `force`).

### Coexistence with the legacy path

- The installer flag `provision_via_casals` (per environment, default off) decides
  whether that environment provisions via Casals or the legacy off-chain deployer.
- Rollout **never** touches the realm version catalog, so it can't interfere with
  the legacy self-service upgrade path.
- Publish Build only updates the catalog when `--update-catalog` is set, so by
  default it won't feed a legacy-mode env a `fileregistry://` URL it can't use.
- `release.yml`, `deploy-mundus.yml`, etc. are untouched.

### Casals gotchas

1. **Local backend builds need a clean venv.** `basilisk` refuses to build if the
   active Python has native (`.so`) packages. Build in an isolated venv with only
   `ic-basilisk`, `ic-basilisk-toolkit`, `ic-python-db`, `ic-python-logging`
   (CI runners are already clean). Set `CANISTER_CANDID_PATH=src/<canister>/<canister>.did`.
2. **Frontend rollout is the slow part.** Casals copies the ~109-file bundle into
   each asset canister in small batches (6 files/call, with retry) to stay inside
   the ~5 min ingress window. Expect several minutes per realm; this is normal.
3. **`reinstall` wipes canister state** on success (the protective snapshot is
   dropped after a verified reinstall). Use `upgrade` unless you mean it.
4. **Always dry-run first** (omit `--execute`) and read the plan table.
5. **Frontend builds need candid declarations.** `publish_build.py` copies the
   committed `src/declarations/*` into each frontend's `src/lib/declarations/`
   before `vite build` (the realm frontend imports `$lib/declarations/realm_backend`).
   Don't remove that step or the main-snapshot build fails to resolve the import.
6. **Large files use incremental finalize.** Uploads over ~200 KB are chunked, and
   the CLI finalizes them with `finalize_chunked_file_step` (batched, on-chain
   hashing skipped, local sha256 passed in). The one-shot `finalize_chunked_file`
   blows the 40 B-instruction limit (`IC0522`) on multi-MB WASMs — don't switch back.

`publish-main.yml` runs automatically on every push to `main` that touches realm/
infra source, publishing a `main.<ts>.<sha>` snapshot to **test**. Watch that run
after merging; it is the live check that the publish path still works.

See `docs/reference/CASALS_ROLLOUT.md` for the full runbook (migrating a realm,
authorization model, cycle budget).

---

## Full Platform Re-deployment

Run sequentially: **deploy-infra → deploy-files → deploy-mundus**

Each stage must complete before the next. Within a stage, environments can run in parallel.

```bash
# Stage 1: Infra
gh workflow run deploy-infra.yml -f environment=test -f deploy_mode=upgrade
gh workflow run deploy-infra.yml -f environment=demo -f deploy_mode=upgrade
gh workflow run deploy-infra.yml -f environment=staging -f deploy_mode=upgrade

# Stage 2: Files (after infra completes)
gh workflow run deploy-files.yml -f environment=test -f scope=all
gh workflow run deploy-files.yml -f environment=demo -f scope=all
gh workflow run deploy-files.yml -f environment=staging -f scope=all

# Stage 3: Mundus (after files completes)
gh workflow run deploy-mundus.yml -f descriptor=deployment-descriptors/test-mundus-layered.yml -f deploy_mode=reinstall -f canister=both
gh workflow run deploy-mundus.yml -f descriptor=deployment-descriptors/demo-mundus-layered.yml -f deploy_mode=reinstall -f canister=both
gh workflow run deploy-mundus.yml -f descriptor=deployment-descriptors/staging-mundus-layered.yml -f deploy_mode=reinstall -f canister=both
```

---

## Known Canister IDs

| Canister | Test | Demo | Staging |
|---|---|---|---|
| file_registry | `uq2mu-kaaaa-aaaah-avqcq-cai` | `vi64l-3aaaa-aaaae-qj4va-cai` | `iebdk-kqaaa-aaaau-agoxq-cai` |
| Agora backend | `rnghe-haaaa-aaaak-qyxyq-cai` | `3bohd-2yaaa-aaaac-qcyla-cai` | `ihbn6-yiaaa-aaaac-beh3a-cai` |
| Agora frontend | `pqwsi-vyaaa-aaaau-agrbq-cai` | `3gpbx-xaaaa-aaaac-qcylq-cai` | `iaalk-vqaaa-aaaac-beh3q-cai` |
| Dominion backend | `ku6cv-2iaaa-aaaab-agrpa-cai` | `h5vpp-qyaaa-aaaac-qai3a-cai` | `ijdaw-dyaaa-aaaac-beh2a-cai` |
| Dominion frontend | `2enu3-byaaa-aaaad-qlxfa-cai` | `gzya5-jyaaa-aaaac-qai5a-cai` | `iocgc-oaaaa-aaaac-beh2q-cai` |
| Syntropia backend | `m2wv3-uaaaa-aaaah-quoiq-cai` | `2lbfz-yiaaa-aaaac-qcyma-cai` | `jnope-2yaaa-aaaac-beh4a-cai` |
| Syntropia frontend | `2dmsp-maaaa-aaaad-qlxfq-cai` | `2madn-vqaaa-aaaac-qcymq-cai` | `jkpjq-xaaaa-aaaac-beh4q-cai` |

---

## Local Development

```bash
# Frontend-only (fast)
scripts/deploy_local_dev.sh -s .realms/realm_* -f

# Clean frontend rebuild (CSS/style changes)
scripts/deploy_local_dev.sh -s .realms/realm_* -f -c

# Backend
scripts/deploy_local_dev.sh -s .realms/realm_* -b
```

Runtime extension bundles load dynamically — no full frontend redeploy needed, only file_registry upload + install.

### Local Extension Dev Server (instant feedback)

For visual iteration on any runtime extension UI without deploying. Works for all 28+ extensions with zero per-extension setup.

**How it works:** A shared dev harness (`extensions/dev-server/`) runs a local Vite server that mounts any extension's Svelte component with real data from the test canister. It provides the same wrapper the canister provides: nav bar, layout shell, Tailwind CSS, and a full `RealmExtensionContext` (backend actor, callSync/callAsync, stores). Images are proxied from the real canister. API calls go through `/api` proxy to `icp0.io`, matching the standard ICP dev workflow. None of the dev harness files affect production builds.

**Setup (once):**

```bash
cd extensions/dev-server && npm install
```

**Run (from any extension):**

```bash
cd extensions/extensions/<ext_id>/frontend-rt
npm run dev
```

Or directly:

```bash
cd extensions/dev-server
node bin/dev.js <ext_id>
```

Opens on `http://localhost:5555`. Edit the extension's Svelte source, save, see changes instantly via HMR. When happy, deploy with the fast remote deploy below.

**Configuration:** Edit `extensions/dev-server/dev-config.json` to point at a different canister or network.

**Workflow:** `edit → see locally → happy? → deploy to IC`

---

### Fast Remote Extension Deploy (~26s)

For iterating on runtime extension bundles against test canisters without CI. No git commit required — edit, deploy, check, repeat. Commit only when the result is correct.

All commands run from the **`realms/` project root**.

**Setup (once per session):**

```bash
export TERM=xterm
export DFX_WARNING=-mainnet_plaintext_identity
dfx identity use my_dev_identity_1
```

`my_dev_identity_1` (principal `ah6ac-cc73l-...`) is a controller of the test canisters.

**Deploy cycle (edit → live in ~26s):**

```bash
realms files build --extensions <ext_id> \
  && realms files publish --network test --extensions-only --extensions <ext_id> \
  && dfx canister call <backend_canister_id> install_extension_from_registry \
     '("{\"registry_canister_id\": \"<file_registry_id>\", \"ext_id\": \"<ext_id>\", \"version\": \"<version>\"}")' \
     --network test
```

| Step | Command | Time | What it does |
|------|---------|------|-------------|
| Build | `realms files build --extensions <ext_id>` | ~4s | Runs `npm install && npm run build` in `frontend-rt/` |
| Publish | `realms files publish --network test ...` | ~8s | Uploads bundle to the file_registry canister |
| Install | `dfx canister call ... install_extension_from_registry` | ~14s | Backend pulls bundle from registry and installs it |

**Concrete example** — `public_dashboard` on Agora (test):

```bash
realms files build --extensions public_dashboard \
  && realms files publish --network test --extensions-only --extensions public_dashboard \
  && dfx canister call rnghe-haaaa-aaaak-qyxyq-cai install_extension_from_registry \
     '("{\"registry_canister_id\": \"uq2mu-kaaaa-aaaah-avqcq-cai\", \"ext_id\": \"public_dashboard\", \"version\": \"1.3.0\"}")' \
     --network test
```

The `install_extension_from_registry` call goes directly to the realm backend, bypassing the installer service. It fetches the bundle from the file_registry and copies the frontend files to the asset canister in one call.

**Canister IDs for the install call** (from the Known Canister IDs table and the descriptor):

| Realm | Backend canister (call target) | File registry (test) |
|-------|-------------------------------|---------------------|
| Agora | `rnghe-haaaa-aaaak-qyxyq-cai` | `uq2mu-kaaaa-aaaah-avqcq-cai` |
| Dominion | `ku6cv-2iaaa-aaaab-agrpa-cai` | `uq2mu-kaaaa-aaaah-avqcq-cai` |
| Syntropia | `m2wv3-uaaaa-aaaah-quoiq-cai` | `uq2mu-kaaaa-aaaah-avqcq-cai` |

**When to use `mundus deploy` instead:** if you need to redeploy the main frontend canister WASM (changes to `src/realm_frontend/`), not just a runtime extension bundle:

```bash
realms mundus deploy deployment-descriptors/test-mundus-layered.yml \
  --realm agora --canister frontend \
  --extensions <ext_id> --codices none --version latest
```

This takes ~90s but handles frontend WASM + branding + extension install together.

**Constraints:**
- The extension bundle must stay under ~200KB for `files publish` to succeed (file_registry instruction limit). Keep heavy libraries (leaflet, h3-js) loaded at runtime via `fetch()` + `eval()` instead of bundling them.
- The extension `version` in `manifest.json` must match the version in the `dfx canister call`. Bump the version when you need to force cache invalidation.
- After finishing iteration, commit the changes to the submodule and update the ref in `realms` (see "Deploying Extension Changes" above).

---

## Environment Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pip install -e cli
```

Verify: `realms --help` and `dfx --version`.

---

## dfx in this environment

dfx 0.30.2 crashes with `ColorOutOfRange` unless the terminal is set up correctly. Always export these before running any `dfx` command:

```bash
export TERM=xterm
export DFX_WARNING=-mainnet_plaintext_identity
```

The first fixes the color panic, the second suppresses the plaintext identity warning that blocks execution on `test`/`staging` networks.

---

## Gotchas

1. **deploy-files `environment` must match target.** Publishing to `staging` (default) won't be visible to `demo` or `test` realms.
2. **Any change inside `extensions/` (including manifest.json edits) requires `deploy-files` before `deploy-mundus`.** The mundus workflow installs extensions from the file registry — if you skip `deploy-files`, the registry still has stale manifests/bundles and the deploy will use old data. Always: `deploy-files` → wait for green → `deploy-mundus`.
3. **Agora is prone to timeouts.** Retry a single failed realm: `-f realm=agora`.
4. **`reinstall` wipes all state.** Use `upgrade` unless you want a clean slate.
5. **Frontend bundles are built by CI.** The `deploy-files` workflow runs `realms files build` to compile `frontend-rt/` sources before publishing. No need to commit `dist/index.js`.

---

## Rules

- **Casals is always the preferred deploy path.** For any realm/infra backend or frontend change, use `publish-build.yml` / `publish-main.yml` + `rollout.yml`. Fall back to the legacy `deploy-*` workflows only when Casals does not cover the operation (e.g. first-time infra bootstrap, or new-realm provisioning before `provision_via_casals` is enabled).
- **Visually verify every UI change before reporting back.** After deploying a frontend or extension change, open the page in the browser and confirm the result matches the requirements. Do not report completion until you have checked the deployed page yourself. If the visual check reveals issues, fix and redeploy in a loop until the result is correct.
- Do not commit unless explicitly told to do so.
- Always use `deploy_mode=upgrade` for production/test deploys.
- Always scope deploys as narrowly as possible:
  - **Realm:** `-f realm=agora` — deploy one realm, not all.
  - **Canister:** `-f canister=frontend` or `-f canister=backend` — skip the half you didn't change.
  - **Extensions/codices:** `-f extensions=voting,vault` or `-f codices=dominion` — deploy only what changed. Use `none` to skip entirely.
- The dfx identity is `deployer`. Use `dfx identity use <name>` to switch.
- **Monitor every workflow you trigger.** After launching a workflow, watch it until it goes green. If it fails, diagnose the error, fix it, re-push, and re-trigger — repeat until the run succeeds. Never leave a red workflow behind.

---

## Browser Testing

### Cursor built-in browser

The `@Browser` tool (Cursor IDE browser tab) works with ICP canister frontends. Use `browser_navigate` to open a canister URL and `browser_snapshot` to inspect the accessibility tree.

**Gotcha — test mode identity is stateful**: the test environment uses `TEST_MODE_II_BYPASS=true`, which auto-logs-in with a deterministic hardcoded identity (seed `0xED, 0x57` → principal `2eqns-rmzes-...`). This identity is the **same across all browser sessions**. If a previous test activated, modified, or consumed resources for that principal, subsequent sessions will see the post-modification state. Before concluding a feature is broken, check whether the test identity's on-chain state already reflects a previous test run:

```bash
dfx canister call <canister_id> is_principal_activated '("2eqns-rmzes-7npxw-dxpw2-qdy2s-mw6ix-svdo2-oya7o-a6ldc-sqgwh-bqe")' --network test
```

### Playwright (headless Chromium)

For automated, repeatable, screenshot-based testing — or when you need to capture console output, intercept network calls, or interact with forms programmatically — use Playwright.

#### Setup (one-time)

```bash
pip install playwright        # if not already installed
playwright install chromium   # downloads ~110 MB headless shell
```

`playwright install --with-deps chromium` requires sudo and will fail in most agent environments. The `--with-deps` flag is not needed if system libraries are already present (they usually are).

#### Inline test script pattern

```python
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Capture console output — must be set up BEFORE page.goto()
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))

        await page.goto("https://<canister_id>.icp0.io/some-page", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=15000)
        await page.wait_for_timeout(3000)  # extra wait for async canister calls

        await page.screenshot(path="/tmp/test_screenshot.png")
        body = await page.inner_text("body")
        print(body[:500])

        # Interact with form elements
        input_el = await page.query_selector('input[type="text"]')
        if input_el:
            await input_el.fill("some value")
            btn = await page.query_selector('button:has-text("Submit")')
            if btn:
                await btn.click()
                await page.wait_for_timeout(5000)
                await page.screenshot(path="/tmp/test_after_submit.png")

        for msg in console_msgs:
            if "Permission" not in msg:
                print(msg)

        await browser.close()

asyncio.run(test())
```

#### Key tips

- **Screenshots** are saved to `/tmp/` and can be viewed with the `Read` tool (it supports PNG).
- **`wait_for_timeout(3000–8000)`** after navigation or clicks — canister calls are async and can take several seconds on the IC boundary nodes.
- **Same test mode identity caveat** applies — Playwright also gets the hardcoded `2eqns-rmzes-...` principal in test environments.
- **Intercepting responses**: use `page.route("**/*", handler)` to log or modify HTTP requests/responses.
- **Network failures**: use `page.on("requestfailed", ...)` to catch failed API calls.

### When to use what

| Scenario | Tool |
|---|---|
| Quick visual check of a page | Cursor `@Browser` |
| Verify canister logic (queries, updates, guards) | `dfx canister call` |
| Automated UI test with screenshots and form interaction | Playwright |
| Full user flow (UI → canister → UI update) | Playwright |
| Admin operations (create codes, toggle modes) | `dfx canister call` with controller identity |

---

## Further Reading

- `docs/reference/DEPLOYMENT_GUIDE.md` — Full deployment guide
- `docs/reference/CASALS_ROLLOUT.md` — On-chain (Casals) deploy & upgrade runbook
- `docs/reference/RUNTIME_EXTENSION_STAGING_DEPLOY.md` — Layered deploy runbook
- `docs/reference/EXTENSION_ARCHITECTURE.md` — Extension lifecycle
- `docs/reference/PRIVATE_DATA_SHARING.md` — End-to-end encrypted, consent-based data sharing for extensions (own entity + scope kind + `ctx.crypto`)
- `cli/README.md` — CLI command reference
