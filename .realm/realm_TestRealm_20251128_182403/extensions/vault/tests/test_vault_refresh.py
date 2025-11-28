"""Test vault refresh to verify transactions are synced"""

from kybra import ic


async def test_refresh():
    """Test vault refresh"""
    ic.print("Starting async vault status check...")

    from entity.treasury import Treasury

    treasury = Treasury.get("Default Realm Treasury")
    ic.print(f"treasury.name: {treasury.name}")
    ic.print(f"treasury.vault_principal_id: {treasury.vault_principal_id}")

    # Call refresh to sync transactions
    result = yield treasury.refresh()

    ic.print(f"✅ Refresh completed!")
    ic.print(f"Result: {result}")


result = test_refresh()
