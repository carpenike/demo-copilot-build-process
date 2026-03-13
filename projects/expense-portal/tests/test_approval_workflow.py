"""Unit tests for the approval workflow (FR-008, FR-009, FR-010, FR-011, FR-012).

Tests are derived from requirements and user stories US-005, US-006,
US-007, US-008 — NOT from implementation.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from conftest import (
    make_employee,
    make_expense_report,
    make_line_item,
    make_mock_db,
    make_threshold,
)


class TestRouteForApproval:
    """UT-WF-001: Route submitted report to manager (FR-008, US-005)."""

    @pytest.mark.asyncio
    async def test_routes_to_submitters_manager(self):
        """FR-008: Upon submission, route to submitter's direct manager."""
        from app.core.approval_workflow import route_for_approval

        db = make_mock_db()
        manager_id = uuid.uuid4()
        submitter_id = uuid.uuid4()
        manager = make_employee(id=manager_id, full_name="Bob Manager")
        submitter = make_employee(id=submitter_id, manager_id=manager_id)

        report = make_expense_report(submitter_id=submitter_id, status="draft")

        call_count = {"n": 0}

        async def execute_side_effect(*args, **kwargs):
            call_count["n"] += 1
            result = AsyncMock()
            if call_count["n"] == 1:
                result.scalar_one_or_none.return_value = submitter
            elif call_count["n"] == 2:
                result.scalar_one_or_none.return_value = manager
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        approver = await route_for_approval(db, report, submitter_id, "127.0.0.1")

        assert approver.id == manager_id
        assert report.status == "submitted"
        assert report.current_approver_id == manager_id
        assert report.submitted_at is not None
        # Approval action was added
        db.add.assert_called()

    @pytest.mark.asyncio
    async def test_raises_when_no_manager_assigned(self):
        """FR-008: Error when submitter has no manager (US-005 scenario 4 — segregation of duties)."""
        from app.core.approval_workflow import route_for_approval

        db = make_mock_db()
        submitter = make_employee(manager_id=None)

        async def execute_side_effect(*args, **kwargs):
            result = AsyncMock()
            result.scalar_one_or_none.return_value = submitter
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        report = make_expense_report(submitter_id=submitter.id, status="draft")

        with pytest.raises(ValueError, match="no manager assigned"):
            await route_for_approval(db, report, submitter.id, "127.0.0.1")


class TestApproveReport:
    """UT-WF-002, UT-WF-003: Approval with and without finance escalation."""

    @pytest.mark.asyncio
    async def test_manager_approval_with_finance_escalation(self):
        """UT-WF-002: Line item > $500 triggers finance review (FR-009, US-006 scenario 1)."""
        from app.core.approval_workflow import approve_report

        db = make_mock_db()
        high_value_item = make_line_item(amount=Decimal("750.00"))
        report = make_expense_report(
            status="submitted",
            line_items=[high_value_item],
        )
        threshold = make_threshold(finance_review_threshold=Decimal("500.00"))

        async def execute_side_effect(*args, **kwargs):
            result = AsyncMock()
            result.scalar_one_or_none.return_value = threshold
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        new_status, next_step = await approve_report(
            db, report, uuid.uuid4(), "127.0.0.1"
        )

        assert new_status == "finance_review"
        assert next_step == "finance_review"
        assert report.status == "finance_review"
        assert report.current_approver_id is None

    @pytest.mark.asyncio
    async def test_manager_approval_without_finance_escalation(self):
        """UT-WF-003: All items <= $500 → directly approved (FR-009, US-006 scenario 2)."""
        from app.core.approval_workflow import approve_report

        db = make_mock_db()
        low_value_item = make_line_item(amount=Decimal("200.00"))
        report = make_expense_report(
            status="submitted",
            line_items=[low_value_item],
        )
        threshold = make_threshold(finance_review_threshold=Decimal("500.00"))

        async def execute_side_effect(*args, **kwargs):
            result = AsyncMock()
            result.scalar_one_or_none.return_value = threshold
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        new_status, next_step = await approve_report(
            db, report, uuid.uuid4(), "127.0.0.1"
        )

        assert new_status == "approved"
        assert next_step is None
        assert report.status == "approved"
        assert report.approved_at is not None

    @pytest.mark.asyncio
    async def test_finance_approval_completes_the_report(self):
        """US-006 scenario 3: Finance reviewer approves → fully approved."""
        from app.core.approval_workflow import approve_report

        db = make_mock_db()
        report = make_expense_report(status="finance_review", line_items=[])
        threshold = make_threshold()

        async def execute_side_effect(*args, **kwargs):
            result = AsyncMock()
            result.scalar_one_or_none.return_value = threshold
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        new_status, next_step = await approve_report(
            db, report, uuid.uuid4(), "127.0.0.1"
        )

        assert new_status == "approved"
        assert report.approved_at is not None

    @pytest.mark.asyncio
    async def test_cannot_approve_draft_report(self):
        """Cannot approve a report that hasn't been submitted."""
        from app.core.approval_workflow import approve_report

        db = make_mock_db()
        report = make_expense_report(status="draft")
        threshold = make_threshold()

        async def execute_side_effect(*args, **kwargs):
            result = AsyncMock()
            result.scalar_one_or_none.return_value = threshold
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        with pytest.raises(ValueError, match="Cannot approve"):
            await approve_report(db, report, uuid.uuid4(), "127.0.0.1")


class TestRejectReport:
    """FR-012, US-008: Rejection with reason."""

    @pytest.mark.asyncio
    async def test_reject_submitted_report(self):
        """FR-012: Rejected report includes reason (US-008 scenario 1)."""
        from app.core.approval_workflow import reject_report

        db = make_mock_db()
        report = make_expense_report(status="submitted")

        await reject_report(db, report, uuid.uuid4(), "127.0.0.1", "Missing receipts")

        assert report.status == "rejected"
        assert report.rejected_at is not None
        assert report.current_approver_id is None
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_finance_review_report(self):
        """US-006 scenario 4: Finance rejects a report in finance_review status."""
        from app.core.approval_workflow import reject_report

        db = make_mock_db()
        report = make_expense_report(status="finance_review")

        await reject_report(db, report, uuid.uuid4(), "127.0.0.1", "Over budget")

        assert report.status == "rejected"

    @pytest.mark.asyncio
    async def test_cannot_reject_draft_report(self):
        """Cannot reject a report that hasn't been submitted."""
        from app.core.approval_workflow import reject_report

        db = make_mock_db()
        report = make_expense_report(status="draft")

        with pytest.raises(ValueError, match="Cannot reject"):
            await reject_report(db, report, uuid.uuid4(), "127.0.0.1", "Bad")


class TestRequestInfo:
    """FR-010, US-005: Request more information."""

    @pytest.mark.asyncio
    async def test_request_info_changes_status(self):
        """FR-010: Approver requests more info → status changes (US-005 scenario 3)."""
        from app.core.approval_workflow import request_info

        db = make_mock_db()
        report = make_expense_report(status="submitted")

        await request_info(db, report, uuid.uuid4(), "127.0.0.1", "Please attach receipt")

        assert report.status == "information_requested"
        assert report.current_approver_id is None

    @pytest.mark.asyncio
    async def test_cannot_request_info_on_approved_report(self):
        """Cannot request info on an already approved report."""
        from app.core.approval_workflow import request_info

        db = make_mock_db()
        report = make_expense_report(status="approved")

        with pytest.raises(ValueError, match="Cannot request info"):
            await request_info(db, report, uuid.uuid4(), "127.0.0.1", "Why?")


class TestEscalation:
    """UT-WF-004: Auto-escalation (FR-011, US-007)."""

    @pytest.mark.asyncio
    async def test_escalates_to_approvers_manager(self):
        """FR-011: Escalate to approver's manager (US-007 scenario 1)."""
        from app.core.approval_workflow import escalate_report

        db = make_mock_db()
        vp_id = uuid.uuid4()
        manager_id = uuid.uuid4()
        manager = make_employee(id=manager_id, manager_id=vp_id, direct_reports=[])
        vp = make_employee(id=vp_id, full_name="VP Director", direct_reports=[])

        report = make_expense_report(status="submitted", current_approver_id=manager_id)

        call_count = {"n": 0}

        async def execute_side_effect(*args, **kwargs):
            call_count["n"] += 1
            result = AsyncMock()
            if call_count["n"] == 1:
                result.scalar_one_or_none.return_value = manager
            elif call_count["n"] == 2:
                result.scalar_one_or_none.return_value = vp
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        new_approver = await escalate_report(db, report)

        assert new_approver is not None
        assert new_approver.id == vp_id
        assert report.current_approver_id == vp_id
        db.add.assert_called_once()  # ApprovalAction for escalation

    @pytest.mark.asyncio
    async def test_escalation_exhausted_when_no_manager_above(self):
        """US-007: Escalation chain exhausted → returns None."""
        from app.core.approval_workflow import escalate_report

        db = make_mock_db()
        manager = make_employee(manager_id=None, direct_reports=[])
        report = make_expense_report(current_approver_id=manager.id)

        async def execute_side_effect(*args, **kwargs):
            result = AsyncMock()
            result.scalar_one_or_none.return_value = manager
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        new_approver = await escalate_report(db, report)

        assert new_approver is None

    @pytest.mark.asyncio
    async def test_no_escalation_when_no_current_approver(self):
        """No escalation when report has no current approver."""
        from app.core.approval_workflow import escalate_report

        db = make_mock_db()
        report = make_expense_report(current_approver_id=None)

        result = await escalate_report(db, report)

        assert result is None
