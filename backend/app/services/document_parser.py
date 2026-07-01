"""Document parsing service for PDF and DOCX files."""

from __future__ import annotations

import logging

import mammoth

from app.services.text_cleaning import fix_mojibake

logger = logging.getLogger(__name__)


def parse_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file.

    Uses pdfplumber for local extraction.

    Args:
        file_bytes: Raw PDF bytes.

    Returns:
        Extracted text content.
    """
    import io

    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "pdfplumber is required for PDF parsing. Install it with: pip install pdfplumber"
        ) from exc

    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
            else:
                logger.warning("Page %d had no extractable text", i + 1)

    full_text = "\n\n".join(text_parts)
    if not full_text.strip():
        raise ValueError("No text could be extracted from the PDF")

    logger.info("Extracted %d characters from %d pages", len(full_text), len(text_parts))
    return full_text


def parse_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file using mammoth.

    Args:
        file_bytes: Raw DOCX bytes.

    Returns:
        Extracted text content.
    """
    import io

    result = mammoth.extract_raw_text(io.BytesIO(file_bytes))
    text = result.value.strip()

    if result.messages:
        for msg in result.messages:
            logger.warning("mammoth: %s", msg)

    if not text:
        raise ValueError("No text could be extracted from the DOCX")

    logger.info("Extracted %d characters from DOCX", len(text))
    return text


def parse_document(file_bytes: bytes, file_name: str) -> str:
    """Parse a document based on its file extension.

    Extracted text is passed through ``fix_mojibake`` so that upstream encoding
    damage (UTF-8 mis-decoded as Windows-1252) is repaired before the text is
    stored or analysed. Clean text is unaffected.

    Args:
        file_bytes: Raw file bytes.
        file_name: Original filename (used to detect type).

    Returns:
        Extracted, mojibake-repaired text content.

    Raises:
        ValueError: If the file type is unsupported or no text was extracted.
    """
    lower_name = file_name.lower()
    if lower_name.endswith(".pdf"):
        text = parse_pdf(file_bytes)
    elif lower_name.endswith(".docx"):
        text = parse_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {file_name}")

    return fix_mojibake(text)
