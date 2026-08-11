# RealmsGOS shared-infra Casals config

Per-environment Casals topology and service-ID snapshots for RealmsGOS
shared platform infrastructure. Tracks [realms#288](https://github.com/smart-social-contracts/realms/issues/288) and
[Casals#11](https://github.com/smart-social-contracts/Casals/issues/11).

## Scope

Each Realms environment (`test`, `staging`, `demo`) gets its **own** Casals
instance. This directory holds the **shared-infra-only** slice of that orchestra
— not realm stands and not orchestration batons.

| Action | Canisters |
|--------|-----------|
| **CREATE** (via sheet deploy) | `casals_backend`, `casals_frontend`, `multisig` |
| **REUSE** (register existing Realms canisters) | `token`/`nft`/`marketplace` backends + frontends, `file_registry` + `file_registry_frontend` |
| **NO** | Batons (`orchestration-baton`), realm stands, installer, realm-registry |

**Control model:** Casals + multisig only. No baton layer; upgrades are driven
directly by Casals controllers / multisig signers.

**file_registry:** The reused `file_registry` canister is the Realms
environment's existing artifact store (same IDs as `canister_ids.json`), not
Casals' template registry.

## Live canister IDs (2026-08-10)

| Env | casals_backend | casals_frontend | multisig |
|-----|----------------|-----------------|----------|
| test | `qugvi-7yaaa-aaaap-quwnq-cai` | `qtht4-saaaa-aaaap-quwna-cai` | `qbbef-6qaaa-aaaap-quwoa-cai` |
| demo | `uvvmt-xaaaa-aaaae-agzta-cai` | `usukh-2yaaa-aaaae-agztq-cai` | `v72oj-vqaaa-aaaae-agzua-cai` |
| staging | `bjzut-ryaaa-aaaaj-a6uta-cai` | `boysh-4aaaa-aaaaj-a6utq-cai` | `adwwj-tiaaa-aaaaj-a6uua-cai` |

Also recorded in `canister_ids.json` and `env-services/*.json`. These are **separate** from the legacy mundus Casals IDs in the repo-root `canister_ids.json`.

## Layout

```
realmsgos/
  canister_ids.json              # new RealmsGOS Casals IDs per env
  sheets/infra-shared.json       # Casals sheet: Infra/multisig only
  env-services/{test,demo,staging}.json   # static SoT for realms#289 v1 resolver
  scripts/deploy_env_casals.sh            # create + seed + adopt one env
  scripts/register_shared_infra.py        # post-deploy: register reused infra
  scripts/sync_env_services_py.py         # regenerate realm_backend embedded snapshots
```

## Sheet (`sheets/infra-shared.json`)

Minimal orchestra: one `Infra` section, one stand named `multisig` with
`wasm_key: orchestration-multisig`. No realm stands, no batons.

Deploy with Casals `deploy_sheet` after seeding orchestration templates (see
Casals `AGENTS.md`). Shared services (`token`, `nft`, `marketplace`,
`file-registry`) are **not** in the sheet — they are registered onto Casals
**after** deploy via `scripts/register_shared_infra.py` (see below).

## env-services snapshots

Static source-of-truth JSON for the [realms#289](https://github.com/smart-social-contracts/realms/issues/289)
v1 service resolver. Reused canister IDs are filled from `canister_ids.json`;
`casals_backend`, `casals_frontend`, and `multisig` stay `null` until the
per-env Casals is deployed and the multisig stand is provisioned.

## Register reused shared infra

After deploying Casals for an environment and adding Casals as a **controller**
of the reused canisters, run:

```bash
python3 casals-config/realmsgos/scripts/register_shared_infra.py \
  --casals <casals_backend_id> \
  --network test \
  --identity my_dev_identity_1
```

The script reads `env-services/<network>.json`, creates Infra stands
(`token`, `nft`, `marketplace`, `file-registry` — names match
`cli/realms/cli/commands/rollout.py` `_INFRA_FAMILY`), and calls Casals
`register_canister` for each backend + frontend pair. It prints every
`icp canister call` before running it and skips stands/canisters that already
exist.

**Prerequisites**

1. Fresh Casals deployed from `sheets/infra-shared.json` (multisig stand live).
2. Casals backend is a controller of each reused canister.
3. `env-services/<network>.json` has non-null reused IDs (already committed from
   `canister_ids.json`).
4. `icp` CLI available; identity is a Casals controller.

**After deploy — update env-services**

Once `casals_backend`, `casals_frontend`, and `multisig` IDs are known, fill
the `null` placeholders in `env-services/<network>.json` (do not overwrite
reused IDs).

## Related docs

- [CASALS_ROLLOUT.md](../../docs/reference/CASALS_ROLLOUT.md) — operational rollout runbook
- [casals-config/README.md](../README.md) — realms-owned Casals objects (full orchestra)
