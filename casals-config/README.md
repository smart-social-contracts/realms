# casals-config — realms-owned Casals objects

The [Casals](https://github.com/smart-social-contracts/Casals) orchestrator engine
is vendored into this repo as the `casals/` git submodule. This directory holds the
**realms-specific** Casals objects (configuration, not engine), so the topology and
per-environment config live with the application they describe instead of in the
engine repo.

```
casals-config/
  arrangements/         # post-deploy config overlays applied by Casals
    test.json           #   full fidelity: 3 realms × identity/codex/~28 ext (93 steps)
    test-lite.json      #   fast iteration: 1 realm (Dominion) + 5 core ext (8 steps)
  sheets/               # orchestra topology (reserved; see note below)
  _gen_test_arrangement.py   # regenerates the arrangements from the realm manifests
```

## Arrangements

An *arrangement* is a Casals entity: a declarative, environment-specific post-deploy
overlay (runtime parameters + a list of `{target, method, args}` steps) that Casals
applies after a sheet deploy/reinstall. For realms that means: set runtime test flags,
set each realm's identity (name/manifesto/welcome), and install its codex + extensions
from the file registry. Canisters self-reconcile (download/install); Casals just drives
the steps.

Regenerate after editing the source data:

```bash
python3 casals-config/_gen_test_arrangement.py
```

## Seeding into a Casals environment

Point the (submoduled) engine's seeder at this config directory:

```bash
casals/scripts/seed.py -e ic --identity <id> \
  --config-dir casals-config \
  --arrangement test-lite --arrangement-only
```

`--config-dir` makes `seed.py` read its `arrangements/` (and, if present, `templates.json`,
`templates/`, `assets/`) from here instead of the engine's in-repo `seed/`. The
`casals-upgrade.yml` workflow does this automatically when given `seed_arrangement`.

## Sheets (topology) — note

The live realms topology was built ad-hoc on-chain rather than from a curated sheet
file, so `sheets/` is reserved for a future export/authoring of the realms orchestra
sheet. The authorized-WASM **catalog** stays managed by `publish-build.yml`, not here.
