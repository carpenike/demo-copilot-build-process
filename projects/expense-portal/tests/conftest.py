"""Shared test fixtures for the Expense Portal test suite."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# --- Model Factories ---


def make_cost_center(**overrides):
    """Create a CostCenter-like object for testing."""
    defaults = {
        "id": uuid.uuid4(),
        "code": "CC-ENG-001",
        "name": "Engineering",
        "budget_amount": Decimal("150000.00"),
        "budget_period": "2026-03",
        "workday_id": "WD-CC-001",
        "is_active": True,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_employee(**overrides):
    """Create an Employee-like object for testing."""
    defaults = {
        "id": uuid.uuid4(),
        "entra_oid": f"entra-{uuid.uuid4()}",
        "email": f"user-{uuid.uuid4().hex[:6]}@acme.com",
        "full_name": "Jane Smith",
        "manager_id": None,
        "cost_center_id": None,
        "cost_center": None,
        "role": "employee",
        "is_active": True,
        "direct_reports": [],
    }
    defaults.update(overrides)
    emp = MagicMock(**defaults)
    emp.is_manager = len(defaults["direct_reports"]) > 0
    emp.is_finance_reviewer = defaults["role"] in ("finance_reviewer", "finance_admin")
    emp.is_finance_admin = defaults["role"] == "finance_admin"
    return emp


def make_expense_report(**overrides):
    """Create an ExpenseReport-like object for testing."""
    defaults = {
        "id": uuid.uuid4(),
        "report_number": "RPT-0001",
        "submitter_id": uuid.uuid4(),
        "title": "Q1 Client Meetings",
        "start_date": date(2026, 3, 1),
        "end_date": date(2026, 3, 7),
        "business_purpose": "Client meetings in Seattle",
        "status": "draft",
        "total_amount": Decimal("0"),
        "currency": "USD",
        "current_approver_id": None,
        "submitted_at": None,
        "approved_at": None,
        "rejected_at": None,
        "is_deleted": False,
        "line_items": [],
        "approval_actions": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    report = MagicMock(**defaults)
    report.is_editable = defaults["status"] in ("draft", "rejected")
    report.line_item_count = len(defaults["line_items"])
    return report


def make_line_item(**overrides):
    """Create a LineItem-like object for testing."""
    defaults = {
        "id": uuid.uuid4(),
        "report_id": uuid.uuid4(),
        "expense_date": date(2026, 3, 1),
        "category_id": uuid.uuid4(),
        "vendor_name": "Café Luna",
        "amount": Decimal("42.50"),
        "currency": "USD",
        "description": "Lunch with client",
        "ocr_status": None,
        "sort_order": 0,
        "receipt": None,
        "policy_violations": [],
        "category": None,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_category(**overrides):
    """Create an ExpenseCategory-like object for testing."""
    defaults = {
        "id": uuid.uuid4(),
        "name": "Meals",
        "daily_limit": Decimal("75.00"),
        "is_reimbursable": True,
        "is_active": True,
        "per_diem_rates": [],
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_per_diem_rate(**overrides):
    """Create a PerDiemRate-like object for testing."""
    defaults = {
        "id": uuid.uuid4(),
        "category_id": uuid.uuid4(),
        "destination": "US-Domestic",
        "rate": Decimal("75.00"),
        "effective_from": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "effective_to": None,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_threshold(**overrides):
    """Create an ApprovalThreshold-like object for testing."""
    defaults = {
        "id": uuid.uuid4(),
        "finance_review_threshold": Decimal("500.00"),
        "auto_escalation_business_days": 5,
        "reminder_business_days": 3,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


# --- Async Mock DB Session ---


def make_mock_db() -> AsyncMock:
    """Create a mock AsyncSession for testing core logic."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.delete = AsyncMock()
    return db


def mock_db_execute_returns(db: AsyncMock, return_value):
    """Configure mock db.execute to return a scalar result."""
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = return_value
    mock_result.scalars.return_value.all.return_value = (
        return_value if isinstance(return_value, list) else [return_value] if return_value else []
    )
    mock_result.first.return_value = return_value
    db.execute.return_value = mock_result
    return mock_result
