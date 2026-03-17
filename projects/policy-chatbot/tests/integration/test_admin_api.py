"""Integration tests for admin API endpoints.

Tests cover:
- FR-005: Re-indexing via admin console
- FR-006: Document version history
- FR-029: Analytics dashboard
- FR-030: Flagged topics
- FR-031: Document upload, retire
- FR-032: Test query
- FR-033: Coverage report
- NFR-010: Admin role required (non-admin gets 403)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


class TestAdminAuth:
    """NFR-010: Admin endpoints require PolicyAdmin role."""

    def test_employee_cannot_access_admin_documents(
        self, client: TestClient
    ) -> None:
        """SEC-002 / IT-015: Employee without PolicyAdmin role gets 403."""
        response = client.get("/api/admin/documents")

        assert response.status_code == 403

    def test_employee_cannot_upload_document(
        self, client: TestClient
    ) -> None:
        """SEC-003: Employee cannot upload documents."""
        response = client.post(
            "/api/admin/documents",
            data={
                "title": "Test",
                "document_external_id": "TEST-001",
                "category": "HR",
                "effective_date": "2025-06-01",
                "owner": "HR Team",
            },
            files={"file": ("test.pdf", b"fake content", "application/pdf")},
        )

        assert response.status_code == 403

    def test_unauthenticated_admin_access_returns_401(
        self, unauthed_client: TestClient
    ) -> None:
        """SEC-001: Unauthenticated admin access returns 401."""
        response = unauthed_client.get("/api/admin/documents")

        assert response.status_code in (401, 403)


class TestListDocuments:
    """GET /api/admin/documents — list policy documents."""

    def test_list_documents_returns_paginated_list(
        self, admin_client: TestClient, mock_doc_service: AsyncMock
    ) -> None:
        """IT-007: Admin can list documents."""
        response = admin_client.get("/api/admin/documents")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert isinstance(data["data"], list)


class TestUploadDocument:
    """POST /api/admin/documents — upload a new policy document."""

    def test_upload_pdf_returns_202(
        self, admin_client: TestClient, mock_doc_service: AsyncMock
    ) -> None:
        """IT-007 / FR-031: Admin can upload a PDF document."""
        mock_doc = MagicMock()
        mock_doc.id = uuid.uuid4()
        mock_doc.title = "Test Policy"
        mock_doc.status = "processing"
        mock_doc_service.upload_document = AsyncMock(return_value=mock_doc)

        response = admin_client.post(
            "/api/admin/documents",
            data={
                "title": "Test Policy",
                "document_external_id": "HR-POL-099",
                "category": "HR",
                "effective_date": "2025-06-01",
                "owner": "HR Team",
            },
            files={"file": ("policy.pdf", b"fake pdf content", "application/pdf")},
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "processing"
        assert data["version"] == 1

    def test_upload_unsupported_format_returns_400(
        self, admin_client: TestClient
    ) -> None:
        """IT-021 / ERR-006: Unsupported file format returns 400."""
        response = admin_client.post(
            "/api/admin/documents",
            data={
                "title": "Test",
                "document_external_id": "TEST-001",
                "category": "HR",
                "effective_date": "2025-06-01",
                "owner": "HR Team",
            },
            files={"file": ("slides.pptx", b"fake", "application/pptx")},
        )

        assert response.status_code == 400
        assert "Unsupported" in response.json()["detail"]


class TestRetireDocument:
    """POST /api/admin/documents/{id}/retire — retire a document."""

    def test_retire_document_returns_200(
        self,
        admin_client: TestClient,
        mock_doc_service: AsyncMock,
        mock_search_service: AsyncMock,
    ) -> None:
        """IT-008 / FR-031: Admin can retire a document."""
        mock_doc = MagicMock()
        mock_doc.id = uuid.uuid4()
        mock_doc.title = "Old Policy"
        mock_doc.status = "retired"
        mock_doc_service.retire_document = AsyncMock(return_value=mock_doc)

        doc_id = str(uuid.uuid4())
        response = admin_client.post(f"/api/admin/documents/{doc_id}/retire")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "retired"


class TestReindex:
    """POST /api/admin/documents/{id}/reindex and /api/admin/reindex-all."""

    def test_reindex_single_returns_202(
        self, admin_client: TestClient
    ) -> None:
        """IT-009 / FR-005: Reindex single document returns 202."""
        doc_id = str(uuid.uuid4())
        response = admin_client.post(
            f"/api/admin/documents/{doc_id}/reindex"
        )

        assert response.status_code == 202

    def test_reindex_all_returns_202(
        self, admin_client: TestClient, mock_doc_service: AsyncMock
    ) -> None:
        """FR-005: Full corpus reindex returns 202."""
        response = admin_client.post("/api/admin/reindex-all")

        assert response.status_code == 202

    def test_reindex_status_returns_200(
        self, admin_client: TestClient
    ) -> None:
        """Admin can check reindex status."""
        response = admin_client.get("/api/admin/reindex-status")

        assert response.status_code == 200


class TestDocumentVersions:
    """GET /api/admin/documents/{id}/versions — version history."""

    def test_versions_returns_list(
        self, admin_client: TestClient, mock_doc_service: AsyncMock
    ) -> None:
        """IT-020 / FR-006: Admin can view document version history."""
        doc_id = str(uuid.uuid4())
        response = admin_client.get(
            f"/api/admin/documents/{doc_id}/versions"
        )

        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert data["document_id"] == doc_id


class TestTestQuery:
    """POST /api/admin/test-query — preview chatbot answers."""

    def test_test_query_returns_live_response(
        self, admin_client: TestClient
    ) -> None:
        """IT-010 / FR-032: Test query returns live response."""
        with pytest.MonkeyPatch.context() as mp:
            from unittest.mock import AsyncMock as AM

            from app.core.intent_classifier import IntentResult
            from app.core.rag_pipeline import RAGResult
            from app.models.schemas import (
                ChatResponseBody,
                IntentInfo,
                IntentType,
            )
            from app.services.llm_service import DISCLAIMER

            mp.setattr(
                "app.api.admin.rag_pipeline.run_pipeline",
                AM(
                    return_value=RAGResult(
                        response_body=ChatResponseBody(
                            content="Test answer",
                            citations=[],
                            disclaimer=DISCLAIMER,
                            intent=IntentInfo(domain="HR", type=IntentType.FACTUAL),
                            confidence=0.85,
                        ),
                        intent=IntentResult("HR", "factual", False),
                    )
                ),
            )

            response = admin_client.post(
                "/api/admin/test-query",
                json={"query": "What is the PTO policy?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "live_response" in data
        assert data["live_response"]["content"] == "Test answer"


class TestCoverageReport:
    """GET /api/admin/coverage — policy domain coverage report."""

    def test_coverage_returns_all_categories(
        self, admin_client: TestClient, mock_doc_service: AsyncMock
    ) -> None:
        """IT-011 / FR-033: Coverage report shows all 7 domains."""
        response = admin_client.get("/api/admin/coverage")

        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) == 7
        assert data["total_documents"] > 0


class TestAnalytics:
    """GET /api/admin/analytics — analytics dashboard."""

    def test_analytics_returns_summary(
        self, admin_client: TestClient, mock_feedback_service: AsyncMock
    ) -> None:
        """IT-012 / FR-029: Analytics endpoint returns dashboard data."""
        response = admin_client.get(
            "/api/admin/analytics?start_date=2026-03-01&end_date=2026-03-17"
        )

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "top_intents" in data
        assert data["summary"]["total_queries"] == 100


class TestUnansweredQueries:
    """GET /api/admin/analytics/unanswered — unanswered query log."""

    def test_unanswered_returns_list(
        self, admin_client: TestClient
    ) -> None:
        """FR-029: Unanswered queries endpoint returns data."""
        response = admin_client.get("/api/admin/analytics/unanswered")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestFlaggedTopics:
    """GET /api/admin/analytics/flagged — flagged topics."""

    def test_flagged_returns_list(
        self, admin_client: TestClient, mock_feedback_service: AsyncMock
    ) -> None:
        """IT-013 / FR-030: Flagged topics endpoint returns data."""
        response = admin_client.get("/api/admin/analytics/flagged")

        assert response.status_code == 200
        data = response.json()
        assert "flagged_topics" in data
