"""OCR service for scanned PDF documents.

Uses pytesseract (Tesseract OCR engine) to extract text from scanned PDFs.
Gracefully degrades when Tesseract is not installed.
"""

import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pytesseract
    _HAS_TESSERACT = True
except ImportError:
    _HAS_TESSERACT = False
    logger.info("pytesseract not installed — OCR for scanned PDFs unavailable")

try:
    from pdf2image import convert_from_bytes
    _HAS_PDF2IMAGE = True
except ImportError:
    _HAS_PDF2IMAGE = False
    logger.info("pdf2image not installed — OCR for scanned PDFs unavailable")


def is_ocr_available() -> bool:
    """Check if OCR dependencies are available."""
    return _HAS_TESSERACT and _HAS_PDF2IMAGE


def ocr_pdf(file_bytes: bytes, dpi: int = 200, max_pages: int = 20) -> Optional[str]:
    """Extract text from a scanned PDF using OCR.

    Args:
        file_bytes: Raw PDF file bytes.
        dpi: Resolution for rendering pages (higher = better accuracy, slower).
        max_pages: Maximum pages to process (prevents timeouts on large docs).

    Returns:
        Extracted text string, or None if OCR is unavailable or fails.
    """
    if not is_ocr_available():
        logger.warning("OCR requested but dependencies not available")
        return None

    try:
        images = convert_from_bytes(file_bytes, dpi=dpi, first_page=1, last_page=max_pages)
        text_parts = []
        for i, img in enumerate(images):
            try:
                page_text = pytesseract.image_to_string(img, lang="eng")
                if page_text.strip():
                    text_parts.append(page_text.strip())
            except Exception as e:
                logger.warning("OCR failed on page %d: %s", i + 1, e)
                continue

        if not text_parts:
            logger.warning("OCR completed but no text extracted")
            return None

        result = "\n".join(text_parts)
        logger.info("OCR extracted %d characters from %d pages", len(result), len(images))
        return result

    except Exception as e:
        logger.error("OCR processing failed: %s", e)
        return None


def ocr_with_fallback(file_bytes: bytes, existing_text: str, dpi: int = 200) -> str:
    """Use OCR as a fallback when normal PDF text extraction yields too little text.

    Args:
        file_bytes: Raw PDF file bytes.
        existing_text: Text already extracted by pdfplumber/PyMuPDF.
        dpi: Resolution for OCR rendering.

    Returns:
        OCR-extracted text if OCR is available and existing text is insufficient,
        otherwise returns the original existing_text.
    """
    if existing_text and len(existing_text.strip()) >= 100:
        return existing_text

    if not is_ocr_available():
        logger.info("Scanned PDF detected but OCR unavailable — returning partial text")
        return existing_text

    logger.info("Attempting OCR fallback for scanned PDF (extracted %d chars so far)",
                len(existing_text.strip()) if existing_text else 0)
    ocr_text = ocr_pdf(file_bytes, dpi=dpi)
    if ocr_text and len(ocr_text.strip()) >= 50:
        # Merge: prefer OCR text but keep any unique lines from existing
        existing_lines = set(existing_text.strip().lower().splitlines()) if existing_text else set()
        merged_lines = []
        for line in ocr_text.splitlines():
            merged_lines.append(line)
        # Add any unique lines from existing text that OCR missed
        for line in (existing_text or "").splitlines():
            if line.strip() and line.strip().lower() not in {l.strip().lower() for l in merged_lines}:
                merged_lines.append(line)
        return "\n".join(merged_lines)

    return existing_text
