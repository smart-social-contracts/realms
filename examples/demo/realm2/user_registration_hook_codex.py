"""
User Registration Hook Codex
Overrides user_register_posthook to add custom logic after user registration.
Creates a 1 ckBTC invoice expiring in 5 minutes for new users.
"""

from kybra import ic
from ggg import Invoice
from datetime import datetime, timedelta

def user_register_posthook(user):
    """Custom user registration hook - creates welcome invoice."""
    try:
        # Calculate expiry time (5 minutes from now)
        expiry_time = datetime.now() + timedelta(minutes=5)
        due_date = expiry_time.isoformat()
        
        # Create 1 ckBTC invoice for the new user
        # Invoice ID is auto-generated and used to derive a unique subaccount
        invoice = Invoice(
            amount=1.0,  # 1 ckBTC
            currency="ckBTC",
            due_date=due_date,
            status="Pending",
            user=user,
            metadata="Welcome bonus - 1 ckBTC invoice"
        )
        
        # Get the deposit address info
        vault_principal = ic.id().to_str()
        subaccount_hex = invoice.get_subaccount_hex()
        
        ic.print(f"✅ Created welcome invoice {invoice.id} for user {user.id}")
        ic.print(f"   Deposit to: {vault_principal} (subaccount: {subaccount_hex[:16]}...)")
        ic.print(f"   Amount: 1 ckBTC, expires in 5 minutes")
        
    except Exception as e:
        ic.print(f"❌ Error creating invoice: {e}")
    
    return
