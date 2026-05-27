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
│   ├── deploy-infra.yml              # Infra canisters
│   ├── deploy-files.yml              # Publish extensions/codices
│   └── deploy-mundus.yml            # Deploy realm canisters
├── scripts/
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
- `docs/reference/RUNTIME_EXTENSION_STAGING_DEPLOY.md` — Layered deploy runbook
- `docs/reference/EXTENSION_ARCHITECTURE.md` — Extension lifecycle
- `cli/README.md` — CLI command reference
