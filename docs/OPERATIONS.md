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

## Checks

```sh
# from Casals/
KEEP=1 SCENARIOS=fresh,idempotent python tests/e2e/run_e2e.py ../realms/casals.json
casals -e local oracle ../realms/casals.json
```

The `realms` CLI (db, files publish, registry, billing, quarter commands)
is a product CLI. It does not provision canisters — that is `casals up`.
