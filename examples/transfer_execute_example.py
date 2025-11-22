"""Transfer Execute Example

Demonstrates how Transfer.execute() is automatically provided by the vault extension
through the manifest-based method override system.

The execute() method is declared in the core Transfer entity but implemented
by the vault extension via manifest.json declaration.
"""

from ggg import Transfer, Balance, Instrument, User
from datetime import datetime


# Example 1: Create and execute an external transfer (withdrawal)
def example_external_transfer():
    """Create an external transfer that automatically triggers vault execution."""
    print("=== Example 1: External Transfer (Withdrawal) ===\n")
    
    # Get user and instrument
    user = User["alice_principal"]
    instrument = Instrument["Realm Token"]
    
    if not user or not instrument:
        print("ERROR: User or instrument not found")
        return
    
    # Check internal balance
    balance_id = f"{user.id}_{instrument.name}"
    balance = Balance[balance_id]
    
    if not balance or balance.amount < 1000:
        print(f"ERROR: Insufficient balance. Current: {balance.amount if balance else 0}")
        return
    
    print(f"User: {user.id}")
    print(f"Balance before: {balance.amount} {instrument.name}")
    
    # Create external transfer
    transfer = Transfer(
        id=f"withdrawal_{int(datetime.now().timestamp())}",
        principal_from="system",  # Treasury
        principal_to=user.id,
        instrument=instrument.name,  # Now a string
        amount=1000,
        timestamp=datetime.now().isoformat(),
        transfer_type="external",  # <-- This makes it external!
        purpose="withdrawal",
        status="pending"
    )
    
    print(f"\n✓ Created external transfer: {transfer.id}")
    print(f"  Type: {transfer.transfer_type}")
    print(f"  Status: {transfer.status}")
    
    # Execute the transfer (calls vault.methods.execute_transfer)
    # This is an ASYNC call!
    print(f"\n⚡ Executing transfer via vault...")
    result = yield transfer.execute()
    
    print(f"\n✓ Transfer execution result:")
    print(f"  Success: {result['success']}")
    if result['success']:
        print(f"  TX ID: {result.get('tx_id')}")
        print(f"  Status: {transfer.status}")
        
        # Balance updated
        balance.amount -= 1000
        print(f"  Balance after: {balance.amount} {instrument.name}")
    else:
        print(f"  Error: {result.get('error')}")


# Example 2: Create an internal transfer (no vault execution)
def example_internal_transfer():
    """Create an internal transfer that doesn't trigger vault."""
    print("\n\n=== Example 2: Internal Transfer (Tax) ===\n")
    
    # Internal transfer for tax collection
    transfer = Transfer(
        id=f"tax_{int(datetime.now().timestamp())}",
        principal_from="alice_principal",
        principal_to="system",
        instrument="Realm Token",
        amount=500,
        timestamp=datetime.now().isoformat(),
        transfer_type="internal",  # <-- Internal!
        purpose="tax",
        status="completed"
    )
    
    print(f"✓ Created internal transfer: {transfer.id}")
    print(f"  Type: {transfer.transfer_type}")
    
    # Execute (no-op for internal transfers)
    result = transfer.execute()  # Sync call!
    
    print(f"\n✓ Execute result:")
    print(f"  Success: {result['success']}")
    print(f"  Message: {result['message']}")
    print(f"  Type: {result['type']}")


# Example 3: Refresh balance from vault
def example_refresh_balance():
    """Sync internal balance with vault state."""
    print("\n\n=== Example 3: Refresh Balance ===\n")
    
    balance_id = "alice_principal_RealmToken"
    balance = Balance[balance_id]
    
    if not balance:
        print("ERROR: Balance not found")
        return
    
    print(f"Balance ID: {balance_id}")
    print(f"Current amount: {balance.amount}")
    
    # Refresh from vault (calls vault.methods.refresh_balance)
    print(f"\n⚡ Refreshing from vault...")
    result = balance.refresh()
    
    print(f"\n✓ Refresh result:")
    print(f"  Success: {result['success']}")
    if result.get('synced'):
        print(f"  Old amount: {result['old_amount']}")
        print(f"  New amount: {result['new_amount']}")
        print(f"  Synced: Yes")
    else:
        print(f"  Synced: No (no vault balance found)")


# Example 4: Check transfer status
def example_check_status():
    """Check the status of a transfer."""
    print("\n\n=== Example 4: Check Transfer Status ===\n")
    
    # Find a transfer
    for transfer in Transfer.instances():
        if transfer.transfer_type == "external":
            print(f"Transfer: {transfer.id}")
            print(f"  Type: {transfer.transfer_type}")
            print(f"  Status: {transfer.status}")
            print(f"  From: {transfer.principal_from}")
            print(f"  To: {transfer.principal_to}")
            print(f"  Amount: {transfer.amount}")
            
            # Check metadata
            if hasattr(transfer, 'get_metadata'):
                tx_id = transfer.get_metadata('vault_tx_id')
                if tx_id:
                    print(f"  Vault TX ID: {tx_id}")
            
            break


# Main execution (for codex)
def async_task():
    """Async task entry point for codex execution."""
    print("=" * 60)
    print("Transfer Execute & Balance Refresh Demo")
    print("=" * 60)
    
    # Run examples
    yield example_external_transfer()
    example_internal_transfer()
    example_refresh_balance()
    example_check_status()
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    # For standalone execution
    print(__doc__)
    print("\nNote: This example requires the vault extension to be installed")
    print("and the method overrides to be loaded during system initialization.")
