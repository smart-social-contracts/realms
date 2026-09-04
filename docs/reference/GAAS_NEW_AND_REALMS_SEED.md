# `gaas new` and `realms seed` — canister actions

Operator checklist (descriptor conductor id, inventories, installer, credits): [GAAS_NEW_REALMS_SEED_RUNBOOK.md](./GAAS_NEW_REALMS_SEED_RUNBOOK.md).

A full platform rebuild is **`gaas new` then `realms seed`**. That leaves **two independent Casals instances** on the environment:

| Instance | Created by | Survives the other command? | Orchestra |
|---|---|---|---|
| **GaaS Casals** | `gaas new` | Yes — `realms seed` must not touch it | Infra: infra-baton, installer, registry backend/frontend; later realms/quarters |
| **Realms GOS Casals** | `realms seed` | Yes — default seed adopts; `--rebuild` destroys **this** stack and mints another | Product: fleet file-registry, marketplace, token, nft |

Each instance has its own backend, frontend, Casals file-registry, authorized-WASM catalog, and sheet. There is **no shared conductor** and **no union sheet**.

- **`gaas new`** deploys `gos-as-a-service/casals.json` onto **GaaS Casals** only.
- **`realms seed`** deploys `realms/casals.json` onto **Realms GOS Casals** only.

Inventories are separate. GaaS Casals principals live in the GaaS descriptor / GaaS `canister_ids`. Product Casals principals live in Realms `canister_ids.json` / `environments/<env>.json`. Seed destroy matches **product** IDs only.

Both commands can call **`casals new`** for **their** instance when an operator opts into a full rebuild (`gaas new --destroy-except-realm-registry-frontend`; `realms seed --rebuild`). Default `realms seed` adopts the existing Realms GOS conductor and product canisters instead.

- **Destroy and re-create** — recover cycles, delete, mint a new canister (new principal).
- **Reinstall (keep principal)** — wipe code/state on the same ID. Required for DNS.
- **Destroy** — recover cycles and delete; do not mint a replacement in this command.

DNS keep-ID canisters: **`realm-registry-frontend`** (`*.gos.earth`) and **`marketplace-frontend`** (`*.realmsgos.org`).

---

## Frontend links to Casals

The two DNS frontends must not bake a Casals principal into WASM / the Vite bundle. Casals can be minted again without rebuilding those frontends.

Each UI reads **its** Casals frontend principal at runtime from a backend that belongs to that product:

| UI | Control | Reads | Written after |
|---|---|---|---|
| GaaS portal (`*.gos.earth`) → **Infrastructure** | GaaS Casals frontend (`https://<id>.icp0.io`) | Registry backend `get_runtime_flags.casals_frontend_canister_id` | `gaas new` (`set_canister_config_json` on the registry) |
| Marketplace (`*.realmsgos.org`) → footer conductor icon | Realms GOS Casals frontend | Marketplace backend runtime config (`casals_frontend_canister_id`) | `realms seed` (same idea on the **marketplace** backend) |

The pointers must never share a store or a value. Seed must not overwrite the registry field with the product Casals id. The portal must not query the marketplace backend; the marketplace must not query the registry for this link.

If the pointer is empty, hide the link. Do not fall back to a bake-time `casals_url`.

`environments/<env>.json` `casals_url` is operator inventory of the **Realms GOS** Casals frontend only.

---

## Review

| Topic | Verdict |
|---|---|
| Casals count after a full re-run | **Two**. GaaS Casals from `gaas new`; Realms GOS Casals from `realms seed`. |
| Seed vs GaaS Casals | Seed **does not** destroy, re-create, or sheet-deploy onto GaaS Casals. |
| DNS pair | Only those two frontends keep their principal. Backends may be new IDs. |
| Casals on both commands | GaaS rebuild always destroy-and-re-creates **its** conductor. Realms default seed **adopts** Realms GOS Casals; `--rebuild` destroy-and-re-creates it. Seed never adopts GaaS Casals. |
| `infra-baton` / `realm-installer` | GaaS-owned; destroy and re-create in `gaas new`. |
| Fleet `file-registry` + frontend | Product-owned; default seed adopts; `--rebuild` destroy and re-create. Different from either Casals’ own file-registry. |
| Token / NFT backends **and** frontends | Product-owned; default seed adopts; `--rebuild` destroy and re-create. |
| Realms / quarters | `gaas new` destroys them. It does not provision replacements. |
| Sheet deploy | GaaS sheet on GaaS Casals. Product sheet on Realms GOS Casals. Never a union. Never Product-only on the GaaS conductor (Pass 2 would stop GaaS stands). |
| Token/NFT catalog | Authorize [ic-tokens v0.1.0](https://github.com/smart-social-contracts/ic-tokens/releases/tag/v0.1.0) backends plus certified-assets for the frontends **on Realms GOS Casals**. No new GitHub release required. |
| Casals frontend URLs | Runtime pointers (table above). Not baked into keep-ID frontend WASM. |

**Default (adopt / reconcile):** `realms seed --env test` authorizes product-sheet WASMs on the **existing** Realms GOS Casals conductor, registers product canister IDs from `canister_ids.json`, runs `casals sheet deploy` of `realms/casals.json` (adopt when live hash matches; reinstall only when needed), writes the product Casals frontend principal onto the marketplace backend, and publishes the extension/codex catalog into the fleet `file_registry`. No `delete_canister`. `--skip-product` is catalog-only.

**Destructive rebuild (opt-in):** `realms seed --env test --rebuild --yes` destroys the **Realms GOS** Casals stack (not GaaS Casals), runs `casals new -y --no-seed`, recreates product canisters (DNS keep-ID for `marketplace-frontend`), then the same authorize/register/sheet/catalog steps. `gaas new` still needs `--destroy-except-realm-registry-frontend` for the GaaS orchestra wipe.

---

## `gaas new` — GaaS (`*.gos.earth`)

### Canisters

| Canister | Action |
|---|---|
| GaaS `casals-backend` | destroy and re-create (`casals new`) |
| GaaS `casals-frontend` | destroy and re-create (`casals new`) |
| GaaS `casals-multisig` | destroy and re-create (`casals new`) |
| GaaS `casals-file-registry-backend` | destroy and re-create (`casals new`) |
| GaaS `casals-file-registry-frontend` | destroy and re-create (`casals new`) |
| `infra-baton` | destroy and re-create |
| `realm-installer` | destroy and re-create |
| `realm-registry-backend` | destroy and re-create |
| `realm-registry-frontend` | **reinstall (keep principal for DNS)** |
| `realmN-baton` | destroy |
| `realmN-backend` | destroy |
| `realmN-frontend` | destroy |
| `realmN-quarter*-backend` | destroy |
| … | destroy (every other realm/quarter canister) |

Do **not** create fleet `file-registry`, marketplace, token, or nft. Those belong to `realms seed`. Do **not** destroy Realms GOS Casals or product canisters that a prior seed created (unless they are realm/quarter canisters listed above).

### Steps

1. **Destroy except `realm-registry-frontend`** — sweep cycles, delete **GaaS** Casals stack, `infra-baton`, installer, registry backend, all realm/quarter canisters. Leave the DNS frontend ID. Do not delete Realms GOS Casals or product stands.
2. **Validate** descriptor, identity, cycles.
3. **`casals new`** — mint a new **GaaS** conductor (`casals-backend`, `casals-frontend`, Casals file-registry backend/frontend, then sheet-mint `casals-multisig` / `infra-baton` as the GaaS sheet requires).
4. **Create** `realm-installer` and `realm-registry-backend` (new principals). **Adopt** `realm-registry-frontend`.
5. **Install backends** (reinstall on the new installer + registry backend).
6. **Configure backends**. Write **GaaS** `casals_frontend` into registry `set_canister_config_json` (`casals_frontend_canister_id`) so Infrastructure can resolve it without a frontend WASM rebuild.
7. **Seed Casals file-registry** with GOS / orchestration WASM namespaces (GaaS Casals’ registry, not the fleet).
8. **Namespace approvals**.
9. **Seed conductor**
   - authorize orchestration + GOS WASMs in the **GaaS** catalog
   - `casals sheet deploy` of `gos-as-a-service/casals.json` on **GaaS Casals**
   - `register_canister` for installer, registry backend, registry frontend
   - do **not** put fleet `file-registry` on an Infra stand
   - grant installer Deployments commander
10. **Prime cycles snapshot**.
11. **Configure multisig signers**.
12. **Build + install `realm-registry-frontend`** onto the **same** DNS principal. Do not bake the Casals principal into that bundle.
13. **Domain wiring** (`*.gos.earth`).
14. **Smoke checks**.
15. **Grant commanders**.
16. **Controller topology**.

---

## `realms seed` — Realms GOS (`*.realmsgos.org`)

### Default (no flags)

| Canister | Action |
|---|---|
| Realms GOS `casals-backend` / `casals-frontend` / Casals file-registry | **adopt** (register + sheet reconcile; Casals protects its own stack from sheet reinstall) |
| `file-registry` (fleet) + frontend | **adopt** (register then `deploy_sheet`; create only if missing from inventory) |
| `marketplace-backend` | **adopt** |
| `marketplace-frontend` | **adopt / reinstall (keep principal for DNS)** |
| `token-backend` / `token-frontend` | **adopt** |
| `nft-backend` / `nft-frontend` | **adopt** |
| GaaS Casals (any of its stack) | **leave untouched** |
| `infra-baton` / installer / registry be+fe | **leave untouched** |

### Steps (default)

1. **Authorize** marketplace, fleet file-registry, token, and nft WASMs in the **Realms GOS Casals** catalog (idempotent).
2. **Register** product IDs from `canister_ids.json` on the conductor **before** sheet deploy.
3. **`casals sheet deploy` `realms/casals.json`** — adopts REGISTERED canisters when wasm hash matches; reinstalls only when required. Product section only; conductor Casals/System canisters are not in the sheet.
4. **Publish** Realms GOS Casals frontend principal onto marketplace backend.
5. **Publish** extension/codex catalog (and branding) into fleet `file_registry`.

### `--rebuild` (destructive)

| Canister | Action |
|---|---|
| Realms GOS `casals-backend` | destroy and re-create (`casals new`) |
| Realms GOS `casals-frontend` | destroy and re-create (`casals new`) |
| Realms GOS `casals-multisig` | destroy and re-create (`casals new`) if the product sheet uses one |
| Realms GOS `casals-file-registry-backend` | destroy and re-create (`casals new`) |
| Realms GOS `casals-file-registry-frontend` | destroy and re-create (`casals new`) |
| `file-registry` (fleet) | destroy and re-create |
| `file-registry-frontend` | destroy and re-create |
| `marketplace-backend` | destroy and re-create |
| `marketplace-frontend` | **reinstall (keep principal for DNS)** |
| `token-backend` | destroy and re-create |
| `token-frontend` | destroy and re-create |
| `nft-backend` | destroy and re-create |
| `nft-frontend` | destroy and re-create |
| GaaS Casals (any of its stack) | **leave untouched** |
| `infra-baton` / installer / registry be+fe | **leave untouched** |

### Steps (`--rebuild`)

1. **Destroy except `marketplace-frontend`** — sweep cycles, delete the **Realms GOS** Casals stack, fleet file-registry (backend + frontend), marketplace backend, token backend/frontend, nft backend/frontend. Match product inventory IDs only. Leave the marketplace DNS frontend ID.
2. **`casals new`** — mint a new **Realms GOS** conductor (`casals new -y --no-seed`), seed catalog into **this** Casals file-registry.
3. **Create** new principals for fleet file-registry, file-registry frontend, marketplace backend, token backend/frontend, nft backend/frontend. **Adopt** `marketplace-frontend`.
4. **dfx install (reinstall)** those product canisters.
5. **Authorize**, **register**, **`casals sheet deploy`**, marketplace pointer, catalog — same as default.
