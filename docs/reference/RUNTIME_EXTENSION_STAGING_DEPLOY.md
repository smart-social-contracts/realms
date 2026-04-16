# Deploying runtime-loaded extensions to staging — Path A (Dominion / realm1)

This runbook deploys the **Layer 2 (runtime extension frontends)** work
from [#168](https://github.com/smart-social-contracts/realms/issues/168)
onto a single staging realm. It is the "fast proof" path: the
realm_backend / realm_frontend code goes through the existing
GitHub Actions pipeline; the file_registry deploy + bundle publication +
runtime install of the extension are wrapped by
`scripts/deploy_runtime_extension_to_staging.sh`.

The plan deploys to **Dominion (realm1)** first because it already has
dedicated backend and frontend descriptors
(`deployments/staging-realm1-backend.yml`,
`deployments/staging-realm1-frontend.yml`). Once it works on Dominion,
the same script can be re-run against Agora (realm2) and Syntropia
(realm3) by changing `--realm-backend`.

## Prerequisites

- A `dfx` identity with controller rights on the staging canisters and
  cycles to create a new canister on staging:
  ```
  dfx identity use my-staging-identity
  dfx identity get-principal     # confirm
  dfx wallet --network staging balance
  ```
- A local checkout of `realms-extensions` next to `realms`:
  ```
  ~/dev/.../realms
  ~/dev/.../realms-extensions
  ```
  (or pass `--extensions-repo <path>` to the script).
- `node`, `npm`, `python3`, `curl`, `dfx` available locally.
- The branch `feat/layered-deployment` (or its merged-to-main equivalent)
  available so the GitHub Actions workflow can check it out.

## Step 1 — Deploy `realm_backend` code to Dominion

The new query method `get_extension_frontend_info` and the `_source.json`
write logic must be live on Dominion before the script's install step
can succeed.

1. Open the [`Deploy` workflow](https://github.com/smart-social-contracts/realms/actions/workflows/deployment.yml).
2. **Run workflow** with:
   - Descriptor: `deployments/staging-realm1-backend.yml`
   - Source: `checkout`
   - Commit: HEAD of `feat/layered-deployment` (e.g. `d2b23323`)
   - **Mode override: `upgrade`** (the descriptor default is `reinstall`,
     which would wipe stable storage including any installed extensions —
     do **not** use `reinstall` here).
3. Wait for the workflow to succeed.
4. Sanity-check from your shell:
   ```
   dfx canister --network staging call <dominion_realm_backend> list_runtime_extensions
   ```
   The response should include the new `sources` field
   (it may be `{}` until the next step).

## Step 2 — Publish the extension bundle and install it

Run the script. On the first run (or first time on a new network) it
also deploys `file_registry`.

```
cd realms
dfx identity use my-staging-identity

bash scripts/deploy_runtime_extension_to_staging.sh \
    --realm-backend <dominion_realm_backend_canister_id> \
    --network staging
```

What the script does (idempotently):

1. Locates `realms-extensions/extensions/test_bench/` and reads the
   version from its manifest.
2. Resolves `file_registry`'s canister id on staging via
   `dfx canister id file_registry --network staging`. If absent, runs
   `dfx deploy file_registry --network staging` to create one and prints
   the new id (record it!).
3. Builds `realms-extensions/extensions/test_bench/frontend-rt/` via
   `vite build --lib` → `dist/index.js`.
4. Uploads `manifest.json`, `backend/*.py`, and `frontend/dist/index.js`
   to `file_registry` under `ext/test_bench/<version>/...`, then
   `publish_namespace`.
5. Verifies the bundle is reachable over HTTP at
   `https://<file_registry>.icp0.io/ext/test_bench/<version>/frontend/dist/index.js`
   with correct MIME and CORS.
6. Calls
   `realm_backend.install_extension_from_registry(...)` so the realm
   records `_source.json`, then calls `get_extension_frontend_info` to
   confirm runtime discovery returns the right registry id + version.

If `file_registry` was newly created in step 2, add its canister id to
`dfx.json` so future deploys reuse it instead of creating duplicates:

```jsonc
"file_registry": {
  ...
  "remote": {
    "id": {
      "staging": "<paste_the_canister_id_here>"
    }
  },
  ...
}
```

(That edit is not done automatically — the script just prints a
reminder.)

## Step 3 — Deploy `realm_frontend` code to Dominion

1. Open the same `Deploy` workflow.
2. Run with:
   - Descriptor: `deployments/staging-realm1-frontend.yml`
   - Source: `checkout`
   - Commit: HEAD of `feat/layered-deployment`
   - Mode override: leave blank (frontend deploys are always reinstall
     of asset storage; the descriptor default is correct).
3. Wait for it to succeed.

## Step 4 — Smoke test in a real browser

Open Dominion's frontend (replace with the actual canister id, available
in the realm registry or in the deployment logs):

```
https://<dominion_realm_frontend>.icp0.io/extensions/test_bench
```

You should see:

- A green card titled **`test_bench (runtime-loaded)`** with a
  **`v0.1.3`** badge (matching the version you published).
- Two buttons:
  `extension_sync_call → test_bench.get_data` and
  `list_runtime_extensions`.

In devtools (Network tab), confirm:

- One request to
  `https://<file_registry>.icp0.io/ext/test_bench/0.1.3/frontend/dist/index.js`
  returns 200 with `Content-Type: application/javascript`.
- No CSP violations in the Console — the realm_frontend CSP allows
  `script-src` from `https://*.icp0.io`.

Click `extension_sync_call → test_bench.get_data`:

- **Anonymous browser:** response should be
  `Access denied: user 2vxsx-fae lacks permission 'extension.sync_call'`.
  This is the expected proof that the dynamic-imported bundle made a real
  inter-canister call to `realm_backend`.
- **Logged in via Internet Identity** with an admin or member profile:
  response should be the actual `get_data` payload.

## Re-running for new versions

Bumping `test_bench`'s version is now a one-liner:

```
# Edit realms-extensions/extensions/test_bench/manifest.json → bump version
bash scripts/deploy_runtime_extension_to_staging.sh \
    --realm-backend <dominion_realm_backend> \
    --network staging
# (the script reads --version from manifest.json by default)
```

No `realm_frontend` redeploy is needed — that's the whole point of
Layer 2.

## Re-running for Agora (realm2) and Syntropia (realm3)

Once the path is validated on Dominion, run the same script against the
other realms (after their `realm_backend` is also upgraded with the new
code via the corresponding `staging-realm{2,3}-backend.yml` descriptor):

```
bash scripts/deploy_runtime_extension_to_staging.sh \
    --realm-backend <agora_realm_backend>      --network staging
bash scripts/deploy_runtime_extension_to_staging.sh \
    --realm-backend <syntropia_realm_backend>  --network staging
```

Each call is idempotent — the bundle on `file_registry` is shared
across all three realms, only `install_extension_from_registry` is
realm-specific.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `realm_backend at <id> does not expose install_extension_from_registry` | Step 1 didn't run, or used `mode: reinstall` and lost state | Re-run Step 1 with `mode_override: upgrade` |
| `get_extension_frontend_info` returns `success:false, error:"No registry source recorded"` | Extension was installed before the `_source.json` code landed | Re-run the script (re-installs and writes `_source.json`) |
| Browser shows blank route or `Refused to load the script ... Content Security Policy` | `realm_frontend` CSP missing `https://*.icp0.io` in `script-src` | Confirm `static/.ic-assets.json5` was deployed in Step 3; rebuild + redeploy |
| HTTP 404 for `index.js` | `publish_namespace` not called, or version mismatch | Re-run script (publish is idempotent) |
| Loader works but `extension_sync_call` returns nothing | Loader still using anonymous actor | Confirm logged in via II; check `/+page.svelte` is using the authenticated `backend` store |
| New canister created on every run | `file_registry` canister id not recorded | Add `remote.id.staging` entry in `dfx.json` |
