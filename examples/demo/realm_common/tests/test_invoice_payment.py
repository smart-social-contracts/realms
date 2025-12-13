#!/usr/bin/env python3
"""
Test invoice payment flow using icw (internet-computer-wallet).

Usage:
    python extensions/vault/tests/test_invoice_payment.py

    (Run from realms root directory!)

Prerequisites:
    - pip install internet-computer-wallet
    - Local dfx replica with ckbtc_ledger and realm_backend deployed
    - Current identity funded with test ckBTC
"""

import json
import os
import shutil
import subprocess
import sys
import time

# Add tests directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Determine working directory: use REALM_DIR env var, or current directory if it has dfx.json
REALM_DIR = os.environ.get("REALM_DIR", os.getcwd())
if not os.path.exists(os.path.join(REALM_DIR, "dfx.json")):
    # Fallback: check if we're in a realm subdirectory
    if os.path.exists("dfx.json"):
        REALM_DIR = os.getcwd()
    else:
        print("ERROR: Must run from a realm directory with dfx.json or set REALM_DIR")
        sys.exit(1)
os.chdir(REALM_DIR)
print(f"Working directory: {REALM_DIR}")

from test_utils import (
    call_realm_extension,
    get_canister_id,
    print_error,
    print_ok,
    run_command,
)


def execute_on_canister(code: str) -> dict:
    """Execute Python code on realm_backend canister."""
    # Use semicolons for one-liner to avoid newline escaping issues
    one_liner = code.strip().replace("\n", "; ")
    escaped = one_liner.replace("\\", "\\\\").replace('"', '\\"')
    cmd = f"dfx canister call realm_backend execute_code_shell '(\"{escaped}\")'"
    result = run_command(cmd)
    if not result:
        return {}
    try:
        # Parse the Candid response - extract the JSON part
        # Response format: ("{ ... }")
        if '"{' in result:
            start = result.find('"{') + 1
            end = result.rfind('}"') + 1
            json_str = result[start:end].replace('\\"', '"').replace("\\n", "\n")
            return json.loads(json_str)
        return {"raw": result}
    except Exception as e:
        return {"raw": result, "parse_error": str(e)}


def invoice_id_to_subaccount_hex(invoice_id: str) -> str:
    """Convert invoice ID to 32-byte hex subaccount (padded with null bytes)."""
    return invoice_id.encode().ljust(32, b'\x00').hex()


def icw_transfer(
    recipient: str, amount: str, subaccount_hex: str, ledger_id: str
) -> bool:
    """Transfer tokens using icw CLI to a specific subaccount (hex format)."""
    # Find icw in PATH or use the realms venv
    icw_path = shutil.which("icw")
    if not icw_path:
        # Try realms venv (script is at examples/demo/realm_common/tests/, so go up 4 levels)
        realms_root = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
        icw_path = os.path.join(realms_root, "venv", "bin", "icw")
        if not os.path.exists(icw_path):
            print_error(f"icw not found in PATH or {icw_path}")
            return False
    
    # Use DFX_NETWORK env var or default to local
    # Map "staging" to "ic" since icw only knows "local" and "ic"
    network = os.environ.get("DFX_NETWORK", "local")
    if network == "staging":
        network = "ic"
    
    cmd = [
        icw_path,
        "-n",
        network,
        "transfer",
        recipient,
        str(amount),
        "-s",
        subaccount_hex,
        "--ledger",
        ledger_id,
        "--fee",
        "10",
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print_error(f"icw transfer failed: {result.stderr}")
        return False
    response = json.loads(result.stdout)
    return response.get("ok", False)


def test_invoice_payment():
    """Test: Create invoice → Pay with icw → Refresh → Verify paid."""
    print("\n" + "=" * 60)
    print("TEST: Invoice Payment Flow")
    print("=" * 60)

    # Get canister IDs
    ledger_id = get_canister_id("ckbtc_ledger")
    vault_id = get_canister_id("realm_backend")
    if not ledger_id or not vault_id:
        print_error("Missing canister IDs")
        return False

    print(f"Ledger: {ledger_id}")
    print(f"Vault: {vault_id}")

    # Step 1: Create invoice
    print("\n--- Step 1: Create Invoice ---")
    # Create invoice with a known ID
    import uuid

    invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
    # Amount in ckBTC - 0.00000001 = 1 satoshi
    invoice_amount = "0.00000001"
    create_code = f'from ggg import Invoice; inv = Invoice(id="{invoice_id}", amount={invoice_amount}, currency="ckBTC", status="Pending", due_date="2025-12-31", metadata="test"); print(inv.id)'
    result = execute_on_canister(create_code)
    if invoice_id not in result.get("raw", ""):
        print_error(f"Failed to create invoice: {result}")
        return False
    print_ok(f"Created invoice: {invoice_id}")

    # Step 2: Transfer to invoice subaccount (hex-encoded)
    print("\n--- Step 2: Transfer ckBTC ---")
    subaccount_hex = invoice_id_to_subaccount_hex(invoice_id)
    print(f"Subaccount hex: {subaccount_hex}")
    if not icw_transfer(vault_id, "0.00000001", subaccount_hex, ledger_id):
        print_error("Transfer failed")
        return False
    print_ok("Transfer successful")

    # Step 3: Wait for indexer to sync
    print("\n--- Step 3: Wait for Indexer ---")
    time.sleep(2)

    # Step 4: Call vault.refresh_invoice to sync this invoice's subaccount
    print("\n--- Step 4: Vault Refresh Invoice ---")
    refresh_args = json.dumps({"invoice_id": invoice_id})
    refresh_result = call_realm_extension("vault", "refresh_invoice", refresh_args)
    if not refresh_result:
        print_error("vault.refresh_invoice call failed")
        return False
    print(f"Refresh result: {refresh_result}")
    
    # Wait for async refresh to complete
    time.sleep(3)

    # Step 5: Check invoice status using realms CLI
    print("\n--- Step 5: Check Invoice Status ---")
    check_cmd = f"realms db get Invoice {invoice_id}"
    result = run_command(check_cmd)
    print(f"Invoice data: {result}")

    if result and '"status": "Paid"' in result:
        print_ok("✅ Invoice correctly marked as Paid!")
        return True
    else:
        print_error(f"❌ Invoice not paid.")
        return False


if __name__ == "__main__":
    import sys

    sys.exit(0 if test_invoice_payment() else 1)
