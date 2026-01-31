from kybra_simple_db import Entity, Float, ManyToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.proposal")


class Proposal(Entity, TimestampedMixin):
    """Governance proposal entity for voting system"""

    __alias__ = "proposal_id"
    proposal_id = String(max_length=64)
    title = String(max_length=256)
    description = String(max_length=2048)
    code_url = String(max_length=512)
    code_checksum = String(max_length=128)
    proposer = ManyToOne("User", "proposals")
    status = String(max_length=32)  # voting, pending_vote, approved, rejected, etc.
    voting_deadline = String(max_length=64)  # ISO format timestamp or None
    votes_yes = Float()
    votes_no = Float()
    votes_abstain = Float()
    total_voters = Float()
    required_threshold = Float()
    metadata = String(max_length=256)
