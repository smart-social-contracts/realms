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
│   ├── deploy-files.yml                         # Publish extensions/codices to file_registry
│   └── deploy-mundus.yml                        # Deploy realm canisters (backend + frontend)
├── scripts/
│   ├── deploy_runtime_extension_to_staging.sh   # Full extension deploy pipeline
│   └── deploy_local_dev.sh                      # Iterative local dev deploy
├── deployment-descriptors/                      # Network/canister topology (YAML)
└── docs/reference/                              # Detailed reference docs
```

**Important:** `extensions/` is a git submodule pointing to the `realms-extensions` repository. Changes to extensions must be committed/pushed there first, then the submodule ref updated in `realms`.

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

This is the standard deployment path for staging and production. It uses two workflows in sequence.

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
| `artifact_version` | `build`, `latest`, or semver | `build` | WASM artifact source |

> **GOTCHA 1:** Setting `canister=frontend` will fail with "Missing artifact URLs in manifest" because the on-chain installer expects both backend and frontend URLs in the manifest. Always use `canister=both` with `deploy_mode=upgrade` — the upgrade is safe and won't wipe data.

> **GOTCHA 2:** The `deploy-files.yml` `environment` parameter must match the target environment. If you're deploying to demo realms, use `-f environment=demo`. The default is `staging`. Each environment has its own file_registry canister — publishing to the wrong one means the realm won't see updated extensions.

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

| Canister | Demo | Staging |
|----------|------|---------|
| file_registry | `vi64l-3aaaa-aaaae-qj4va-cai` | `iebdk-kqaaa-aaaau-agoxq-cai` |
| Agora backend | `3bohd-2yaaa-aaaac-qcyla-cai` | `ihbn6-yiaaa-aaaac-beh3a-cai` |
| Agora frontend | `3gpbx-xaaaa-aaaac-qcylq-cai` | `iaalk-vqaaa-aaaac-beh3q-cai` |
| Dominion backend | `h5vpp-qyaaa-aaaac-qai3a-cai` | — |
| Dominion frontend | `gzya5-jyaaa-aaaac-qai5a-cai` | — |
| Syntropia backend | `2lbfz-yiaaa-aaaac-qcyma-cai` | — |
| Syntropia frontend | `2madn-vqaaa-aaaac-qcymq-cai` | — |

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
- **Never use `canister=frontend` alone** in `deploy-mundus` — it fails. Use `canister=both` with `deploy_mode=upgrade`.

## Further Reading

- `docs/reference/DEPLOYMENT_GUIDE.md` — Full deployment guide (4-script bundled flow)
- `docs/reference/RUNTIME_EXTENSION_STAGING_DEPLOY.md` — Layered deploy runbook
- `docs/reference/EXTENSION_ARCHITECTURE.md` — Extension lifecycle
- `README.md` § Layered Deployment Architecture — High-level overview
- `cli/README.md` — CLI command reference
