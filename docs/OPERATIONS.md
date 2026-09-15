# Operating the Realms product orchestra

The marketplace, fleet file registry, token, NFT, and the demo realm stand are
declared in [`casals.json`](../casals.json). The Casals runbook
(`Casals/docs/OPERATIONS.md`) is the command reference; this page is what is
specific to this repo.

## Build, then `up`

The sheet references product wasms and frontend dists as `local:` paths.
Build them first (the recipes are the build steps of
[`.github/workflows/release.yml`](../.github/workflows/release.yml)), then
from the Casals repo:

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
