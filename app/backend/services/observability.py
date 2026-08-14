"""Optional Sentry error reporting. No-ops when SENTRY_DSN is unset."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_initialized = False


def init_observability() -> None:
    global _initialized
    if _initialized:
        return
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("ENVIRONMENT", "development"),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            send_default_pii=False,
        )
        _initialized = True
        logger.info("Sentry initialized")
    except Exception as exc:
        logger.warning("Sentry init skipped: %s", exc)


def capture_exception(error: BaseException) -> None:
    if not _initialized:
        logger.exception("Unhandled error", exc_info=error)
        return
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(error)
    except Exception:
        logger.exception("Unhandled error", exc_info=error)


def capture_message(message: str, *, level: str = "error") -> None:
    if not _initialized:
        logger.error("%s", message)
        return
    try:
        import sentry_sdk
        sentry_sdk.capture_message(message, level=level)
    except Exception:
        logger.error("%s", message)
