from kybra_simple_db import (
    Entity,
    Integer,
    ManyToOne,
    String,
    TimestampedMixin,
)
from kybra_simple_logging import get_logger

logger = get_logger("entity.transfer")


class Transfer(Entity, TimestampedMixin):
    """
    Represents a token transfer on the ledger.
    
    When a transfer is to the vault with a subaccount, it may be linked
    to an Invoice that it paid.
    """
    
    __alias__ = "id"
    id = String()
    principal_from = String()
    principal_to = String()
    subaccount = String(max_length=64)  # Hex-encoded destination subaccount
    invoice = ManyToOne("Invoice", "transfers")  # Linked invoice if this paid one
    instrument = String()
    amount = Integer()
    timestamp = String()
    tags = String()
    status = String()

    def execute(self):
        raise NotImplementedError("Transfer execution is not implemented")
