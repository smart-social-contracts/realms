# CycleOps Management

Scripts and documentation for managing IC canister cycles via [CycleOps](https://cycleops.dev).

Dashboard: https://cycleops.dev/app/team/my-team-1/canisters/

## Top-Up Rules

### Current Configuration (as of 2026-04-21)

Canisters are split into two tiers based on cycle burn rate:

| Tier | Threshold | Top-Up To | Canisters |
|------|-----------|-----------|-----------|
| **HIGH_BURN** | 4 TC | 8 TC | `realm_installer` (staging + demo), `file_registry` (staging + demo) |
| **Standard** | 2 TC | 4 TC | All other canisters (~30) |

### Why Two Tiers?

The `realm_installer` and `file_registry` canisters store large binary data (WASM modules and uploaded files). On the IC, storage costs cycles continuously — you pay per byte per second. These canisters have storage in the range of 1–7 GB, which translates to cycle burn rates of 0.85–2.81 TC over the monitoring period. At the old 2 TC threshold, they could drain below the freeze threshold between CycleOps monitoring intervals.

### Protocol Memory Cost Increase (2.5x)

The IC protocol is increasing memory costs by **2.5x** (from ~$6.97/mo to ~$17.41/mo for our fleet). This makes the higher threshold even more important — at 2.5x burn rate, a canister burning 2.81 TC would burn ~7 TC, which would blow through a 4 TC balance in days.

**Recommendation**: After the cost increase takes effect, reassess whether the HIGH_BURN tier should be raised further to **12 TC @ 6 TC** or even **16 TC @ 8 TC**.

## High-Burn Canisters

| CycleOps Name | Canister ID | Network | Storage | Burn Rate | Freeze Risk |
|---|---|---|---|---|---|
| staging-realm_installer | `lusjm-wqaaa-aaaau-ago7q-cai` | staging | 6.83 GB | 2.81 TC | Apr 27 |
| demo-realm_installer | `2s4td-daaaa-aaaao-bazmq-cai` | demo | 2.60 GB | 1.1 TC | **Apr 21 (critical)** |
| staging-file_registry | `iebdk-kqaaa-aaaau-agoxq-cai` | staging | 1.34 GB | 0.85 TC | May 8 |
| demo-file_registry | `vi64l-3aaaa-aaaae-qj4va-cai` | demo | 1.24 GB | ~99B cycles | Oct 6 |

> Data from CycleOps dashboard snapshot on 2026-04-21.

## Scripts

### `emergency_topup.sh` — Emergency Cycle Top-Up

For canisters at imminent freeze risk. Sends cycles via the CycleOps `manualTopup` API.

```bash
# Top up demo-realm_installer with 8 TC
bash scripts/cycleops/emergency_topup.sh 2s4td-daaaa-aaaao-bazmq-cai 8

# Top up staging-realm_installer with 10 TC
bash scripts/cycleops/emergency_topup.sh lusjm-wqaaa-aaaau-ago7q-cai 10
```

### `update_thresholds.sh` — Configure All Canister Top-Up Rules

Registers all project canisters with CycleOps and sets their top-up rules (two tiers). Run this after adding new canisters or changing thresholds.

```bash
bash scripts/cycleops/update_thresholds.sh
```

### `generate_csv.py` — Generate CycleOps CSV for Bulk Upload

Generates a CSV file for CycleOps bulk canister import. Queries the realm registry and `canister_ids.json`.

```bash
python3 scripts/cycleops/generate_csv.py --network staging
```

## Reference Files

| File | Description |
|---|---|
| `CANISTER_CREATION.md` | How to create canisters programmatically via CycleOps API |
| `canisters.csv` | Master list of all canister IDs, networks, and repo locations |
| `expenses/` | Billing history and account exports from CycleOps |

Private email threads with Byron Becker (CycleOps) are in `realms-strategy/` (private repo).

## Key Principals

| Item | Value |
|---|---|
| CycleOps canister | `qc4nb-ciaaa-aaaap-aawqa-cai` |
| V3 Blackhole | `cpbhu-5iaaa-aaaad-aalta-cai` |
| dfx identity | `my_dev_identity_1` |
| dfx principal | `ah6ac-cc73l-bb2zc-ni7bh-jov4q-roeyj-6k2ob-mkg5j-pequi-vuaa6-2ae` |
| Team principal | `xee7m-jddpf-rwyzl-pobzx-izlbn-vhsbt-ublzn-lf4vo-kbvz2-buwfk-xh6` |
| Team ICP deposit | `d9813cedffb1e4ea6ab206d82a86fe8f5b675bc685ece951720260a828ff3def` |

## Preventing Canister Freeze

1. **Monitor the dashboard** regularly: https://cycleops.dev/app/team/my-team-1/canisters/
2. **Watch for freeze dates** within 2 weeks — run `emergency_topup.sh` immediately.
3. **Keep the team ICP balance funded** — send ICP to the deposit address above.
4. **After deploying new canisters**, run `update_thresholds.sh` to register them.
5. **Reduce storage** where possible: purge old WASM versions from `realm_installer`, clean unused files from `file_registry`.
