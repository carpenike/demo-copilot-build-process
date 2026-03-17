"""Celery tasks for document ingestion and indexing.

These tasks run in background workers (separate ACA instances) and handle
the CPU/IO-intensive work of parsing documents, chunking, generating
embeddings, and upserting into Azure AI Search.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from celery import Celery  # type: ignore[import-untyped]

logger = structlog.get_logger()


def create_celery_app() -> Celery:
    """Create and configure the Celery app.

    Reads broker URL from settings at call time, not at module scope.
    """
    from app.config import Settings

    settings = Settings()
    broker_url = settings.effective_celery_broker_url

    celery_app = Celery(
        "policy_chatbot",
        broker=broker_url,
        backend=broker_url,
    )

    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
    )

    return celery_app


# Lazy initialization — celery_app is created when this module's tasks are discovered
_celery_app: Celery | None = None


def get_celery_app() -> Celery:
    """Get or create the Celery app singleton."""
    global _celery_app
    if _celery_app is None:
        _celery_app = create_celery_app()
    return _celery_app


def _chunk_text(text: str, max_chunk_size: int = 1000) -> list[dict[str, Any]]:
    """Split document text into semantically meaningful chunks.

    Attempts to split on section headings first, then falls back to
    paragraph-level splitting. Each chunk includes the section heading
    it belongs to.
    """
    heading_pattern = re.compile(r"^(#{1,4}\s+.+|[A-Z][^.!?]*:)\s*$", re.MULTILINE)

    sections: list[dict[str, Any]] = []
    current_heading = ""
    current_content: list[str] = []

    for line in text.split("\n"):
        if heading_pattern.match(line.strip()):
            if current_content:
                content = "\n".join(current_content).strip()
                if content:
                    sections.append(
                        {
                            "heading": current_heading,
                            "content": content,
                        }
                    )
            current_heading = line.strip().lstrip("# ").rstrip(":")
            current_content = []
        else:
            current_content.append(line)

    if current_content:
        content = "\n".join(current_content).strip()
        if content:
            sections.append({"heading": current_heading, "content": content})

    # Split large sections into smaller chunks
    chunks: list[dict[str, Any]] = []
    for section in sections:
        content = section["content"]
        heading = section["heading"]

        if len(content) <= max_chunk_size:
            chunks.append({"heading": heading, "content": content})
        else:
            paragraphs = content.split("\n\n")
            current_chunk: list[str] = []
            current_size = 0

            for para in paragraphs:
                if current_size + len(para) > max_chunk_size and current_chunk:
                    chunks.append(
                        {
                            "heading": heading,
                            "content": "\n\n".join(current_chunk),
                        }
                    )
                    current_chunk = []
                    current_size = 0

                current_chunk.append(para)
                current_size += len(para)

            if current_chunk:
                chunks.append(
                    {
                        "heading": heading,
                        "content": "\n\n".join(current_chunk),
                    }
                )

    return chunks


def _extract_text_from_bytes(content: bytes, filename: str) -> str:
    """Extract text content from PDF, DOCX, or HTML file bytes.

    Uses appropriate parser based on file extension.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        try:
            import pypdf  # type: ignore[import-not-found]

            reader = pypdf.PdfReader(__import__("io").BytesIO(content))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            logger.warning("pypdf_not_installed_using_raw_decode")
            return content.decode("utf-8", errors="replace")

    if ext == "docx":
        try:
            import docx  # type: ignore[import-not-found]

            doc = docx.Document(__import__("io").BytesIO(content))
            return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())
        except ImportError:
            logger.warning("python_docx_not_installed_using_raw_decode")
            return content.decode("utf-8", errors="replace")

    if ext in ("html", "htm"):
        try:
            from bs4 import BeautifulSoup  # type: ignore[import-not-found]

            soup = BeautifulSoup(content, "html.parser")
            return soup.get_text(separator="\n\n", strip=True)  # type: ignore[no-any-return]
        except ImportError:
            logger.warning("beautifulsoup_not_installed_using_raw_decode")
            return content.decode("utf-8", errors="replace")

    return content.decode("utf-8", errors="replace")
