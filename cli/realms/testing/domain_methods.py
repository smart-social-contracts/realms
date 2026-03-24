"""
Domain-specific methods that have real logic beyond simple CRUD.

These get attached to the appropriate entity classes in ggg_module.py.
"""


# ---------------------------------------------------------------------------
# LedgerEntry
# ---------------------------------------------------------------------------

def ledger_create_transaction(cls, transaction_id, entries, validate=True):
    """Create a balanced double-entry transaction.

    Args:
        transaction_id: Unique ID grouping the entries.
        entries: List of dicts with entry_type, category, debit/credit, etc.
        validate: If True, raise ValueError when debits != credits.

    Returns:
        List of created LedgerEntry instances.
    """
    total_debit = sum(e.get("debit", 0) or 0 for e in entries)
    total_credit = sum(e.get("credit", 0) or 0 for e in entries)
    if validate and total_debit != total_credit:
        raise ValueError(
            f"Unbalanced transaction {transaction_id}: "
            f"debit={total_debit} credit={total_credit}"
        )
    result = []
    for e in entries:
        entry = cls(transaction_id=transaction_id, **e)
        result.append(entry)
    return result


def ledger_validate_transaction(cls, transaction_id):
    """Check that debits == credits for a given transaction_id."""
    entries = [e for e in cls.instances() if getattr(e, "transaction_id", None) == transaction_id]
    total_debit = sum(getattr(e, "debit", 0) or 0 for e in entries)
    total_credit = sum(getattr(e, "credit", 0) or 0 for e in entries)
    return total_debit == total_credit


def ledger_get_balance(cls, entry_type, category=None, fund=None):
    """Calculate net balance (debit - credit) for an entry type."""
    total = 0
    for e in cls.instances():
        if getattr(e, "entry_type", None) != entry_type:
            continue
        if category and getattr(e, "category", None) != category:
            continue
        if fund and getattr(e, "fund", None) is not fund:
            continue
        total += (getattr(e, "debit", 0) or 0) - (getattr(e, "credit", 0) or 0)
    return total


def ledger_amount(self):
    """Return the non-zero amount (debit or credit)."""
    d = getattr(self, "debit", 0) or 0
    c = getattr(self, "credit", 0) or 0
    return d if d else c


def ledger_is_debit(self):
    return (getattr(self, "debit", 0) or 0) > 0


def ledger_is_credit(self):
    return (getattr(self, "credit", 0) or 0) > 0


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

def budget_variance(self):
    """Calculate budget variance (actual - planned)."""
    return (getattr(self, "actual_amount", 0) or 0) - (getattr(self, "planned_amount", 0) or 0)


def budget_variance_percent(self):
    """Calculate variance as percentage of planned."""
    planned = getattr(self, "planned_amount", 0) or 0
    if planned == 0:
        return 0.0
    return (self.variance() / planned) * 100.0


def budget_update_actual(self, amount):
    """Add to actual amount."""
    self.actual_amount = (getattr(self, "actual_amount", 0) or 0) + amount


# ---------------------------------------------------------------------------
# FiscalPeriod
# ---------------------------------------------------------------------------

def fiscal_period_is_open(self):
    return getattr(self, "status", None) == "open"


def fiscal_period_close(self):
    self.status = "closed"


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

def invoice_mark_paid(self):
    """Mark this invoice as paid with current timestamp."""
    from datetime import datetime, timezone
    self.status = "Paid"
    self.paid_on = datetime.now(timezone.utc).isoformat()


def invoice_get_amount_raw(self):
    """Get the invoice amount in raw satoshis."""
    amount = getattr(self, "amount", 0) or 0
    return int(amount * 100_000_000)


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

def token_is_enabled(self):
    return getattr(self, "enabled", "true") == "true"


# ---------------------------------------------------------------------------
# Member
# ---------------------------------------------------------------------------

def member_is_active(self):
    """Check if this member is active (identity verified)."""
    return getattr(self, "identity_verification", None) == "verified"


def member_activate(self):
    """Activate this member — set identity as verified and enable voting/benefits."""
    self.identity_verification = "verified"
    self.voting_eligibility = "eligible"
    self.public_benefits_eligibility = "eligible"


def member_deactivate(self, reason="suspended"):
    """Deactivate this member — suspend identity and revoke voting/benefits."""
    self.identity_verification = reason
    self.voting_eligibility = "ineligible"
    self.public_benefits_eligibility = "ineligible"


def member_reactivate(self):
    """Reactivate a previously deactivated member."""
    member_activate(self)


def member_for_user(cls, user_id):
    """Find the Member record linked to a user ID. Returns Member or None."""
    for member in cls.instances():
        if member.user and member.user.id == user_id:
            return member
    return None


def member_count_active(cls):
    """Count all active members."""
    return sum(1 for m in cls.instances()
               if getattr(m, "identity_verification", None) == "verified")


# ---------------------------------------------------------------------------
# Proposal
# ---------------------------------------------------------------------------

def proposal_tally(self):
    """Count votes from linked Vote entities and update tally fields."""
    from . import ggg_module
    yes = no = abstain = 0
    # Query Vote instances linked to this proposal (mimics OneToMany lookup)
    for vote in ggg_module.Vote.instances():
        if getattr(vote, "proposal", None) is not self:
            continue
        choice = (getattr(vote, "vote_choice", "") or "").lower()
        if choice == "yes":
            yes += 1
        elif choice == "no":
            no += 1
        elif choice == "abstain":
            abstain += 1
    self.votes_yes = float(yes)
    self.votes_no = float(no)
    self.votes_abstain = float(abstain)
    self.total_voters = float(yes + no + abstain)
    return {"yes": yes, "no": no, "abstain": abstain, "total": yes + no + abstain}


def proposal_is_quorum_met(self, active_member_count, quorum_percent):
    """Check if enough members voted to meet quorum."""
    if active_member_count <= 0:
        return False
    total = getattr(self, "total_voters", 0) or 0
    return (total / active_member_count) * 100 >= quorum_percent


def proposal_is_approved(self):
    """Check if yes votes exceed the required threshold."""
    threshold = getattr(self, "required_threshold", 0.5) or 0.5
    yes = getattr(self, "votes_yes", 0) or 0
    no = getattr(self, "votes_no", 0) or 0
    votes_cast = yes + no
    if votes_cast == 0:
        return False
    return (yes / votes_cast) > threshold


def proposal_resolve(self, active_member_count, quorum_percent):
    """Tally votes and resolve proposal status."""
    proposal_tally(self)
    if not proposal_is_quorum_met(self, active_member_count, quorum_percent):
        self.status = "no_quorum"
    elif proposal_is_approved(self):
        self.status = "approved"
    else:
        self.status = "rejected"
    return self.status


# ---------------------------------------------------------------------------
# LedgerEntry — Financial Statements
# ---------------------------------------------------------------------------

def ledger_get_balance_sheet(cls, fund=None, fiscal_period=None, as_of_date=None):
    """Generate Balance Sheet from ledger entries."""
    def get_entries(entry_type):
        entries = [e for e in cls.instances()
                   if getattr(e, "entry_type", None) == entry_type]
        if fund:
            entries = [e for e in entries if getattr(e, "fund", None) is fund]
        if fiscal_period:
            entries = [e for e in entries if getattr(e, "fiscal_period", None) is fiscal_period]
        if as_of_date:
            entries = [e for e in entries if getattr(e, "entry_date", None) and e.entry_date <= as_of_date]
        return entries

    def by_category(entries, normal_debit):
        categories = {}
        for entry in entries:
            cat = getattr(entry, "category", None) or "uncategorized"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(entry)
        result = {}
        for cat, cat_entries in categories.items():
            td = sum(getattr(e, "debit", 0) or 0 for e in cat_entries)
            tc = sum(getattr(e, "credit", 0) or 0 for e in cat_entries)
            result[cat] = td - tc if normal_debit else tc - td
        return result

    assets = by_category(get_entries("asset"), normal_debit=True)
    liabilities = by_category(get_entries("liability"), normal_debit=False)
    fund_balance = by_category(get_entries("equity"), normal_debit=False)

    total_assets = sum(assets.values())
    total_liabilities = sum(liabilities.values())
    total_fund_balance = sum(fund_balance.values())

    return {
        "title": "Balance Sheet (Statement of Net Position)",
        "assets": {"items": assets, "total": total_assets},
        "liabilities": {"items": liabilities, "total": total_liabilities},
        "fund_balance": {"items": fund_balance, "total": total_fund_balance},
        "total_liabilities_and_fund_balance": total_liabilities + total_fund_balance,
        "is_balanced": total_assets == (total_liabilities + total_fund_balance),
        "net_position": total_assets - total_liabilities,
    }


def ledger_get_income_statement(cls, fiscal_period=None, fund=None,
                                start_date=None, end_date=None):
    """Generate Income Statement from ledger entries."""
    def get_entries(entry_type):
        entries = [e for e in cls.instances()
                   if getattr(e, "entry_type", None) == entry_type]
        if fund:
            entries = [e for e in entries if getattr(e, "fund", None) is fund]
        if fiscal_period:
            entries = [e for e in entries if getattr(e, "fiscal_period", None) is fiscal_period]
        if start_date:
            entries = [e for e in entries if getattr(e, "entry_date", None) and e.entry_date >= start_date]
        if end_date:
            entries = [e for e in entries if getattr(e, "entry_date", None) and e.entry_date <= end_date]
        return entries

    def by_category(entries, normal_debit):
        categories = {}
        for entry in entries:
            cat = getattr(entry, "category", None) or "uncategorized"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(entry)
        result = {}
        for cat, cat_entries in categories.items():
            td = sum(getattr(e, "debit", 0) or 0 for e in cat_entries)
            tc = sum(getattr(e, "credit", 0) or 0 for e in cat_entries)
            result[cat] = td - tc if normal_debit else tc - td
        return result

    revenues = by_category(get_entries("revenue"), normal_debit=False)
    expenses = by_category(get_entries("expense"), normal_debit=True)

    total_revenues = sum(revenues.values())
    total_expenses = sum(expenses.values())
    net_income = total_revenues - total_expenses

    return {
        "title": "Income Statement (Statement of Activities)",
        "revenues": {"items": revenues, "total": total_revenues},
        "expenses": {"items": expenses, "total": total_expenses},
        "net_income": net_income,
        "surplus_or_deficit": "surplus" if net_income >= 0 else "deficit",
    }


# ---------------------------------------------------------------------------
# JusticeSystem / Court / Case helpers
# ---------------------------------------------------------------------------

def is_active(self):
    return getattr(self, "status", None) == "active"


def case_is_open(self):
    return getattr(self, "status", None) in ("filed", "assigned", "in_progress")


def case_has_verdict(self):
    return getattr(self, "verdict", None) is not None


def case_can_appeal(self):
    return self.has_verdict() and getattr(self, "status", None) != "appealed"


def verdict_is_appealed(self):
    return getattr(self, "appeal", None) is not None


def verdict_total_penalty_amount(self):
    total = 0.0
    for p in getattr(self, "penalties", []):
        total += getattr(p, "amount", 0) or 0
    return total


def penalty_is_financial(self):
    return getattr(self, "penalty_type", None) in ("fine", "restitution")


def penalty_is_pending(self):
    return getattr(self, "status", None) == "pending"


def appeal_is_pending(self):
    return getattr(self, "status", None) in ("filed", "under_review")


def appeal_was_granted(self):
    return getattr(self, "status", None) == "granted"


def court_can_hear_appeal(self):
    level = getattr(self, "level", None)
    return level in ("appellate", "supreme") and self.is_active()


# ---------------------------------------------------------------------------
# UserProfile
# ---------------------------------------------------------------------------

def userprofile_add(self, operation):
    current = getattr(self, "allowed_to", "") or ""
    ops = [o.strip() for o in current.split(",") if o.strip()]
    if operation not in ops:
        ops.append(operation)
    self.allowed_to = ",".join(ops)


def userprofile_remove(self, operation):
    current = getattr(self, "allowed_to", "") or ""
    ops = [o.strip() for o in current.split(",") if o.strip()]
    if operation in ops:
        ops.remove(operation)
    self.allowed_to = ",".join(ops)


def userprofile_is_allowed(self, operation):
    current = getattr(self, "allowed_to", "") or ""
    ops = [o.strip() for o in current.split(",") if o.strip()]
    return "ALL" in ops or operation in ops


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

def task_new_task_execution(self):
    """Create a new TaskExecution for this task."""
    # Import here to avoid circular ref at module level
    from . import ggg_module
    te = ggg_module.TaskExecution(name=f"exec_{self._id}", task=self, status="idle")
    return te
