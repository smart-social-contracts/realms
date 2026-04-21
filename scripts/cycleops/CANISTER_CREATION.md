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

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Customer account not found` | Calling principal not registered with CycleOps | Call `createCustomerRecord` first |
| `insufficient funds` | Team (or personal) account has no ICP | Fund the team's deposit address |
| `variant field by_amount not found` | Wrong type for `topupAmount` | Use `variant { cycles = ... }` not `variant { by_amount = ... }` |

## Notes

- **No local testing**: CycleOps has no local replica. All testing must be on IC mainnet.
- **Not a public API**: Byron confirmed this is not officially supported yet. API may change.
- **Cost**: Creating a canister with 0.5T cycles costs ~$0.65 in ICP at current rates ($1.57/TC).
- **dfx version**: Must run from a directory without `dfx.json` version pinning, or use a compatible version. We ran from `/tmp` to avoid the realms repo's `dfx.json` pinning to 0.29.0.
