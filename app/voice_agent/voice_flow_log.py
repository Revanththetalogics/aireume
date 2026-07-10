"""Structured logging helpers for LiveKit cloud voice screening flow."""
from __future__ import annotations

import json
import logging
from typing import Any

LOG_PREFIX = "[voice]"


def log_step(
    logger: logging.Logger,
    session_id: int | str | None,
    step: str,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    """Emit a consistent, grep-friendly log line for voice pipeline steps."""
    sid = session_id if session_id is not None else "-"
    extras = " ".join(
        f"{key}={value}"
        for key, value in fields.items()
        if value is not None and value != ""
    )
    message = f"{LOG_PREFIX} session={sid} step={step}"
    if extras:
        message = f"{message} {extras}"
    logger.log(level, message)


def metadata_summary(metadata: dict[str, Any]) -> dict[str, Any]:
    """Summarize dispatch metadata without dumping full payloads into logs."""
    kit = metadata.get("interview_kit") or {}
    questions = kit.get("questions") if isinstance(kit, dict) else []
    raw = json.dumps(metadata, default=str)
    return {
        "metadata_bytes": len(raw.encode("utf-8")),
        "metadata_keys": ",".join(sorted(metadata.keys())),
        "kit_questions": len(questions) if isinstance(questions, list) else 0,
    }
