"""Integration tests for admin document management, reindex, test-query, coverage.

Covers: FR-001, FR-005, FR-006, FR-031, FR-032, FR-033
User Stories: US-008, US-009, US-012
"""

import io
import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.admin import router
from conftest import (
    build_test_app,
    make_admin_user,
    make_document,
    make_document_version,
    make_employee_user,
    make_mock_db,
    make_mock_services,
    mock_db_scalar_result,
)


def _build_admin_app(user=None, db=None, services=None):
    user = user or make_admin_user()
    db = db or make_mock_db()
    services = services or make_mock_services()
    return build_test_app(
        router, current_user=user, mock_db=db, services=services, admin_required=True
    )


# ---------------------------------------------------------------------------
# IT-DOC-001: POST /v1/admin/documents — Upload new document (FR-001, FR-031)
# ---------------------------------------------------------------------------


class TestCreateDocument:
    """POST /v1/admin/documents uploads and indexes a policy document."""

    @pytest.mark.asyncio
    async def test_upload_pdf_returns_201(self) -> None:
        """IT-DOC-001: Upload a valid PDF returns 201 with indexing_status."""
        admin = make_admin_user()
        db = make_mock_db()
        services = make_mock_services()

        # No duplicate title
        db.execute.side_effect = [
            mock_db_scalar_result(None),  # no existing doc with same title
        ]

        app = _build_admin_app(user=admin, db=db, services=services)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/admin/documents",
                data={
                    "title": "HR-POL-099: New Policy",
                    "category": "HR",
                    "effective_date": "2026-03-01",
                    "owner": "HR Team",
                },
                files={"file": ("policy.pdf", b"%PDF-fake-content", "application/pdf")},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["indexing_status"] == "in_progress"
        assert data["category"] == "HR"
        services["blob_service"].upload.assert_called_once()
        services["search_service"].reindex_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type_returns_400(self) -> None:
        """ERR-006: Unsupported file type returns 400."""
        app = _build_admin_app()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/admin/documents",
                data={
                    "title": "Bad File",
                    "category": "HR",
                    "effective_date": "2026-03-01",
                    "owner": "HR Team",
                },
                files={"file": ("policy.exe", b"malware", "application/octet-stream")},
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_invalid_category_returns_400(self) -> None:
        """ERR-007: Invalid category returns 400."""
        app = _build_admin_app()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/admin/documents",
                data={
                    "title": "Bad Category",
                    "category": "Marketing",
                    "effective_date": "2026-03-01",
                    "owner": "HR Team",
                },
                files={"file": ("policy.pdf", b"%PDF-content", "application/pdf")},
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_duplicate_title_returns_409(self) -> None:
        """ERR-008: Duplicate document title returns 409."""
        db = make_mock_db()
        existing_doc = make_document(title="Existing Policy")

        db.execute.side_effect = [
            mock_db_scalar_result(existing_doc),  # duplicate found
        ]

        app = _build_admin_app(db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/admin/documents",
                data={
                    "title": "Existing Policy",
                    "category": "HR",
                    "effective_date": "2026-03-01",
                    "owner": "HR Team",
                },
                files={"file": ("policy.pdf", b"%PDF-content", "application/pdf")},
            )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_employee_cannot_upload_returns_403(self) -> None:
        """SEC-003: Employee calling admin endpoint returns 403."""
        employee = make_employee_user()
        db = make_mock_db()
        services = make_mock_services()
        app = build_test_app(router, current_user=employee, mock_db=db, services=services)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/admin/documents",
                data={
                    "title": "Test",
                    "category": "HR",
                    "effective_date": "2026-03-01",
                    "owner": "HR",
                },
                files={"file": ("policy.pdf", b"%PDF-content", "application/pdf")},
            )

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# IT-DOC-002: GET /v1/admin/documents/{id} — Document detail (FR-006)
# ---------------------------------------------------------------------------


class TestGetDocumentDetail:
    """GET /v1/admin/documents/{id} returns document with version history."""

    @pytest.mark.asyncio
    async def test_get_document_with_versions(self) -> None:
        """IT-DOC-002: Document detail includes version history."""
        db = make_mock_db()
        doc_id = uuid.uuid4()
        doc = make_document(id=doc_id)
        version = make_document_version(document_id=doc_id)

        ver_result = MagicMock()
        ver_result.scalars.return_value.all.return_value = [version]
        db.execute.side_effect = [
            mock_db_scalar_result(doc),
            ver_result,
        ]

        app = _build_admin_app(db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/v1/admin/documents/{doc_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(doc_id)
        assert len(data["versions"]) == 1

    @pytest.mark.asyncio
    async def test_get_document_not_found_returns_404(self) -> None:
        """ERR-010: Non-existent document returns 404."""
        db = make_mock_db()
        db.execute.return_value = mock_db_scalar_result(None)

        app = _build_admin_app(db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/v1/admin/documents/{uuid.uuid4()}")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# IT-DOC-003: PATCH /v1/admin/documents/{id} — Retire document (FR-031)
# ---------------------------------------------------------------------------


class TestPatchDocument:
    """PATCH /v1/admin/documents/{id} updates metadata or retires a document."""

    @pytest.mark.asyncio
    async def test_retire_document(self) -> None:
        """IT-DOC-003: Setting status to 'retired' succeeds."""
        db = make_mock_db()
        doc = make_document()

        db.execute.return_value = mock_db_scalar_result(doc)

        app = _build_admin_app(db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/v1/admin/documents/{doc.id}",
                json={"status": "retired"},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "retired"

    @pytest.mark.asyncio
    async def test_patch_invalid_status_returns_400(self) -> None:
        """ERR-009: Invalid status value returns 400."""
        db = make_mock_db()
        doc = make_document()

        db.execute.return_value = mock_db_scalar_result(doc)

        app = _build_admin_app(db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/v1/admin/documents/{doc.id}",
                json={"status": "archived"},
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_patch_document_not_found(self) -> None:
        """PATCH on non-existent document returns 404."""
        db = make_mock_db()
        db.execute.return_value = mock_db_scalar_result(None)

        app = _build_admin_app(db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/v1/admin/documents/{uuid.uuid4()}",
                json={"status": "retired"},
            )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# IT-DOC-004: POST /v1/admin/documents/{id}/reindex (FR-005)
# ---------------------------------------------------------------------------


class TestReindexDocument:
    """POST /v1/admin/documents/{id}/reindex triggers re-indexing."""

    @pytest.mark.asyncio
    async def test_reindex_single_document(self) -> None:
        """IT-DOC-004: Reindex returns 200 with in_progress status."""
        db = make_mock_db()
        services = make_mock_services()
        doc = make_document()

        db.execute.return_value = mock_db_scalar_result(doc)

        app = _build_admin_app(db=db, services=services)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(f"/v1/admin/documents/{doc.id}/reindex")

        assert response.status_code == 200
        assert response.json()["indexing_status"] == "in_progress"
        services["search_service"].reindex_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_reindex_not_found_returns_404(self) -> None:
        """Reindex non-existent document returns 404."""
        db = make_mock_db()
        db.execute.return_value = mock_db_scalar_result(None)

        app = _build_admin_app(db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(f"/v1/admin/documents/{uuid.uuid4()}/reindex")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# IT-DOC-005: POST /v1/admin/reindex — Full corpus (FR-005)
# ---------------------------------------------------------------------------


class TestReindexCorpus:
    """POST /v1/admin/reindex triggers full corpus re-indexing."""

    @pytest.mark.asyncio
    async def test_reindex_all_documents(self) -> None:
        """IT-DOC-005: Full reindex returns 202 with document count."""
        db = make_mock_db()
        services = make_mock_services()

        count_result = mock_db_scalar_result(140)
        db.execute.return_value = count_result

        app = _build_admin_app(db=db, services=services)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/v1/admin/reindex")

        assert response.status_code == 200
        data = response.json()
        assert data["indexing_status"] == "in_progress"
        services["search_service"].reindex_all.assert_called_once()


# ---------------------------------------------------------------------------
# IT-DOC-006: GET /v1/admin/documents — List documents (FR-031)
# ---------------------------------------------------------------------------


class TestListDocuments:
    """GET /v1/admin/documents lists all documents with pagination."""

    @pytest.mark.asyncio
    async def test_list_documents_returns_200(self) -> None:
        """IT-DOC-006: Document list returns data array."""
        db = make_mock_db()
        doc = make_document()

        result = MagicMock()
        result.scalars.return_value.all.return_value = [doc]
        db.execute.return_value = result

        app = _build_admin_app(db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/admin/documents")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 1


# ---------------------------------------------------------------------------
# IT-TQ-001: POST /v1/admin/test-query — Live answer (FR-032, US-009)
# ---------------------------------------------------------------------------


class TestAdminTestQuery:
    """POST /v1/admin/test-query previews chatbot answers."""

    @pytest.mark.asyncio
    async def test_test_query_returns_live_answer(self) -> None:
        """IT-TQ-001: Test query returns live_answer."""
        db = make_mock_db()
        services = make_mock_services()

        app = _build_admin_app(db=db, services=services)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/admin/test-query",
                json={"query": "What is the PTO policy?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "live_answer" in data
        assert data["preview_answer"] is None

    @pytest.mark.asyncio
    async def test_test_query_with_draft_not_found_returns_404(self) -> None:
        """ERR-011: draft_document_id not found returns 404."""
        db = make_mock_db()
        services = make_mock_services()

        db.execute.return_value = mock_db_scalar_result(None)

        app = _build_admin_app(db=db, services=services)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/admin/test-query",
                json={
                    "query": "Test query",
                    "draft_document_id": str(uuid.uuid4()),
                },
            )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# IT-COV-001: GET /v1/admin/coverage — Coverage report (FR-033, US-012)
# ---------------------------------------------------------------------------


class TestCoverageReport:
    """GET /v1/admin/coverage shows policy coverage by domain."""

    @pytest.mark.asyncio
    async def test_coverage_report_returns_categories(self) -> None:
        """IT-COV-001: Coverage report lists all 7 categories."""
        db = make_mock_db()

        # Each category query returns (count, pages, last_indexed)
        result_covered = AsyncMock()
        result_covered.one.return_value = (10, 500, datetime.now(UTC))
        result_gap = AsyncMock()
        result_gap.one.return_value = (0, 0, None)

        # 7 categories: Compliance, Facilities, Finance, HR, IT, Legal, Safety (sorted)
        db.execute.side_effect = [
            result_covered,  # Compliance
            result_covered,  # Facilities
            result_covered,  # Finance
            result_covered,  # HR
            result_covered,  # IT
            result_covered,  # Legal
            result_gap,      # Safety
        ]

        app = _build_admin_app(db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/admin/coverage")

        assert response.status_code == 200
        data = response.json()
        assert len(data["categories"]) == 7
        assert "Safety" in data["categories_with_gaps"]
