# Per-environment Realms GOS product stacks

Realms maintains three IC **product environments** — `demo`, `staging`, and
`test` — each with its own canister set for the GOS **product surface**
(landing page, extension marketplace, and file registry). These are distinct
from the GaaS **portal** sites at `*.gos.earth` (registry wizard, Casals,
realm provisioning), which are owned by
[gos-as-a-service](https://github.com/smart-social-contracts/gos-as-a-service).

| Environment | IC network | Product domain | GaaS portal |
|---|---|---|---|
| demo | `demo` | `demo.realmsgos.org` | `https://demo.gos.earth` |
| staging | `staging` | `staging.realmsgos.org` | `https://staging.gos.earth` |
| test | `test` | `test.realmsgos.org` | `https://test.gos.earth` |

## Stack canisters

Each environment deploys four canisters (declared in root `dfx.json`):

| Canister | Role |
|---|---|
| `file_registry` | On-chain artifact store (extensions, codices, realm WASMs) |
| `file_registry_frontend` | Admin UI for the file registry (prebuilt from gos-as-a-service) |
| `marketplace_backend` | Extension/codex marketplace API (Basilisk Python) |
| `marketplace_frontend` | Product landing page + marketplace UI (SvelteKit static assets) |

Canister IDs for each network live in root `canister_ids.json` under the
matching network key (`demo`, `staging`, `test`).

## Environment config schema

Configs live in `environments/<name>.json` at the repo root:

```json
{
  "name": "demo",
  "network": "demo",
  "domain": "demo.realmsgos.org",
  "portal_url": "https://demo.gos.earth",
  "casals_url": "https://usukh-2yaaa-aaaae-agztq-cai.icp0.io",
  "realms_version": "main",
  "billing_service_principal": "",
  "canisters": [
    "file_registry",
    "file_registry_frontend",
    "marketplace_backend",
    "marketplace_frontend"
  ]
}
```

| Field | Description |
|---|---|
| `name` | Environment identifier (must match filename) |
| `network` | dfx network name (`demo`, `staging`, `test`) |
| `domain` | Custom product domain (`*.realmsgos.org`) |
| `portal_url` | Linked GaaS portal URL (`*.gos.earth`) — passed to the frontend as `VITE_PORTAL_URL` |
| `casals_url` | Realms GOS Casals frontend URL — passed to the frontend as `VITE_CASALS_URL` |
| `realms_version` | Version label baked into the frontend (`VITE_REALMS_VERSION`) |
| `billing_service_principal` | Optional principal for `set_billing_service_principal` on marketplace_backend |
| `canisters` | Ordered list of stack canisters (documentation; deploy always uses the full stack) |

Keep the schema minimal — add fields only when the deploy command needs them.

## CLI: `realms env deploy`

Deploy or upgrade the full product stack for one environment:

```bash
export DFX_WARNING=-mainnet_plaintext_identity
dfx identity use deployer

realms env deploy --env demo
realms env deploy --env staging --mode upgrade --yes
realms env deploy --env test --identity deployer
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--env` / `-e` | *(required)* | Environment name (`demo`, `staging`, `test`) |
| `--mode` / `-m` | `auto` | dfx deploy mode: `auto`, `install`, `upgrade`, `reinstall` |
| `--identity` | dfx default | dfx identity name or PEM path |
| `--yes` / `-y` | off | Skip confirmations (stale-id recreate, `reinstall` wipe) |
| `--skip-frontend-build` | off | Deploy existing `src/marketplace_frontend/dist/` without `npm run build` |
| `--domain` / `--no-domain` | `--domain` | Write `.well-known/ic-domains` before frontend build |

### Deploy steps

1. **Resolve canister IDs** — read from `canister_ids.json` / dfx; if an ID is
   missing or dead on the IC, create a replacement and update `canister_ids.json`.
2. **Deploy `file_registry`** — vendored WASM from `.external-wasms/`.
3. **Deploy `file_registry_frontend`** — fetches prebuilt dist via
   `scripts/fetch_gos_artifacts.py --what frontend`.
4. **Deploy `marketplace_backend`** — wires `file_registry_canister_id` (and
   billing principal when configured) via post-deploy update calls.
5. **Build `marketplace_frontend`** — `npm run build --workspace=marketplace_frontend`
   with `CANISTER_ID_MARKETPLACE_BACKEND`, `CANISTER_ID_FILE_REGISTRY`,
   `VITE_ENV_NAME`, `VITE_PORTAL_URL`, `VITE_CASALS_URL`, `VITE_REALMS_VERSION` (and
   `VITE_BILLING_SERVICE_URL` when set in config).
6. **Deploy `marketplace_frontend`** — asset canister from `dist/`.
7. **Custom domain prep** (when `--domain` and `domain` is set) — writes
   `src/marketplace_frontend/static/.well-known/ic-domains` before the build.

Re-running with default `--mode auto` upgrades in place without wiping state.
Use `--mode reinstall` only when you intentionally want a clean canister.

### Stale canister IDs

If `canister_ids.json` points at a wiped or deleted canister, `dfx canister
status` fails with "not found". The deploy command detects this, prints a clear
message, and offers to create a replacement (auto-approved with `--yes`). The
old ID is removed from `canister_ids.json` before `dfx canister create`.

If deploy fails mid-flight with a stale ID that was not caught, re-run with
`--yes` or pass `--mode reinstall` to wipe in-place state on an existing live
canister.

## CLI: `realms env status`

```bash
realms env status --env staging
```

Prints canister IDs from dfx / `canister_ids.json` plus a one-line
`dfx canister status` summary per stack canister.

## Custom domain (DNS)

After deploy, the marketplace frontend asset canister serves
`/.well-known/ic-domains` listing the environment domain (e.g.
`demo.realmsgos.org`). Complete setup manually:

1. **DNS** — add a CNAME record:
   ```
   demo.realmsgos.org  →  demo.realmsgos.org.icp1.io
   ```
   Alternatively use the A/AAAA records shown at
   [reg.icp0.io](https://reg.icp0.io) for your domain.

2. **Registration** — open [https://reg.icp0.io](https://reg.icp0.io) and
   register the domain against the `marketplace_frontend` canister ID printed
   at the end of deploy.

3. **Verify** — once DNS propagates, `https://<domain>/.well-known/ic-domains`
   should return the domain name and the site should load over HTTPS.

Until registration completes, use the default gateway URL:
`https://<marketplace_frontend_id>.icp0.io/`.

## Related commands

- `realms marketplace deploy` — deploy marketplace canisters only (optional
  `--with-registry`); does not manage per-env config or custom domains.
- `scripts/infra_dev_deploy.sh -f marketplace` — fast single-family iteration
  during development.
- GaaS portal deploy — see
  [gos-as-a-service](https://github.com/smart-social-contracts/gos-as-a-service)
  (`gaas deploy`); portal domains are `*.gos.earth`, not `*.realmsgos.org`.
