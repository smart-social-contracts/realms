"""
Realm Backend Configuration

This file contains canister IDs for external services used by the realm backend.
Values are updated during deployment from deployment.json.

For local development, these default to IC mainnet values.
During deployment, the deploy script updates these with actual canister IDs.
"""

# Test-mode flags are NOT defined here. They are runtime config on the Realm
# entity, set via set_canister_config (test_flags_json) and read live through
# core.runtime_flags (backend, extensions) and status() (frontend). Defining
# them here would be misleading — a value set in this file has no effect.

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
    
    # REALM token canister (ledger + indexer in one canister)
    # Staging: xbkkh-syaaa-aaaah-qq3ya-cai
    "realm_token_ledger": "xbkkh-syaaa-aaaah-qq3ya-cai",
    "realm_token_indexer": "xbkkh-syaaa-aaaah-qq3ya-cai",  # Same canister provides both
    
    # NFT backend canister for LAND NFTs
    # Updated during deployment with realm-specific NFT canister
    "nft_backend": "",
}
