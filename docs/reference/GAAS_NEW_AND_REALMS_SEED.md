# `gaas new` and `realms seed` — canister actions

Both commands call **`casals new`** when they need a conductor. That call **destroys and re-creates** the Casals stack (new principals) unless it is passed existing IDs and upgrades in place.

- **Destroy and re-create** — recover cycles, delete, mint a new canister (new principal).
- **Reinstall (keep principal)** — wipe code/state on the same ID. Required for DNS.
- **Destroy** — recover cycles and delete; do not mint a replacement in this command.

DNS keep-ID canisters: **`realm-registry-frontend`** (`*.gos.earth`) and **`marketplace-frontend`** (`*.realmsgos.org`).

A full platform rebuild is **`gaas new` then `realms seed`**. The second command must **adopt** the conductor `gaas new` just created — not run a second destroy/re-create of Casals.

---

## Review

| Topic | Verdict |
|---|---|
| DNS pair | Only those two frontends keep their principal. Backends may be new IDs. |
| Casals on both commands | Correct for a **standalone** run. Sequential full rebuild: `gaas new` creates Casals; `realms seed` must **not** destroy it again. |
| `infra-baton` / `realm-installer` | GaaS-owned; destroy and re-create in `gaas new`. |
| Fleet `file-registry` + frontend | Product-owned; destroy and re-create in `realms seed`. Different from Casals’ own file-registry. |
| Token / NFT backends **and** frontends | Product-owned; destroy and re-create in `realms seed`. |
| Realms / quarters | `gaas new` destroys them. It does not provision replacements. |
| Sheet deploy | `gaas new` deploys `gos-as-a-service/casals.json`. `realms seed` deploys the **union** with `realms/casals.json` (must not send Product-only). |
| Token/NFT catalog | Authorize [ic-tokens v0.1.0](https://github.com/smart-social-contracts/ic-tokens/releases/tag/v0.1.0) backends plus certified-assets for the frontends. No new GitHub release required. |

**Not implemented yet:** `realms seed` does not call `casals new`, does not destroy token/nft, and Product-only `sheet deploy` would stop GaaS infra. Steps below are the **target** pipeline.

---

## `gaas new` — GaaS (`*.gos.earth`)

### Canisters

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

### Steps

1. **Destroy except `realm-registry-frontend`** — sweep cycles, delete Casals stack, `infra-baton`, installer, registry backend, all realm/quarter canisters. Leave the DNS frontend ID.
2. **Validate** descriptor, identity, cycles.
3. **`casals new`** — mint a new conductor (`casals-backend`, `casals-frontend`, Casals file-registry backend/frontend, then sheet-mint `casals-multisig` / `infra-baton` as the GaaS sheet requires).
4. **Create** `realm-installer` and `realm-registry-backend` (new principals). **Adopt** `realm-registry-frontend`.
5. **Install backends** (reinstall on the new installer + registry backend).
6. **Configure backends**.
7. **Seed Casals file-registry** with GOS / orchestration WASM namespaces.
8. **Namespace approvals**.
9. **Seed conductor**
   - authorize orchestration + GOS WASMs in the catalog
   - `casals sheet deploy` of `gos-as-a-service/casals.json`
   - `register_canister` for installer, registry backend, registry frontend
   - do **not** put fleet `file-registry` on an Infra stand
   - grant installer Deployments commander
10. **Prime cycles snapshot**.
11. **Configure multisig signers**.
12. **Build + install `realm-registry-frontend`** onto the **same** DNS principal.
13. **Domain wiring** (`*.gos.earth`).
14. **Smoke checks**.
15. **Grant commanders**.
16. **Controller topology**.

---

## `realms seed` — Realms GOS (`*.realmsgos.org`)

### Canisters

| Canister | Action |
|---|---|
| `casals-backend` | destroy and re-create (`casals new`) — **standalone only**; adopt if `gaas new` already ran |
| `casals-frontend` | destroy and re-create (`casals new`) — standalone only |
| `casals-multisig` | destroy and re-create (`casals new`) — standalone only |
| `casals-file-registry-backend` | destroy and re-create (`casals new`) — standalone only |
| `casals-file-registry-frontend` | destroy and re-create (`casals new`) — standalone only |
| `file-registry` (fleet) | destroy and re-create |
| `file-registry-frontend` | destroy and re-create |
| `marketplace-backend` | destroy and re-create |
| `marketplace-frontend` | **reinstall (keep principal for DNS)** |
| `token-backend` | destroy and re-create |
| `token-frontend` | destroy and re-create |
| `nft-backend` | destroy and re-create |
| `nft-frontend` | destroy and re-create |

### Steps

1. **Destroy except `marketplace-frontend`** — sweep cycles, delete fleet file-registry (backend + frontend), marketplace backend, token backend/frontend, nft backend/frontend. Leave the DNS frontend ID. If this is a **standalone** seed (no prior `gaas new`), also destroy the Casals stack here. If `gaas new` already ran, **skip** Casals destroy.
2. **`casals new`** — standalone: mint a new conductor. After `gaas new`: **adopt** the existing conductor IDs (upgrade, do not delete).
3. **Create** new principals for fleet file-registry, file-registry frontend, marketplace backend, token backend/frontend, nft backend/frontend. **Adopt** `marketplace-frontend`.
4. **dfx install (reinstall)** those product canisters. Token/NFT backends from ic-tokens v0.1.0; frontends are certified-assets.
5. **Authorize** marketplace, file-registry, token, nft WASMs in the Casals catalog (and certified-assets for UIs).
6. **Register** product canister IDs on the conductor (Product stands: marketplace, file-registry, token, nft). Include the DNS frontend so sheet deploy does not stop it.
7. **`casals sheet deploy` the union** of the live GaaS sheet and `realms/casals.json`. Reinstalls listed product canisters in place. Must not deploy Product-only JSON.
8. **Publish** extension/codex catalog (and branding) into the **fleet** `file-registry`.
