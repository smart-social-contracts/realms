# Vendored Candid declarations for GaaS canisters

The directories `realm_registry_backend/` and `realm_installer/` contain
Candid interface files and generated JS/TS bindings vendored from
[smart-social-contracts/gos-as-a-service](https://github.com/smart-social-contracts/gos-as-a-service)
release artifacts.

Source `.did` files live under `src/gos-vendor/<canister>/` (not here) so
`dfx generate` can refresh bindings in this tree without deleting the candid
input. Refresh both trees when bumping the GOS release pin in `dfx.json` and
`scripts/fetch_gos_artifacts.py` (`GOS_RELEASE`).
