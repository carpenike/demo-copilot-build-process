"""Integration tests for receipt upload and OCR status endpoints.

Covers: FR-003, FR-004
User stories: US-002
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from conftest import make_employee, make_expense_report, make_line_item


def _build_test_app(current_user, db_mock):
    from fastapi import FastAPI
    from starlette.middleware.sessions import SessionMiddleware

    from app.api.receipts import router
    from app.api.dependencies import get_current_user, get_db

    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-secret")
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db_mock
    return app


# ====================================================================
# FR-003 + US-002: Receipt upload validation
# ====================================================================


class TestReceiptUpload:
    """IT-REC-001 through IT-REC-003: File upload validation."""

    @pytest.mark.asyncio
    async def test_reject_unsupported_file_type(self):
        """IT-REC-003: Unsupported file format rejected (FR-003, US-002 scenario 3)."""
        user = make_employee()
        db = AsyncMock()

        # Mock report and item lookup
        report = make_expense_report(submitter_id=user.id, status="draft")
        item = make_line_item(report_id=report.id)

        call_count = {"n": 0}

        async def execute_side_effect(*args, **kwargs):
            call_count["n"] += 1
            result = AsyncMock()
            if call_count["n"] == 1:
                result.scalar_one_or_none.return_value = report
            elif call_count["n"] == 2:
                result.scalar_one_or_none.return_value = item
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        app = _build_test_app(user, db)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/v1/expenses/reports/{report.id}/line-items/{item.id}/receipt",
                files={"file": ("test.exe", b"fake content", "application/x-msdownload")},
            )

        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reject_file_over_10mb(self):
        """IT-REC-002: File > 10 MB rejected (FR-003, US-002 scenario 2)."""
        user = make_employee()
        db = AsyncMock()

        report = make_expense_report(submitter_id=user.id, status="draft")
        item = make_line_item(report_id=report.id)

        call_count = {"n": 0}

        async def execute_side_effect(*args, **kwargs):
            call_count["n"] += 1
            result = AsyncMock()
            if call_count["n"] == 1:
                result.scalar_one_or_none.return_value = report
            elif call_count["n"] == 2:
                result.scalar_one_or_none.return_value = item
            return result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        app = _build_test_app(user, db)
        # Create content just over 10 MB
        large_content = b"x" * (10 * 1024 * 1024 + 1)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/v1/expenses/reports/{report.id}/line-items/{item.id}/receipt",
                files={"file": ("big.jpg", large_content, "image/jpeg")},
            )

        assert response.status_code == 400
        assert "10 MB" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reject_upload_on_non_editable_report(self):
        """Cannot upload receipt to a submitted (non-editable) report (SEC-010)."""
        user = make_employee()
        db = AsyncMock()

        report = make_expense_report(submitter_id=user.id, status="submitted")
        report.is_editable = False

        report_result = AsyncMock()
        report_result.scalar_one_or_none.return_value = report
        db.execute = AsyncMock(return_value=report_result)

        app = _build_test_app(user, db)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/v1/expenses/reports/{report.id}/line-items/{uuid.uuid4()}/receipt",
                files={"file": ("receipt.jpg", b"content", "image/jpeg")},
            )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_reject_upload_by_non_owner(self):
        """Cannot upload receipt to another user's report (NFR-008)."""
        user = make_employee()
        db = AsyncMock()

        # Report owned by someone else
        report = make_expense_report(submitter_id=uuid.uuid4(), status="draft")

        report_result = AsyncMock()
        report_result.scalar_one_or_none.return_value = report
        db.execute = AsyncMock(return_value=report_result)

        app = _build_test_app(user, db)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/v1/expenses/reports/{report.id}/line-items/{uuid.uuid4()}/receipt",
                files={"file": ("receipt.jpg", b"content", "image/jpeg")},
            )

        assert response.status_code == 403
