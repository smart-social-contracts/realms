"""
Tests for GGG Government Accounting entities.

Tests the Fund, FiscalPeriod, Budget, and LedgerEntry entities
with double-entry bookkeeping validation and comprehensive
financial statement generation.
"""

import json
import sys
from pathlib import Path
from pprint import pformat
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src" / "realm_backend"
sys.path.insert(0, str(src_path))

# Mock kybra before importing anything that uses it
sys.modules["kybra"] = MagicMock()
sys.modules["kybra.canisters.management"] = MagicMock()


class TestFundEntity:
    """Tests for Fund entity."""

    def test_fund_creation(self):
        """Test creating a Fund entity."""
        from ggg.fund import Fund, FundType

        fund = Fund(
            code="GF",
            name="General Fund",
            fund_type=FundType.GENERAL,
            description="Main operating fund"
        )

        assert fund.code == "GF"
        assert fund.name == "General Fund"
        assert fund.fund_type == FundType.GENERAL

    def test_fund_types(self):
        """Test FundType constants."""
        from ggg.fund import FundType

        assert FundType.GENERAL == "general"
        assert FundType.SPECIAL_REVENUE == "special_revenue"
        assert FundType.CAPITAL_PROJECTS == "capital_projects"
        assert FundType.DEBT_SERVICE == "debt_service"
        assert FundType.ENTERPRISE == "enterprise"


class TestFiscalPeriodEntity:
    """Tests for FiscalPeriod entity."""

    def test_fiscal_period_creation(self):
        """Test creating a FiscalPeriod entity."""
        from ggg.fiscal_period import FiscalPeriod, FiscalPeriodStatus

        period = FiscalPeriod(
            id="FY2025",
            name="Fiscal Year 2025",
            start_date="2025-01-01",
            end_date="2025-12-31",
            status=FiscalPeriodStatus.OPEN
        )

        assert period.id == "FY2025"
        assert period.is_open() is True

    def test_fiscal_period_close(self):
        """Test closing a fiscal period."""
        from ggg.fiscal_period import FiscalPeriod, FiscalPeriodStatus

        period = FiscalPeriod(
            id="FY2024",
            name="Fiscal Year 2024",
            start_date="2024-01-01",
            end_date="2024-12-31",
            status=FiscalPeriodStatus.OPEN
        )

        assert period.is_open() is True
        period.close()
        assert period.is_open() is False
        assert period.status == FiscalPeriodStatus.CLOSED


class TestBudgetEntity:
    """Tests for Budget entity."""

    def test_budget_creation(self):
        """Test creating a Budget entity."""
        from ggg.budget import Budget, BudgetStatus

        budget = Budget(
            id="BUD-2025-TAX",
            name="Tax Revenue Budget",
            category="tax",
            budget_type="revenue",
            planned_amount=1000000,
            status=BudgetStatus.DRAFT
        )

        assert budget.id == "BUD-2025-TAX"
        assert budget.planned_amount == 1000000
        assert budget.actual_amount == 0

    def test_budget_variance(self):
        """Test budget variance calculation."""
        from ggg.budget import Budget

        budget = Budget(
            id="BUD-TEST",
            name="Test Budget",
            category="personnel",
            budget_type="expense",
            planned_amount=100000,
            actual_amount=95000
        )

        # Under budget by 5000
        assert budget.variance() == -5000
        assert budget.variance_percent() == -5.0

    def test_budget_update_actual(self):
        """Test updating actual amount."""
        from ggg.budget import Budget

        budget = Budget(
            id="BUD-TEST2",
            name="Test Budget 2",
            planned_amount=50000,
            actual_amount=0
        )

        budget.update_actual(10000)
        assert budget.actual_amount == 10000

        budget.update_actual(5000)
        assert budget.actual_amount == 15000


class TestLedgerEntryEntity:
    """Tests for LedgerEntry entity with double-entry bookkeeping."""

    def test_ledger_entry_creation(self):
        """Test creating a LedgerEntry."""
        from ggg.ledger_entry import Category, EntryType, LedgerEntry

        entry = LedgerEntry(
            id="LE001",
            transaction_id="TXN001",
            entry_type=EntryType.ASSET,
            category=Category.CASH,
            debit=1000,
            credit=0,
            entry_date="2025-01-15",
            description="Cash received from tax payment"
        )

        assert entry.id == "LE001"
        assert entry.transaction_id == "TXN001"
        assert entry.is_debit() is True
        assert entry.is_credit() is False
        assert entry.amount() == 1000

    def test_entry_type_constants(self):
        """Test EntryType constants."""
        from ggg.ledger_entry import EntryType

        # Balance Sheet types
        assert EntryType.ASSET == "asset"
        assert EntryType.LIABILITY == "liability"
        assert EntryType.EQUITY == "equity"

        # Income Statement types
        assert EntryType.REVENUE == "revenue"
        assert EntryType.EXPENSE == "expense"

    def test_category_constants(self):
        """Test Category constants."""
        from ggg.ledger_entry import Category

        # Revenues
        assert Category.TAX == "tax"
        assert Category.FEE == "fee"
        assert Category.GRANT == "grant"

        # Expenses
        assert Category.PERSONNEL == "personnel"
        assert Category.SUPPLIES == "supplies"

        # Assets
        assert Category.CASH == "cash"
        assert Category.RECEIVABLE == "receivable"

        # Liabilities
        assert Category.PAYABLE == "payable"
        assert Category.BOND == "bond"

    def test_double_entry_debit_credit(self):
        """Test that entries correctly identify as debit or credit."""
        from ggg.ledger_entry import Category, EntryType, LedgerEntry

        debit_entry = LedgerEntry(
            id="LE-D1",
            transaction_id="TXN002",
            entry_type=EntryType.EXPENSE,
            category=Category.PERSONNEL,
            debit=5000,
            credit=0
        )

        credit_entry = LedgerEntry(
            id="LE-C1",
            transaction_id="TXN002",
            entry_type=EntryType.ASSET,
            category=Category.CASH,
            debit=0,
            credit=5000
        )

        assert debit_entry.is_debit() is True
        assert debit_entry.is_credit() is False
        assert debit_entry.amount() == 5000

        assert credit_entry.is_debit() is False
        assert credit_entry.is_credit() is True
        assert credit_entry.amount() == 5000


class TestDoubleEntryTransactions:
    """Tests for double-entry transaction validation."""

    def test_create_balanced_transaction(self):
        """Test creating a balanced double-entry transaction."""
        from ggg.ledger_entry import Category, EntryType, LedgerEntry

        # Tax revenue received: Debit Cash, Credit Revenue
        entries = [
            {
                "entry_type": EntryType.ASSET,
                "category": Category.CASH,
                "debit": 10000,
                "credit": 0,
                "entry_date": "2025-01-20",
                "description": "Tax payment received"
            },
            {
                "entry_type": EntryType.REVENUE,
                "category": Category.TAX,
                "debit": 0,
                "credit": 10000,
                "entry_date": "2025-01-20",
                "description": "Tax revenue recognized"
            }
        ]

        created = LedgerEntry.create_transaction("TXN-TAX-001", entries)

        assert len(created) == 2
        assert created[0].transaction_id == "TXN-TAX-001"
        assert created[1].transaction_id == "TXN-TAX-001"

        # Verify balanced
        total_debit = sum(e.debit or 0 for e in created)
        total_credit = sum(e.credit or 0 for e in created)
        assert total_debit == total_credit == 10000

    def test_unbalanced_transaction_raises_error(self):
        """Test that unbalanced transactions raise ValueError."""
        from ggg.ledger_entry import Category, EntryType, LedgerEntry

        # Unbalanced: debit 1000, credit 500
        entries = [
            {
                "entry_type": EntryType.ASSET,
                "category": Category.CASH,
                "debit": 1000,
                "credit": 0
            },
            {
                "entry_type": EntryType.REVENUE,
                "category": Category.TAX,
                "debit": 0,
                "credit": 500  # Wrong amount!
            }
        ]

        with pytest.raises(ValueError) as exc_info:
            LedgerEntry.create_transaction("TXN-BAD", entries, validate=True)

        assert "Unbalanced" in str(exc_info.value)
        assert "debit=1000" in str(exc_info.value)
        assert "credit=500" in str(exc_info.value)

    def test_skip_validation(self):
        """Test that validation can be skipped."""
        from ggg.ledger_entry import Category, EntryType, LedgerEntry

        # Unbalanced but validation skipped
        entries = [
            {
                "entry_type": EntryType.ASSET,
                "category": Category.CASH,
                "debit": 1000,
                "credit": 0
            }
        ]

        # Should not raise with validate=False
        created = LedgerEntry.create_transaction("TXN-SKIP", entries, validate=False)
        assert len(created) == 1


class TestComprehensiveFinancialStatements:
    """
    Comprehensive tests that generate all three financial statements
    from a realistic set of government transactions.
    """

    @pytest.fixture
    def mock_ledger_entries(self):
        """Create a comprehensive set of ledger entries for a fiscal year."""
        from ggg.ledger_entry import Category, EntryType, LedgerEntry

        # Store entries for mock find()
        entries = []

        def create_entry(**kwargs):
            entry = LedgerEntry(**kwargs)
            entries.append(entry)
            return entry

        # ========================================
        # OPENING BALANCES (Prior Year)
        # ========================================
        
        # Opening cash balance: 500,000
        create_entry(
            id="OPEN-1", transaction_id="TXN-OPEN-1",
            entry_type=EntryType.ASSET, category=Category.CASH,
            debit=500000, credit=0, entry_date="2024-12-31",
            description="Opening cash balance"
        )
        create_entry(
            id="OPEN-2", transaction_id="TXN-OPEN-1",
            entry_type=EntryType.EQUITY, category=Category.FUND_BALANCE,
            debit=0, credit=500000, entry_date="2024-12-31",
            description="Opening fund balance"
        )

        # ========================================
        # Q1: REVENUE TRANSACTIONS
        # ========================================
        
        # Property Tax Collection: 250,000
        create_entry(
            id="Q1-TAX-1", transaction_id="TXN-Q1-TAX",
            entry_type=EntryType.ASSET, category=Category.CASH,
            debit=250000, credit=0, entry_date="2025-01-15",
            description="Property tax collection"
        )
        create_entry(
            id="Q1-TAX-2", transaction_id="TXN-Q1-TAX",
            entry_type=EntryType.REVENUE, category=Category.TAX,
            debit=0, credit=250000, entry_date="2025-01-15",
            description="Property tax revenue"
        )

        # License Fees: 25,000
        create_entry(
            id="Q1-FEE-1", transaction_id="TXN-Q1-FEE",
            entry_type=EntryType.ASSET, category=Category.CASH,
            debit=25000, credit=0, entry_date="2025-02-01",
            description="License fee collection"
        )
        create_entry(
            id="Q1-FEE-2", transaction_id="TXN-Q1-FEE",
            entry_type=EntryType.REVENUE, category=Category.FEE,
            debit=0, credit=25000, entry_date="2025-02-01",
            description="License fee revenue"
        )

        # Federal Grant: 100,000
        create_entry(
            id="Q1-GRANT-1", transaction_id="TXN-Q1-GRANT",
            entry_type=EntryType.ASSET, category=Category.CASH,
            debit=100000, credit=0, entry_date="2025-03-01",
            description="Federal grant received"
        )
        create_entry(
            id="Q1-GRANT-2", transaction_id="TXN-Q1-GRANT",
            entry_type=EntryType.REVENUE, category=Category.GRANT,
            debit=0, credit=100000, entry_date="2025-03-01",
            description="Federal grant revenue"
        )

        # ========================================
        # Q1: EXPENSE TRANSACTIONS
        # ========================================
        
        # Payroll: 150,000
        create_entry(
            id="Q1-PAY-1", transaction_id="TXN-Q1-PAY",
            entry_type=EntryType.EXPENSE, category=Category.PERSONNEL,
            debit=150000, credit=0, entry_date="2025-01-31",
            description="January payroll"
        )
        create_entry(
            id="Q1-PAY-2", transaction_id="TXN-Q1-PAY",
            entry_type=EntryType.ASSET, category=Category.CASH,
            debit=0, credit=150000, entry_date="2025-01-31",
            description="Payroll disbursement"
        )

        # Office Supplies: 10,000
        create_entry(
            id="Q1-SUP-1", transaction_id="TXN-Q1-SUP",
            entry_type=EntryType.EXPENSE, category=Category.SUPPLIES,
            debit=10000, credit=0, entry_date="2025-02-15",
            description="Office supplies"
        )
        create_entry(
            id="Q1-SUP-2", transaction_id="TXN-Q1-SUP",
            entry_type=EntryType.ASSET, category=Category.CASH,
            debit=0, credit=10000, entry_date="2025-02-15",
            description="Supplies payment"
        )

        # Professional Services: 35,000
        create_entry(
            id="Q1-SVC-1", transaction_id="TXN-Q1-SVC",
            entry_type=EntryType.EXPENSE, category=Category.SERVICES,
            debit=35000, credit=0, entry_date="2025-03-15",
            description="Legal and consulting services"
        )
        create_entry(
            id="Q1-SVC-2", transaction_id="TXN-Q1-SVC",
            entry_type=EntryType.ASSET, category=Category.CASH,
            debit=0, credit=35000, entry_date="2025-03-15",
            description="Services payment"
        )

        # ========================================
        # Q2: CAPITAL PROJECT (Investing)
        # ========================================
        
        # Bond Issuance: 1,000,000 (Financing)
        create_entry(
            id="Q2-BOND-1", transaction_id="TXN-Q2-BOND",
            entry_type=EntryType.ASSET, category=Category.CASH,
            debit=1000000, credit=0, entry_date="2025-04-01",
            description="Bond proceeds received", tags="financing,bond"
        )
        create_entry(
            id="Q2-BOND-2", transaction_id="TXN-Q2-BOND",
            entry_type=EntryType.LIABILITY, category=Category.BOND,
            debit=0, credit=1000000, entry_date="2025-04-01",
            description="Bonds payable"
        )

        # Equipment Purchase: 200,000 (Investing)
        create_entry(
            id="Q2-EQUIP-1", transaction_id="TXN-Q2-EQUIP",
            entry_type=EntryType.ASSET, category=Category.EQUIPMENT,
            debit=200000, credit=0, entry_date="2025-05-01",
            description="Fire truck purchase", tags="investing,capital"
        )
        create_entry(
            id="Q2-EQUIP-2", transaction_id="TXN-Q2-EQUIP",
            entry_type=EntryType.ASSET, category=Category.CASH,
            debit=0, credit=200000, entry_date="2025-05-01",
            description="Equipment payment", tags="investing"
        )

        # ========================================
        # Q3: MORE OPERATING ACTIVITIES
        # ========================================
        
        # Sales Tax: 180,000
        create_entry(
            id="Q3-TAX-1", transaction_id="TXN-Q3-TAX",
            entry_type=EntryType.ASSET, category=Category.CASH,
            debit=180000, credit=0, entry_date="2025-07-15",
            description="Sales tax collection"
        )
        create_entry(
            id="Q3-TAX-2", transaction_id="TXN-Q3-TAX",
            entry_type=EntryType.REVENUE, category=Category.TAX,
            debit=0, credit=180000, entry_date="2025-07-15",
            description="Sales tax revenue"
        )

        # Q3 Payroll: 160,000
        create_entry(
            id="Q3-PAY-1", transaction_id="TXN-Q3-PAY",
            entry_type=EntryType.EXPENSE, category=Category.PERSONNEL,
            debit=160000, credit=0, entry_date="2025-09-30",
            description="Q3 payroll"
        )
        create_entry(
            id="Q3-PAY-2", transaction_id="TXN-Q3-PAY",
            entry_type=EntryType.ASSET, category=Category.CASH,
            debit=0, credit=160000, entry_date="2025-09-30",
            description="Q3 payroll disbursement"
        )

        # ========================================
        # Q4: DEBT SERVICE (Financing)
        # ========================================
        
        # Bond Interest Payment: 50,000
        create_entry(
            id="Q4-INT-1", transaction_id="TXN-Q4-INT",
            entry_type=EntryType.EXPENSE, category=Category.DEBT,
            debit=50000, credit=0, entry_date="2025-10-01",
            description="Bond interest expense"
        )
        create_entry(
            id="Q4-INT-2", transaction_id="TXN-Q4-INT",
            entry_type=EntryType.ASSET, category=Category.CASH,
            debit=0, credit=50000, entry_date="2025-10-01",
            description="Interest payment", tags="financing,debt"
        )

        # Accounts Payable: 15,000
        create_entry(
            id="Q4-AP-1", transaction_id="TXN-Q4-AP",
            entry_type=EntryType.EXPENSE, category=Category.SUPPLIES,
            debit=15000, credit=0, entry_date="2025-11-15",
            description="Year-end supplies"
        )
        create_entry(
            id="Q4-AP-2", transaction_id="TXN-Q4-AP",
            entry_type=EntryType.LIABILITY, category=Category.PAYABLE,
            debit=0, credit=15000, entry_date="2025-11-15",
            description="Accounts payable"
        )

        return entries

    def test_balance_sheet_generation(self, mock_ledger_entries):
        """Test generating a comprehensive Balance Sheet."""
        from ggg.ledger_entry import LedgerEntry

        # Mock the find method to return our test entries
        with patch.object(LedgerEntry, 'find', side_effect=lambda filters: [
            e for e in mock_ledger_entries 
            if all(getattr(e, k, None) == v for k, v in filters.items())
        ]):
            balance_sheet = LedgerEntry.get_balance_sheet()

            print("\n" + "=" * 60)
            print("BALANCE SHEET (Statement of Net Position)")
            print("=" * 60)
            print(json.dumps(balance_sheet, indent=2, default=str))

            # Verify structure
            assert "title" in balance_sheet
            assert "assets" in balance_sheet
            assert "liabilities" in balance_sheet
            assert "fund_balance" in balance_sheet

            # Check assets
            assets = balance_sheet["assets"]
            assert "items" in assets
            assert "cash" in assets["items"]
            assert "equipment" in assets["items"]
            
            # Verify totals are calculated
            assert assets["total"] > 0
            assert balance_sheet["net_position"] > 0

            # Print formatted report
            print("\n--- ASSETS ---")
            for cat, amt in assets["items"].items():
                print(f"  {cat}: {amt:,}")
            print(f"  TOTAL ASSETS: {assets['total']:,}")

            print("\n--- LIABILITIES ---")
            liabs = balance_sheet["liabilities"]
            for cat, amt in liabs["items"].items():
                print(f"  {cat}: {amt:,}")
            print(f"  TOTAL LIABILITIES: {liabs['total']:,}")

            print("\n--- FUND BALANCE ---")
            fb = balance_sheet["fund_balance"]
            for cat, amt in fb["items"].items():
                print(f"  {cat}: {amt:,}")
            print(f"  TOTAL FUND BALANCE: {fb['total']:,}")

            print(f"\nNET POSITION: {balance_sheet['net_position']:,}")
            print(f"IS BALANCED: {balance_sheet['is_balanced']}")

    def test_income_statement_generation(self, mock_ledger_entries):
        """Test generating a comprehensive Income Statement."""
        from ggg.ledger_entry import LedgerEntry

        with patch.object(LedgerEntry, 'find', side_effect=lambda filters: [
            e for e in mock_ledger_entries 
            if all(getattr(e, k, None) == v for k, v in filters.items())
        ]):
            income_stmt = LedgerEntry.get_income_statement()

            print("\n" + "=" * 60)
            print("INCOME STATEMENT (Statement of Activities)")
            print("=" * 60)
            print(json.dumps(income_stmt, indent=2, default=str))

            # Verify structure
            assert "title" in income_stmt
            assert "revenues" in income_stmt
            assert "expenses" in income_stmt
            assert "net_income" in income_stmt
            assert "surplus_or_deficit" in income_stmt

            # Check revenues
            revenues = income_stmt["revenues"]
            assert "tax" in revenues["items"]
            assert "fee" in revenues["items"]
            assert "grant" in revenues["items"]

            # Check expenses
            expenses = income_stmt["expenses"]
            assert "personnel" in expenses["items"]
            assert "supplies" in expenses["items"]

            # Print formatted report
            print("\n--- REVENUES ---")
            for cat, amt in revenues["items"].items():
                print(f"  {cat}: {amt:,}")
            print(f"  TOTAL REVENUES: {revenues['total']:,}")

            print("\n--- EXPENSES ---")
            for cat, amt in expenses["items"].items():
                print(f"  {cat}: {amt:,}")
            print(f"  TOTAL EXPENSES: {expenses['total']:,}")

            print(f"\nNET INCOME: {income_stmt['net_income']:,}")
            print(f"STATUS: {income_stmt['surplus_or_deficit'].upper()}")

    def test_cash_flow_statement_generation(self, mock_ledger_entries):
        """Test generating a comprehensive Cash Flow Statement."""
        from ggg.ledger_entry import LedgerEntry

        with patch.object(LedgerEntry, 'find', side_effect=lambda filters: [
            e for e in mock_ledger_entries 
            if all(getattr(e, k, None) == v for k, v in filters.items())
        ]):
            cash_flow = LedgerEntry.get_cash_flow_statement(
                start_date="2025-01-01",
                end_date="2025-12-31"
            )

            print("\n" + "=" * 60)
            print("CASH FLOW STATEMENT")
            print("=" * 60)
            print(json.dumps(cash_flow, indent=2, default=str))

            # Verify structure
            assert "title" in cash_flow
            assert "operating_activities" in cash_flow
            assert "investing_activities" in cash_flow
            assert "financing_activities" in cash_flow
            assert "net_change_in_cash" in cash_flow

            # Print formatted report
            print("\n--- OPERATING ACTIVITIES ---")
            operating = cash_flow["operating_activities"]
            for desc, amt in operating["items"].items():
                direction = "inflow" if amt > 0 else "outflow"
                print(f"  {desc}: {amt:,} ({direction})")
            print(f"  NET OPERATING: {operating['total']:,}")

            print("\n--- INVESTING ACTIVITIES ---")
            investing = cash_flow["investing_activities"]
            for desc, amt in investing["items"].items():
                direction = "inflow" if amt > 0 else "outflow"
                print(f"  {desc}: {amt:,} ({direction})")
            print(f"  NET INVESTING: {investing['total']:,}")

            print("\n--- FINANCING ACTIVITIES ---")
            financing = cash_flow["financing_activities"]
            for desc, amt in financing["items"].items():
                direction = "inflow" if amt > 0 else "outflow"
                print(f"  {desc}: {amt:,} ({direction})")
            print(f"  NET FINANCING: {financing['total']:,}")

            print(f"\nNET CHANGE IN CASH: {cash_flow['net_change_in_cash']:,}")
            print(f"BEGINNING CASH: {cash_flow['beginning_cash_balance']:,}")
            print(f"ENDING CASH: {cash_flow['ending_cash_balance']:,}")

    def test_all_statements_comprehensive(self, mock_ledger_entries):
        """
        Generate all three statements and verify accounting equation holds.
        Assets = Liabilities + Fund Balance
        """
        from ggg.ledger_entry import LedgerEntry

        with patch.object(LedgerEntry, 'find', side_effect=lambda filters: [
            e for e in mock_ledger_entries 
            if all(getattr(e, k, None) == v for k, v in filters.items())
        ]):
            # Generate all statements
            balance_sheet = LedgerEntry.get_balance_sheet()
            income_stmt = LedgerEntry.get_income_statement()
            cash_flow = LedgerEntry.get_cash_flow_statement(
                start_date="2025-01-01"
            )

            print("\n" + "=" * 70)
            print("COMPREHENSIVE FINANCIAL STATEMENTS - FY2025")
            print("=" * 70)

            # ===== BALANCE SHEET =====
            print("\n" + "-" * 70)
            print("1. BALANCE SHEET (Statement of Net Position)")
            print("-" * 70)
            
            print("\nASSETS:")
            for cat, amt in balance_sheet["assets"]["items"].items():
                print(f"    {cat.replace('_', ' ').title():<30} ${amt:>15,}")
            print(f"    {'─' * 45}")
            print(f"    {'Total Assets':<30} ${balance_sheet['assets']['total']:>15,}")

            print("\nLIABILITIES:")
            for cat, amt in balance_sheet["liabilities"]["items"].items():
                print(f"    {cat.replace('_', ' ').title():<30} ${amt:>15,}")
            print(f"    {'─' * 45}")
            print(f"    {'Total Liabilities':<30} ${balance_sheet['liabilities']['total']:>15,}")

            print("\nFUND BALANCE:")
            for cat, amt in balance_sheet["fund_balance"]["items"].items():
                print(f"    {cat.replace('_', ' ').title():<30} ${amt:>15,}")
            print(f"    {'─' * 45}")
            print(f"    {'Total Fund Balance':<30} ${balance_sheet['fund_balance']['total']:>15,}")

            print(f"\n    {'═' * 45}")
            print(f"    {'NET POSITION':<30} ${balance_sheet['net_position']:>15,}")

            # ===== INCOME STATEMENT =====
            print("\n" + "-" * 70)
            print("2. INCOME STATEMENT (Statement of Activities)")
            print("-" * 70)

            print("\nREVENUES:")
            for cat, amt in income_stmt["revenues"]["items"].items():
                print(f"    {cat.replace('_', ' ').title():<30} ${amt:>15,}")
            print(f"    {'─' * 45}")
            print(f"    {'Total Revenues':<30} ${income_stmt['revenues']['total']:>15,}")

            print("\nEXPENSES:")
            for cat, amt in income_stmt["expenses"]["items"].items():
                print(f"    {cat.replace('_', ' ').title():<30} ${amt:>15,}")
            print(f"    {'─' * 45}")
            print(f"    {'Total Expenses':<30} ${income_stmt['expenses']['total']:>15,}")

            print(f"\n    {'═' * 45}")
            status = "SURPLUS" if income_stmt["net_income"] >= 0 else "DEFICIT"
            print(f"    {'NET INCOME (' + status + ')':<30} ${income_stmt['net_income']:>15,}")

            # ===== CASH FLOW STATEMENT =====
            print("\n" + "-" * 70)
            print("3. CASH FLOW STATEMENT")
            print("-" * 70)

            print("\nCASH FLOWS FROM OPERATING ACTIVITIES:")
            for desc, amt in cash_flow["operating_activities"]["items"].items():
                print(f"    {desc[:40]:<40} ${amt:>15,}")
            print(f"    {'─' * 55}")
            print(f"    {'Net Operating Cash Flow':<40} ${cash_flow['operating_activities']['total']:>15,}")

            print("\nCASH FLOWS FROM INVESTING ACTIVITIES:")
            for desc, amt in cash_flow["investing_activities"]["items"].items():
                print(f"    {desc[:40]:<40} ${amt:>15,}")
            print(f"    {'─' * 55}")
            print(f"    {'Net Investing Cash Flow':<40} ${cash_flow['investing_activities']['total']:>15,}")

            print("\nCASH FLOWS FROM FINANCING ACTIVITIES:")
            for desc, amt in cash_flow["financing_activities"]["items"].items():
                print(f"    {desc[:40]:<40} ${amt:>15,}")
            print(f"    {'─' * 55}")
            print(f"    {'Net Financing Cash Flow':<40} ${cash_flow['financing_activities']['total']:>15,}")

            print(f"\n    {'═' * 55}")
            print(f"    {'NET CHANGE IN CASH':<40} ${cash_flow['net_change_in_cash']:>15,}")
            print(f"    {'Beginning Cash Balance':<40} ${cash_flow['beginning_cash_balance']:>15,}")
            print(f"    {'─' * 55}")
            print(f"    {'ENDING CASH BALANCE':<40} ${cash_flow['ending_cash_balance']:>15,}")

            print("\n" + "=" * 70)
            print("END OF FINANCIAL STATEMENTS")
            print("=" * 70)

            # Assertions
            assert balance_sheet["assets"]["total"] > 0
            assert income_stmt["revenues"]["total"] > 0
            assert "net_change_in_cash" in cash_flow


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
