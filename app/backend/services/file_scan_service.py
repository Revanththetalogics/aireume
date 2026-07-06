"""
File safety scanning for uploaded documents (resumes, JDs).

Two layers of protection:
  1. Magic-byte / content-type validation — cheap, always on. Rejects files
     whose real content does not match an accepted document type.
  2. Antivirus scanning via ClamAV (clamd) — optional, enabled when
     CLAMAV_HOST is configured. Streams bytes to a clamd daemon.

Design goals:
  - Never crash the request path. If AV is misconfigured/unavailable we log
    loudly and (by default) fail-closed only when CLAMAV_REQUIRED=1.
  - No hard dependency on the `clamd` package unless AV scanning is enabled.
"""
import logging
import os

log = logging.getLogger("aria.filescan")


class UnsafeFileError(ValueError):
    """Raised when an uploaded file is rejected as unsafe or unsupported."""


# Accepted document magic-byte signatures.
#   PDF:  %PDF
#   ZIP-based (DOCX/XLSX/PPTX): PK\x03\x04 (also PK\x05\x06 empty, PK\x07\x08 spanned)
#   Legacy OLE (DOC/XLS):  D0 CF 11 E0 A1 B1 1A E1
#   RTF:  {\rtf
_PDF_MAGIC = b"%PDF"
_ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_RTF_MAGIC = b"{\\rtf"

# Plain-text resumes (.txt) have no reliable magic bytes; allowed by extension.
_TEXT_EXTENSIONS = {".txt", ".md"}
_DOC_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".rtf", ".txt", ".md"}


def validate_document_bytes(data: bytes, filename: str = "") -> None:
    """
    Validate that ``data`` looks like an accepted document type.

    Raises UnsafeFileError on rejection.
    """
    if not data:
        raise UnsafeFileError("File is empty")

    ext = os.path.splitext(filename or "")[1].lower()
    if ext and ext not in _DOC_EXTENSIONS:
        raise UnsafeFileError(f"Unsupported file type: {ext}")

    head = data[:8]
    if head.startswith(_PDF_MAGIC):
        return
    if any(head.startswith(m) for m in _ZIP_MAGICS):
        return
    if head.startswith(_OLE_MAGIC):
        return
    if head.startswith(_RTF_MAGIC):
        return

    # Allow plain text only when the extension explicitly says so and the
    # content decodes as UTF-8/Latin-1 text.
    if ext in _TEXT_EXTENSIONS:
        try:
            data[:4096].decode("utf-8")
            return
        except UnicodeDecodeError:
            try:
                data[:4096].decode("latin-1")
                return
            except UnicodeDecodeError:
                pass

    raise UnsafeFileError("File content does not match a supported document type")


def _clamav_enabled() -> bool:
    return bool(os.getenv("CLAMAV_HOST"))


def _clamav_required() -> bool:
    return os.getenv("CLAMAV_REQUIRED", "").lower() in ("1", "true")


def scan_bytes_for_malware(data: bytes) -> None:
    """
    Scan ``data`` with ClamAV when configured. Raises UnsafeFileError if the
    scanner reports a virus. If ClamAV is not configured, this is a no-op.
    If ClamAV is configured but unreachable, behaviour depends on
    CLAMAV_REQUIRED (fail-closed when set, otherwise log and allow).
    """
    if not _clamav_enabled():
        return

    host = os.getenv("CLAMAV_HOST")
    port = int(os.getenv("CLAMAV_PORT", "3310"))
    try:
        import clamd  # type: ignore
    except ImportError:
        msg = "CLAMAV_HOST set but python `clamd` package is not installed"
        if _clamav_required():
            raise UnsafeFileError("Virus scanning unavailable")
        log.error(msg)
        return

    try:
        import io
        cd = clamd.ClamdNetworkSocket(host=host, port=port, timeout=30)
        result = cd.instream(io.BytesIO(data))
    except Exception as e:  # connection / protocol failures
        if _clamav_required():
            log.error("ClamAV scan failed and CLAMAV_REQUIRED=1: %s", e)
            raise UnsafeFileError("Virus scanning unavailable")
        log.error("ClamAV scan failed (allowing upload; set CLAMAV_REQUIRED=1 to block): %s", e)
        return

    status = (result or {}).get("stream")
    if status and status[0] == "FOUND":
        signature = status[1] if len(status) > 1 else "unknown"
        log.warning("Malware detected in upload: %s", signature)
        raise UnsafeFileError(f"File rejected: malware detected ({signature})")


def validate_and_scan(data: bytes, filename: str = "") -> None:
    """Run both content validation and (optional) malware scan."""
    validate_document_bytes(data, filename)
    scan_bytes_for_malware(data)
