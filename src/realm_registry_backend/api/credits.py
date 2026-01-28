"""API functions for managing user credits."""

import time
import uuid
from typing import Dict, List, Optional

from core.models import CreditTransaction, UserCredits
from kybra_simple_logging import get_logger

logger = get_logger("credits")


def get_user_credits(principal_id: str) -> Dict:
    """Get a user's credit balance."""
    try:
        user_credits = UserCredits.get(principal_id)
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
        user_credits = UserCredits.get(principal_id)
        
        if user_credits:
            # Update existing record
            user_credits.balance = (user_credits.balance or 0) + amount
            user_credits.total_purchased = (user_credits.total_purchased or 0) + amount
            user_credits.save()
        else:
            # Create new record
            user_credits = UserCredits(
                principal_id=principal_id,
                balance=amount,
                total_purchased=amount,
                total_spent=0,
            )
            user_credits.save()

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
        transaction.save()

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
        user_credits = UserCredits.get(principal_id)
        
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
        user_credits.save()

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
        transaction.save()

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
