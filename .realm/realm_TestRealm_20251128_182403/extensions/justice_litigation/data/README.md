# Justice Litigation Extension Data

This directory contains initial data for the justice litigation extension.

## litigation_data.json

Contains sample litigation/dispute cases that will be loaded into the database during realm deployment.

### Data Structure

The file follows the GGG entity format for Dispute entities. Each dispute record includes:

- **_type**: "Dispute"
- **_id**: Unique identifier for the entity
- **Standard fields**: timestamp_created, timestamp_updated, creator, updater, owner
- **Entity-specific fields**:
  - dispute_id: Human-readable dispute ID (e.g., "lit_001")
  - requester: Reference to User entity ID (the party initiating the dispute)
  - defendant: Reference to User entity ID (the party being disputed against)
  - case_title: Title of the litigation case
  - description: Detailed description of the dispute
  - status: Case status (pending, mediation, resolved, appealed, dismissed, in_review)
  - verdict: Verdict or resolution (can be codex function call or empty string)
  - actions_taken: JSON array string of actions taken (e.g., ["verdict_rendered", "case_closed"])
  - metadata: Additional metadata as JSON string

### Loading Data

This data is automatically loaded during realm deployment via the automatic extension data loading feature.

When you run `realms realm create --deploy`, the system will:
1. Discover all `extensions/*/data/*.json` files
2. Import them automatically into the database

### Notes

- The `requester` and `defendant` fields reference existing User entity IDs
- Default sample data uses user IDs "3" and "4" (user_001 and user_002)
- `actions_taken` is stored as a JSON array string
- Verdicts can include codex function calls like `transfer(defendant, requester, 1000, 'Compensation')`
- Status values: pending, mediation, resolved, appealed, dismissed, in_review
- Adjust user references based on your actual realm data
