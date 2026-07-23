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
│   ├── publish-build.yml            # Build + publish artifacts into file_registry + Casals
│   ├── rollout.yml                   # Upgrade/reinstall realm+infra canisters via Casals
│   ├── deploy-mundus.yml             # Off-chain realm deploy (fast path; test/demo/staging)
│   ├── casals-upgrade.yml            # Upgrade the Casals orchestrator itself
│   └── deploy-files.yml              # Publish extensions/codices into file_registry
├── casals/                           # Casals orchestrator engine (git submodule)
├── casals-config/                    # Realms-owned Casals objects (arrangements, sheet)
├── scripts/
│   └── publish_build.py              # Build+publish engine used by publish-build.yml
├── deployment-descriptors/           # Network topology (YAML)
└── docs/reference/
```

`extensions/` is a git submodule. Commit/push there first, then update the ref in `realms`.

---

## Deploying Code Changes

Visual overview (decision tree): [`.AGENTS/realms-deployment-paths.svg`](.AGENTS/realms-deployment-paths.svg) — paths **P1**–**P6** (see diagram footer).

### Choose your path first

**Default for agents:** if you changed code under a realm canister (`src/realm_frontend/`,
`src/realm_backend/`) and need to see it live on test/demo/staging, use **`realms mundus
deploy`** (~90s). Do **not** start with Casals for routine UI/backend iteration — the
Casals frontend rollout copies ~109 asset files in small batches and takes several minutes
per realm.

| Goal | Path | Typical time |
|---|---|---|
| **Realm UI or backend change** (Agora, Dominion, Syntropia) | `realms mundus deploy` with `--version build` | ~90s |
| **Runtime extension bundle** (`extensions/*/frontend-rt/`) | `deploy-files` → install, **or** [direct runtime install](#direct-runtime-install-no-file-registry) | ~26s via registry; direct path skips registry |
| **Registry / installer / other infra** during dev | `scripts/infra_dev_deploy.sh` or direct `dfx deploy` | ~2–5 min |
| **Pre-merge / make Casals authoritative** | `publish-build` → `rollout` | several min |

### What changed?

| What changed | Dev iteration (use this) | Authoritative (pre-merge only) |
|---|---|---|
| **Frontend** (`src/realm_frontend/`) | `mundus deploy --canister frontend --version build` | `publish-build` (`component=frontend`) → `rollout` (`scope=frontend`) |
| **Backend** (`src/realm_backend/`) | `mundus deploy --canister backend --version build` | `publish-build` (`component=both`) → `rollout` (`scope=backend`) |
| **Extension** (`extensions/`) | `deploy-files` → re-install the extension | `deploy-files` → rollout (or re-install) |

### Fast realm deploy (mundus) — default

Builds from your **local checkout**, uploads artifacts, and upgrades the target realm
canister(s) via the registry installer. No git push required.

```bash
export TERM=xterm
export DFX_WARNING=-mainnet_plaintext_identity

# Frontend-only, staging Agora (~90s)
realms mundus deploy deployment-descriptors/staging-mundus-layered.yml \
  --realm agora --canister frontend \
  --skip-extensions --codices none \
  --version build

# Same for test
realms mundus deploy deployment-descriptors/test-mundus-layered.yml \
  --realm agora --canister frontend \
  --skip-extensions --codices none \
  --version build
```

| Flag | Notes |
|---|---|
| `--version build` | **Required for local/un-pushed changes** — compiles from the repo checkout |
| `--version latest` | Pulls artifacts from the latest GitHub release — **will not include your local edits** |
| `--canister frontend` / `backend` | Scope to what changed; omit both flags to redeploy both |
| `--skip-extensions` | Skip extension/codex install when you only changed realm frontend/backend |
| `--realm agora` | One realm instead of all three in the descriptor |

Descriptors: `deployment-descriptors/test-mundus-layered.yml`, `staging-mundus-layered.yml`,
`demo-mundus-layered.yml` (each sets the network).

### Casals rollout (pre-merge / authoritative)

Use Casals when you need the environment's **authorized-WASM catalog** updated — e.g.
before merge, or to roll the same artifact to all realms at once. See "Casals — On-Chain
Deploy & Upgrade" below for the full reference.

```bash
git add . && git commit -m "fix: describe change" && git push origin main

# 1. Publish the current main checkout as a snapshot into test's registry + catalog
gh workflow run publish-build.yml \
  -f environment=test -f family=realm -f component=both \
  -f from_main=true -f update_catalog=true

# 2. Roll it out (scope to what changed; upgrade preserves state)
gh workflow run rollout.yml \
  -f environments=test -f targets=all-realms -f scope=both \
  -f mode=upgrade -f version=main
```

Scope as narrowly as possible: `scope=frontend` skips the backend; `targets=dominion`
does one realm instead of all three.

**Before merge**, align Casals with what you deployed off-chain via mundus:

```bash
python3 scripts/publish_build.py --environment staging --family realm \
  --component frontend --from-main --identity deployer
realms rollout -e staging -t agora -s frontend -v main \
  --identity deployer --execute --yes
```

### Environments

| Environment | Domain |
|---|---|
| Test | `<canister_id>.icp0.io` |
| Demo | `<canister_id>.icp0.io` |
| Staging | `<canister_id>.icp0.io` |

---

## Deploying Extension Changes

Extensions/codices are published into the `file_registry` (via `deploy-files.yml` or
`realms files`), then installed by the realm backend pulling them from the registry.

```bash
# 1. Build
cd extensions/extensions/<ext_id>/frontend-rt && npm run build && cd -

# 2. Push submodule
cd extensions && git add -A && git commit -m "feat(<ext_id>): change" && git push origin main && cd ..

# 3. Update submodule ref
git add extensions && git commit -m "chore: bump extensions" && git push origin main

# 4. Publish to file_registry (specific extension, or omit --extensions for all)
gh workflow run deploy-files.yml -f scope=extensions-only -f environment=test -f extensions=<ext_id>

# 5. Install it on the realm (see "Fast Remote Extension Deploy" below for the direct call),
#    or for a fresh full realm, the rollout's active arrangement reinstalls every extension.
```

### `deploy-files.yml` Parameters

| Parameter | Options | Default | Notes |
|---|---|---|---|
| `environment` | `test`, `staging`, `demo` | `staging` | |
| `scope` | `all`, `extensions-only`, `codices-only`, `branding-only` | `all` | `branding-only` publishes the demo realms' logo/background (see Branding below) |
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

> **Two deploy paths on non-production:** authoritative Casals (`publish-build.yml` +
> `rollout.yml`) and fast off-chain (`deploy-mundus.yml` or `realms mundus deploy`).
> `deploy-files.yml` publishes extension/codex bundles into `file_registry` for either path.

Casals is an **on-chain orchestrator** that owns the realm canisters and upgrades
them for us. Instead of an off-chain CI job installing WASMs, Casals pulls the
artifacts from `file_registry` and installs them itself, with **automatic
snapshot → install → verify-hash → rollback-on-failure** built in.

There are exactly **two steps**:

1. **Publish Build** — build the artifacts, upload them into `file_registry`, and
   register ("authorize") them in Casals. Nothing is deployed yet.
2. **Rollout** — tell Casals to upgrade (or reinstall) the chosen canisters to a
   published version.

**Casals is deployed and wired on all three environments** (`test`, `demo`, `staging`):
each one's realm and infra canisters are registered in Casals. Orchestra canisters are
controlled by **Casals + CycleOps**; on **test/staging**, the **`deployer`** identity
remains a co-controller so you can use the [fast infra deploy](#fast-infra-deploy-dev-only)
path during development. Publishing builds and authoritative rollouts still go through
Casals. New-realm *provisioning* still has a dormant off-chain code path in the
installer (gated by `provision_via_casals`, default off), but it is not wired to any
active workflow.

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

### What each deploy path upgrades

After an off-chain redeploy, demo/staging can still show an old **Realm Registry**
footer (e.g. `0.3.7`) while test shows `0.4.0` — even though the three realms were
upgraded. That is expected: the footer is **`realm_registry_frontend`** (infra), not
the realm apps.

| Component | Off-chain (`deploy-mundus` / `realms mundus deploy`) | Casals (`publish-build` → `rollout`) |
|---|---|---|
| Realm backends + frontends (Dominion, Agora, Syntropia) | Yes | Yes |
| Extensions/codices on realms | Yes (manifest + `file_registry`) | Yes (arrangement) |
| **Realm registry** (backend + frontend — `test`/`demo`/`staging`.realmsgos.org) | **No** (mundus) — **Yes** via [`scripts/infra_dev_deploy.sh`](#fast-infra-deploy-dev-only) | Yes (`family=registry`, target `realm-registry`) |
| Installer, `file_registry`, marketplace, dashboard | **No** (mundus) — **Yes** via [`scripts/infra_dev_deploy.sh`](#fast-infra-deploy-dev-only) | Yes (`all-infra` or per-family) |

Notes:

- Mundus descriptors only list `type: realm` entries. The registry backend is used
  to *enqueue* deploy jobs; it is **not** upgraded by mundus deploy.
- `artifact_version=latest` in mundus deploy refers to **realm** GitHub-release
  artifacts, not registry/infra.
- The registry footer version ≠ individual realm WASM version. Realm cards’
  “updated X ago” is catalog metadata, not proof of realm code version.
- To align demo/staging registry UI with test after a mundus realm deploy, publish
  and roll out the **`registry`** family (Casals path, `mode=upgrade`).

```bash
# Per environment (example: staging)
gh workflow run publish-build.yml \
  -f environment=staging -f family=registry -f component=both -f version=0.4.0

gh workflow run rollout.yml \
  -f environments=staging -f targets=realm-registry -f scope=both \
  -f mode=upgrade -f version=0.4.0
```

Repeat for `demo`. Or locally after publish:

```bash
realms rollout -e staging,demo -t realm-registry -s both -m upgrade -v 0.4.0 \
  --identity deployer --execute --yes
```

### Fast infra deploy (dev only)

While developing registry / installer / other infra, skip Casals publish + rollout and
**deploy directly with `dfx`** from the repo root (~2–5 min per component). This updates
the live canister code immediately but does **not** update the Casals authorized-WASM
catalog — run the full Casals path before merge.

**Setup (once per shell):**

```bash
export TERM=xterm
export DFX_WARNING=-mainnet_plaintext_identity
dfx identity use deployer
```

**Deploy:**

```bash
# Registry backend only (~2–3 min) — e.g. draft APIs, provision_via_casals
scripts/infra_dev_deploy.sh -e staging -f registry -c backend

# Registry frontend only (~3–5 min) — e.g. wizard UI, version picker
scripts/infra_dev_deploy.sh -e staging -f registry -c frontend

# Both
scripts/infra_dev_deploy.sh -e staging -f registry -c both

# Other infra families: installer | file-registry | marketplace | dashboard
scripts/infra_dev_deploy.sh -e test -f installer -c backend
```

Equivalent raw commands (registry backend example):

```bash
export TERM=xterm DFX_WARNING=-mainnet_plaintext_identity
export PATH="$PWD/.venv-basilisk/bin:$PATH"
export CANISTER_CANDID_PATH=src/realm_registry_backend/realm_registry_backend.did
export DFX_NETWORK=staging
dfx build realm_registry_backend --network staging
dfx canister install 7wzxh-wyaaa-aaaau-aggyq-cai --network staging --mode upgrade \
  --wasm .basilisk/realm_registry_backend/realm_registry_backend.wasm.gz
npm run build --workspace=realm_registry_frontend
dfx deploy realm_registry_frontend --network staging --yes
```

**When to use which path** (see also [Choose your path first](#choose-your-path-first) at the top):

| Situation | Path |
|---|---|
| Realm UI/backend change (Agora, Dominion, …) | `realms mundus deploy` with `--version build` |
| Iterating on registry/wizard during development | `scripts/infra_dev_deploy.sh` |
| Pre-merge / making Casals authoritative | `publish_build.py` → `realms rollout` |

**Before merge**, align Casals with what you deployed off-chain (realm code):

```bash
python3 scripts/publish_build.py --environment staging --family realm \
  --component frontend --from-main --identity deployer
realms rollout -e staging -t agora -s frontend -v main \
  --identity deployer --execute --yes
```

To sync **registry** UI after a mundus deploy (footer version, etc.):

```bash
python3 scripts/publish_build.py --environment staging --family registry \
  --component both --from-main --identity deployer
realms rollout -e staging -t realm-registry -s both -m upgrade -v main \
  --identity deployer --execute --yes
```

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
# Trigger manually (same workflow as a release, with from_main):
gh workflow run publish-build.yml -f environment=test -f family=realm \
  -f component=both -f from_main=true

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
```bash
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
  -f mode=upgrade -f version=0.4.0
```

| `rollout` flag / `rollout.yml` input | Options | Default | Notes |
|---|---|---|---|
| `-e` / `environments` | comma list or `all` | `test` | Skips envs with no Casals |
| `-t` / `targets` | stand names, `all-realms`, `all-infra`, `all` | — | required |
| `-s` / `scope` | `backend`, `frontend`, `both` | `both` | |
| `-m` / `mode` | `upgrade`, `reinstall` | `upgrade` | `reinstall` **wipes state** |
| `-v` / `version` | `main`, `latest`, or semver | `latest` | `main` = newest main snapshot |
| `--execute` / `execute` | flag / bool | on | Always executes — no dry-run mode |
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
  by **Casals** plus **CycleOps** (`cpbhu-5iaaa-aaaad-aalta-cai`, for cycle top-ups).
  On **test/staging**, **`deployer`** (`ah6ac-cc73l-...`) is also a co-controller so
  [`scripts/infra_dev_deploy.sh`](#fast-infra-deploy-dev-only) can upgrade infra directly
  during development. Casals remains the authoritative upgrade path before merge.
- **Casals canisters**: controlled by `ah6ac-cc73l-...` (the `my_dev_identity_1` /
  `deployer` key), the dedicated CI key, and a conductor Internet Identity.
- **CI identity**: workflows use the **`CASALS_CI_PEM`** secret (a controller of all
  three Casals), falling back to `IC_IDENTITY_PEM` if it is unset. To change a
  controller list, call Casals' admin-only `set_canister_controllers` (it refuses to
  drop Casals from the list unless you pass `force`).

### Catalog / self-service upgrade interaction

- Rollout **never** touches the realm version catalog, so it can't interfere with
  the in-realm self-service upgrade path.
- Publish Build only updates the catalog when `--update-catalog` is set, so by
  default it won't feed an env a `fileregistry://` URL it can't use.
- `release.yml` (semver release artifacts) is independent of rollout.

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
4. **Frontend builds need candid declarations.** `publish_build.py` copies the
   committed `src/declarations/*` into each frontend's `src/lib/declarations/`
   before `vite build` (the realm frontend imports `$lib/declarations/realm_backend`).
   Don't remove that step or the main-snapshot build fails to resolve the import.
5. **Large files use incremental finalize.** Uploads over ~200 KB are chunked, and
   the CLI finalizes them with `finalize_chunked_file_step` (batched, on-chain
   hashing skipped, local sha256 passed in). The one-shot `finalize_chunked_file`
   blows the 40 B-instruction limit (`IC0522`) on multi-MB WASMs — don't switch back.
6. **Cycle autopilot is not guaranteed on.** Casals can auto-top-up from its treasury,
   but autopilot may be disabled on an env, and it never *restarts* a canister that
   already stopped from cycle starvation. A `reinstall` won't start a stopped frontend
   either (you'll see HTTP 503 "Response Verification Error"). Fix: top up + call
   `start_canister`, then re-`provision_assets`. Check balances with `casals cycles -e test`.

See `docs/reference/CASALS_ROLLOUT.md` for the full runbook (migrating a realm,
authorization model, cycle budget).

---

## Realm config via Casals arrangements (branding, registration, runtime flags)

A sheet rollout stands up the canisters (code); a Casals **arrangement** configures
them afterwards (state). Realms-owned arrangements live in
`casals-config/arrangements/` and are **generated** — edit deployment-descriptors
`parameters` and realm manifests, then re-run `python3 casals-config/_gen_arrangements.py`
(never hand-edit the JSON). One arrangement per environment (`test`, `staging`, `demo`);
`realms rollout` upserts `casals-config/arrangements/<env>.json` before applying it.
JSON. Variants:

| Arrangement | Scope | Use |
|---|---|---|
| `test` | all 3 realms, **full** extension set | full-fidelity test env |
| `test-lite` | **Dominion only**, core extensions | fast single-realm iteration |
| `test-lite-all` | **all 3 realms**, core extensions | proves a full sheet reinstall end-to-end, fast |

Each realm gets an ordered set of steps (all `(text)->(text)` calls on the realm
backend): `set_canister_config_json` (runtime flags + file-registry / frontend /
marketplace ids) → `update_realm_config` (name / manifesto / welcome message) →
`register_realm_from_registry` (registry) → `install_branding_from_registry` →
`install_codex_from_registry` → `install_extension_from_registry` (per extension).
Seed/activate an arrangement via `casals-upgrade.yml -f seed_arrangement=<name>`; only
one is active at a time (seeding deactivates the others).

> The **welcome message** is rendered by the `welcome` extension — it's in the full
> `test` set but **not** in the lite extension set, so on `test-lite`/`test-lite-all`
> the message is stored in config but has no UI. Add `welcome` to `LITE_EXTENSIONS`
> (or use `test`) if you need it shown.

### Branding (decentralized)

Branding is **fully decentralized** — no central server. The create-realm wizard
uploads the user's logo/background straight from the browser to the `file_registry`
canister (`file-registry-client.js`), and the deploy manifest references those
registry paths. The realm backend then pulls them and writes them to its own frontend
asset canister via `install_branding_from_registry` (served same-origin at
`/custom/logo.png`, `/custom/background.png`). This survives a frontend `reinstall`
because Casals re-grants the backend `Commit` on the (wiped) asset canister during
provisioning.

For the demo realms, publish their source images into the registry first:

```bash
realms files publish-branding --network test          # or: deploy-files.yml -f scope=branding-only
```

Optimize source PNGs before publishing (logos ~25 KB, backgrounds <1 MB) so they stay
under the file_registry per-file instruction limit.

### Registration in the realm registry

Realms must register with the `realm-registry` to appear on its frontend (otherwise
"No Realms"). The registry keys each realm on `ic.caller()` (the realm backend's id),
so registration is idempotent.

- **User / wizard realms** register automatically — the `realm_installer` calls
  `registry.register_realm(...)` at finalization.
- **Demo / sheet realms** are deployed directly by Casals (bypassing the installer),
  so the **arrangement** registers them via the backend's
  `register_realm_from_registry(text)` step. To register an already-deployed realm
  out-of-band, call `register_realm_with_registry` on its backend directly.

## Full Platform Re-deployment (clean reinstall via Casals)

Reinstalling the whole orchestra is three stages. Each stage completes before the next.

```bash
# Stage 1: Publish all artifacts (realm + infra) from main into the env's registry+catalog
gh workflow run publish-build.yml -f environment=test -f family=realm -f component=both -f from_main=true -f update_catalog=true
# repeat per family as needed: installer, registry, dashboard, marketplace, file-registry

# Stage 2: Publish extension/codex bundles into file_registry
gh workflow run deploy-files.yml -f environment=test -f scope=all

# Stage 3: Reinstall via Casals, then the seeded arrangement reinstalls extensions/codices
#          and applies runtime config. (reinstall WIPES state — intentional for a clean slate.)
gh workflow run rollout.yml \
  -f environments=test -f targets=all -f scope=both \
  -f mode=reinstall -f version=main -f include_infra_reinstall=true
```

The active arrangement (seeded via `casals-upgrade.yml` `-f seed_arrangement=...` from
`casals-config/arrangements/`) is what reinstalls extensions/codices and applies runtime
flags after the canisters come up. See "Realm config via Casals arrangements" below for
the arrangement variants (`test`, `staging`, `demo`, plus `test-lite` / `test-lite-all`
for fast test iteration) and per-realm steps.

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

**Realm frontend/backend redeploy** (changes to `src/realm_frontend/` or
`src/realm_backend/`, not just a runtime extension bundle): use
[`mundus deploy`](#fast-realm-deploy-mundus--default) with `--version build` (~90s).
See the top of this doc — do not default to Casals for iteration.

```bash
realms mundus deploy deployment-descriptors/staging-mundus-layered.yml \
  --realm agora --canister frontend \
  --skip-extensions --codices none --version build
```

This handles frontend WASM + branding; add `--extensions <ext_id>` when you also need
to reinstall extensions. Use `--version latest` only when deploying a tagged release
artifact, not local edits.

**Constraints:**
- The extension bundle must stay under ~200KB for `files publish` to succeed (file_registry instruction limit). Keep heavy libraries (leaflet, h3-js) loaded at runtime via `fetch()` + `eval()` instead of bundling them.
- The extension `version` in `manifest.json` must match the version in the `dfx canister call`. Bump the version when you need to force cache invalidation.
- After finishing iteration, commit the changes to the submodule and update the ref in `realms` (see "Deploying Extension Changes" above).

### Direct runtime install (no file registry, no Casals installer)

When iterating on **one specific realm** and the file registry is unavailable,
out of cycles, or the Casals installer is slow/stuck, push packages straight to
the realm canister with `dfx`. No publish step, no ICP for the registry, no
installer polling.

| What changed | Direct command | Notes |
|---|---|---|
| **Realm backend** (`src/realm_backend/`) | Build WASM locally → `dfx canister install --mode upgrade` | ~25s; preserves canister state |
| **Extension** (backend + frontend bundle) | `realms extension runtime-install` | Backend via `install_extension`; frontend via asset-canister `store` |
| **Codex** (`kind: codex` packages) | `realms codex runtime-install --run-init` | Backend via `install_extension`; runs codex `init` hook |

> **Not the same as `mundus deploy`.** `realms mundus deploy --version build`
> builds locally but still submits to the Casals installer canister (artifact
> upload + verify polling). Use that when the installer is healthy (~90s). Use
> the pure `dfx` path below when you need to skip the installer entirely.

**Setup (once per session):**

```bash
export TERM=xterm-256color DFX_WARNING=-mainnet_plaintext_identity
export PATH="$PWD/.venv-basilisk/bin:$PATH"   # basilisk refuses to build outside this venv
export CANISTER_CANDID_PATH=src/realm_backend/realm_backend.did
dfx identity use deployer   # or my_dev_identity_1 on test
```

**Staging canister IDs:**

| Realm | Backend | Frontend |
|---|---|---|
| Syntropia | `jnope-2yaaa-aaaac-beh4a-cai` | `jkpjq-xaaaa-aaaac-beh4q-cai` |
| Agora | `ihbn6-yiaaa-aaaac-beh3a-cai` | `iaalk-vqaaa-aaaac-beh3q-cai` |

**Full example — justice courts on staging Syntropia (verified Jul 2026):**

```bash
cd /path/to/realms

# 1. Backend WASM — build locally, upgrade directly (~25s)
python -m basilisk realm_backend src/realm_backend/main.py
gzip -c .basilisk/realm_backend/realm_backend.wasm > /tmp/realm_backend.wasm.gz
dfx canister install jnope-2yaaa-aaaac-beh4a-cai \
  --wasm /tmp/realm_backend.wasm.gz --mode upgrade --network staging

# 2. Codex (seeds court hierarchy via init → seed_justice)
realms codex runtime-install \
  --canister jnope-2yaaa-aaaac-beh4a-cai \
  --source-dir codices/codices/syntropia \
  --network staging --run-init

# 3. Extension (backend + frontend bundle + initialize hook)
realms files build --extensions justice_litigation   # build frontend-rt/dist first
realms extension runtime-install \
  --canister jnope-2yaaa-aaaac-beh4a-cai \
  --source-dir extensions/extensions/justice_litigation \
  --frontend-canister jkpjq-xaaaa-aaaac-beh4q-cai \
  --network staging
```

Repeat steps 2–3 for Agora (`ihbn6-yiaaa-aaaac-beh3a-cai` / `iaalk-vqaaa-aaaac-beh3q-cai`)
with `--source-dir codices/codices/agora`.

**What the pure `dfx` backend upgrade skips (usually fine on staging):**

- Casals protective snapshot / automatic rollback
- `set_canister_config` post-deploy (frontend ID, version string, test flags — these
  persist from prior deploys; `--mode upgrade` keeps state)
- Branding upload + `/custom/` pinning on the frontend canister

**When to use which path:**

| Situation | Use |
|---|---|
| Single-realm dev iteration, registry or installer down | **Direct runtime install** (this section) |
| Normal fast iteration when installer is healthy | [`mundus deploy`](#fast-realm-deploy-mundus--default) (~90s) |
| Extension-only change, registry healthy | [Fast Remote Extension Deploy](#fast-remote-extension-deploy-26s) above |
| Quarters / multi-realm / pre-merge authoritative deploy | `deploy-files` → registry install → Casals rollout |

Direct install only affects the canister you target. It does **not** update
the file registry catalog — run `deploy-files` before merge so other realms and
quarter bootstrap can pull the new packages.

**Gotchas (learned staging Jul 2026):**

1. **Deploy to the realm you're actually viewing.** Capital Syntropia/Agora
   canister IDs (table above) are *not* manual-test or quarter realms created
   via the registry wizard. If the UI shows e.g. `ManualTest410Syntropia`, look
   up its backend/frontend IDs first:

   ```bash
   dfx canister call 7wzxh-wyaaa-aaaau-aggyq-cai list_realms '()' \
     --network staging --query | grep -i manualtest
   ```

   Then pass those IDs to `--canister` / `--frontend-canister`.

2. **Manifest version ≠ UI version after direct extension install.** The info
   tooltip reads `manifest.json` (e.g. `0.4.0`) but the tab bar comes from the
   **frontend JS bundle**. The loader resolves the bundle path via
   `get_extension_frontend_info`, which historically read stale `_source.json`
   from an earlier registry install (e.g. still pointing at `0.3.8`). Symptom:
   new backend works, tooltip shows new version, UI looks unchanged.

   **Fix:** bump `version` in `manifest.json`, upload the bundle to
   `/ext/{id}/{new-version}/frontend/dist/index.js` on the realm **frontend**
   asset canister, then ensure `_source.json` matches (backend now syncs this
   on `install_extension`; older backends may need a one-off patch):

   ```bash
   # Verify what the loader will use:
   dfx canister call <backend-id> get_extension_frontend_info \
     '("{\"extension_id\": \"justice_litigation\"}")' --network staging --query

   # Should return the new version. If not, patch _source.json:
   dfx canister call <backend-id> install_extension \
     '("{\"extension_id\":\"justice_litigation\",\"files\":{\"_source.json\":\"{\\\"registry_canister_id\\\":\\\"iebdk-kqaaa-aaaau-agoxq-cai\\\",\\\"version\\\":\\\"0.4.0\\\"}\"}}")' \
     --network staging
   ```

   Hard-refresh the browser (Ctrl+Shift+R). In DevTools → Network, confirm the
   request is `/ext/justice_litigation/0.4.0/frontend/dist/index.js`, not an
   older version.

3. **Codex direct install and emoji.** IC Python's narrow unicode build rejects
   emoji in extension/codex sources during `open(..., 'w')`. The CLI strips
   astral characters on upload; registry installs are unaffected.

4. **Manual-test realms need all three steps.** Backend WASM (if ggg/codex hooks
   changed), codex `runtime-install --run-init`, and extension
   `runtime-install --frontend-canister` — same as capital, just different
   canister IDs.

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

dfx 0.30.2 crashes with `ColorOutOfRange` (`panicked at src/dfx/src/main.rs: Failed to set stderr output color`) unless the terminal is set up correctly. Always export these before running any `dfx` command:

```bash
export TERM=xterm
export DFX_WARNING=-mainnet_plaintext_identity
```

The first fixes the color panic, the second suppresses the plaintext identity warning that blocks execution on `test`/`staging` networks.

**If the panic still occurs** (including inside wrappers like `realms files publish`, which shells out to dfx): the shell has `NO_COLOR` and/or `FORCE_COLOR` set, and dfx panics on the conflict. **Unset both** and use a color-capable TERM:

```bash
env -u NO_COLOR -u FORCE_COLOR TERM=xterm-256color DFX_WARNING=-mainnet_plaintext_identity \
  realms files publish --network staging --extensions-only --extensions <ext_id>
```

Counter-intuitively, `NO_COLOR=1` / `TERM=dumb` does **not** reliably avoid the panic — dfx needs a real color terminal, not a colorless one.

---

## Debugging Python canisters (`__browse__` / `__shell__`)

Realm backends (and other Basilisk canisters built with
[`basilisk`](https://github.com/smart-social-contracts/basilisk) /
[`ic-basilisk-toolkit`](https://github.com/smart-social-contracts/ic-basilisk-toolkit))
can expose two agent-oriented endpoints. **Use them liberally** for
investigating live canister state — they are the fastest way to answer “what is
actually on-chain?” without redeploying or adding one-off query methods.

Enable at build time (realm backend already has both):

```python
__basilisk_features__ = ["shell", "browse"]
```

Full reference: [`../basilisk/AGENTS.md`](../basilisk/AGENTS.md).

### `__browse__` — read-only inspection (query, cheap)

Structured JSON access to stable maps/sets/vecs. Good first step when you need
counts, keys, or individual records without writing Python.

```bash
export TERM=xterm DFX_WARNING=-mainnet_plaintext_identity
dfx identity use my_dev_identity_1

# Schema of stable structures
dfx canister call <canister_id> __browse__ \
  '("{\"action\": \"schema\"}")' --query --network ic

# List keys / fetch one item (see basilisk AGENTS.md for actions)
dfx canister call <canister_id> __browse__ \
  '("{\"action\": \"len\", \"map\": \"User\"}")' --query --network ic
```

No special permission beyond ordinary query access (subject to any endpoint
guard you added). Prefer `__browse__` over ad-hoc `status()` fields when you
need entity-level detail.

### `__shell__` — Python REPL inside the canister (update)

Executes arbitrary Python against the live `ggg` entity model (`User`,
`Quarter`, `Realm`, …). Persistent namespace **per caller principal** — variables
from one call are visible on the next.

```bash
dfx canister call <canister_id> __shell__ \
  '("from ggg import User; print(len(list(User.instances())))")' \
  --network ic --identity my_dev_identity_1
```

Gated by `@require(Operations.SHELL_EXECUTE)`, but **IC controllers bypass** all
permission checks (`core/access.py`). So `__shell__` works when your dfx
principal is in that canister's **controller list**.

| Canister | Typical controllers | `__shell__` with `my_dev_identity_1` |
|---|---|---|
| Capital realm backend | Casals + CycleOps + deployer (varies by env) | Usually **yes** |
| Auto-provisioned quarter | Casals + capital + inherited capital controllers | Usually **yes** (after Casals provision) |
| Casals-managed orchestra stand | Casals + CycleOps only | **no** (use Casals relay below) |

When you are not a controller, relay through Casals (Casals *is* a quarter
controller):

```bash
dfx canister call <casals_id> canister_exec \
  '("{\"canister\":\"agora-quarter-2\",\"code\":\"from ggg import User; print(len(list(User.instances())))\"}")' \
  --network ic --identity my_dev_identity_1
```

### Quarter scaling and controllers

Casals **inherits the stand commander's full IC controller list** when minting a
canister (`lifecycle._resolve_provision_controllers`): new quarters get Casals,
CycleOps (when enabled), the capital backend as commander, plus every controller
the capital already has (deploy key, etc.). No separate post-provision step.

Existing quarters provisioned before this change keep their old controller set
until updated manually or re-provisioned.

---

## Gotchas

1. **`deploy-files` `environment` must match target.** Publishing to `staging` (default) won't be visible to `demo` or `test` realms.
2. **Any change inside `extensions/` (including manifest.json edits) requires `deploy-files` before installing.** Extensions are pulled from the file registry — if you skip `deploy-files`, the registry still has stale manifests/bundles and the install uses old data. Always: `deploy-files` → wait for green → install / rollout.
3. **Agora is prone to timeouts.** Retry a single failed realm: `-f targets=agora`.
4. **`reinstall` wipes all state.** Use `upgrade` unless you want a clean slate.
5. **Frontend bundles are built by CI.** The `deploy-files` workflow runs `realms files build` to compile `frontend-rt/` sources before publishing. No need to commit `dist/index.js`.

---

## Rules

- **Default deploy path for realm changes:** `realms mundus deploy` with
  `--version build` (~90s). Casals (`publish-build.yml` + `rollout.yml`) is for
  **pre-merge / authoritative** rollouts only — frontend rollout there is slow
  (several minutes per realm). **Fast infra:** `scripts/infra_dev_deploy.sh` or direct
  `dfx deploy` for registry/installer during development. **Extensions:**
  `deploy-files.yml` to publish bundles into the file registry.
- **Visually verify every UI change before reporting back.** After deploying a frontend or extension change, open the page in the browser and confirm the result matches the requirements. Do not report completion until you have checked the deployed page yourself. If the visual check reveals issues, fix and redeploy in a loop until the result is correct.
- Do not commit unless explicitly told to do so.
- Always use `mode=upgrade` for production/test deploys (`reinstall` wipes state).
- Always scope rollouts as narrowly as possible:
  - **Target:** `-f targets=agora` — roll out one realm, not `all-realms`.
  - **Scope:** `-f scope=frontend` or `-f scope=backend` — skip the half you didn't change.
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

- [`.AGENTS/realms-deployment-paths.svg`](.AGENTS/realms-deployment-paths.svg) — Deployment decision tree (Casals, mundus, extensions, release)
- `AGENTS.md` — Agent/operator guide (deploy paths, canister IDs, fast iteration)
- `docs/reference/CASALS_ROLLOUT.md` — On-chain (Casals) deploy & upgrade runbook
- `docs/reference/RUNTIME_EXTENSION_STAGING_DEPLOY.md` — Layered deploy runbook
- `docs/reference/EXTENSION_ARCHITECTURE.md` — Extension lifecycle
- `docs/reference/PRIVATE_DATA_SHARING.md` — End-to-end encrypted, consent-based data sharing for extensions (own entity + scope kind + `ctx.crypto`)
- `cli/README.md` — CLI command reference
