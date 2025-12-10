# Shared Realm Codex Files

This folder contains common configuration and codex files shared by all demo realms (realm1, realm2, realm3, etc.).

## Purpose

These files serve as a **single source of truth** for realm automation logic. Any changes here will apply to all realms that reference these files.

## Shared Files

### Configuration

#### `adjustments.py`
Post-deployment adjustment script that:
- Loads the realm's `manifest.json` and applies entity method overrides
- Updates realm name and logo from manifest
- Prints entity counts for verification

### Codex Files

#### `tax_collection_codex.py`
Automated tax collection system with progressive tax rates:
- Calculates taxes based on user income from transfers
- Progressive rates: 10% (≤10K), 20% (≤50K), 30% (>50K)
- Automatically creates tax payment transfers to the system account

#### `social_benefits_codex.py`
Social benefits distribution system:
- Checks member eligibility based on residence, tax compliance, and identity verification
- Calculates benefit amounts based on member status
- Automatically distributes benefits to eligible members

#### `governance_automation_codex.py`
Democratic governance automation:
- Creates and manages governance proposals
- Processes votes and determines outcomes
- Tallies results and closes proposals after voting deadline

#### `satoshi_transfer_codex.py`
Scheduled satoshi transfer task:
- Sends 1 satoshi to a configured target principal per execution
- Designed to run as a scheduled task
- Creates transfer records and executes via vault extension

#### `user_registration_hook_codex.py`
Custom user registration hook:
- Overrides the default `user_register_posthook` method
- Creates a 1 ckBTC welcome invoice for new users
- Invoice expires in 5 minutes with unique subaccount

## Realm-Specific Files

The following files remain in each realm's directory as they are unique per realm:

| File | Description |
|------|-------------|
| `manifest.json` | Realm name, options, seed, and method overrides |
| `logo.svg` | Realm-specific logo |
| `canister_ids.json` | Deployment-specific canister IDs |

## Usage

When creating a new realm, these shared files can be:
1. Symlinked from this directory
2. Copied during realm generation
3. Referenced directly by the realm's deployment scripts

The `realm_generator.py` script will use these files as templates when creating new demo realms.

## Customization

To customize behavior for a specific realm without affecting others:
1. Copy the relevant file to the realm's directory
2. Modify the copy as needed
3. The realm-specific version will take precedence

## Contributing

When modifying shared codex files:
1. Test changes across all demo realms
2. Ensure backward compatibility
3. Update this README if adding new shared files
