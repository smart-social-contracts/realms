# Operator runbook — `gaas new` then `realms seed` then `realms new`

What the CLIs **do not** do for you. Canister ownership and DNS keep-IDs: [GAAS_NEW_AND_REALMS_SEED.md](./GAAS_NEW_AND_REALMS_SEED.md).

This is live-destructive. Do not run destroy until you have named the environment (**test** / **demo** / **staging**). Examples below are **test**.

Two inventories. Do not copy Realms GOS product ids into the GaaS descriptor. Do not copy GaaS Casals ids into Realms `casals_*`.

| File | What it is for |
|---|---|
| `gos-as-a-service/environments/<env>.json` | GaaS descriptor. Destroy reads **`canisters.casals_backend` here**. |
| `gos-as-a-service/canister_ids.json` | Last-known GaaS ids. Destroy does **not** read this. |
| `realms/canister_ids.json` | Realms GOS Casals + product ids. Seed destroy reads **this**. |
| `realms/environments/<env>.json` | Product stack list + `casals_url` (Realms GOS Casals frontend only). |

---

## 0. Shell (every command)

```bash
export TERM=xterm
export DFX_WARNING=-mainnet_plaintext_identity
# dfx panics if these are set:
unset NO_COLOR FORCE_COLOR

dfx identity use deployer   # or: icp identity default deployer
```

Install CLIs from the checkouts you will run (not PyPI), and point at a Casals tree:

```bash
pip install -e /path/to/gos-as-a-service/cli
pip install -e /path/to/realms/cli
export CASALS_SRC=/path/to/Casals   # or a sibling ../Casals checkout
```

`gaas new --network ic` means “IC replica” (not local). The environment name is still `test` / `demo` / `staging` from the descriptor. `dfx --network test` is the Realms/dfx alias for that same IC.

---

## 1. Before `gaas new` — point destroy at the **live GaaS** conductor

Destroy is: call **this** Casals, drain its orchestra, delete **that** Casals. The only address it uses is the GaaS descriptor field `canisters.casals_backend`.

If that field is missing, destroy errors. If you skip `--destroy-except-realm-registry-frontend`, `casals new` mints a **second** conductor and the old stack stays up.

`canister_ids.json` may already have a test Casals id. That is a hint, not an input.

1. Candidate from `gos-as-a-service/canister_ids.json` (test last recorded: `3adcv-rqaaa-aaaad-qmdcq-cai`). Docs/`AGENTS.md` may list an older id (`qthgp-…`). Ignore docs until status confirms.
2. Confirm it is live and that **deployer** is a controller:

```bash
dfx canister status <casals_backend> --network test --identity deployer
```

3. Put **that** principal in `gos-as-a-service/environments/test.json`:

```json
"canisters": {
  "casals_backend": "<live GaaS Casals backend>",
  "realm_registry_frontend": "qtank-3qaaa-aaaaa-qhb6q-cai"
}
```

4. Optional, same GaaS stack only (helps extra-delete if they are not on the orchestra tree): `casals_frontend`, `casals_file_registry`, `realm_installer`, `realm_registry_backend`. Confirm each with `dfx canister status` first.

Do **not** add fleet `file_registry`, marketplace, token, or nft to this file. Those are Realms GOS.

DNS keep-ID for GaaS: `realm_registry_frontend` (`qtank-…` → `test.gos.earth`). Confirm it is live. If it is dead, `test.gos.earth` breaks until you re-register at [reg.icp0.io](https://reg.icp0.io).

---

## 2. Before `gaas new` — product canisters on the **old** GaaS orchestra

GaaS destroy should not list Realms GOS names. `destroy_orchestra` still deletes **every registered canister and every pool entry** except `preserve`.

Casals `delete_canister` only drops the orchestra row. The id goes to the **pool** and is still destroyed.

Inspect the tree:

```bash
dfx canister call <casals_backend> get_tree '()' --network test --identity deployer
```

If marketplace / fleet file-registry / token / nft appear as stands:

- **Non-DNS product canisters** — they will be deleted with the GaaS orchestra. That is expected on a full rebuild if they were still registered there. Also copy their ids into Realms `canister_ids.json` under `test` (step 3) so `realms seed` can clean leftovers that were **not** on the tree.
- **`marketplace_frontend` (`mxyd5-…`, `test.realmsgos.org`)** — if it is on this orchestra or in its pool, destroy will IC-delete it unless it is in `preserve`. Today the only preserve input is ids listed in the GaaS descriptor. Putting `marketplace_frontend` there is GaaS knowing about Realms GOS; it is a **one-shot DNS guard** until destroy no longer sees that canister. After this wipe, remove it from the GaaS descriptor and never put it back.

Confirm `mxyd5-…` is live before wipe. If it is already dead, DNS is already broken; do not invent a new keep-ID in the GaaS file.

---

## 3. Before `realms seed` — Realms inventory for adopt or rebuild

Default `realms seed` **adopts** ids from **Realms** `canister_ids.json` (register + sheet reconcile). It does not `delete_canister` unless you pass **`--rebuild`**.

For **`--rebuild`**, the same inventory lists what will be destroyed (except `marketplace_frontend` DNS). Test product principals (verify with `dfx canister status`):

| Name | Role |
|---|---|
| `marketplace_frontend` | **Keep on rebuild.** DNS. Default seed adopts; rebuild must not delete this id. |
| `marketplace_backend` | Adopt (default) / destroy + recreate (`--rebuild`) |
| `file_registry` | Adopt (default) / destroy + recreate (`--rebuild`; fleet, not Casals’ own) |
| `file_registry_frontend` | Adopt (default) / destroy + recreate (`--rebuild`) |
| `token_backend` / `token_frontend` | Adopt (default) / destroy + recreate (`--rebuild`) |
| `nft_backend` / `nft_frontend` | Adopt (default) / destroy + recreate (`--rebuild`) |
| `casals_backend` (+ other `casals_*`) | Adopt (default) / destroy + recreate (`--rebuild`) |

Do **not** put GaaS `casals_*` into Realms `casals_*`. If Realms still has a test Casals id that is actually the **GaaS** conductor, seed will try to delete it unless that id is also in the GaaS descriptor (seed treats those as protected). After `gaas new`, GaaS Casals is a **new** principal; an old id in Realms inventory is a dead canister seed can clear.

---

## 4. Run `gaas new`

From `gos-as-a-service`:

```bash
gaas new environments/test.json --identity deployer --network ic --yes \
  --destroy-except-realm-registry-frontend
```

Keep the rewritten `environments/test.json`. `realms new --gaas-config` needs the **new** `realm_registry_backend` and `realm_installer`.

`--yes` skips interactive Casals commander grants. Re-run that phase later on a TTY if you need II commanders.

---

## 5. Before `realms seed` (after `gaas new`)

No extra inventory edit if step 3 is done. Confirm GaaS Casals in the descriptor is the **new** id (not the one you just destroyed).

```bash
realms seed --env test --identity deployer --yes
```

Adopts existing Realms GOS Casals + product canisters when ids are in `canister_ids.json`. For a full wipe:

```bash
realms seed --env test --identity deployer --rebuild --yes
```

From the Realms repo. Needs `CASALS_SRC`. First seed after `gaas new` with no Realms GOS Casals yet may still use `--rebuild` or let `env deploy` create missing canisters via `--from-phase env_deploy` after `casals new`.

---

## 6. Before `realms new` — credits + founder

`realms seed` already points the installer at fleet `file_registry` + marketplace (`casals_canister_id` stays GaaS Casals).

1. New registry has no credits. `realms new` still requires ≥ 5 even with `can_test_mode`:

```bash
realms registry billing add_credits \
  --principal <founder-II-principal> --amount 5 \
  --network test --canister-id <new realm_registry_backend>
```

2. Founder identity: II-linked to `https://test.realmsgos.org`, or `--co-admin <browser-II-principal>`. Do not use `deployer` as the only founder if you will log in with Internet Identity.

```bash
realms new spec.json --identity <ii-linked> --network test --yes \
  --gaas-config /path/to/gos-as-a-service/environments/test.json
```

This creates **one wizard realm**. It does not recreate Agora / Dominion / Syntropia (those were destroyed in `gaas new`).

---

## 7. After the run (not blockers)

- **DNS** — none if `qtank-…` and `mxyd5-…` stayed live.
- **CycleOps** (`cpbhu-5iaaa-aaaad-aalta-cai`) is not re-added by controller topology. Add it if you still want autopilot.
- **Commit** GaaS `environments/test.json` + `canister_ids.json` and Realms `canister_ids.json` + `environments/test.json` (`casals_url`) when you want inventories saved. Do not commit until asked if that is the standing rule.

Sanity: portal Infrastructure → GaaS Casals frontend; marketplace footer → Realms GOS Casals frontend; empty pointer hides the link.
