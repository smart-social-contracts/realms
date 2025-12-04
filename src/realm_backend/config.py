"""
Realm Backend Configuration

This file contains canister IDs for external services used by the realm backend.
Values are updated during deployment from deployment.json.

For local development, these default to IC mainnet values.
During deployment, the deploy script updates these with actual canister IDs.
"""

# Shared canister IDs - updated during deployment
CANISTER_IDS = {
    # ckBTC ledger canister for token operations
    # IC mainnet: mxzaz-hqaaa-aaaar-qaada-cai
    "ckbtc_ledger": "mxzaz-hqaaa-aaaar-qaada-cai",
    
    # ckBTC indexer canister for transaction history
    # IC mainnet: n5wcd-faaaa-aaaar-qaaea-cai
    "ckbtc_indexer": "n5wcd-faaaa-aaaar-qaaea-cai",
    
    # Internet Identity canister for authentication
    # IC mainnet: rdmx6-jaaaa-aaaaa-aaadq-cai
    "internet_identity": "rdmx6-jaaaa-aaaaa-aaadq-cai",
}
