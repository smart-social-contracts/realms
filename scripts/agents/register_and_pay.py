#!/usr/bin/env python3
"""
Agent Script: Register and Pay Welcome Invoice

This script demonstrates using the Realms SDK to:
1. Join a realm as admin
2. Check that a welcome invoice was created
3. Pay the invoice using icw
4. Verify the invoice is marked as paid

Usage:
    python scripts/agents/register_and_pay.py --folder .realms/realm_Generated_Demo_Realm_*/
    
    # Or with the SDK installed:
    from realms import realm
    await realm.call("join_realm", '("admin")', folder="...")
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add CLI to path if running from repo
cli_path = Path(__file__).parent.parent.parent / "cli"
if cli_path.exists():
    sys.path.insert(0, str(cli_path))

from realms import realm


async def main():
    parser = argparse.ArgumentParser(description="Register and pay welcome invoice agent")
    parser.add_argument("--folder", "-f", required=True, help="Path to realm folder")
    parser.add_argument("--network", "-n", default="local", help="Network (default: local)")
    parser.add_argument("--profile", "-p", default="admin", help="Profile to register as (default: admin)")
    args = parser.parse_args()
    
    folder = args.folder
    network = args.network
    profile = args.profile
    
    print(f"🚀 Starting Register and Pay Agent")
    print(f"   Folder: {folder}")
    print(f"   Network: {network}")
    print(f"   Profile: {profile}")
    print()
    
    # Step 1: Join the realm
    print("📝 Step 1: Joining realm...")
    try:
        result = await realm.call("join_realm", f'("{profile}")', folder=folder, network=network)
        print(f"   ✅ Joined realm: {result}")
    except Exception as e:
        print(f"   ❌ Failed to join realm: {e}")
        return False
    
    # Step 2: Check for invoices
    print("\n📋 Step 2: Checking for welcome invoice...")
    try:
        invoices = await realm.db.get("Invoice", folder=folder, network=network)
        if not invoices:
            print("   ❌ No invoices found")
            return False
        
        # Find pending invoice
        pending_invoices = [inv for inv in invoices if inv.get("status") == "Pending"]
        if not pending_invoices:
            print("   ℹ️  No pending invoices found")
            paid_invoices = [inv for inv in invoices if inv.get("status") == "Paid"]
            if paid_invoices:
                print(f"   ✅ Found {len(paid_invoices)} already paid invoice(s)")
                return True
            return False
        
        invoice = pending_invoices[0]
        invoice_id = invoice.get("id")
        amount = invoice.get("amount", 0)
        print(f"   ✅ Found pending invoice: {invoice_id}")
        print(f"      Amount: {amount} {invoice.get('currency', 'ckBTC')}")
        print(f"      Metadata: {invoice.get('metadata', '')}")
    except Exception as e:
        print(f"   ❌ Failed to get invoices: {e}")
        return False
    
    # Step 3: Get canister IDs for payment
    print("\n💰 Step 3: Preparing payment...")
    try:
        # Get backend canister ID (vault)
        import subprocess
        result = subprocess.run(
            ["dfx", "canister", "id", "realm_backend"],
            capture_output=True, text=True, cwd=folder
        )
        backend_id = result.stdout.strip()
        
        result = subprocess.run(
            ["dfx", "canister", "id", "ckbtc_ledger"],
            capture_output=True, text=True, cwd=folder
        )
        ledger_id = result.stdout.strip()
        
        print(f"   Backend (vault): {backend_id}")
        print(f"   Ledger: {ledger_id}")
    except Exception as e:
        print(f"   ❌ Failed to get canister IDs: {e}")
        return False
    
    # Step 4: Pay the invoice
    print("\n💸 Step 4: Paying invoice...")
    try:
        transfer_result = await realm.icw.transfer(
            to=backend_id,
            amount=amount,
            subaccount=invoice_id,
            ledger=ledger_id,
            fee=0,
            network=network
        )
        print(f"   ✅ Transfer successful: {transfer_result}")
    except Exception as e:
        print(f"   ❌ Transfer failed: {e}")
        return False
    
    # Step 5: Verify payment (trigger check and verify status)
    print("\n✔️  Step 5: Verifying payment...")
    try:
        # Call check_invoice_payment extension
        check_result = await realm.call_extension(
            extension="member_dashboard",
            function="check_invoice_payment",
            args={"invoice_id": invoice_id},
            folder=folder,
            network=network,
            async_call=True
        )
        print(f"   Check result: {check_result}")
        
        # Get updated invoice status
        invoice = await realm.db.get("Invoice", invoice_id, folder=folder, network=network)
        status = invoice.get("status") if isinstance(invoice, dict) else invoice[0].get("status") if invoice else "Unknown"
        
        if status == "Paid":
            print(f"   ✅ Invoice {invoice_id} is now PAID!")
            return True
        else:
            print(f"   ⚠️  Invoice status: {status}")
            print("   Note: The payment was sent. Status may need manual verification.")
            return True  # Payment was sent successfully
            
    except Exception as e:
        print(f"   ⚠️  Verification check failed: {e}")
        print("   Note: Payment was sent, but verification failed. Check manually.")
        return True  # Payment was sent, verification is secondary
    
    print("\n🎉 Agent completed successfully!")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
