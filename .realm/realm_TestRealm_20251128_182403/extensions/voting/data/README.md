# Voting Extension Data

This directory contains initial data for the voting extension.

## voting_data.json

Contains the initial governance proposals that will be loaded into the database during realm deployment.

### Data Structure

The file follows the same format as `realm_data.json` in the main realm directory. Each record includes:

- **_type**: Entity type (e.g., "Proposal")
- **_id**: Unique identifier for the entity
- **Standard fields**: timestamp_created, timestamp_updated, creator, updater, owner
- **Entity-specific fields**: 
  - proposal_id: Human-readable proposal ID (e.g., "prop_001")
  - title: Proposal title
  - description: Detailed description
  - code_url: URL to the proposal code
  - code_checksum: SHA256 checksum of the code
  - proposer: Reference to User entity ID
  - status: Current status (voting, pending_vote, approved, rejected, etc.)
  - voting_deadline: ISO format timestamp or empty string
  - votes_yes, votes_no, votes_abstain: Vote counts
  - total_voters: Total number of voters
  - required_threshold: Threshold for approval (0.0-1.0)
  - metadata: Additional metadata as JSON string

### Loading Data

To load this data into your realm:

1. **During realm creation** with `realms realm create`:
   ```bash
   realms realm create --random --output-dir my-realm
   ```

2. **During deployment** with `realms realm deploy`:
   The data will be automatically loaded when you run:
   ```bash
   cd my-realm
   realms import extensions/voting/data/voting_data.json
   ```

3. **Manual import**:
   ```bash
   realms import extensions/voting/data/voting_data.json
   ```

### Notes

- The `proposer` field should reference existing User entity IDs in your realm
- The example data uses user IDs "3" and "4" which correspond to user_001 and user_002 in the default realm_data.json
- Adjust the user references based on your actual realm data
