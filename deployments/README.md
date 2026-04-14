# Deployment Descriptors

Each `.yml` file defines a deployment target for `realms deploy --file deployments/<file>.yml`.

## Environments

| Environment | Purpose |
|-------------|---------|
| **demo**    | Showcasing to prospective users and quick testing |
| **uat**     | User Acceptance Testing |
| **staging** | Manual testing and development |
| **ci**      | Automated CI workflows |

## Naming Convention

- `<env>-mundus.yml` — Full mundus deploy (all backends + frontend + extensions + data)
- `<env>-<canister>.yml` — Single canister deploy (e.g., `staging-realm1-backend.yml`)
