"""Tests for issued financial reports (compile + issue)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
BACKEND = REPO_ROOT / "src" / "realm_backend"
sys.path.insert(0, str(BACKEND))
sys.modules.setdefault("basilisk", MagicMock())
sys.modules.setdefault("_cdk", MagicMock())

from ic_python_db import Database  # noqa: E402


class MockStorage:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def insert(self, key, value):
        self.data[key] = value

    def remove(self, key):
        if key in self.data:
            del self.data[key]

    def items(self):
        return self.data.items()

    def keys(self):
        return list(self.data.keys())

    def __len__(self):
        return len(self.data)


if Database._instance is None:
    Database.init(db_storage=MockStorage(), audit_enabled=False)

import ggg  # noqa: F401, E402


@pytest.fixture(scope="module", autouse=True)
def _isolate_treasury_modules():
    yield
    import core

    for name in ("core.treasury_allocation", "core.financial_reports"):
        sys.modules.pop(name, None)
    for attr in ("treasury_allocation", "financial_reports"):
        if hasattr(core, attr):
            delattr(core, attr)


@pytest.fixture(autouse=True)
def clean_db():
    Database.get_instance().clear()
    yield
    Database.get_instance().clear()


@pytest.fixture
def period():
    from ggg import FiscalPeriod, FiscalPeriodStatus

    return FiscalPeriod(
        id="2025-H1",
        name="First half 2025",
        start_date="2025-01-01",
        end_date="2025-06-30",
        status=FiscalPeriodStatus.CLOSED,
    )


@pytest.fixture
def two_revenue_pairs(period):
    from ggg import Category, EntryType, LedgerEntry

    LedgerEntry.create_transaction(
        "TXN-IN",
        [
            {
                "entry_type": EntryType.ASSET,
                "category": Category.CASH,
                "debit": 1000,
                "credit": 0,
                "entry_date": "2025-03-01",
                "fiscal_period": period,
            },
            {
                "entry_type": EntryType.REVENUE,
                "category": Category.TAX,
                "debit": 0,
                "credit": 1000,
                "entry_date": "2025-03-01",
                "fiscal_period": period,
            },
        ],
    )
    LedgerEntry.create_transaction(
        "TXN-AFTER",
        [
            {
                "entry_type": EntryType.ASSET,
                "category": Category.CASH,
                "debit": 2000,
                "credit": 0,
                "entry_date": "2025-08-01",
                "fiscal_period": period,
            },
            {
                "entry_type": EntryType.REVENUE,
                "category": Category.TAX,
                "debit": 0,
                "credit": 2000,
                "entry_date": "2025-08-01",
                "fiscal_period": period,
            },
        ],
    )


@patch("core.treasury_allocation.treasury_currency", return_value="ICP")
class TestCompileStatements:
    def test_balance_sheet_includes_later_entries(
        self, _mock_currency, period, two_revenue_pairs
    ):
        from core.financial_reports import compile_statements

        out = compile_statements(
            "2025-12-31",
            period=period,
            window_start="2025-01-01",
        )
        assert out["statements"]["balance_sheet"]["assets"]["total"] == 3000

    def test_income_statement_respects_window(
        self, _mock_currency, period, two_revenue_pairs
    ):
        from core.financial_reports import compile_statements

        out = compile_statements(
            "2025-06-30",
            period=period,
            window_start="2025-01-01",
        )
        assert out["statements"]["income_statement"]["net_income"] == 1000
        assert out["statements"]["summary"]["net_income"] == 1000


@patch("core.treasury_allocation.treasury_currency", return_value="ICP")
class TestIssuePeriodReport:
    def test_idempotent_skip(self, _mock_currency, period, two_revenue_pairs):
        from core.financial_reports import issue_period_report
        from ggg import FinancialReport

        first = issue_period_report("2025-H1", issued_by="alice")
        second = issue_period_report("2025-H1", issued_by="alice")

        assert first["success"] is True
        assert first["skipped"] is False
        assert first["id"] == "FR-2025-H1"
        assert second["skipped"] is True
        assert len(list(FinancialReport.instances())) == 1

    def test_restatement_supersedes(self, _mock_currency, period, two_revenue_pairs):
        from core.financial_reports import issue_period_report, latest_report_for_period
        from ggg import FinancialReport

        issue_period_report("2025-H1", issued_by="system")
        restated = issue_period_report(
            "2025-H1", issued_by="manager", restate=True
        )

        assert restated["id"] == "FR-2025-H1-R1"
        assert restated["skipped"] is False
        report = FinancialReport[restated["id"]]
        assert report.supersedes.id == "FR-2025-H1"
        assert latest_report_for_period("2025-H1").id == "FR-2025-H1-R1"


@patch("core.treasury_allocation.treasury_currency", return_value="ICP")
class TestIssueAsOf:
    def test_creates_as_of_kind(self, _mock_currency, period, two_revenue_pairs):
        from core.financial_reports import issue_as_of
        from ggg import FinancialReport, FinancialReportKind

        out = issue_as_of(
            as_of="2025-12-31", issued_by="bob", period_id="2025-H1"
        )
        report = FinancialReport[out["id"]]
        assert report.kind == FinancialReportKind.AS_OF
        assert report.as_of == "2025-12-31"
        assert report.issued_by == "bob"


@patch("core.treasury_allocation.treasury_currency", return_value="ICP")
@patch("core.treasury_allocation._now_ts", return_value=1_735_689_600)
class TestIssueDraft:
    def test_creates_draft_kind(self, _mock_now, _mock_currency, period, two_revenue_pairs):
        from core.financial_reports import issue_draft, latest_report_for_period
        from ggg import FinancialReport, FinancialReportKind

        out = issue_draft(issued_by="carol")
        report = FinancialReport[out["id"]]
        assert out["success"] is True
        assert report.kind == FinancialReportKind.DRAFT
        assert report.issued_by == "carol"
        assert report.id.startswith("FR-draft-")
        assert latest_report_for_period("2025-H1") is None
