# Casals migration — operational rollout runbook

Status: ready to execute (gated on go-ahead). Companion to `CASALS_MIGRATION.md`.

This is the step-by-step procedure to switch a Realms environment over to Casals-driven
on-chain provisioning. It is **incremental and reversible**: the on-chain path is behind
the installer's `provision_via_casals` flag (off by default), so nothing changes until
you flip it, and you can flip it back.

> Conventions
> - Casals canister + identity use **icp-cli** (`icp ...`, identity `casals`).
> - Realms canisters use **dfx** / the `realms` CLI with your Realms controller identity.
> - JSON-in-text args must be escaped: `'("{\"key\":\"value\"}")'`.
> - Replace `<…>` placeholders. Known IDs are filled in where stable.

## 0. Decisions to lock before starting

1. **One Casals or one per env?** Realms `staging`/`demo`/`test` are all on IC mainnet.
   You can use **one** Casals with env-scoped Sections (e.g. `Deployments-staging`) or a
   separate Casals per env. Recommended: start with the **existing mainnet Casals**
   (`ip2wh-iyaaa-aaaao-bbaoq-cai`) and a single `Deployments` Section for the pilot env.
2. **Installer authorization (IMPORTANT).** The installer must create a Stand per realm.
   `create_stand` today requires a Casals **controller**. Two options:
   - **A — installer as Casals controller** (zero code change, broad power). Simplest.
   - **B — least privilege** (agreed target, now supported): installer = `Deployments`
     **section commander** with `stand.create` + `canister.create` + `commander.assign`.
     Casals now lets a section commander holding these permissions create stands /
     register canisters / assign stand commanders **within its own section** (generic
     feature, no controller needed). See step 4b.
   Either works; B is recommended.
3. **file_registry source.** Casals will pull realm WASMs + frontend bundles from the
   **Realms** `file_registry` (not Casals' own template registry).

Known IDs:

| Thing | ID |
|-------|----|
| casals_backend (mainnet) | `ip2wh-iyaaa-aaaao-bbaoq-cai` |
| Realms file_registry — staging | `iebdk-kqaaa-aaaau-agoxq-cai` |
| Realms file_registry — demo | `vi64l-3aaaa-aaaae-qj4va-cai` |
| Realms file_registry — test | `uq2mu-kaaaa-aaaah-avqcq-cai` |
| realm_installer — staging | `lusjm-wqaaa-aaaau-ago7q-cai` |

Set shell vars for the chosen env (example: staging):

```bash
CASALS=ip2wh-iyaaa-aaaao-bbaoq-cai
FR=iebdk-kqaaa-aaaau-agoxq-cai            # Realms file_registry
INSTALLER=lusjm-wqaaa-aaaau-ago7q-cai
REGISTRY=<realm_registry_backend canister id>
SECTION=Deployments
```

## 1. Confirm / deploy Casals

The mainnet Casals already exists. Just confirm it answers and note its version.

```bash
icp canister call $CASALS get_status '()' -e ic --identity casals
```

✅ **Check:** returns JSON with version + object counts (no trap).

(If deploying a fresh Casals instead: in the Casals repo, `make build` then
`icp deploy -e ic --identity casals --mode upgrade -y`, per Casals `AGENTS.md`.)

## 2. Fund the treasury (cycles)

`casals_backend` pays ~2T cycles per canister created (2 per realm) plus top-ups.
Budget ≈ **5T per realm** + a reserve. For a pilot, 100T is ample.

```bash
icp token balance --identity casals -e ic          # ensure the identity holds ICP
icp cycles mint --icp <amount> --identity casals -e ic   # ICP -> cycles (if needed)
icp canister top-up --amount 100t $CASALS -e ic --identity casals
```

✅ **Check:** treasury reflects the top-up.

```bash
icp canister call $CASALS get_cycles '()' -e ic --identity casals
```

## 3. Configure Casals settings

Point Casals at the Realms file_registry and set the per-canister create budget +
reserve. **Cycles refills stay with CycleOps for now** — so leave Casals' native
autopilot **off** and enable the CycleOps integration: Casals will add the CycleOps
principal as a co-controller of each canister it creates, exactly like today, and
CycleOps keeps topping them up. You can flip to Casals-native later (step 3b).

```bash
CYCLEOPS=<cycleops principal>
icp canister call $CASALS set_settings \
  "(\"{\\\"file_registry_canister_id\\\":\\\"$FR\\\",\\\"create_cycles\\\":2000000000000,\\\"treasury_reserve\\\":5000000000000,\\\"cycleops_enabled\\\":true,\\\"cycleops_principal\\\":\\\"$CYCLEOPS\\\",\\\"cycles_autopilot\\\":false}\")" \
  -e ic --identity casals
```

✅ **Check:** `casals_metadata` shows the file_registry id, `cycleops_enabled: true`,
the CycleOps principal, and `cycles_autopilot: false`.

### 3b. (Later) switch refills to Casals-native

When you want Casals to be the paymaster instead of CycleOps, flip one setting — no
redeploy, no controller changes:

```bash
icp canister call $CASALS set_settings \
  '("{\"cycles_autopilot\":true,\"default_min_cycles\":1000000000000,\"default_topup_cycles\":2000000000000}")' \
  -e ic --identity casals
# optionally also "cycleops_enabled":false to stop CycleOps wiring on new canisters
```

```bash
icp canister call $CASALS casals_metadata '()' -e ic --identity casals
```

## 4. Create the orchestra

### 4a. Sections (controller / `casals` identity)

```bash
icp canister call $CASALS create_section '("{\"name\":\"Infra\"}")'        -e ic --identity casals
icp canister call $CASALS create_section '("{\"name\":\"Deployments\"}")'  -e ic --identity casals
```

✅ **Check:** `get_tree` lists both Sections.

### 4b. Grant the installer rights (choose A or B from step 0)

Get the installer's principal (it is the canister's own principal):

```bash
echo $INSTALLER   # the realm_installer canister principal
```

- **Option A (controller):** add the installer as a Casals controller (icp-cli /
  management). Then it can create stands + canisters + assign commanders. Done.
- **Option B (least privilege):** make the installer the `Deployments` commander with the
  needed permissions:

```bash
icp canister call $CASALS set_commander \
  "(\"{\\\"section\\\":\\\"Deployments\\\",\\\"commander_principal\\\":\\\"$INSTALLER\\\",\\\"permissions\\\":[\\\"canister.create\\\",\\\"commander.assign\\\",\\\"stand.create\\\"]}\")" \
  -e ic --identity casals
```

> Option B is now fully supported in Casals: a section commander holding `stand.create`
> may create stands within its own section, `canister.create` may create/register
> canisters there, and `commander.assign` may set those stands' commanders — all without
> being a Casals controller.

✅ **Check:** `get_tree` shows `Deployments` with `commander_principal = $INSTALLER`.

## 5. Publish a realm release (artifacts → file_registry + authorize in Casals)

Build the backend WASM and the frontend `dist/`, then publish + authorize in one command
(`files publish-release`, added for this migration). `--assets-wasm` is the DFINITY
certified-assets canister WASM (needed so Casals can install + then fill the frontend).

```bash
realms files publish-release \
  --network staging \
  --family realm \
  --version <X.Y.Z> \
  --backend-wasm  <path>/realm_backend.wasm.gz \
  --frontend-dist <path>/realm_registry_frontend/dist \
  --assets-wasm   <path>/assetstorage.wasm.gz \
  --registry $FR \
  --casals $CASALS \
  --registry-backend $REGISTRY \
  --identity <realms-controller-identity>
```

✅ **Checks:**
- file_registry has the namespaces: `wasm/realm-backend/<ver>`,
  `frontend/realm-assets/<ver>`, `wasm/realm-assetstorage/<ver>`.
- Casals lists the authorized WASMs `realm-backend@<ver>` (kind backend) and
  `realm-assets@<ver>` (kind frontend, with `bundle_namespace = frontend/realm-assets/<ver>`):

```bash
icp canister call $CASALS get_status '()' -e ic --identity casals   # wasm count bumped
# (or inspect via the Casals Authorized-WASMs UI)
```

## 6. Configure the installer (still OFF)

Tell the installer where Casals is and who may trigger provisioning, but leave the flag
**off** so nothing changes yet. Use your Realms controller identity (controller-only).

```bash
dfx canister call $INSTALLER set_casals_config \
  "(\"{\\\"provision_via_casals\\\":false,\\\"casals_canister_id\\\":\\\"$CASALS\\\",\\\"casals_section\\\":\\\"$SECTION\\\",\\\"registry_principal\\\":\\\"$REGISTRY\\\"}\")" \
  --network ic --identity <realms-controller-identity>
```

✅ **Check:**

```bash
dfx canister call $INSTALLER get_casals_config '()' --network ic
```

## 7. Pilot — provision ONE realm through Casals

Create a deployment the normal way (registry wizard / `enqueue_deployment`), then enable
the flag and trigger `provision_via_casals` manually for that one job. The manifest must
carry a `casals` block so the installer knows which WASM keys to use:

```json
{
  "realm": { "name": "pilot", "extensions": [], "codex": null },
  "registry_canister_id": "<REGISTRY>",
  "deploy_scope": "both",
  "casals": {
    "section": "Deployments",
    "stand": "pilot",
    "backend_wasm_key": "realm-backend@<X.Y.Z>",
    "frontend_wasm_key": "realm-assets@<X.Y.Z>"
  }
}
```

Enable + trigger:

```bash
dfx canister call $INSTALLER set_casals_config '("{\"provision_via_casals\":true}")' \
  --network ic --identity <realms-controller-identity>

dfx canister call $INSTALLER provision_via_casals '("<job_id>")' \
  --network ic --identity <realms-controller-identity>
```

✅ **Checks (the critical validation gate):**
- Returns `Ok` with `backend_canister_id` + `frontend_canister_id`.
- Casals `get_tree` shows a `pilot` Stand under `Deployments` with backend + frontend
  canisters; the Stand commander = the backend canister id.
- Backend module hash matches the authorized hash (Casals verified on install; confirm
  via `dfx canister info <backend_id>` / management `canister_status`).
- **Frontend serves the real page** at `https://<frontend_id>.icp0.io/` (this exercises
  the multi-file bundle upload end-to-end — the part not yet replica-tested).
- Job reaches `registering` → `completed`; registry credits settle (`deployment_succeeded`).

> If any check fails, **stop here** and flip the flag back off (step 10). No existing
> realm is affected — this only created new pilot canisters.

## 8. Migrate existing realms (no redeploy)

For each live realm, transfer its canisters' controller to Casals, then register them so
Casals can manage them. This does **not** reinstall code.

```bash
# 1) Add Casals as controller of the realm's canisters (keep a backup controller!)
dfx canister update-settings <realm_backend_id>  --add-controller $CASALS --network ic
dfx canister update-settings <realm_frontend_id> --add-controller $CASALS --network ic

# 2) Create the Stand (controller / casals identity, or installer under Option A)
icp canister call $CASALS create_stand '("{\"section\":\"Deployments\",\"name\":\"<slug>\"}")' -e ic --identity casals

# 3) Register the existing canisters into the Stand
icp canister call $CASALS register_canister \
  "(\"{\\\"stand\\\":\\\"<slug>\\\",\\\"name\\\":\\\"<slug>-backend\\\",\\\"canister_id\\\":\\\"<realm_backend_id>\\\",\\\"kind\\\":\\\"backend\\\"}\")" -e ic --identity casals
icp canister call $CASALS register_canister \
  "(\"{\\\"stand\\\":\\\"<slug>\\\",\\\"name\\\":\\\"<slug>-frontend\\\",\\\"canister_id\\\":\\\"<realm_frontend_id>\\\",\\\"kind\\\":\\\"frontend\\\"}\")" -e ic --identity casals

# 4) Make the realm backend the Stand commander (self-upgrade)
icp canister call $CASALS set_commander '("{\"stand\":\"<slug>\",\"commander_principal\":\"<realm_backend_id>\"}")' -e ic --identity casals
```

✅ **Checks:** `get_tree` shows the realm; a no-op `upgrade_to` (same version) or a
`create_snapshot` succeeds, proving Casals controls the canisters.

> Do **not** remove the old controllers until you have confirmed Casals can manage the
> canister (rollback safety).

## 9. Cutover

- Wire `casals_backend` id into `realm_registry_frontend/src/lib/config.js` /
  `canister_ids.json` as needed.
- Have the registry call `provision_via_casals` automatically on new deployments
  (registry → installer), now that the manual pilot passed.
- Once stable, **retire the off-chain deployer**: stop the `realms-deployer` worker,
  remove its callback usage, and delete the dead dfx paths (per `CASALS_MIGRATION.md`
  "Deleted / retired").

✅ **Check:** create a brand-new realm end-to-end with the worker stopped — it provisions
purely on-chain.

## 10. Rollback

At any point before deleting the off-chain worker:

```bash
dfx canister call $INSTALLER set_casals_config '("{\"provision_via_casals\":false}")' \
  --network ic --identity <realms-controller-identity>
```

The installer immediately reverts to the off-chain path (the worker + callbacks are still
present). Canisters already provisioned via Casals keep working; Casals remains a
controller of them (harmless). Full revert of a migrated realm = remove Casals from its
controller set if desired.

## Cycle budget cheat-sheet

| Item | Cycles |
|------|--------|
| Create one canister (default `create_cycles`) | ~2T |
| Per realm (backend + frontend) | ~4–5T |
| Pilot top-up | 100T (plenty) |
| Per-realm-canister auto-topup floor / amount | `default_min_cycles` / `default_topup_cycles` |
| Treasury reserve (never spent below this) | `treasury_reserve` |

## 11. Ongoing releases: Publish Build + Rollout

Once an environment is migrated, new versions are shipped in two manual,
Casals-native steps. Neither is triggered by a push to `main`.

### Step A — Publish Build (`.github/workflows/publish-build.yml`)

Builds and publishes one artifact *family* into an environment's `file_registry`
and authorizes the WASM(s) in that environment's Casals. Inputs: `environment`
(test/staging/demo), `family`, `component` (backend / frontend / both),
`version`, `update_catalog`. Locally:

```bash
python3 scripts/publish_build.py \
  --environment test --family realm --component both \
  --version 0.0.2 --identity <realms-controller-identity>
```

Buildable families: `realm`, `installer`, `registry`, `file-registry`,
`dashboard` (frontend only), `marketplace`. `token`/`nft` are external
ledger-style canisters and are not built by this pipeline (they are still
managed in Casals for visibility / lifecycle).

Authorized WASM keys follow `\<family\>-backend@\<version\>` and
`\<family\>-assets@\<version\>` — exactly what Rollout resolves.

**Main-branch snapshots (no release):** use `.github/workflows/publish-main.yml`
(or `publish_build.py --from-main`). Each publish gets a unique label
`main.<unix_ts>.<git_sha>`. Roll out with `realms rollout -v main` (or
`rollout.yml` with `version=main`) to pick the newest main snapshot. Push to
`main` auto-publishes realm/infra source changes to **test** (when Casals exists
there). `-v latest` still means the newest **semver** release, not main.

### Step B — Rollout (`.github/workflows/rollout.yml` / `realms rollout`)

Upgrades/reinstalls any matrix of environments x targets x canister-kind by
driving Casals `upgrade_to` (backends) and `upgrade_to` + batched
`provision_assets` (frontends). Snapshot -> install -> verify-hash ->
rollback-on-failure is automatic. **Dry-run by default**; pass `--execute`.

```bash
# Preview every realm backend in test
realms rollout -e test -t all-realms -s backend

# Upgrade just Agora's backend in test
realms rollout -e test -t agora -s backend --execute

# Upgrade all realms + infra across all environments
realms rollout -e all -t all -s both --execute

# Reinstall all infra in test (explicit opt-in required for state-wiping infra)
realms rollout -e test -t all-infra -m reinstall --include-infra-reinstall --execute
```

`reinstall` wipes canister state on success (the protective snapshot is dropped
after a verified reinstall), so it prompts for confirmation and refuses
`file-registry` / `realm-registry` unless `--include-infra-reinstall` is given.

Per-environment Casals IDs live in `cli/realms/cli/commands/rollout.py`
(`_CASALS_IDS`); add `staging`/`demo` there once Casals is deployed in those
environments.

### Coexistence with the legacy deployer

Both paths run side by side:

- The per-environment switch `InstallerConfig.provision_via_casals` (default
  off) decides whether a given environment uses Casals or the legacy off-chain
  deployer. `test` can be on Casals while `staging`/`demo` stay on the deployer.
- `release.yml` (GitHub Releases + PyPI) and the off-chain deployer are
  untouched; Publish Build + Rollout are additive.
- `rollout` never touches the registry version catalog, so it cannot interfere
  with the legacy self-service `request_upgrade` path.
- Publish Build does **not** update the realm version catalog unless
  `--update-catalog` is set, so it never feeds a legacy-mode deployer a
  `fileregistry://` URL it cannot download.
