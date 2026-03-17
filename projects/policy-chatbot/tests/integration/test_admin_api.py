"""Integration tests for the Admin API endpoints.

Tests derived from wireframe-spec.md and user stories US-008–US-011.
Auth/authz edge cases: Employee vs Administrator role boundaries.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from tests.conftest import _create_test_client, make_admin_user, make_employee_user


class TestAdminAuthBoundary:
    """NFR-010: RBAC — only administrators can access admin endpoints."""

    def test_employee_cannot_list_documents(
        self, employee_client: TestClient
    ) -> None:
        """IT-AUTH-002: Employee role returns 403 on admin endpoints."""
        response = employee_client.get("/v1/admin/documents")
        assert response.status_code == 403

    def test_employee_cannot_upload_document(
        self, employee_client: TestClient
    ) -> None:
        response = employee_client.post("/v1/admin/documents")
        assert response.status_code in (403, 422)

    def test_employee_cannot_view_analytics(
        self, employee_client: TestClient
    ) -> None:
        response = employee_client.get(
            "/v1/admin/analytics", params={"period": "week"}
        )
        assert response.status_code == 403

    def test_employee_cannot_view_coverage(
        self, employee_client: TestClient
    ) -> None:
        response = employee_client.get("/v1/admin/coverage")
        assert response.status_code == 403

    def test_employee_cannot_view_flagged_topics(
        self, employee_client: TestClient
    ) -> None:
        response = employee_client.get("/v1/admin/analytics/flagged-topics")
        assert response.status_code == 403

    def test_admin_can_access_coverage(
        self, admin_client: TestClient, mock_db: AsyncMock
    ) -> None:
        """IT-AUTH-003: Admin role can access admin endpoints."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        response = admin_client.get("/v1/admin/coverage")
        assert response.status_code == 200


class TestDocumentManagement:
    """FR-031: Upload, retire, and manage policy documents."""

    def test_upload_invalid_file_type(
        self, admin_client: TestClient
    ) -> None:
        """Edge case: non-PDF/DOCX file is rejected."""
        import io

        response = admin_client.post(
            "/v1/admin/documents",
            data={
                "title": "Test Policy",
                "document_external_id": "TEST-001",
                "category": "HR",
                "effective_date": "2026-01-01",
                "owner": "VP HR",
            },
            files={"file": ("test.xlsx", io.BytesIO(b"data"), "application/vnd.openxmlformats")},
        )

        assert response.status_code in (400, 422)

    def test_retire_document(
        self, admin_client: TestClient, mock_db: AsyncMock
    ) -> None:
        """IT-ADM-009: Admin can retire a document by setting status=retired."""
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.title = "Old Travel Policy"
        mock_doc.status = "active"
        mock_doc.updated_at = datetime.now(tz=UTC)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        response = admin_client.patch(
            f"/v1/admin/documents/{doc_id}",
            json={"status": "retired"},
        )

        assert response.status_code == 200
        assert mock_doc.status == "retired"

    def test_retire_nonexistent_document(
        self, admin_client: TestClient, mock_db: AsyncMock
    ) -> None:
        """Edge case: patching a non-existent document returns 404."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = admin_client.patch(
            f"/v1/admin/documents/{uuid.uuid4()}",
            json={"status": "retired"},
        )

        assert response.status_code == 404


class TestReindexing:
    """FR-005: Manual re-indexing of documents."""

    def test_reindex_single_document(
        self, admin_client: TestClient, mock_db: AsyncMock
    ) -> None:
        """IT-ADM-003: Trigger re-indexing for a specific document."""
        doc_id = uuid.uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        response = admin_client.post(
            f"/v1/admin/documents/{doc_id}/reindex"
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "processing"
        assert data["document_id"] == str(doc_id)

    def test_reindex_nonexistent_document(
        self, admin_client: TestClient, mock_db: AsyncMock
    ) -> None:
        """Edge case: re-indexing a non-existent document returns 404."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = admin_client.post(
            f"/v1/admin/documents/{uuid.uuid4()}/reindex"
        )

        assert response.status_code == 404

    def test_reindex_all_documents(
        self, admin_client: TestClient, mock_db: AsyncMock
    ) -> None:
        """IT-ADM-004: Trigger full corpus re-indexing."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 140
        mock_db.execute.return_value = mock_result

        response = admin_client.post("/v1/admin/documents/reindex-all")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "processing"
        assert data["document_count"] == 140


class TestDocumentVersions:
    """FR-006: Document version history."""

    def test_list_versions(
        self, admin_client: TestClient, mock_db: AsyncMock
    ) -> None:
        """IT-ADM-005: View version history for a document."""
        doc_id = uuid.uuid4()

        mock_version = MagicMock()
        mock_version.id = uuid.uuid4()
        mock_version.version_number = 2
        mock_version.file_type = "pdf"
        mock_version.page_count = 12
        mock_version.indexed_by = "admin@acme.com"
        mock_version.indexing_status = "completed"
        mock_version.indexed_at = datetime.now(tz=UTC)
        mock_version.created_at = datetime.now(tz=UTC)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_version]
        mock_db.execute.return_value = mock_result

        response = admin_client.get(f"/v1/admin/documents/{doc_id}/versions")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["version_number"] == 2


class TestTestQuery:
    """FR-032: Admin test query preview."""

    def test_test_query(
        self, admin_client: TestClient, mock_rag_pipeline: AsyncMock
    ) -> None:
        """IT-ADM-010: Admin can preview chatbot answers."""
        response = admin_client.post(
            "/v1/admin/test-query",
            json={"query": "What is the PTO policy?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "current_corpus_response" in data


class TestCoverageReport:
    """FR-033: Policy coverage report."""

    def test_coverage_report(
        self, admin_client: TestClient, mock_db: AsyncMock
    ) -> None:
        """IT-ADM-011: Coverage report shows all policy domains."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        response = admin_client.get("/v1/admin/coverage")

        assert response.status_code == 200
        data = response.json()
        assert "domains" in data
        assert len(data["domains"]) == 7  # HR, IT, Finance, Facilities, Legal, Compliance, Safety
        assert "total_documents" in data
        assert "gaps" in data


class TestFlaggedTopics:
    """FR-030: View topics flagged for admin review."""

    def test_flagged_topics(
        self, admin_client: TestClient, mock_db: AsyncMock
    ) -> None:
        """IT-ADM-007: View flagged topics returns list."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        response = admin_client.get("/v1/admin/analytics/flagged-topics")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
