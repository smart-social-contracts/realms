"""Initialize vault extension Canisters entities with local test canister IDs."""

import json
import traceback

from kybra import ic

# Canister IDs will be injected here by test_entrypoint.sh
CKBTC_LEDGER_ID = "PLACEHOLDER_LEDGER_ID"
CKBTC_INDEXER_ID = "PLACEHOLDER_INDEXER_ID"

# Sync execution - no function wrapper needed
try:
    ic.print("[INFO] Initializing vault with local test canister IDs...")

    # Import after ic.print to ensure logging works
    from extension_packages.vault.vault_lib.entities import Canisters

    if not CKBTC_LEDGER_ID or not CKBTC_INDEXER_ID:
        ic.print(
            f"[ERROR] Missing canister IDs: ledger={CKBTC_LEDGER_ID}, indexer={CKBTC_INDEXER_ID}"
        )
        result = {"success": False, "error": "Missing canister IDs"}
    elif "PLACEHOLDER" in CKBTC_LEDGER_ID or "PLACEHOLDER" in CKBTC_INDEXER_ID:
        ic.print("[ERROR] Canister IDs not properly injected")
        result = {"success": False, "error": "Placeholder IDs not replaced"}
    else:
        ic.print(f"[INFO] Configuring ckBTC ledger: {CKBTC_LEDGER_ID}")
        ic.print(f"[INFO] Configuring ckBTC indexer: {CKBTC_INDEXER_ID}")

        # Create/update Canisters entities with local test canister IDs
        ledger_canister = Canisters["ckBTC ledger"]
        ledger_canister.principal = CKBTC_LEDGER_ID

        indexer_canister = Canisters["ckBTC indexer"]
        indexer_canister.principal = CKBTC_INDEXER_ID

        ic.print("[SUCCESS] Vault configured with local test canisters")
        ic.print(f"  - ckBTC ledger: {ledger_canister.principal}")
        ic.print(f"  - ckBTC indexer: {indexer_canister.principal}")

        result = {
            "success": True,
            "ledger_id": CKBTC_LEDGER_ID,
            "indexer_id": CKBTC_INDEXER_ID,
        }

except Exception as e:
    ic.print(f"[ERROR] Failed to configure vault: {str(e)}")
    ic.print(traceback.format_exc())
    result = {"success": False, "error": str(e)}
