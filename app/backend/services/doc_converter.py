"""
DOC/DOCX to PDF conversion service.

Enterprise-grade conversion using LibreOffice headless mode.
Falls back gracefully when LibreOffice is not installed.
"""
import io
import logging
import os
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


def _find_soffice() -> Optional[str]:
    """Locate the LibreOffice/soffice binary."""
    candidates = [
        "soffice",
        "soffice.exe",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/usr/bin/soffice",
        "/usr/lib/libreoffice/program/soffice",
    ]
    for cmd in candidates:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


# Lazy singleton
_soffice_path: Optional[str] = None


def get_soffice_path() -> Optional[str]:
    global _soffice_path
    if _soffice_path is None:
        _soffice_path = _find_soffice()
        if _soffice_path:
            logger.info("LibreOffice found at: %s", _soffice_path)
        else:
            logger.warning("LibreOffice (soffice) not found. DOC-to-PDF conversion unavailable.")
    return _soffice_path


def convert_to_pdf(file_bytes: bytes, original_filename: str) -> Optional[bytes]:
    """Convert a DOC/DOCX file to PDF using LibreOffice headless.

    Args:
        file_bytes: Raw file bytes.
        original_filename: Original filename (used to determine input format).

    Returns:
        PDF bytes if conversion succeeded, None otherwise.
    """
    soffice = get_soffice_path()
    if not soffice:
        logger.debug("LibreOffice not available; skipping DOC-to-PDF conversion")
        return None

    ext = os.path.splitext(original_filename.lower())[1]
    if ext not in (".doc", ".docx"):
        logger.debug("File extension %s does not require conversion", ext)
        return None

    tmp_in_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_in:
            tmp_in.write(file_bytes)
            tmp_in_path = tmp_in.name

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [
                    soffice,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", tmp_dir,
                    tmp_in_path,
                ],
                capture_output=True,
                timeout=60,
            )

            if result.returncode != 0:
                logger.warning(
                    "LibreOffice conversion failed (rc=%d): %s",
                    result.returncode,
                    result.stderr.decode("utf-8", errors="ignore")[:500],
                )
                return None

            # Find the converted PDF
            pdf_files = [f for f in os.listdir(tmp_dir) if f.endswith(".pdf")]
            if not pdf_files:
                logger.warning("LibreOffice conversion produced no PDF output")
                return None

            pdf_path = os.path.join(tmp_dir, pdf_files[0])
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            if len(pdf_bytes) < 100:
                logger.warning("LibreOffice produced empty/invalid PDF (%d bytes)", len(pdf_bytes))
                return None

            logger.info(
                "DOC-to-PDF conversion succeeded: %s → %d bytes",
                original_filename,
                len(pdf_bytes),
            )
            return pdf_bytes

    except subprocess.TimeoutExpired:
        logger.warning("LibreOffice conversion timed out after 60s")
        return None
    except Exception as e:
        logger.warning("LibreOffice conversion error: %s", e)
        return None
    finally:
        if tmp_in_path and os.path.exists(tmp_in_path):
            try:
                os.unlink(tmp_in_path)
            except OSError:
                pass


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber (best for converted docs).

    Args:
        pdf_bytes: Raw PDF bytes.

    Returns:
        Extracted text string.
    """
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.warning("pdfplumber extraction from converted PDF failed: %s", e)
        return ""
