# Marketplace v2 (Basilisk, file_registry-backed)

The realms marketplace is a pair of standalone canisters that lets users
discover, publish, like, and purchase **extensions** and **codices**
without rebuilding any realm. It sits on top of the existing
`file_registry` canister: the marketplace itself stores only metadata
and a pointer; the actual artifact files (extension bundles, codex `*.py`
modules) live in the registry.

## Canisters

| Canister | Path | Purpose |
|---|---|---|
| `marketplace_backend` | `src/marketplace_backend/` (Basilisk Python) | Listings, likes, rankings, purchases, audit/verification status, developer licenses, off-chain billing-service integration. |
| `marketplace_frontend` | `src/marketplace_frontend/` (SvelteKit static) | Top Charts homepage, browse/detail/upload pages, My Purchases, Developer dashboard, Admin / curator queue. |
| `file_registry` | `src/file_registry/` | Holds the actual extension/codex files. Marketplace listings carry `(file_registry_canister_id, file_registry_namespace)` pointers into it. |

The marketplace runs on the same dfx replica as a realms mundus. Deploy it via:

```bash
realms marketplace deploy --network local
# or
realms marketplace deploy --network ic --identity my-pem \
    --file-registry-canister-id <FR_ID> \
    --billing-service-principal <BILLING_PRINCIPAL>
```

## What you get

### Two kinds of listings

- **Extensions** — keyed by `extension_id`, namespace `ext/<id>/<version>`.
- **Codices** — keyed by `codex_id` (may contain a `/` for `realm_type/codex_id`),
  namespace `codex/<id>/<version>`.

Both kinds share:

- `name`, `description`, `version`, `icon`, `categories`, `price_e8s` (display only).
- `installs` and `likes` counters (denormalised; see ranking endpoints).
- `verification_status` (`unverified` / `pending_audit` / `verified` / `rejected`)
  and `verification_notes`.

### Likes

Authenticated users can `like_item("ext"|"codex", item_id)` and
`unlike_item(...)` (idempotent). The listing's `likes` counter mirrors the
row count in `LikeEntity`. `my_likes()` returns the caller's likes.

### Rankings (Top Charts)

Four query endpoints, each returns top-N by the relevant metric and
respects an optional `verified_only` flag:

- `top_extensions_by_downloads(n: nat64, verified_only: bool)`
- `top_extensions_by_likes(n: nat64, verified_only: bool)`
- `top_codices_by_downloads(n: nat64, verified_only: bool)`
- `top_codices_by_likes(n: nat64, verified_only: bool)`

The frontend's homepage exposes them via two toggles
(extensions ⇄ codices, downloads ⇄ likes) plus the verified filter.

### Open uploads

Anyone authenticated with Internet Identity can publish an extension or
codex — no developer license required. The flow is:

1. `marketplace_backend.get_file_registry_canister_id_q()` →
   `<FILE_REGISTRY_ID>`.
2. Browser uploads the file folder directly to the file_registry via
   `store_file` / `store_file_chunk` + `finalize_chunked_file_step`,
   then `publish_namespace`. The first authenticated caller of an
   empty namespace is auto-granted publisher rights by the registry.
3. Browser calls `marketplace_backend.create_extension(...)` or
   `create_codex(...)` with the namespace pointer + metadata.

The marketplace canister itself never writes to the registry — it only
records the pointer.

### Paid developer license + audit/verification

Anyone can publish, but **getting verified** requires a paid annual
developer license. The flow:

1. Developer page POSTs to
   `${BILLING_SERVICE_URL}/marketplace/license/checkout` with their
   principal and a `return_url`. The off-chain billing service
   returns a Stripe checkout URL.
2. After Stripe completes, the billing service webhook calls
   `marketplace_backend.record_license_payment(LicensePaymentInput)`
   from a principal stored in `config.billing_service_principal`. The
   marketplace creates or extends the developer's license.
3. Developer can then `request_audit("ext"|"codex", item_id)` on any
   listing they own. The listing's status flips to `pending_audit`.
4. A controller (Smart Social Contracts curator) calls
   `set_verification_status(item_kind, item_id, "verified" | "rejected", notes)`
   from the Admin page in the marketplace UI. The listing's status
   flips and surfaces the curator notes.
5. `verified_only=true` filters limit Top Charts and browse pages to
   approved items.

For local development the off-chain billing service is usually not
running. Controllers can call `grant_manual_license(principal,
duration_seconds, note)` directly via `dfx canister call` or the Admin
page's "Grant manual license" form.

## Authorisation matrix

| Endpoint | Caller |
|---|---|
| All `*_q` queries, browse / search / status / get_*_details / has_purchased / has_liked / my_likes / my_purchases / get_my_*  | open |
| `create_extension`, `create_codex`, `update_extension`, `update_codex`, `buy_*`, `like_*`, `unlike_*` | any II principal |
| `delist_*` | listing owner OR controller |
| `request_audit` | active license + listing owner |
| `record_license_payment` | controller OR `config.billing_service_principal` |
| `grant_manual_license`, `revoke_license`, `set_verification_status`, `set_*_canister_id`, `set_billing_service_principal`, `set_license_pricing`, `list_pending_audits`, `recount_listing_likes` | controller-only |

`request_audit` requires both ownership and a license — the license is
the gate to even enter the audit queue.

## Data model

Stable storage uses ic_python_db Entities:

- `ExtensionListingEntity` — keyed by `extension_id`.
- `CodexListingEntity` — keyed by a slash-safe alias (`syntropia/membership` ↔ `syntropia__membership`). Original id is preserved as a separate field.
- `PurchaseEntity` — one row per `buy_*` call. `item_kind = "ext" | "codex"`.
- `LikeEntity` — one row per `(principal, item_kind, item_id)` tuple, composite key `"{principal}|{kind}|{id}"`.
- `DeveloperLicenseEntity` — keyed by principal.
- `MarketplaceConfigEntity` — singleton (`alias = "config"`) holding the file_registry canister id, billing service principal, and license pricing.

## CLI

```bash
realms marketplace deploy [--network local|staging|ic]
                          [--mode auto|install|upgrade|reinstall]
                          [--identity NAME-OR-PEM]
                          [--with-registry / --no-with-registry]
                          [--file-registry-canister-id ID]
                          [--billing-service-principal PRINCIPAL]

realms marketplace status [--network ...]
realms marketplace call <method> [args] [--network ...] [--canister-id ID]
                        [--output json|candid] [--verbose]
```

## Off-chain billing service contract

The Stripe leg of the license-payment flow is handled by an off-chain
service (the same one that powers `realm_registry_backend.add_credits`,
running at `https://billing.realmsgos.dev`). Two endpoints power the
marketplace integration:

- `POST /marketplace/license/checkout`

  Request body:

  ```json
  {
    "principal_id": "<II principal text>",
    "return_url": "https://<marketplace_frontend>/developer?license_status=success",
    "marketplace_canister_id": "<canister id>"
  }
  ```

  Response:

  ```json
  { "checkout_url": "https://checkout.stripe.com/..." }
  ```

- `POST /marketplace/license/webhook` (Stripe → service)

  On Stripe success the service calls
  `marketplace_backend.record_license_payment(record { principal = ...; stripe_session_id = ...; duration_seconds = ...; payment_method = "stripe"; note = "" })`
  from the principal stored in `config.billing_service_principal`.

The service's principal must be configured on the marketplace via
`set_billing_service_principal(<principal>)` from a controller. The
local equivalent is `grant_manual_license`.

## Migration from v1 (Kybra)

The previous marketplace shipped as `kybra-simple-marketplace` (a
separate GitHub repo) and was pulled into the realms `dfx.json` as a
remote-WASM canister. v2 replaces that entirely:

- Builds locally via `python -m basilisk marketplace_backend …`,
  matching every other backend canister in this repo.
- Lives in `src/marketplace_*` (no longer in the
  `realms-extensions` submodule).
- Switched from a static build-time `extensions.json` snapshot to live,
  on-chain listings.

Existing demo/staging canister IDs (`ehyfg-wyaaa-aaaae-qg3qq-cai`) are
no longer pinned in `dfx.json` — first deploy on each network allocates
fresh ids.

## Testing

Unit tests in `tests/backend/marketplace/` cover all business logic
(34 tests including ranking ordering, like idempotency, license
expiry, and verification authorisation). Run with:

```bash
pytest tests/backend/marketplace -q
```

Local end-to-end smoke (requires `dfx` + `python -m basilisk install-dfx-extension`):

```bash
dfx start --background --clean
realms marketplace deploy --network local
MP=$(dfx canister id marketplace_backend)
dfx canister call $MP status
dfx canister call $MP create_extension '(record {
  extension_id = "demo"; name = "Demo"; description = "test";
  version = "0.1.0"; price_e8s = 0 : nat64; icon = "🧩";
  categories = "other";
  file_registry_canister_id = "'$(dfx canister id file_registry)'";
  file_registry_namespace = "ext/demo/0.1.0";
  download_url = "";
})'
dfx canister call $MP buy_extension '("demo")'
dfx canister call $MP like_item '("ext", "demo")'
dfx canister call $MP top_extensions_by_likes '(20 : nat64, false)'
```

Then visit the marketplace_frontend URL printed by `dfx deploy` to
exercise the UI.
