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
    ic.print(f"🎯 user_register_posthook() called for user: {user.id if user else 'None'}")
    
    if not user:
        ic.print("❌ No user provided to posthook")
        return
    
    try:
        ic.print(f"📋 User details: id={user.id}, principal={getattr(user, 'principal_id', 'N/A')}")
        
        # Calculate expiry time (5 minutes from now)
        expiry_time = datetime.now() + timedelta(minutes=5)
        due_date = expiry_time.isoformat()
        ic.print(f"⏰ Invoice due date: {due_date}")
        
        # Create 1 ckBTC invoice for the new user
        # Invoice ID is auto-generated and used to derive a unique subaccount
        ic.print("📝 Creating invoice...")
        invoice = Invoice(
            amount=1.0,  # 1 ckBTC
            currency="ckBTC",
            due_date=due_date,
            status="Pending",
            user=user,
            metadata="Welcome fee - 1 ckBTC invoice"
        )
        ic.print(f"✅ Invoice created with id: {invoice.id}")
        
        # Get the deposit address info
        vault_principal = ic.id().to_str()
        subaccount_hex = invoice.get_subaccount_hex()
        
        ic.print(f"🎉 Welcome invoice {invoice.id} created for user {user.id}")
        ic.print(f"   💰 Amount: 1 ckBTC")
        ic.print(f"   📍 Deposit to: {vault_principal}")
        ic.print(f"   🔑 Subaccount: {subaccount_hex}")
        ic.print(f"   ⏳ Expires: {due_date}")
        
    except Exception as e:
        ic.print(f"❌ Error in user_register_posthook: {e}")
        import traceback
        ic.print(f"📜 Traceback: {traceback.format_exc()}")
    
    return
