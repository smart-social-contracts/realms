# Voting Extension Database Migration

## Overview

The voting extension has been migrated from hardcoded data to using GGG (Generalized Global Governance) entities stored in the database.

## Changes Made

### 1. Enhanced GGG Entity Definitions

**File: `src/realm_backend/ggg/proposal.py`**
- Added comprehensive fields for governance proposals:
  - `proposal_id`: Unique identifier (e.g., "prop_001")
  - `title`: Proposal title
  - `description`: Detailed description
  - `code_url`: URL to proposal code
  - `code_checksum`: SHA256 checksum
  - `proposer`: Reference to User entity
  - `status`: Current status (voting, pending_vote, etc.)
  - `voting_deadline`: ISO timestamp
  - Vote counts: `votes_yes`, `votes_no`, `votes_abstain`
  - `total_voters`: Number of voters
  - `required_threshold`: Approval threshold
  - `metadata`: Additional data

**File: `src/realm_backend/ggg/vote.py`**
- Added fields to track individual votes:
  - `proposal`: Reference to Proposal entity
  - `voter`: Reference to User entity
  - `vote_choice`: Choice ('yes', 'no', 'abstain')
  - `metadata`: Additional data

**File: `src/realm_backend/ggg/user.py`**
- Added relationships:
  - `proposals`: OneToMany relationship to Proposal
  - `votes`: OneToMany relationship to Vote

### 2. Created Initial Data File

**File: `extensions/voting/data/voting_data.json`**
- Contains initial proposal data in the same format as `realm_data.json`
- Includes two sample proposals matching the previous hardcoded data
- References existing user entities (user_001 and user_002)

### 3. Updated Backend Implementation

**File: `extensions/voting/backend/entry.py`**
- Replaced hardcoded `DUMMY_PROPOSALS` with database queries
- All functions now use `Proposal.instances()`, `User.instances()`, and `Vote.instances()`
- Added proper error handling and logging
- Functions updated:
  - `get_proposals()`: Loads proposals from database with optional filtering
  - `get_proposal()`: Retrieves single proposal by ID
  - `submit_proposal()`: Creates new proposal entity in database
  - `cast_vote()`: Creates/updates vote entities and updates proposal vote counts

## Migration Steps

### For New Realms

1. Create a new realm:
   ```bash
   realms realm create --random --output-dir my-realm
   ```

2. Import the voting data:
   ```bash
   cd my-realm
   realms import extensions/voting/data/voting_data.json
   ```

### For Existing Realms

1. Clear the Kybra build cache:
   ```bash
   rm -rf .kybra/realm_backend
   ```

2. Redeploy the realm:
   ```bash
   realms realm deploy
   ```

3. Import the voting data:
   ```bash
   realms import extensions/voting/data/voting_data.json
   ```

## Data Format

The `voting_data.json` follows the standard GGG entity format:

```json
{
  "timestamp_created": "2024-01-15 10:00:00.000",
  "timestamp_updated": "2024-01-15 10:00:00.000",
  "creator": "system",
  "updater": "system",
  "owner": "system",
  "_type": "Proposal",
  "_id": "1",
  "proposal_id": "prop_001",
  "title": "Proposal Title",
  "description": "Detailed description",
  "code_url": "https://github.com/example/proposal.py",
  "code_checksum": "sha256:...",
  "proposer": "3",
  "status": "voting",
  "voting_deadline": "2024-01-22T10:00:00Z",
  "votes_yes": 15.0,
  "votes_no": 3.0,
  "votes_abstain": 2.0,
  "total_voters": 20.0,
  "required_threshold": 0.6,
  "metadata": "{}"
}
```

## Benefits

1. **Persistent Storage**: Proposals and votes are now stored in the database
2. **Consistency**: Uses the same entity system as other realm components
3. **Relationships**: Proper relationships between Users, Proposals, and Votes
4. **Scalability**: Can handle large numbers of proposals and votes
5. **Data Import**: Can load initial data via standard `realms import` command

## Testing

After migration, verify that:

1. Proposals are loaded correctly:
   - Navigate to the Voting page in the UI
   - Verify that proposals are displayed

2. Voting functionality works:
   - Try casting a vote on a proposal
   - Verify vote counts update correctly

3. Proposal submission works:
   - Try creating a new proposal
   - Verify it appears in the proposal list

## Troubleshooting

**Issue**: Proposals not showing up
- Solution: Ensure voting_data.json has been imported and the user IDs in the `proposer` field exist

**Issue**: Build errors about missing imports
- Solution: Clear Kybra cache with `rm -rf .kybra/realm_backend` and rebuild

**Issue**: Vote casting fails
- Solution: Check that the user and proposal entities exist in the database
