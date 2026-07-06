"""
Tests for file safety scanning (services/file_scan_service.py):
  - magic-byte / content-type validation
  - optional ClamAV malware scan (no-op when unconfigured; fail modes when set)
"""
import io
import pytest

from app.backend.services.file_scan_service import (
    validate_document_bytes,
    scan_bytes_for_malware,
    validate_and_scan,
    UnsafeFileError,
)

PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
DOCX = b"PK\x03\x04" + b"\x00" * 40
OLE_DOC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 40
RTF = b"{\\rtf1\\ansi test}"


class TestContentValidation:
    def test_accepts_pdf(self):
        validate_document_bytes(PDF, "resume.pdf")

    def test_accepts_docx(self):
        validate_document_bytes(DOCX, "resume.docx")

    def test_accepts_legacy_doc(self):
        validate_document_bytes(OLE_DOC, "resume.doc")

    def test_accepts_rtf(self):
        validate_document_bytes(RTF, "resume.rtf")

    def test_accepts_plain_text_by_extension(self):
        validate_document_bytes(b"John Doe\nSoftware Engineer\n", "resume.txt")

    def test_rejects_empty_file(self):
        with pytest.raises(UnsafeFileError):
            validate_document_bytes(b"", "resume.pdf")

    def test_rejects_unsupported_extension(self):
        with pytest.raises(UnsafeFileError):
            validate_document_bytes(PDF, "resume.exe")

    def test_rejects_disguised_executable(self):
        """A PE/ELF binary renamed to .pdf must be rejected by magic bytes."""
        with pytest.raises(UnsafeFileError):
            validate_document_bytes(b"MZ\x90\x00" + b"\x00" * 40, "malware.pdf")

    def test_latin1_decodable_txt_is_accepted(self):
        """Known limitation: .txt is accepted if it decodes as latin-1 (which
        accepts any byte). Documents current behaviour; magic-byte checks guard
        the higher-risk office/pdf types."""
        validate_document_bytes(b"\xff\xfe\x00\x01\x02\x03", "notes.txt")


class TestMalwareScan:
    def test_noop_when_clamav_unconfigured(self, monkeypatch):
        monkeypatch.delenv("CLAMAV_HOST", raising=False)
        # Should not raise regardless of content when AV is not configured.
        scan_bytes_for_malware(b"anything")

    def test_detects_virus_when_clamav_reports_found(self, monkeypatch):
        monkeypatch.setenv("CLAMAV_HOST", "clamav")
        monkeypatch.setenv("CLAMAV_PORT", "3310")

        class _FakeClamd:
            def instream(self, _stream):
                return {"stream": ("FOUND", "Eicar-Test-Signature")}

        fake_module = type("m", (), {
            "ClamdNetworkSocket": lambda self=None, **kw: _FakeClamd()
        })()
        # clamd.ClamdNetworkSocket(...) → _FakeClamd()
        import sys
        monkeypatch.setitem(sys.modules, "clamd", type("clamd", (), {
            "ClamdNetworkSocket": lambda **kw: _FakeClamd()
        }))
        with pytest.raises(UnsafeFileError) as exc:
            scan_bytes_for_malware(b"X5O!P%@AP")
        assert "malware" in str(exc.value).lower()

    def test_fail_open_when_unreachable_and_not_required(self, monkeypatch):
        monkeypatch.setenv("CLAMAV_HOST", "unreachable")
        monkeypatch.delenv("CLAMAV_REQUIRED", raising=False)
        import sys

        def _boom(**kw):
            raise ConnectionError("no route to host")

        monkeypatch.setitem(sys.modules, "clamd", type("clamd", (), {
            "ClamdNetworkSocket": _boom
        }))
        # Not required → log and allow (no raise).
        scan_bytes_for_malware(b"data")

    def test_fail_closed_when_unreachable_and_required(self, monkeypatch):
        monkeypatch.setenv("CLAMAV_HOST", "unreachable")
        monkeypatch.setenv("CLAMAV_REQUIRED", "1")
        import sys

        def _boom(**kw):
            raise ConnectionError("no route to host")

        monkeypatch.setitem(sys.modules, "clamd", type("clamd", (), {
            "ClamdNetworkSocket": _boom
        }))
        with pytest.raises(UnsafeFileError):
            scan_bytes_for_malware(b"data")


class TestValidateAndScan:
    def test_combined_rejects_bad_content(self, monkeypatch):
        monkeypatch.delenv("CLAMAV_HOST", raising=False)
        with pytest.raises(UnsafeFileError):
            validate_and_scan(b"MZ\x90\x00", "x.pdf")

    def test_combined_accepts_valid_pdf(self, monkeypatch):
        monkeypatch.delenv("CLAMAV_HOST", raising=False)
        validate_and_scan(PDF, "resume.pdf")
