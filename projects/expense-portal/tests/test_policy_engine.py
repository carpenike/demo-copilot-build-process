"""Unit tests for the policy engine (FR-005, FR-013, FR-014, FR-015).

Tests are derived from requirements and user stories US-003/US-009,
NOT from the implementation.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from conftest import make_category, make_line_item, make_mock_db, make_per_diem_rate


# ---- Helper to set up mock DB responses per-call ----


def _setup_db_for_policy(db, category, per_diem_rates=None):
    """Configure mock DB to return the given category and per diem rates."""
    call_count = {"n": 0}
    original_execute = db.execute

    async def execute_side_effect(*args, **kwargs):
        call_count["n"] += 1
        result = AsyncMock()
        # First call: _get_category
        if call_count["n"] == 1:
            result.scalar_one_or_none.return_value = category
        # Second call: _check_per_diem (per diem rates)
        elif call_count["n"] == 2:
            result.scalars.return_value.all.return_value = per_diem_rates or []
        else:
            result.scalar_one_or_none.return_value = None
            result.scalars.return_value.all.return_value = []
        return result

    db.execute = AsyncMock(side_effect=execute_side_effect)


# ====================================================================
# FR-005 + US-003: Policy validation — happy path
# ====================================================================


class TestPolicyValidation:
    """UT-POL-001 through UT-POL-007: Policy engine validation rules."""

    @pytest.mark.asyncio
    async def test_valid_line_item_passes_all_checks(self):
        """UT-POL-001: Line item within limits and in reimbursable category
        passes with no violations (US-003 scenario 1)."""
        from app.core.policy_engine import validate_line_items

        db = make_mock_db()
        category = make_category(daily_limit=Decimal("75.00"), is_reimbursable=True)
        item = make_line_item(amount=Decimal("42.50"), category_id=category.id)

        _setup_db_for_policy(db, category, per_diem_rates=[])

        violations = await validate_line_items(db, [item])

        assert len(violations) == 0

    # ====================================================================
    # FR-013 + US-003: Daily limit exceeded
    # ====================================================================

    @pytest.mark.asyncio
    async def test_daily_limit_exceeded_returns_blocking_violation(self):
        """UT-POL-002: Amount exceeding category daily limit produces
        a blocking violation (FR-013, US-003 scenario 2)."""
        from app.core.policy_engine import validate_line_items

        db = make_mock_db()
        category = make_category(name="Meals", daily_limit=Decimal("75.00"), is_reimbursable=True)
        item = make_line_item(amount=Decimal("125.00"), category_id=category.id)

        _setup_db_for_policy(db, category, per_diem_rates=[])

        violations = await validate_line_items(db, [item])

        assert len(violations) == 1
        v = violations[0]
        assert v.rule == "daily_limit_exceeded"
        assert v.is_blocking is True
        assert "$125.00" in v.message
        assert "$75.00" in v.message

    @pytest.mark.asyncio
    async def test_amount_at_exactly_daily_limit_passes(self):
        """Edge case: amount exactly at the limit should pass."""
        from app.core.policy_engine import validate_line_items

        db = make_mock_db()
        category = make_category(daily_limit=Decimal("75.00"), is_reimbursable=True)
        item = make_line_item(amount=Decimal("75.00"), category_id=category.id)

        _setup_db_for_policy(db, category, per_diem_rates=[])

        violations = await validate_line_items(db, [item])

        assert len(violations) == 0

    @pytest.mark.asyncio
    async def test_no_daily_limit_configured_passes_any_amount(self):
        """Category with no daily limit (null) allows any amount."""
        from app.core.policy_engine import validate_line_items

        db = make_mock_db()
        category = make_category(daily_limit=None, is_reimbursable=True)
        item = make_line_item(amount=Decimal("9999.99"), category_id=category.id)

        _setup_db_for_policy(db, category, per_diem_rates=[])

        violations = await validate_line_items(db, [item])

        assert len(violations) == 0

    # ====================================================================
    # FR-015 + US-003: Non-reimbursable category
    # ====================================================================

    @pytest.mark.asyncio
    async def test_non_reimbursable_category_returns_blocking_violation(self):
        """UT-POL-003: Non-reimbursable category produces a blocking violation
        (FR-015, US-003 scenario 3)."""
        from app.core.policy_engine import validate_line_items

        db = make_mock_db()
        category = make_category(
            name="Personal Entertainment", is_reimbursable=False, daily_limit=None
        )
        item = make_line_item(amount=Decimal("50.00"), category_id=category.id)

        _setup_db_for_policy(db, category, per_diem_rates=[])

        violations = await validate_line_items(db, [item])

        assert len(violations) == 1
        v = violations[0]
        assert v.rule == "non_reimbursable"
        assert v.is_blocking is True
        assert "Personal Entertainment" in v.message

    # ====================================================================
    # FR-014: Per diem rate exceeded
    # ====================================================================

    @pytest.mark.asyncio
    async def test_per_diem_exceeded_returns_non_blocking_warning(self):
        """UT-POL-004: Amount exceeding per diem rate produces a non-blocking
        warning (FR-014, US-003 scenario 2)."""
        from app.core.policy_engine import validate_line_items

        db = make_mock_db()
        category = make_category(
            name="Meals", daily_limit=Decimal("200.00"), is_reimbursable=True
        )
        rate = make_per_diem_rate(
            category_id=category.id,
            rate=Decimal("75.00"),
            effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            effective_to=None,
        )
        item = make_line_item(amount=Decimal("100.00"), category_id=category.id)

        _setup_db_for_policy(db, category, per_diem_rates=[rate])

        violations = await validate_line_items(db, [item])

        assert len(violations) == 1
        v = violations[0]
        assert v.rule == "per_diem_exceeded"
        assert v.is_blocking is False

    @pytest.mark.asyncio
    async def test_amount_within_per_diem_passes(self):
        """Amount within per diem rate produces no violation."""
        from app.core.policy_engine import validate_line_items

        db = make_mock_db()
        category = make_category(daily_limit=Decimal("200.00"), is_reimbursable=True)
        rate = make_per_diem_rate(
            category_id=category.id,
            rate=Decimal("100.00"),
        )
        item = make_line_item(amount=Decimal("80.00"), category_id=category.id)

        _setup_db_for_policy(db, category, per_diem_rates=[rate])

        violations = await validate_line_items(db, [item])

        assert len(violations) == 0

    @pytest.mark.asyncio
    async def test_no_per_diem_rates_configured_skips_check(self):
        """No per diem rates configured for category → no per diem violation."""
        from app.core.policy_engine import validate_line_items

        db = make_mock_db()
        category = make_category(daily_limit=None, is_reimbursable=True)
        item = make_line_item(amount=Decimal("500.00"), category_id=category.id)

        _setup_db_for_policy(db, category, per_diem_rates=[])

        violations = await validate_line_items(db, [item])

        assert len(violations) == 0

    # ====================================================================
    # US-003 scenario 4: Multiple violations on one report
    # ====================================================================

    @pytest.mark.asyncio
    async def test_multiple_line_items_each_checked_independently(self):
        """Multiple line items produce independent violations (US-003 scenario 4)."""
        from app.core.policy_engine import validate_line_items

        db = make_mock_db()
        category_meals = make_category(
            name="Meals", daily_limit=Decimal("75.00"), is_reimbursable=True
        )
        category_banned = make_category(
            name="Alcohol", is_reimbursable=False, daily_limit=None
        )

        item1 = make_line_item(amount=Decimal("100.00"), category_id=category_meals.id)
        item2 = make_line_item(amount=Decimal("30.00"), category_id=category_banned.id)

        call_count = {"n": 0}

        async def execute_side_effect(*args, **kwargs):
            call_count["n"] += 1
            result = AsyncMock()
            # Calls 1,3 = _get_category for item1, item2
            # Calls 2,4 = _check_per_diem for item1, item2
            if call_count["n"] == 1:
                result.scalar_one_or_none.return_value = category_meals
            elif call_count["n"] == 2:
                result.scalars.return_value.all.return_value = []
            elif call_count["n"] == 3:
                result.scalar_one_or_none.return_value = category_banned
            elif call_count["n"] == 4:
                result.scalars.return_value.all.return_value = []
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        violations = await validate_line_items(db, [item1, item2])

        assert len(violations) == 2
        rules = {v.rule for v in violations}
        assert "daily_limit_exceeded" in rules
        assert "non_reimbursable" in rules

    # ====================================================================
    # Edge case: Unknown category
    # ====================================================================

    @pytest.mark.asyncio
    async def test_unknown_category_skipped_no_violation(self):
        """Line item with unknown category_id is skipped (no crash)."""
        from app.core.policy_engine import validate_line_items

        db = make_mock_db()
        item = make_line_item(amount=Decimal("100.00"), category_id=uuid.uuid4())

        _setup_db_for_policy(db, None)  # Category not found

        violations = await validate_line_items(db, [item])

        assert len(violations) == 0
