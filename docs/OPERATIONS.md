# Operating the Realms product orchestra

The marketplace, fleet file registry, token, NFT, and the demo realm stand are
declared in [`casals.json`](../casals.json). The Casals runbook
(`Casals/docs/OPERATIONS.md`) is the command reference; this page is what is
specific to this repo.

## Build, then `up`

The sheet references product wasms and frontend dists as `local:` paths.
Build them first (the recipes are the build steps of
[`.github/workflows/release.yml`](../.github/workflows/release.yml)). basilisk
bundles whatever Python packages are installed, so install the pinned
[`requirements.txt`](../requirements.txt) before building: a stale
`ic-python-db` produces a wasm that traps at init (the conductor then
re-downloads and re-installs it every tick without ever converging).

Build the realm halves as the variant the environment declares
(`environments.<env>.build_variant`): `local` is `test`
(`scripts/pack_realm_backend.py --variant test`, `REALMS_BUILD_VARIANT=test npm
run build`), `production` is `production` (the defaults). The demo stand's
`converged_when` asserts `build_variant` from `get_runtime_flags`, so the wrong
variant never converges instead of quietly refusing (or quietly accepting) test
flags. Then, from the Casals repo:

```sh
python -m casals_cli.main -e local --identity local-dev up ../realms/casals.json --yes
```

The same command with `-e production` and the environment's deployer identity
is the production procedure. Environment differences (principals, DNS, flags)
live in the sheet's `environments` block. Two things production needs on top:

- **Pins.** `up -e production` requires a `sha256` on every `registry.wasms`
  row *and* every `registry.publish` row (the frontend bundles: their hash is
  the *bundle hash* of `Casals/docs/BUNDLES.md`). After building, `casals pin
  casals.json` writes both; `casals pin --check` in CI catches drift.
- **Bindings and the key.** Every command after the first `up` reads the
  conductor id from `$CASALS_HOME/<orchestra>.production.json`; point
  `CASALS_HOME` at the directory that holds it, or `up` will think there is no
  conductor and stop (it refuses to bootstrap a second production conductor
  without `--bootstrap`). With a touch-policy hardware key as `--identity`,
  add `--upload-identity <plaintext identity>` so the hundreds of store
  uploads of step 4 do not each ask for a touch; the key still signs
  bootstrap, `set_sheet` and every apply. The CLI prints `signing <method> as
  <identity>` before each HSM call so you know when to touch.

## Updating a frontend (marketplace, demo realm)

A frontend canister serves exactly the bundle its `content` names, so a new
build is a new bundle, not a new canister:

```sh
# realms/: build, then pack the dist into a canonical hashed bundle
casals bundle src/marketplace_frontend/dist -o marketplace-<version>.tgz   # prints the bundle sha256
```

Then either edit the sheet (`registry.publish` row → `local:marketplace-<version>.tgz`
+ its `sha256`, or a release asset URL) and `up` — or, without the CLI or the
deployer key at all, as a commander with `wasm.upload` + `sheet.apply`: Casals
frontend → **Files → Upload bundle** (pick the `dist/` folder or the `.tgz`;
hashing, diff against the store and the one-batch upload happen in the
browser) → **Pin in sheet** → **Plan / Drift → Apply** the `sync_assets`
item. The same page shows, per bundle, whether the store matches the pin and
which canisters serve it.

`Realms/demo` (the demo realm: real realm wasm + realm frontend bundle) is
the stand you usually do *not* want dragged along by a marketplace fix. Mark
it `"sync": "manual"` in the sheet: `plan`/`up` then report its drift under
*manual* and leave it alone, and you deploy it on purpose with
`casals up casals.json --stand demo` (its `content` must be pinned — the guard
for a stand nothing reconciles routinely).

Realm *instances* that users deploy through the GaaS portal are stands of the
**GaaS** orchestra, not this one. See `gos-as-a-service/docs/OPERATIONS.md`.

## Custom domain, after `up`

`casals up` does not touch DNS (`domains` reports `unverifiable`). The sheet's
`domains` block (`realmsgos.org` → `marketplace-frontend`) is applied by the
product CLI, which reads the canister id from the conductor:

```sh
# from realms/, with CASALS_HOME pointing at the bindings `casals up` wrote
realms domains check casals.json -e production            # read-only, exit 1 on drift
export CLOUDFLARE_API_TOKEN=…                             # Zone:Read + DNS:Edit on the zone; never commit it
realms domains apply casals.json -e production            # Cloudflare records → IC gateway registration → HTTP 200
```

`apply` is idempotent and is what a re-minted frontend needs: it rewrites the
`_canister-id` TXT record and re-points (`PATCH`) the existing gateway
registration, then waits until `https://<host>/` answers. Run it **before**
destroying the previous frontend — the gateway validates the new canister's
`/.well-known/ic-domains`, and the old canister's disappearance is what takes
the site down. The same command serves the GaaS sheet
(`realms domains apply ../gos-as-a-service/casals.json -e production`).

## Content, after `up`

`casals up` provisions canisters; it does not put packages in them. The
controllers of every product canister are the conductor and the multisig,
so the sheet grants the **operator** (`environments.<env>.principals.operator`)
what the product CLI needs, through config rows the conductor applies:

| canister | row | gives the operator |
|---|---|---|
| `fleet-file-registry` | `grant_publish {namespace: "*"}` | upload to every namespace (`realms files publish`) |
| `fleet-file-registry` | `grant_publish {namespace: "_approvers"}` → marketplace | lets `review_listing` stamp approvals on the registry |
| `marketplace-backend` | `admin_grant_publisher {reviewer: true}` | developer license (to submit) + reviewer seat (to approve) |

Then, with the operator identity (a hardware key: `export DFX_HSM_PIN=…`
first; the CLI passes it to every `icp` call):

```sh
# ids from the live conductor, never from a table in the repo
casals -e production export casals.json          # bindings: fleet-file-registry, marketplace-backend

# packages the marketplace lists (its listings name this registry)
realms files publish -n ic --registry <fleet-file-registry> --identity prod-identity
realms marketplace publish -n ic --marketplace <marketplace-backend> --registry <fleet-file-registry> --identity prod-identity
```

`marketplace publish` creates or updates a listing for every first-party
extension and codex (the same set `files publish` uploads) and approves it as
reviewer; a listing ends `verified` only when the registry accepted the
approval stamp. Re-running either command is idempotent (unchanged files are
skipped, listings are upserted).

Packages that realms **install** through the GaaS portal are fetched from the
GaaS orchestra's own `file-registry` (its installer's `file_registry_id`), so
they are published there too — see `gos-as-a-service/docs/OPERATIONS.md`.

CI (`realms-e2e.yml`) runs this chain on the converged local orchestra and
fails when a listing does not come back `verified`.

## Checks

```sh
# from Casals/
KEEP=1 SCENARIOS=fresh,idempotent python tests/e2e/run_e2e.py ../realms/casals.json
casals -e local oracle ../realms/casals.json
```

The `realms` CLI (db, files publish, registry, billing, quarter commands)
is a product CLI. It does not provision canisters — that is `casals up`.
