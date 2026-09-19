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

The same command with `-e ic` and the environment's deployer identity is the
production procedure. Environment differences (principals, DNS, flags) live
in the sheet's `environments` block.

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

## Checks

```sh
# from Casals/
KEEP=1 SCENARIOS=fresh,idempotent python tests/e2e/run_e2e.py ../realms/casals.json
casals -e local oracle ../realms/casals.json
```

The `realms` CLI (db, files publish, registry, billing, quarter commands)
is a product CLI. It does not provision canisters — that is `casals up`.
