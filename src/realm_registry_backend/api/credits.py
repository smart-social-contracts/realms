"""API functions for managing user credits."""

import time
import uuid
from typing import Dict, List, Optional

from core.models import CreditTransaction, DeploymentCreditHold, UserCredits
from ic_python_logging import get_logger

logger = get_logger("credits")


def get_user_credits(principal_id: str) -> Dict:
    """Get a user's credit balance."""
    try:
        user_credits = UserCredits[principal_id]
        if user_credits:
            return {
                "success": True,
                "credits": {
                    "principal_id": user_credits.principal_id,
                    "balance": user_credits.balance or 0,
                    "total_purchased": user_credits.total_purchased or 0,
                    "total_spent": user_credits.total_spent or 0,
                },
            }
        else:
            # Return zero balance for new users
            return {
                "success": True,
                "credits": {
                    "principal_id": principal_id,
                    "balance": 0,
                    "total_purchased": 0,
                    "total_spent": 0,
                },
            }
    except Exception as e:
        logger.error(f"Error getting credits for {principal_id}: {str(e)}")
        return {"success": False, "error": str(e)}


def add_user_credits(
    principal_id: str,
    amount: int,
    stripe_session_id: str = "",
    description: str = "Credit top-up",
) -> Dict:
    """Add credits to a user's balance (called after successful payment)."""
    if amount <= 0:
        return {"success": False, "error": "Amount must be positive"}

    if amount > 1000:
        return {"success": False, "error": "Amount cannot exceed 1000"}

    try:
        # Get or create user credits record
        user_credits = UserCredits[principal_id]
        
        if user_credits:
            # Update existing record
            user_credits.balance = (user_credits.balance or 0) + amount
            user_credits.total_purchased = (user_credits.total_purchased or 0) + amount
        else:
            # Create new record
            user_credits = UserCredits(
                principal_id=principal_id,
                balance=amount,
                total_purchased=amount,
                total_spent=0,
            )

        # Record the transaction
        transaction_id = f"tx_{uuid.uuid4().hex[:16]}"
        transaction = CreditTransaction(
            id=transaction_id,
            principal_id=principal_id,
            amount=amount,
            transaction_type="topup",
            description=description,
            stripe_session_id=stripe_session_id,
            timestamp=time.time(),
        )
        logger.info(f"Added {amount} credits to {principal_id}. New balance: {user_credits.balance}")

        return {
            "success": True,
            "credits": {
                "principal_id": user_credits.principal_id,
                "balance": user_credits.balance,
                "total_purchased": user_credits.total_purchased,
                "total_spent": user_credits.total_spent or 0,
            },
            "transaction_id": transaction_id,
        }
    except Exception as e:
        logger.error(f"Error adding credits for {principal_id}: {str(e)}")
        return {"success": False, "error": str(e)}


def deduct_user_credits(
    principal_id: str,
    amount: int,
    description: str = "Credit spend",
) -> Dict:
    """Deduct credits from a user's balance (e.g., for realm deployment)."""
    if amount <= 0:
        return {"success": False, "error": "Amount must be positive"}

    try:
        user_credits = UserCredits[principal_id]
        
        if not user_credits:
            return {"success": False, "error": "User has no credits"}

        current_balance = user_credits.balance or 0
        if current_balance < amount:
            return {
                "success": False,
                "error": f"Insufficient credits. Balance: {current_balance}, Required: {amount}",
            }

        # Deduct credits
        user_credits.balance = current_balance - amount
        user_credits.total_spent = (user_credits.total_spent or 0) + amount

        # Record the transaction
        transaction_id = f"tx_{uuid.uuid4().hex[:16]}"
        transaction = CreditTransaction(
            id=transaction_id,
            principal_id=principal_id,
            amount=-amount,  # Negative for spend
            transaction_type="spend",
            description=description,
            stripe_session_id="",
            timestamp=time.time(),
        )

        logger.info(f"Deducted {amount} credits from {principal_id}. New balance: {user_credits.balance}")

        return {
            "success": True,
            "credits": {
                "principal_id": user_credits.principal_id,
                "balance": user_credits.balance,
                "total_purchased": user_credits.total_purchased or 0,
                "total_spent": user_credits.total_spent,
            },
            "transaction_id": transaction_id,
        }
    except Exception as e:
        logger.error(f"Error deducting credits for {principal_id}: {str(e)}")
        return {"success": False, "error": str(e)}


def get_billing_status() -> Dict:
    """Get overall billing status across all users."""
    try:
        all_users = list(UserCredits.instances())
        
        total_balance = sum(u.balance or 0 for u in all_users)
        total_purchased = sum(u.total_purchased or 0 for u in all_users)
        total_spent = sum(u.total_spent or 0 for u in all_users)
        users_count = len(all_users)
        
        return {
            "success": True,
            "billing": {
                "users_count": users_count,
                "total_balance": total_balance,
                "total_purchased": total_purchased,
                "total_spent": total_spent,
            },
        }
    except Exception as e:
        logger.error(f"Error getting billing status: {str(e)}")
        return {"success": False, "error": str(e)}


def get_user_transactions(principal_id: str, limit: int = 50) -> Dict:
    """Get a user's transaction history."""
    try:
        # Get all transactions for this user
        all_transactions = CreditTransaction.all()
        user_transactions = [
            tx for tx in all_transactions if tx.principal_id == principal_id
        ]
        
        # Sort by timestamp descending and limit
        user_transactions.sort(key=lambda x: x.timestamp or 0, reverse=True)
        user_transactions = user_transactions[:limit]

        transactions_data = [
            {
                "id": tx.id,
                "principal_id": tx.principal_id,
                "amount": tx.amount or 0,
                "transaction_type": tx.transaction_type or "",
                "description": tx.description or "",
                "stripe_session_id": tx.stripe_session_id or "",
                "timestamp": tx.timestamp or 0,
            }
            for tx in user_transactions
        ]

        return {"success": True, "transactions": transactions_data}
    except Exception as e:
        logger.error(f"Error getting transactions for {principal_id}: {str(e)}")
        return {"success": False, "error": str(e)}


def create_deployment_hold(
    principal_id: str,
    job_id: str,
    amount: int,
    description: str = "Deployment hold",
) -> Dict:
    """Reserve credits for a deployment job (idempotent by job_id)."""
    if amount <= 0:
        return {"success": False, "error": "Amount must be positive"}
    if not job_id:
        return {"success": False, "error": "job_id is required"}
    try:
        existing = DeploymentCreditHold[job_id]
        if existing:
            return {
                "success": existing.status in ("held", "captured"),
                "hold": existing.to_dict(),
                "idempotent": True,
            }

        user_credits = UserCredits[principal_id]
        if not user_credits:
            return {"success": False, "error": "User has no credits"}
        balance = user_credits.balance or 0
        if balance < amount:
            return {
                "success": False,
                "error": f"Insufficient credits. Balance: {balance}, Required: {amount}",
            }

        user_credits.balance = balance - amount
        hold = DeploymentCreditHold(
            job_id=job_id,
            principal_id=principal_id,
            amount=amount,
            status="held",
            reason=description,
            created_at=time.time(),
            settled_at=0.0,
        )
        CreditTransaction(
            id=f"tx_{uuid.uuid4().hex[:16]}",
            principal_id=principal_id,
            amount=-amount,
            transaction_type="hold",
            description=f"{description} (job={job_id})",
            stripe_session_id="",
            timestamp=time.time(),
        )
        return {"success": True, "hold": hold.to_dict(), "idempotent": False}
    except Exception as e:
        logger.error(f"Error creating deployment hold for {principal_id}: {str(e)}")
        return {"success": False, "error": str(e)}


def capture_deployment_hold(job_id: str, description: str = "Deployment captured") -> Dict:
    """Capture a held deployment amount into spent credits (idempotent)."""
    if not job_id:
        return {"success": False, "error": "job_id is required"}
    try:
        hold = DeploymentCreditHold[job_id]
        if not hold:
            return {"success": False, "error": f"Hold not found for job_id={job_id}"}
        if hold.status == "captured":
            return {"success": True, "hold": hold.to_dict(), "idempotent": True}
        if hold.status == "released":
            return {"success": False, "error": "Hold already released"}

        principal_id = hold.principal_id
        user_credits = UserCredits[principal_id]
        if not user_credits:
            user_credits = UserCredits(
                principal_id=principal_id,
                balance=0,
                total_purchased=0,
                total_spent=0,
            )
        user_credits.total_spent = (user_credits.total_spent or 0) + (hold.amount or 0)
        hold.status = "captured"
        hold.reason = description
        hold.settled_at = time.time()
        CreditTransaction(
            id=f"tx_{uuid.uuid4().hex[:16]}",
            principal_id=principal_id,
            amount=0,
            transaction_type="capture",
            description=f"{description} (job={job_id})",
            stripe_session_id="",
            timestamp=time.time(),
        )
        return {"success": True, "hold": hold.to_dict(), "idempotent": False}
    except Exception as e:
        logger.error(f"Error capturing deployment hold {job_id}: {str(e)}")
        return {"success": False, "error": str(e)}


def release_deployment_hold(job_id: str, description: str = "Deployment released") -> Dict:
    """Release a held deployment amount back to user balance (idempotent)."""
    if not job_id:
        return {"success": False, "error": "job_id is required"}
    try:
        hold = DeploymentCreditHold[job_id]
        if not hold:
            return {"success": False, "error": f"Hold not found for job_id={job_id}"}
        if hold.status == "released":
            return {"success": True, "hold": hold.to_dict(), "idempotent": True}
        if hold.status == "captured":
            return {"success": False, "error": "Hold already captured"}

        principal_id = hold.principal_id
        amount = hold.amount or 0
        user_credits = UserCredits[principal_id]
        if user_credits:
            user_credits.balance = (user_credits.balance or 0) + amount
        else:
            user_credits = UserCredits(
                principal_id=principal_id,
                balance=amount,
                total_purchased=0,
                total_spent=0,
            )
        hold.status = "released"
        hold.reason = description
        hold.settled_at = time.time()
        CreditTransaction(
            id=f"tx_{uuid.uuid4().hex[:16]}",
            principal_id=principal_id,
            amount=amount,
            transaction_type="release",
            description=f"{description} (job={job_id})",
            stripe_session_id="",
            timestamp=time.time(),
        )
        return {"success": True, "hold": hold.to_dict(), "idempotent": False}
    except Exception as e:
        logger.error(f"Error releasing deployment hold {job_id}: {str(e)}")
        return {"success": False, "error": str(e)}
