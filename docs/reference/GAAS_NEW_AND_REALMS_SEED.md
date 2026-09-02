# `gaas new` and `realms seed` — canister actions

Both commands call **`casals new`**, which destroys and re-creates the Casals conductor stack (new principals).

- **Destroy and re-create** — recover cycles, delete, mint a new canister (new principal).
- **Reinstall (keep principal)** — wipe code/state on the same ID. Required for DNS.
- **Destroy** — recover cycles and delete; do not mint a replacement in this command.

## `gaas new` — GaaS (`*.gos.earth`)

| Canister | Action |
|---|---|
| `casals-backend` | destroy and re-create (`casals new`) |
| `casals-frontend` | destroy and re-create (`casals new`) |
| `casals-multisig` | destroy and re-create (`casals new`) |
| `casals-file-registry-backend` | destroy and re-create (`casals new`) |
| `casals-file-registry-frontend` | destroy and re-create (`casals new`) |
| `infra-baton` | destroy and re-create |
| `realm-installer` | destroy and re-create |
| `realm-registry-backend` | destroy and re-create |
| `realm-registry-frontend` | **reinstall (keep principal for DNS)** |
| `realmN-baton` | destroy |
| `realmN-backend` | destroy |
| `realmN-frontend` | destroy |
| `realmN-quarter*-backend` | destroy |
| … | destroy (every other realm/quarter canister) |

## `realms seed` — Realms GOS (`*.realmsgos.org`)

| Canister | Action |
|---|---|
| `casals-backend` | destroy and re-create (`casals new`) |
| `casals-frontend` | destroy and re-create (`casals new`) |
| `casals-multisig` | destroy and re-create (`casals new`) |
| `casals-file-registry-backend` | destroy and re-create (`casals new`) |
| `casals-file-registry-frontend` | destroy and re-create (`casals new`) |
| `file-registry` (fleet) | destroy and re-create |
| `file-registry-frontend` | destroy and re-create |
| `marketplace-backend` | destroy and re-create |
| `marketplace-frontend` | **reinstall (keep principal for DNS)** |
| `token-backend` | destroy and re-create |
| `token-frontend` | destroy and re-create |
| `nft-backend` | destroy and re-create |
| `nft-frontend` | destroy and re-create |

DNS keep-ID canisters: **`realm-registry-frontend`** (`*.gos.earth`) and **`marketplace-frontend`** (`*.realmsgos.org`).
