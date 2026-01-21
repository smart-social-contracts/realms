from kybra_simple_db import (
    Entity,
    ManyToOne,
    OneToMany,
    String,
    TimestampedMixin,
)
from kybra_simple_logging import get_logger

logger = get_logger("entity.fund")


class FundType:
    """Standard governmental fund types."""
    GENERAL = "general"
    SPECIAL_REVENUE = "special_revenue"
    CAPITAL_PROJECTS = "capital_projects"
    DEBT_SERVICE = "debt_service"
    ENTERPRISE = "enterprise"
    INTERNAL_SERVICE = "internal_service"
    TRUST = "trust"
    AGENCY = "agency"


class Fund(Entity, TimestampedMixin):
    """
    Governmental Fund - GGG Government Accounting Standard.
    
    Organizes money by purpose. Each fund is a self-balancing set of
    ledger entries for specific activities or objectives.
    
    Fund types follow GASB standards:
    - general: Main operating fund
    - special_revenue: Restricted revenue sources
    - capital_projects: Major capital acquisitions
    - debt_service: Principal and interest payments
    - enterprise: Business-type activities
    - internal_service: Services to other departments
    - trust: Fiduciary resources
    - agency: Custodial resources
    """
    __alias__ = "code"
    code = String(max_length=16)
    name = String(max_length=256)
    fund_type = String(max_length=32, default=FundType.GENERAL)
    description = String(max_length=512)
    realm = ManyToOne("Realm", "funds")
    ledger_entries = OneToMany("LedgerEntry", "fund")
    budgets = OneToMany("Budget", "fund")

    def __repr__(self):
        return f"Fund(code={self.code!r}, name={self.name!r})"
