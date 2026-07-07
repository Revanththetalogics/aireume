import logging

from app.backend.main import _RedactSecretsFilter


def test_redacts_gemini_key_query_param():
    filt = _RedactSecretsFilter()
    record = logging.LogRecord(
        name="httpx",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=SECRET123 "HTTP/1.1 200 OK"',
        args=(),
        exc_info=None,
    )
    assert filt.filter(record) is True
    assert "SECRET123" not in record.getMessage()
    assert "key=***REDACTED***" in record.getMessage()
