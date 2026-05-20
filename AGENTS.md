# Agents Guide — Realms Extension Development & Deployment

## Project Structure

```
realms/                                          # Main repo
├── extensions/ (submodule → realms-extensions)  # Git submodule
│   └── extensions/<ext_id>/                     # Extension source code
│       ├── manifest.json                        # Extension metadata (name, version, permissions)
│       ├── backend/                             # Python backend (optional)
│       │   └── entry.py                         # Extension RPC handler
│       └── frontend-rt/                         # Runtime-loaded frontend bundle
│           ├── src/                             # Svelte source
│           ├── dist/index.js                    # Built ESM bundle (committed)
│           ├── vite.config.ts                   # Lib-mode build config
│           └── package.json
├── .github/workflows/
│   ├── deploy-infra.yml                         # Deploy infra canisters (registry, file_registry, marketplace, etc.)
│   ├── deploy-files.yml                         # Publish extensions/codices to file_registry
│   └── deploy-mundus.yml                        # Deploy realm canisters (backend + frontend)
├── scripts/
│   ├── deploy_runtime_extension_to_staging.sh   # Full extension deploy pipeline
│   └── deploy_local_dev.sh                      # Iterative local dev deploy
├── deployment-descriptors/                      # Network/canister topology (YAML)
└── docs/reference/                              # Detailed reference docs
```

**Important:** `extensions/` is a git submodule pointing to the `realms-extensions` repository. Changes to extensions must be committed/pushed there first, then the submodule ref updated in `realms`.

## Deploying Code Changes (Standard Workflow)

For any change to the realm frontend or backend source code (i.e., files under `src/`), the standard deployment workflow is:

```bash
# 1. Commit and push to main
git add <changed files>
git commit -m "fix: describe the change"
git push origin main

# 2. Trigger the deploy-mundus workflow (upgrade mode preserves all state)
gh workflow run deploy-mundus.yml \
  -f descriptor=deployment-descriptors/test-mundus-layered.yml \
  -f deploy_mode=upgrade \
  -f canister=both \
  -f artifact_version=build

# Frontend-only fast deploy (skips backend build, WASM install, and extensions)
gh workflow run deploy-mundus.yml \
  -f descriptor=deployment-descriptors/test-mundus-layered.yml \
  -f deploy_mode=upgrade \
  -f canister=frontend \
  -f skip_extensions=true \
  -f artifact_version=latest \
  -f realm=agora
```

Choose the descriptor matching the target environment (`test-`, `demo-`, or `staging-mundus-layered.yml`). **Always use `deploy_mode=upgrade`** unless a full state reset is intended — upgrade is safe and preserves all canister state.

**Frontend-only deploys** (`canister=frontend`) are supported and significantly faster — they skip backend WASM compilation, WASM installation, and WASM verification. Combine with `skip_extensions=true` to also skip the extension/codex installation phase, reducing deploy time from ~5min to ~40s. Use `artifact_version=latest` to skip building from source entirely (uses the latest GitHub release).

This is the preferred workflow for all code changes — no other steps (deploy-infra, deploy-files, etc.) are needed unless you're changing infrastructure canisters or extension bundles.

## Extension Frontend Build

Each runtime extension has a `frontend-rt/` directory containing a Svelte 5 app built as an ES module library.

```bash
cd extensions/extensions/<ext_id>/frontend-rt
npm install
npm run build    # produces dist/index.js
```

The vite config uses `build.lib` mode with `formats: ['es']` and externalizes `leaflet` and `h3-js` (loaded at runtime from esm.sh). The bundle is self-contained Svelte compiled code.

## Deploying a Runtime Extension

Runtime extensions are deployed to the **file_registry** canister and then installed into a realm via `install_extension_from_registry`. There are two deployment models:

| Model | When to use |
|-------|-------------|
| **Bundled** | Local dev, quick demos (`realms realm create --deploy`) — extensions baked into WASM |
| **Layered** (production) | Long-lived realms — artifacts stored in file_registry, pulled at install time |

### Method 1: GitHub Actions Workflows (Standard for CI)

This is the standard deployment path for staging and production. It uses workflows in sequence.

#### Step-by-step: Deploying Extension Changes

```bash
# 1. Build the frontend bundle
cd extensions/extensions/<ext_id>/frontend-rt
npm run build

# 2. Commit and push to the realms-extensions submodule
cd /path/to/realms/extensions   # this IS the realms-extensions repo
git add -A
git commit -m "feat(<ext_id>): describe change"
git push origin main

# 3. Update submodule ref in realms, commit, and push
cd /path/to/realms
git add extensions
git commit -m "chore: bump extensions submodule"
git push origin main

# 4. Publish extension files to file_registry
gh workflow run deploy-files.yml -f scope=extensions-only
# Wait for completion before next step

# 5. Deploy realm canisters (upgrade mode — safe, preserves state)
gh workflow run deploy-mundus.yml \
  -f descriptor=deployment-descriptors/demo-mundus-layered.yml \
  -f deploy_mode=upgrade \
  -f realm=agora \
  -f canister=both
```

#### `deploy-files.yml` Parameters

| Parameter | Options | Default | Description |
|-----------|---------|---------|-------------|
| `environment` | `test`, `staging`, `demo` | `staging` | Target environment |
| `scope` | `all`, `extensions-only`, `codices-only` | `all` | What to publish |
| `reinstall` | `true`/`false` | `false` | Wipe file_registry first (destructive) |

#### `deploy-mundus.yml` Parameters

| Parameter | Options | Default | Description |
|-----------|---------|---------|-------------|
| `descriptor` | YAML paths in `deployment-descriptors/` | staging | Defines realms & canister topology |
| `deploy_mode` | `reinstall`, `upgrade`, `install` | `reinstall` | **Use `upgrade` to preserve data** |
| `realm` | realm name or blank for all | blank | Filter to single realm |
| `canister` | `both`, `backend`, `frontend` | `both` | Which canisters to deploy |
| `skip_extensions` | `true`, `false` | `false` | Skip extension/codex installation (faster deploys) |
| `artifact_version` | `build`, `latest`, or semver | `build` | WASM artifact source |

> **TIP:** For fast frontend-only redeployments, use `canister=frontend` + `skip_extensions=true` + `artifact_version=latest`. This skips backend build/install, WASM verification, and extension installation — completing in ~40s instead of ~5min.

> **GOTCHA 2:** The `deploy-files.yml` `environment` parameter must match the target environment. If you're deploying to demo realms, use `-f environment=demo`. The default is `staging`. Each environment has its own file_registry canister — publishing to the wrong one means the realm won't see updated extensions.

#### `deploy-infra.yml` Parameters

| Parameter | Options | Default | Description |
|-----------|---------|---------|-------------|
| `environment` | `test`, `demo`, `staging` | `staging` | Target environment |
| `deploy_mode` | `upgrade`, `reinstall`, `install` | `upgrade` | WASM deploy mode |
| `canisters` | `all`, `realm_registry_backend`, `realm_registry_frontend`, `realm_installer`, `file_registry`, `file_registry_frontend`, `marketplace_backend`, `marketplace_frontend`, `platform_dashboard_frontend` | `all` | Which infra canisters to deploy |

#### Full Platform Re-deployment (All Environments)

When re-deploying the entire platform across all networks, workflows **must run sequentially** in this order:

1. **deploy-infra** — upgrades infrastructure canisters (file_registry, marketplace, realm_registry, etc.)
2. **deploy-files** — publishes extensions and codices to the file_registry
3. **deploy-mundus** — deploys realm canisters (which pull extensions from file_registry)

Within each stage, all 3 environments (test, demo, staging) can run in parallel since they have separate concurrency groups.

```bash
# Stage 1: Deploy infra (all environments in parallel, wait for all to complete)
gh workflow run deploy-infra.yml -f environment=test -f deploy_mode=upgrade -f canisters=all
gh workflow run deploy-infra.yml -f environment=demo -f deploy_mode=upgrade -f canisters=all
gh workflow run deploy-infra.yml -f environment=staging -f deploy_mode=upgrade -f canisters=all
# Wait for all 3 to complete before proceeding

# Stage 2: Deploy files (all environments in parallel, wait for all to complete)
gh workflow run deploy-files.yml -f environment=test -f scope=all
gh workflow run deploy-files.yml -f environment=demo -f scope=all
gh workflow run deploy-files.yml -f environment=staging -f scope=all
# Wait for all 3 to complete before proceeding

# Stage 3: Deploy mundus (all environments in parallel)
gh workflow run deploy-mundus.yml -f descriptor=deployment-descriptors/test-mundus-layered.yml -f deploy_mode=reinstall -f canister=both
gh workflow run deploy-mundus.yml -f descriptor=deployment-descriptors/demo-mundus-layered.yml -f deploy_mode=reinstall -f canister=both
gh workflow run deploy-mundus.yml -f descriptor=deployment-descriptors/staging-mundus-layered.yml -f deploy_mode=reinstall -f canister=both
```

> **GOTCHA 3:** The deploy-mundus workflow deploys realms in parallel (matrix strategy with `fail-fast: false`). Individual realm failures (commonly timeouts on agora) do not block other realms. Retry a single failed realm with `-f realm=agora` rather than re-running the entire workflow.

> **GOTCHA 4:** Never run deploy-mundus before deploy-files completes. The mundus reinstall creates fresh canisters that need to pull extensions from the file_registry — if files haven't been published yet, extension installation will fail or be incomplete.

### Method 2: CLI Commands (Local / Manual)

The `realms` CLI provides high-level commands that handle all the upload/publish/install plumbing:

```bash
# 1. Build the frontend bundle
cd extensions/extensions/<ext_id>/frontend-rt
npm install
npm run build
cd -

# 2. Publish to file_registry (uploads manifest, backend/*.py, frontend bundle, i18n)
realms extension publish \
  --registry <file_registry_canister_id> \
  --source-dir extensions/extensions/<ext_id> \
  --network <network>

# 3. Install into realm (pulls from registry into realm stable memory)
realms extension registry-install \
  --canister <realm_backend_canister_id> \
  --registry <file_registry_canister_id> \
  --extension-id <ext_id> \
  --network <network>
```

### Method 3: Shell Script (Staging)

The all-in-one script handles build + upload + install + verification:

```bash
bash scripts/deploy_runtime_extension_to_staging.sh \
  --realm-backend <realm_backend_canister_id> \
  --network <network> \
  --extension-id <ext_id> \
  --extensions-repo extensions \
  --file-registry <file_registry_canister_id>
```

### Method 4: Bulk Publish (All Extensions)

```bash
realms files publish --network <network>    # publish all extensions + codices
realms files reset --network <network>      # wipe + reinstall registry (destructive)
```

### Method 5: Manual dfx Calls (Low-Level)

For debugging or when the CLI is unavailable:

#### 1. Build the frontend bundle

```bash
cd extensions/extensions/<ext_id>/frontend-rt
npm install
npm run build
```

#### 2. Upload files to file_registry

Upload each file using `store_file` with namespace `ext/<ext_id>/<version>`:

```bash
dfx canister call --network <network> file_registry store_file \
  '("{\"namespace\":\"ext/<ext_id>/<version>\",\"path\":\"frontend/dist/index.js\",\"content_b64\":\"<base64>\",\"content_type\":\"application/javascript\"}")'
```

#### 3. Publish the namespace

```bash
dfx canister call --network <network> file_registry publish_namespace \
  '("{\"namespace\":\"ext/<ext_id>/<version>\"}")'
```

#### 4. Install into realm

```bash
dfx canister call --network <network> <realm_backend_canister_id> install_extension_from_registry \
  '("{\"registry_canister_id\":\"<file_registry_id>\",\"ext_id\":\"<ext_id>\",\"version\":\"<version>\"}")'
```

#### 5. Verify

```bash
dfx canister call --network <network> <realm_backend_canister_id> get_extension_frontend_info \
  '("{\"extension_id\":\"<ext_id>\"}")'
```

## Known Canister IDs

| Canister | Test | Demo | Staging |
|----------|------|------|---------|
| file_registry | `uq2mu-kaaaa-aaaah-avqcq-cai` | `vi64l-3aaaa-aaaae-qj4va-cai` | `iebdk-kqaaa-aaaau-agoxq-cai` |
| Dominion backend | `ku6cv-2iaaa-aaaab-agrpa-cai` | `h5vpp-qyaaa-aaaac-qai3a-cai` | `ijdaw-dyaaa-aaaac-beh2a-cai` |
| Dominion frontend | `2enu3-byaaa-aaaad-qlxfa-cai` | `gzya5-jyaaa-aaaac-qai5a-cai` | `iocgc-oaaaa-aaaac-beh2q-cai` |
| Agora backend | `rnghe-haaaa-aaaak-qyxyq-cai` | `3bohd-2yaaa-aaaac-qcyla-cai` | `ihbn6-yiaaa-aaaac-beh3a-cai` |
| Agora frontend | `pqwsi-vyaaa-aaaau-agrbq-cai` | `3gpbx-xaaaa-aaaac-qcylq-cai` | `iaalk-vqaaa-aaaac-beh3q-cai` |
| Syntropia backend | `m2wv3-uaaaa-aaaah-quoiq-cai` | `2lbfz-yiaaa-aaaac-qcyma-cai` | `jnope-2yaaa-aaaac-beh4a-cai` |
| Syntropia frontend | `2dmsp-maaaa-aaaad-qlxfq-cai` | `2madn-vqaaa-aaaac-qcymq-cai` | `jkpjq-xaaaa-aaaac-beh4q-cai` |

- Test network uses `.icp0.io` domain
- Demo network uses `.cp0.io` domain (e.g., `3gpbx-xaaaa-aaaac-qcylq-cai.cp0.io`)
- Staging network uses `.icp0.io` domain
- Full canister IDs in `canister_ids.json` and `deployment-descriptors/`

## Local Development Workflow

For iterative local dev (using a `.realms/` deployment):

```bash
# Frontend-only redeploy (fast)
scripts/deploy_local_dev.sh -s .realms/realm_* -f

# Clean frontend rebuild (after CSS/style changes)
scripts/deploy_local_dev.sh -s .realms/realm_* -f -c

# Backend redeploy
scripts/deploy_local_dev.sh -s .realms/realm_* -b
```

Extension frontend-rt bundles are loaded dynamically at runtime by the realm frontend — they do NOT require a full frontend redeploy. Only the file_registry upload + install step is needed.

## Environment Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pip install -e cli
```

Verify: `realms --help` and `dfx --version`.

## Important Notes

- Do not commit unless explicitly told to do so.
- The `dist/index.js` bundle IS committed to the repo — always rebuild after source changes.
- **Submodule workflow:** `extensions/` is the `realms-extensions` repo checked out as a submodule. To deploy changes: (1) commit+push inside `extensions/`, (2) `cd` to `realms/` root, `git add extensions && git commit && git push`, (3) trigger workflows.
- The `--extensions-repo` flag in the shell script defaults to `$REPO_ROOT/../realms-extensions`. When working from this repo, pass `--extensions-repo extensions` to point at the in-repo extensions directory.
- The current dfx identity is `deployer`. Use `dfx identity use <name>` to switch.
- Runtime extension frontend bundles are loaded dynamically from the file_registry at runtime — only the `deploy-files` step is needed for pure frontend changes. Backend changes (`entry.py`) also require a `deploy-mundus` upgrade to reload into the canister.
- The realm backend must expose `install_extension_from_registry` and `get_extension_frontend_info` (Layer 2 code) before registry-install works.
- The realm frontend must have the dynamic `/extensions/[id]` route to load ESM bundles at runtime.
- **deploy_mode=upgrade vs reinstall:** `upgrade` preserves all canister state (stable memory, tasks, executions). `reinstall` wipes everything. Always use `upgrade` for production unless a full reset is intended.
- **`canister=frontend`** is fully supported for `upgrade` deploys. The installer and off-chain deployer handle `deploy_scope=frontend_only` manifests correctly, skipping backend steps. Combine with `--skip-extensions` for fastest deploys.
- **Deployment ordering is critical:** When running multiple workflows, always execute in order: `deploy-infra` → `deploy-files` → `deploy-mundus`. Each stage must complete before the next begins.
- **Transient timeout failures:** The agora realm deploy is particularly prone to network timeouts. When this happens, retry just that realm: `gh workflow run deploy-mundus.yml -f descriptor=<descriptor> -f deploy_mode=reinstall -f canister=both -f realm=agora`.

## Further Reading

- `docs/reference/DEPLOYMENT_GUIDE.md` — Full deployment guide (4-script bundled flow)
- `docs/reference/RUNTIME_EXTENSION_STAGING_DEPLOY.md` — Layered deploy runbook
- `docs/reference/EXTENSION_ARCHITECTURE.md` — Extension lifecycle
- `README.md` § Layered Deployment Architecture — High-level overview
- `cli/README.md` — CLI command reference
