from kybra_simple_db import Entity, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.member")


class Member(Entity, TimestampedMixin):
    __alias__ = "id"
    id = String()
    user = OneToOne("User", "member")

    residence_permit: str
    tax_compliance: str
    identity_verification: str
    voting_eligibility: str
    public_benefits_eligibility: str
    criminal_record: str
