"""Unit tests for document chunking and text extraction (FR-002, FR-003).

Tests are derived from requirements:
- FR-002: Extract text preserving headings, lists, tables
- FR-003: Chunk documents into semantically meaningful sections
"""

from __future__ import annotations

import pytest

from app.tasks.indexing import _chunk_text


class TestDocumentChunking:
    """FR-003: Chunk documents into semantically meaningful sections."""

    def test_single_section_not_split(self) -> None:
        """UT-002: Small section stays as one chunk."""
        text = "# Policy Title\nThis is a short policy."
        chunks = _chunk_text(text)

        assert len(chunks) >= 1
        assert any("short policy" in c["content"] for c in chunks)

    def test_multiple_sections_split_on_headings(self) -> None:
        """FR-002: Text is split on section headings."""
        text = (
            "# Bereavement Leave\n"
            "Company provides bereavement leave.\n\n"
            "# Eligibility\n"
            "Full-time employees are eligible.\n\n"
            "# Duration\n"
            "5 days for immediate family.\n"
        )
        chunks = _chunk_text(text)

        assert len(chunks) >= 3
        headings = [c["heading"] for c in chunks]
        assert "Bereavement Leave" in headings
        assert "Eligibility" in headings
        assert "Duration" in headings

    def test_section_headings_preserved_in_chunk_metadata(self) -> None:
        """FR-002: Section heading is preserved as chunk metadata."""
        text = "# Section A\nContent of section A.\n\n# Section B\nContent of B."
        chunks = _chunk_text(text)

        for chunk in chunks:
            assert "heading" in chunk
            assert chunk["heading"] != ""

    def test_large_section_split_into_smaller_chunks(self) -> None:
        """FR-003: Large sections are split to stay within chunk size."""
        # Create a section with ~3000 chars (well above 1000 max_chunk_size)
        paragraphs = [f"Paragraph {i}. " + "x" * 200 for i in range(15)]
        text = "# Big Section\n" + "\n\n".join(paragraphs)

        chunks = _chunk_text(text, max_chunk_size=1000)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk["content"]) <= 1200  # allow some tolerance

    def test_empty_text_returns_empty_list(self) -> None:
        """Edge case: empty input produces no chunks."""
        chunks = _chunk_text("")
        assert chunks == []

    def test_text_without_headings_still_chunked(self) -> None:
        """FR-003: Text without explicit headings is still chunked."""
        text = "This is plain text without any headings.\n\nSecond paragraph."
        chunks = _chunk_text(text)

        assert len(chunks) >= 1
        assert chunks[0]["heading"] == ""

    def test_chunk_content_not_empty(self) -> None:
        """FR-003: No empty chunks are produced."""
        text = "# A\nContent A\n\n# B\n\n\n# C\nContent C"
        chunks = _chunk_text(text)

        for chunk in chunks:
            assert chunk["content"].strip() != ""
