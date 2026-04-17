# Deployment Descriptors (v2)

Mundus descriptors describe the **entire** deployment of a realms ecosystem
in a single YAML file: which infrastructure canisters to bootstrap (file
registry, realm installer), what artifacts to publish (base WASM,
extensions, codices), and which mundus members (registry + N realms) to
install.

A descriptor is consumed end-to-end by:

```bash
python scripts/ci_install_mundus.py --file <descriptor>.yml --stages 0,1,2,3
```

The same script is the only thing every CI workflow ever calls; the
workflows are just thin shells that pick a descriptor and a stage subset.

## Files

| File | Purpose |
|------|---------|
| `local-mundus.yml`            | Ephemeral mundus on the local replica. Used by `ci-pr.yml` (every PR) and `ci-main.yml` Phase A (gating). |
| `staging-mundus-layered.yml`  | Long-lived staging mundus on the IC staging subnet. Used by `ci-main.yml` Phase B and `layered-deploy-dominion.yml`. |

That's it. Per-canister descriptors (`staging-realm1-backend.yml`, etc.)
no longer exist — everything goes through the unified mundus descriptor.

## Schema (v2)

```yaml
version: 2
network: local | staging | ic

# Optional. Pin pre-existing infra canister ids. If absent on a network,
# stage 0 will create them via dfx.
infrastructure_overrides:
  file_registry:           { canister_id: <…> }
  file_registry_frontend:  { canister_id: <…> }
  realm_installer:         { canister_id: <…> }

# Stage 1: what to publish to file_registry.
artifacts:
  base_wasm:
    source: src/realm_backend
    version: "0.5.0"           # also accepts ${{ github.sha }} via env interpolation
  extensions: all              # or [voting, vault, …]
  codices:    all              # or [basic_governance, …]

# Stage 2: who lives in the mundus.
mundus:
  - name: registry
    type: realm_registry
    canister_id: <pinned id, optional>
    extensions: []
    codices:    []
  - name: dominion
    type: realm
    canister_id: <pinned id>
    manifest:   examples/demo/dominion/manifest.json
    seed_data:  examples/demo/dominion/data.json
    extensions: inherit_from_artifacts   # or explicit list
    codices:    inherit_from_artifacts

# Stage 3: how to verify.
verify:
  e2e_specs:
    - src/realm_frontend/tests/e2e/specs/layered-parity.spec.ts
  integration_tests:
    - tests/backend/test_status_api.py
```

## Stages

| Stage | Action | Skipped when |
|-------|--------|--------------|
| 0 | Bootstrap infrastructure (file_registry, realm_installer, file_registry_frontend) via `dfx`. | The descriptor pins the canister ids in `infrastructure_overrides` AND they already respond. |
| 1 | Build base WASM + every per-extension `frontend-rt/` bundle, then publish base WASM + extensions + codices to file_registry. | `artifacts:` is empty. |
| 2 | For each mundus member: ensure canister exists, add realm_installer as controller, `realms wasm install`, `realms extension registry-install` ×N, `realms codex registry-install` ×N. | `mundus:` is empty. |
| 3 | Per-member seed data upload + Playwright/integration test smoke. | `verify:` is empty. |

Stages compose: PR CI runs all four against `local`; main CI runs all four
against `local` (gating) then 1+2+3 against `staging` (deploy).

## Environment placeholder syntax

Anywhere in the YAML you can write `${ENV_VAR}` — values are substituted
at load time by `scripts/ci_install_mundus.py`. GitHub Actions
`${{ vars.X }}` / `${{ inputs.X }}` are pre-expanded by the runner before
the script ever sees them.
