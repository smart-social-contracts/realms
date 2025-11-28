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
import subprocess
import sys
import time

# Add tests directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Change to realms root for dfx commands
REALMS_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
os.chdir(REALMS_ROOT)

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


def icw_transfer(
    recipient: str, amount: float, subaccount: str, ledger_id: str
) -> bool:
    """Transfer tokens using icw CLI to a specific subaccount."""
    cmd = [
        "icw",
        "-n",
        "local",
        "transfer",
        recipient,
        str(amount),
        "-s",
        subaccount,
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
    create_code = f'from ggg import Invoice; inv = Invoice(id="{invoice_id}", amount=0.0001, currency="ckBTC", status="Pending", due_date="2025-12-31", metadata="test"); print(inv.id)'
    result = execute_on_canister(create_code)
    if invoice_id not in result.get("raw", ""):
        print_error(f"Failed to create invoice: {result}")
        return False
    print_ok(f"Created invoice: {invoice_id}")

    # Step 2: Transfer to invoice subaccount (subaccount = invoice_id padded)
    print("\n--- Step 2: Transfer ckBTC ---")
    if not icw_transfer(vault_id, 0.0001, invoice_id, ledger_id):
        print_error("Transfer failed")
        return False
    print_ok("Transfer successful")

    # Step 3: Wait for indexer and check invoice payment
    print("\n--- Step 3: Check Invoice Payment ---")
    time.sleep(2)

    # Call check_invoice_payment which queries the subaccount balance directly
    check_args = json.dumps({"invoice_id": invoice_id})
    check_result = call_realm_extension(
        "member_dashboard", "check_invoice_payment", check_args
    )

    if not check_result:
        print_error("check_invoice_payment call failed")
        return False

    print(f"Check result: {check_result}")

    if check_result.get("success"):
        data = check_result.get("data", {})
        if data.get("paid") or data.get("already_paid"):
            print_ok("✅ Invoice correctly marked as Paid!")
            return True
        else:
            print_error(
                f"❌ Invoice not paid. Shortfall: {data.get('shortfall_satoshis')} satoshis"
            )
            return False
    else:
        print_error(f"❌ Check failed: {check_result.get('error')}")
        return False


if __name__ == "__main__":
    import sys

    sys.exit(0 if test_invoice_payment() else 1)
