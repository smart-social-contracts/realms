from ggg import (
    Trade,
    Transfer,
    Dispute,
    User,
    Instrument,
)
from kybra_simple_logging import get_logger
from .config import NUM_TRADES, NUM_TRANSFERS, NUM_USERS, NUM_INSTRUMENTS
import random

logger = get_logger("demo_loader.transactions")

def run():
    """Create various transactions."""
    logger.info(f"Creating {NUM_TRADES} trades and {NUM_TRANSFERS} transfers")

    # Create trades
    trades = []
    trade_types = [
        "pension_payment",
        "rental_payment",
        "tax_payment",
        "license_fee",
        "service_payment",
        "donation",
        "refund",
        "salary_payment",
        "investment",
        "dividend"
    ]

    for i in range(NUM_TRADES):
        trade_type = random.choice(trade_types)
        trade = Trade(
            metadata=f'{{"type": "{trade_type}", "id": "TR{i:06d}"}}'
        )
        trades.append(trade)

    # Create transfers
    transfers = []
    for i in range(NUM_TRANSFERS):
        # Randomly select user IDs (1 to NUM_USERS) and instrument IDs (1 to NUM_INSTRUMENTS)
        from_user_id = random.randint(1, NUM_USERS)
        to_user_id = random.randint(1, NUM_USERS)
        instrument_id = random.randint(1, NUM_INSTRUMENTS)
        
        # Generate random amount between 10 and 1000
        amount = random.randint(10, 1000)
        
        transfer = Transfer(amount=amount)
        # Use the ID as the name since we know the entities exist with these IDs
        transfer.from_user = User(name=f"user_{from_user_id}")
        transfer.to_user = User(name=f"user_{to_user_id}")
        transfer.instrument = Instrument(name=f"instrument_{instrument_id}")
        
        # Randomly assign some transfers to trades
        if i < len(trades):
            if random.random() < 0.5:  # 50% chance to be transfer_1
                trades[i].transfer_1 = transfer
            else:  # 50% chance to be transfer_2
                trades[i].transfer_2 = transfer
        
        transfers.append(transfer)

    # Create some disputes
    disputes = []
    for i in range(min(5, len(trades))):  # Create up to 5 disputes
        dispute = Dispute(status="OPEN")
        disputes.append(dispute)

    logger.info(f"Created {len(trades)} trades, {len(transfers)} transfers, and {len(disputes)} disputes")

    return f"Created {len(trades)} trades, {len(transfers)} transfers, and {len(disputes)} disputes"
