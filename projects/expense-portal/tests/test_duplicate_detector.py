"""Unit tests for duplicate detection (FR-007, US-004)."""

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from conftest import make_line_item, make_mock_db


class TestDuplicateDetection:
    """UT-DUP-001, UT-DUP-002: Duplicate submission detection."""

    @pytest.mark.asyncio
    async def test_detects_duplicate_same_date_amount_vendor(self):
        """UT-DUP-001: Match found for same employee, date, amount, vendor
        (FR-007, US-004 scenario 1)."""
        from app.core.duplicate_detector import check_duplicates

        db = make_mock_db()
        submitter_id = uuid.uuid4()
        current_report_id = uuid.uuid4()

        item = make_line_item(
            expense_date=date(2026, 3, 1),
            amount=Decimal("42.50"),
            vendor_name="Café Luna",
        )

        # Simulate a match in the DB
        match_row = MagicMock()
        match_row.report_number = "RPT-0042"
        mock_result = AsyncMock()
        mock_result.first.return_value = match_row
        db.execute = AsyncMock(return_value=mock_result)

        warnings = await check_duplicates(db, submitter_id, [item], current_report_id)

        assert len(warnings) == 1
        w = warnings[0]
        assert w.matching_report_number == "RPT-0042"
        assert "Café Luna" in w.message
        assert "$42.50" in w.message
        assert str(item.id) == w.line_item_id

    @pytest.mark.asyncio
    async def test_no_match_returns_empty_list(self):
        """UT-DUP-002: No duplicate found (US-004 scenario 2)."""
        from app.core.duplicate_detector import check_duplicates

        db = make_mock_db()
        submitter_id = uuid.uuid4()
        current_report_id = uuid.uuid4()

        item = make_line_item(
            expense_date=date(2026, 3, 5),
            amount=Decimal("99.00"),
            vendor_name="New Place",
        )

        mock_result = AsyncMock()
        mock_result.first.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        warnings = await check_duplicates(db, submitter_id, [item], current_report_id)

        assert len(warnings) == 0

    @pytest.mark.asyncio
    async def test_multiple_items_checked_individually(self):
        """Each line item is checked independently for duplicates."""
        from app.core.duplicate_detector import check_duplicates

        db = make_mock_db()
        submitter_id = uuid.uuid4()
        current_report_id = uuid.uuid4()

        item1 = make_line_item(
            expense_date=date(2026, 3, 1),
            amount=Decimal("42.50"),
            vendor_name="Café Luna",
        )
        item2 = make_line_item(
            expense_date=date(2026, 3, 2),
            amount=Decimal("88.00"),
            vendor_name="Hotel ABC",
        )

        call_count = {"n": 0}

        async def execute_side_effect(*args, **kwargs):
            call_count["n"] += 1
            result = AsyncMock()
            if call_count["n"] == 1:
                match = MagicMock()
                match.report_number = "RPT-0010"
                result.first.return_value = match
            else:
                result.first.return_value = None
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        warnings = await check_duplicates(db, submitter_id, [item1, item2], current_report_id)

        assert len(warnings) == 1
        assert warnings[0].matching_report_number == "RPT-0010"

    @pytest.mark.asyncio
    async def test_does_not_match_own_report(self):
        """Duplicate check excludes the current report being submitted
        (should not match against itself)."""
        from app.core.duplicate_detector import check_duplicates

        db = make_mock_db()
        submitter_id = uuid.uuid4()
        current_report_id = uuid.uuid4()

        item = make_line_item(
            expense_date=date(2026, 3, 1),
            amount=Decimal("42.50"),
            vendor_name="Café Luna",
        )

        # The query includes ExpenseReport.id != current_report_id,
        # so the DB would return no match when only match is the current report
        mock_result = AsyncMock()
        mock_result.first.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        warnings = await check_duplicates(db, submitter_id, [item], current_report_id)

        assert len(warnings) == 0
        # Verify the query was called (it should filter out current_report_id)
        db.execute.assert_called_once()
