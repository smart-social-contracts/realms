# Demo Realm Configuration Files

This folder contains sample configuration and codex files used by the `realms create` command to generate demo realm instances.

## Configuration Files

### `manifest.json`
Realm configuration with entity method overrides:
- Defines the realm name (updated dynamically during generation)
- Specifies entity method overrides (e.g., `user_register_posthook`)
- Links to custom codex implementations for lifecycle hooks

### `adjustments.py`
Post-deployment adjustment script:
- Loads `manifest.json` and applies entity method overrides to the Realm
- Prints entity counts for verification (Realm, Treasury, Users, Codex, etc.)
- Runs after data upload to configure the deployed realm canister

## Codex Files

### 1. `tax_collection_codex.py`
Automated tax collection system with progressive tax rates:
- Calculates taxes based on user income from transfers
- Progressive rates: 10% (≤10K), 20% (≤50K), 30% (>50K)
- Automatically creates tax payment transfers to the system account

### 2. `social_benefits_codex.py`
Social benefits distribution system:
- Checks member eligibility based on residence, tax compliance, and identity verification
- Calculates benefit amounts based on member status
- Automatically distributes benefits to eligible members

### 3. `governance_automation_codex.py`
Democratic governance automation:
- Creates and manages governance proposals
- Processes votes and determines outcomes
- Tallies results and closes proposals after voting deadline

### 4. `user_registration_hook_codex.py`
Custom user registration hook:
- Overrides the default `user_register_posthook` method
- Creates a 1 ckBTC welcome invoice for new users
- Invoice expires in 5 minutes with unique subaccount

## Usage

These files are automatically copied when running:
```bash
realms create --random --members 100 --organizations 10
```

The `realm_generator.py` script copies these files from `examples/demo/` to the generated realm directory, where they can be imported into the realm canister.

## Customization

You can modify these files to create your own demo scenarios:
1. Edit the codex files in this folder
2. Run `realms create` to generate a new realm with your custom codex files
3. The updated files will be automatically copied to your new realm

## Single Source of Truth

These files serve as the canonical examples for realm codex automation. Any changes made here will automatically propagate to all newly created demo realms, ensuring consistency and maintainability.
