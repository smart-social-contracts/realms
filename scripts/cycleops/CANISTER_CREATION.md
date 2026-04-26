# CycleOps Programmatic Canister Creation

Tested and verified on Apr 10, 2026.

## Overview

CycleOps (`qc4nb-ciaaa-aaaap-aawqa-cai`) supports programmatic canister creation via its `createCanister` endpoint. This creates a canister on IC mainnet, funds it with cycles from the team's ICP balance, and automatically registers it for CycleOps monitoring — all in one call.

> **Note**: This is not a publicly supported API. Byron Becker (CycleOps) shared it as a workaround. See `realms-strategy/CycleOps_ Cycle Consumption Question.eml` for the original email thread (private repo).

## Prerequisites

### 1. CycleOps Account

Sign in at https://cycleops.dev with Internet Identity. This creates a CycleOps customer account with a derived principal.

### 2. Create a Team

Teams are required because the dfx CLI identity has a different principal than the Internet Identity used to sign in to CycleOps. The team acts as a shared account.

- Go to **Settings > Teams** in the CycleOps dashboard
- Create a team (e.g., "staging")
- Note the **team principal** (retrievable via API, see below)

### 3. Register the dfx Identity as a CycleOps Customer

The dfx principal must be registered as a CycleOps customer before it can be added to a team:

```bash
dfx identity use my_dev_identity_1
# Principal: ah6ac-cc73l-bb2zc-ni7bh-jov4q-roeyj-6k2ob-mkg5j-pequi-vuaa6-2ae

dfx canister call qc4nb-ciaaa-aaaap-aawqa-cai createCustomerRecord \
  '(record {
    metadata = record {
      description = opt "Realms deployer";
      displayName = opt "Realms Dev";
      logoUrl = null;
      username = "realms-dev";
      website = opt "https://realmsgos.org"
    }
  })' --network ic
```

### 4. Add dfx Identity to the Team

In the CycleOps dashboard:
- Go to team **Settings > Members**
- Click **Add Member**
- Paste the dfx principal: `ah6ac-cc73l-bb2zc-ni7bh-jov4q-roeyj-6k2ob-mkg5j-pequi-vuaa6-2ae`
- Set role to **Admin** (or Member)

### 5. Fund the Team

The team needs ICP to create canisters (ICP is converted to cycles).

**Get team deposit address:**
```bash
dfx canister call qc4nb-ciaaa-aaaap-aawqa-cai teams_accountsLocalAccountText \
  '(record { teamID = principal "xee7m-jddpf-rwyzl-pobzx-izlbn-vhsbt-ublzn-lf4vo-kbvz2-buwfk-xh6" })' \
  --network ic
# Returns: "d9813cedffb1e4ea6ab206d82a86fe8f5b675bc685ece951720260a828ff3def"
```

Send ICP to this account ID from any wallet. ~1 ICP is sufficient for testing.

**Check team balance:**
```bash
dfx canister call qc4nb-ciaaa-aaaap-aawqa-cai teams_accountsBalance \
  '(record { teamID = principal "xee7m-jddpf-rwyzl-pobzx-izlbn-vhsbt-ublzn-lf4vo-kbvz2-buwfk-xh6" })' \
  --network ic
```

## Creating a Canister

### Find the Team Principal

```bash
dfx canister call qc4nb-ciaaa-aaaap-aawqa-cai teams_getTeamsCallerIsMemberOf \
  '()' --query --network ic
```

### Get the V3 Blackhole Principal

CycleOps requires the V3 blackhole as a controller for monitoring:

```bash
dfx canister call qc4nb-ciaaa-aaaap-aawqa-cai getDefaultBlackhole '()' --network ic
# Returns: cpbhu-5iaaa-aaaad-aalta-cai (version 3)
```

### Create the Canister

```bash
dfx canister call qc4nb-ciaaa-aaaap-aawqa-cai createCanister \
  '(record {
    asTeamPrincipal = opt principal "xee7m-jddpf-rwyzl-pobzx-izlbn-vhsbt-ublzn-lf4vo-kbvz2-buwfk-xh6";
    controllers = vec {
      principal "ah6ac-cc73l-bb2zc-ni7bh-jov4q-roeyj-6k2ob-mkg5j-pequi-vuaa6-2ae";
      principal "cpbhu-5iaaa-aaaad-aalta-cai"
    };
    name = opt "my-canister-name";
    subnetSelection = null;
    topupRule = null;
    withStartingCyclesBalance = 500_000_000_000 : nat
  })' --network ic
```

**Response:**
```
(variant { ok = principal "axsmf-laaaa-aaaan-q56ta-cai" })
```

The canister is immediately:
- Created on IC mainnet
- Funded with the specified cycles (converted from team ICP)
- Registered for CycleOps monitoring
- Visible in the CycleOps dashboard

### Verify

```bash
dfx canister status axsmf-laaaa-aaaan-q56ta-cai --network ic
```

## Topping Up a Canister

### Top up with cycles

```bash
dfx canister call qc4nb-ciaaa-aaaap-aawqa-cai manualTopup \
  '(record {
    asTeamPrincipal = opt principal "xee7m-jddpf-rwyzl-pobzx-izlbn-vhsbt-ublzn-lf4vo-kbvz2-buwfk-xh6";
    canisterId = principal "axsmf-laaaa-aaaan-q56ta-cai";
    topupAmount = variant { cycles = 1_000_000_000_000 : nat }
  })' --network ic
```

### Top up with ICP (auto-converted to cycles)

```bash
dfx canister call qc4nb-ciaaa-aaaap-aawqa-cai manualTopup \
  '(record {
    asTeamPrincipal = opt principal "xee7m-jddpf-rwyzl-pobzx-izlbn-vhsbt-ublzn-lf4vo-kbvz2-buwfk-xh6";
    canisterId = principal "axsmf-laaaa-aaaan-q56ta-cai";
    topupAmount = variant { icp = record { e8s = 100_000_000 : nat64 } }
  })' --network ic
```

## Candid Interface Reference

### createCanister

```candid
createCanister:
  (record {
    asTeamPrincipal: opt TeamID;
    controllers: vec principal;
    name: opt text;
    subnetSelection: opt SubnetSelection__1;
    topupRule: opt TopupRule__2;
    withStartingCyclesBalance: nat;
  }) -> (Result_20);

type TeamID = principal;

type SubnetSelection__1 = variant {
  Filter: record { subnet_type: opt text };
  Subnet: record { subnet: principal };
};

type TopupRule__2 = record {
  method: variant {
    by_amount: nat;   // top up by this many cycles
    to_balance: nat;  // top up to this cycle balance
  };
  threshold: nat;     // trigger when cycles fall below this
};

type Result_20 = variant {
  err: text;
  ok: principal;
};
```

### manualTopup

```candid
manualTopup:
  (record {
    asTeamPrincipal: opt TeamID;
    canisterId: principal;
    topupAmount: ManualTopupType;
  }) -> (Result_1);

type ManualTopupType = variant {
  cycles: nat;
  icp: record { e8s: nat64 };
};
```

## Key Principals and Addresses

| Item | Value |
|---|---|
| CycleOps canister | `qc4nb-ciaaa-aaaap-aawqa-cai` |
| V3 Blackhole | `cpbhu-5iaaa-aaaad-aalta-cai` |
| dfx identity | `my_dev_identity_1` |
| dfx principal | `ah6ac-cc73l-bb2zc-ni7bh-jov4q-roeyj-6k2ob-mkg5j-pequi-vuaa6-2ae` |
| Team principal (staging) | `xee7m-jddpf-rwyzl-pobzx-izlbn-vhsbt-ublzn-lf4vo-kbvz2-buwfk-xh6` |
| Team ICP deposit address | `d9813cedffb1e4ea6ab206d82a86fe8f5b675bc685ece951720260a828ff3def` |
| Test canister created | `axsmf-laaaa-aaaan-q56ta-cai` |

## Test environment (RealmGOS) — canisters to create

Use this when provisioning a third IC environment (`test`) with the **same topology as staging** (`deployments/staging-mundus-layered.yml` plus token/NFT frontends tracked in `canister_ids.json`).

### 1. Canister list (18 total)

Create each canister once via `createCanister` (see [Creating a Canister](#creating-a-canister)). Use the suggested **`name`** for CycleOps so `canisters.csv` and `update_thresholds.sh` stay consistent.

| # | Suggested CycleOps `name` | Role | Top-up tier after registration |
|---|---------------------------|------|--------------------------------|
| 1 | `test-file_registry` | WASM / asset storage (`file_registry`) | **HIGH_BURN** (same as staging `file_registry`) |
| 2 | `test-realm_installer` | Installer (large WASM storage) | **HIGH_BURN** |
| 3 | `test-file_registry_frontend` | `file_registry_frontend` assets | Standard |
| 4 | `test-registry_backend` | `realm_registry_backend` | Standard |
| 5 | `test-registry_frontend` | `realm_registry_frontend` | Standard |
| 6 | `test-dominion_backend` | Realm 1 (Dominion) backend | Standard |
| 7 | `test-dominion_frontend` | Realm 1 frontend | Standard |
| 8 | `test-agora_backend` | Realm 2 (Agora) backend | Standard |
| 9 | `test-agora_frontend` | Realm 2 frontend | Standard |
| 10 | `test-syntropia_backend` | Realm 3 (Syntropia) backend | Standard |
| 11 | `test-syntropia_frontend` | Realm 3 frontend | Standard |
| 12 | `test-marketplace_backend` | `marketplace_backend` | Standard |
| 13 | `test-marketplace_frontend` | `marketplace_frontend` | Standard |
| 14 | `test-platform_dashboard_frontend` | `platform_dashboard_frontend` | Standard |
| 15 | `test-token_backend` | ICRC token backend | Standard |
| 16 | `test-token_frontend` | Token UI | Standard |
| 17 | `test-nft_backend` | NFT backend | Standard |
| 18 | `test-nft_frontend` | NFT UI | Standard |

**Not included** (same as current staging descriptor): ckBTC ledger/indexer (demo-only entries in root `canister_ids.json`), separate Agora “quarter” canister (present in `update_thresholds.sh` for staging but not in `staging-mundus-layered.yml`), and generic `realm_backend` / `realm_frontend` rows in `canister_ids.json` that duplicate named realms—add those only if your `test` descriptor still references them.

### 2. Bulk dry-run / provision

From the repo root (`realms/`), run:

```bash
bash scripts/cycleops/provision_test_env_cycleops.sh          # print createCanister commands only
EXECUTE=1 bash scripts/cycleops/provision_test_env_cycleops.sh   # run against IC (costs ICP)
```

**Do not create duplicate canisters.** With `EXECUTE=1`, the script appends each successful `ok = principal "…"` to `scripts/cycleops/test_env_cycleops_ids.tsv` (override with `STATE_FILE=…`). On the next run, any name already in that file is **skipped** so an interrupted run or a second invocation does not mint a second fleet. Delete or edit the TSV only if you are recovering from a mistake (and see the CycleOps dashboard before re-running).

To force another create for the same CycleOps `name` (almost never correct), set `ALLOW_DUPLICATE_NAMES=1`.

Override defaults if needed: `TEAM_PRINCIPAL`, `DFX_CONTROLLER`, `BLACKHOLE`, `STARTING_CYCLES`, `STARTING_CYCLES_HIGH_BURN`. If `dfx` fails due to version pinning, run from `/tmp` or another directory without a pinned `dfx.json`, as in [Notes](#notes).

### 3. Register for monitoring and top-ups

After every principal exists:

1. **`canister_ids.json`** and **`dfx.json`** — add `test` keys (repo wiring; see deployment docs).
2. **`scripts/cycleops/canisters.csv`** — append one row per canister (`network` = `test`, `Full Canister ID` = new principal).
3. **`scripts/cycleops/update_thresholds.sh`** — add `test-file_registry` and `test-realm_installer` to `HIGH_BURN_CANISTERS`, and the rest to `ALL_CANISTERS`, then run `bash scripts/cycleops/update_thresholds.sh`.
4. Optional: `python3 scripts/cycleops/generate_csv.py --network test` for a CycleOps bulk CSV once `canister_ids.json` includes `test` entries.

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Customer account not found` | Calling principal not registered with CycleOps | Call `createCustomerRecord` first |
| `insufficient funds` | Team (or personal) account has no ICP | Fund the team's deposit address |
| `Created canisters must start with at least 100 billion spare cycles` | `withStartingCyclesBalance` below IC minimum | Use at least `100_000_000_000` (100B) cycles; the script default is 500B |
| `variant field by_amount not found` | Wrong type for `topupAmount` | Use `variant { cycles = ... }` not `variant { by_amount = ... }` |

## Cost Reference

### Per-Canister Creation Cost (CycleOps `createCanister`)

CycleOps converts team ICP to cycles at the current XDR rate. Costs measured
on 2026-04-25:

| Canister Role | Starting Cycles | Approx. ICP Cost |
|---|---|---|
| Realm backend | 1.5 TC | ~1.2 ICP |
| Realm frontend | 800 B | ~0.74 ICP |
| **Total per realm deployment** | **2.3 TC** | **~1.94 ICP** |

> A single realm deployment (1 backend + 1 frontend) costs **~2 ICP** from the
> CycleOps team balance. At $12/ICP this is ~$24 per deployment.
>
> The `realms-staging-deployments` team was funded with 5 ICP for the first
> staging E2E test. After one deployment, ~3.06 ICP remained.

### Ongoing Costs

After creation, canisters consume cycles proportional to storage + compute:
- A typical realm backend uses ~10–50 MB → ~0.01–0.05 TC/day idle
- CycleOps auto-tops at the Standard tier (2 TC threshold → 4 TC)
- Monthly cost per realm: ~0.5–2 ICP depending on usage

## Notes

- **Not a public API**: Byron confirmed this is not officially supported yet. API may change.
- **Cost**: Creating a canister with 0.5T cycles costs ~$0.65 in ICP at current rates ($1.57/TC).
  For realm deployments (1.5T backend + 800B frontend) the total is ~1.94 ICP per realm.
- **dfx version**: Must run from a directory without `dfx.json` version pinning, or use a compatible version. We ran from `/tmp` to avoid the realms repo's `dfx.json` pinning to 0.29.0.
- **Local testing**: Use the mock CycleOps canister (`scripts/cycleops/mock_cycleops/`) on a local dfx replica. See `scripts/test_local_e2e.sh`.
