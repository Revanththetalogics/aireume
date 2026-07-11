"""
Resilient JSON LLM invocation — multi-tier prompts, parse repair, Gemini JSON mode.

Used by narrative, interview kit, and other structured LLM outputs so transient
empty/truncated responses retry instead of surfacing as user-visible failures.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

log = logging.getLogger("aria.llm_json")

DEFAULT_TIER_DELAY_S = float(os.getenv("LLM_JSON_TIER_DELAY", "1.5"))
DEFAULT_MAX_TIERS = max(1, int(os.getenv("LLM_JSON_MAX_TIERS", "4")))


async def invoke_llm_json_resilient(
    prompts: List[str],
    *,
    max_output_tokens: int = 2200,
    log_label: str = "llm_json",
    temperature: float = 0.2,
) -> Optional[Dict[str, Any]]:
    """Try prompts in order until one returns parseable JSON."""
    from app.backend.services.app_llm_client import generate_app_llm
    from app.backend.services.hybrid_pipeline import _parse_llm_json_response

    tiers = [p for p in prompts if p and str(p).strip()][:DEFAULT_MAX_TIERS]
    if not tiers:
        return None

    for attempt, prompt in enumerate(tiers):
        if attempt > 0:
            await asyncio.sleep(DEFAULT_TIER_DELAY_S * attempt)

        tier_tokens = max_output_tokens if attempt == 0 else min(max_output_tokens, 1800)
        tier_temp = temperature if attempt == 0 else min(temperature, 0.15)

        try:
            raw = await generate_app_llm(
                prompt,
                max_output_tokens=tier_tokens,
                temperature=tier_temp,
                json_mode=True,
                log_label=f"{log_label}_tier{attempt + 1}",
            )
        except Exception as err:
            log.warning(
                "%s tier %s call failed: %s: %s",
                log_label,
                attempt + 1,
                type(err).__name__,
                str(err)[:160],
            )
            continue

        if not raw or len(str(raw).strip()) < 10:
            log.warning("%s tier %s returned empty response", log_label, attempt + 1)
            continue

        parsed = _parse_llm_json_response(str(raw))
        if parsed is not None:
            log.info(
                "%s succeeded on tier %s (%d chars)",
                log_label,
                attempt + 1,
                len(str(raw)),
            )
            return parsed

        log.warning(
            "%s tier %s returned non-JSON (%d chars)",
            log_label,
            attempt + 1,
            len(str(raw)),
        )

    return None
