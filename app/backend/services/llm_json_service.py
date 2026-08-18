"""
Resilient JSON LLM invocation — multi-tier prompts, parse repair, Gemini JSON mode.

Used by narrative, interview kit, and other structured LLM outputs so transient
empty/truncated responses retry instead of surfacing as user-visible failures.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from typing import Any, Dict, List, Optional

log = logging.getLogger("aria.llm_json")

DEFAULT_TIER_DELAY_S = float(os.getenv("LLM_JSON_TIER_DELAY", "1.5"))
DEFAULT_MAX_TIERS = max(1, int(os.getenv("LLM_JSON_MAX_TIERS", "4")))


def _tier_output_tokens(prompt: str, *, max_output_tokens: int, attempt: int) -> int:
    from app.backend.services.llm_service import compute_max_output_tokens

    tier_tokens = compute_max_output_tokens(
        prompt,
        requested=max_output_tokens,
        json_mode=True,
    )
    if attempt > 0:
        tier_tokens = max(tier_tokens, int(max_output_tokens * 0.85))
    return tier_tokens


async def invoke_llm_json_resilient(
    prompts: List[str],
    *,
    max_output_tokens: int = 2200,
    log_label: str = "llm_json",
    temperature: float = 0.2,
    allow_provider_fallback: bool = True,
    validate_parsed: Callable[[Dict[str, Any]], bool] | None = None,
    on_rejected: Callable[[Dict[str, Any], int, str], None] | None = None,
) -> Optional[Dict[str, Any]]:
    """Try prompts in order until one returns parseable, validated JSON."""
    from app.backend.services.app_llm_client import (
        _try_gemini,
        _try_ollama,
        _try_openrouter,
    )
    from app.backend.services.hybrid_pipeline import _parse_llm_json_response
    from app.backend.services.llm_service import compute_max_output_tokens

    tiers = [p for p in prompts if p and str(p).strip()][:DEFAULT_MAX_TIERS]
    if not tiers:
        return None

    for attempt, prompt in enumerate(tiers):
        if attempt > 0:
            await asyncio.sleep(DEFAULT_TIER_DELAY_S * attempt)

        tier_tokens = _tier_output_tokens(prompt, max_output_tokens=max_output_tokens, attempt=attempt)
        tier_temp = temperature if attempt == 0 else min(temperature, 0.15)
        tier_label = f"{log_label}_tier{attempt + 1}"

        effective_max = compute_max_output_tokens(
            prompt,
            requested=tier_tokens,
            json_mode=True,
        )
        llm_kwargs = {
            "system": None,
            "max_output_tokens": effective_max,
            "temperature": tier_temp,
            "json_mode": True,
            "log_label": tier_label,
        }
        network_kwargs = {**llm_kwargs, "timeout": 120.0}

        provider_chain: list[tuple[str, Any, dict[str, Any]]] = [
            ("gemini", _try_gemini, llm_kwargs),
        ]
        if allow_provider_fallback:
            provider_chain.extend(
                [
                    ("ollama", _try_ollama, network_kwargs),
                    ("openrouter", _try_openrouter, network_kwargs),
                ]
            )

        tier_had_response = False
        for provider_name, provider_fn, kwargs in provider_chain:
            try:
                raw = await provider_fn(prompt, **kwargs)
            except Exception as err:
                log.warning(
                    "%s tier %s %s call failed: %s: %s",
                    log_label,
                    attempt + 1,
                    provider_name,
                    type(err).__name__,
                    str(err)[:160],
                )
                continue

            if not raw or len(str(raw).strip()) < 10:
                log.warning(
                    "%s tier %s %s returned empty response",
                    log_label,
                    attempt + 1,
                    provider_name,
                )
                continue

            tier_had_response = True
            raw_text = str(raw)
            parsed = _parse_llm_json_response(raw_text)
            if parsed is None:
                log.warning(
                    "%s tier %s %s returned non-JSON (%d chars)",
                    log_label,
                    attempt + 1,
                    provider_name,
                    len(raw_text),
                )
                continue

            if validate_parsed is not None and not validate_parsed(parsed):
                log.warning(
                    "%s tier %s %s parsed JSON rejected by validator (%d chars)",
                    log_label,
                    attempt + 1,
                    provider_name,
                    len(raw_text),
                )
                if on_rejected:
                    try:
                        on_rejected(parsed, attempt + 1, raw_text)
                    except Exception as cb_err:
                        log.debug("%s on_rejected callback failed: %s", log_label, cb_err)
                continue

            log.info(
                "%s succeeded on tier %s via %s (%d chars)",
                log_label,
                attempt + 1,
                provider_name,
                len(raw_text),
            )
            return parsed

        if not tier_had_response:
            log.warning(
                "%s tier %s exhausted all providers with no usable response",
                log_label,
                attempt + 1,
            )

    return None
