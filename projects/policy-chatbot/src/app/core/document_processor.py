"""Document processing — text extraction, chunking, and embedding generation."""

import io
import logging
import re

import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from docx import Document as DocxDocument

logger = logging.getLogger(__name__)

# Target chunk size in characters — balances context quality with token limits
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200


def extract_text_from_pdf(data: bytes) -> list[dict[str, str]]:
    """Extract text from a PDF preserving section headings (FR-002).

    Returns a list of sections with 'heading' and 'content' keys.
    """
    doc = fitz.open(stream=data, filetype="pdf")
    sections: list[dict[str, str]] = []
    current_heading = ""
    current_content: list[str] = []

    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                text = "".join(span["text"] for span in line["spans"]).strip()
                if not text:
                    continue

                # Heuristic: detect headings by font size (larger than body text)
                avg_size = sum(span["size"] for span in line["spans"]) / len(line["spans"])
                is_bold = any("bold" in span.get("font", "").lower() for span in line["spans"])

                if avg_size > 12 or is_bold:
                    if current_content:
                        sections.append(
                            {
                                "heading": current_heading,
                                "content": "\n".join(current_content),
                            }
                        )
                    current_heading = text
                    current_content = []
                else:
                    current_content.append(text)

    if current_content:
        sections.append({"heading": current_heading, "content": "\n".join(current_content)})

    doc.close()
    return sections


def extract_text_from_docx(data: bytes) -> list[dict[str, str]]:
    """Extract text from a DOCX preserving section headings (FR-002)."""
    doc = DocxDocument(io.BytesIO(data))
    sections: list[dict[str, str]] = []
    current_heading = ""
    current_content: list[str] = []

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue

        if paragraph.style and paragraph.style.name.startswith("Heading"):
            if current_content:
                sections.append(
                    {
                        "heading": current_heading,
                        "content": "\n".join(current_content),
                    }
                )
            current_heading = text
            current_content = []
        else:
            current_content.append(text)

    if current_content:
        sections.append({"heading": current_heading, "content": "\n".join(current_content)})

    return sections


def extract_text_from_html(data: bytes) -> list[dict[str, str]]:
    """Extract text from HTML preserving section headings (FR-002)."""
    soup = BeautifulSoup(data, "html.parser")
    sections: list[dict[str, str]] = []
    current_heading = ""
    current_content: list[str] = []

    heading_tags = {"h1", "h2", "h3", "h4", "h5", "h6"}

    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td"]):
        text = element.get_text(strip=True)
        if not text:
            continue

        if element.name in heading_tags:
            if current_content:
                sections.append(
                    {
                        "heading": current_heading,
                        "content": "\n".join(current_content),
                    }
                )
            current_heading = text
            current_content = []
        else:
            current_content.append(text)

    if current_content:
        sections.append({"heading": current_heading, "content": "\n".join(current_content)})

    return sections


def extract_text(data: bytes, file_type: str) -> list[dict[str, str]]:
    """Route to the appropriate text extractor based on file type."""
    extractors = {
        "pdf": extract_text_from_pdf,
        "docx": extract_text_from_docx,
        "html": extract_text_from_html,
    }
    extractor = extractors.get(file_type)
    if not extractor:
        msg = f"Unsupported file type: {file_type}"
        raise ValueError(msg)
    return extractor(data)


def chunk_sections(
    sections: list[dict[str, str]],
    *,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict[str, str]]:
    """Split extracted sections into semantic chunks for embedding (FR-003).

    Uses heading-aware splitting: keeps section headings attached to their content,
    and splits long sections with overlap to preserve context.
    """
    chunks: list[dict[str, str]] = []

    for section in sections:
        heading = section["heading"]
        content = section["content"]

        if len(content) <= chunk_size:
            chunks.append({"heading": heading, "content": content})
            continue

        # Split long sections by paragraph boundaries
        paragraphs = re.split(r"\n\s*\n|\n", content)
        current_chunk: list[str] = []
        current_length = 0

        for paragraph in paragraphs:
            para_length = len(paragraph)

            if current_length + para_length > chunk_size and current_chunk:
                chunks.append({"heading": heading, "content": "\n".join(current_chunk)})
                # Keep overlap from the end of the previous chunk
                overlap_text = "\n".join(current_chunk)[-overlap:]
                current_chunk = [overlap_text, paragraph]
                current_length = len(overlap_text) + para_length
            else:
                current_chunk.append(paragraph)
                current_length += para_length

        if current_chunk:
            chunks.append({"heading": heading, "content": "\n".join(current_chunk)})

    return chunks


def count_tokens(text: str) -> int:
    """Approximate token count for a text string.

    Uses a simple heuristic (words * 1.3) for speed. For production accuracy,
    tiktoken would be used but adds cold-start latency.
    """
    word_count = len(text.split())
    return int(word_count * 1.3)
