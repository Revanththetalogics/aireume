"""Shared application LLM client — Gemini primary, Ollama fallback."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def parse_json_from_llm(text: str) -> dict[str, Any] | None:
    """Parse JSON from an LLM response, tolerating markdown fences."""
    if not text or not str(text).strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for pattern in (
        r"```json\s*(\{.*?\})\s*```",
        r"```\s*(\{.*?\})\s*```",
        r"(\{.*\})",
    ):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    return None


async def generate_app_llm(
    prompt: str,
    *,
    system: str | None = None,
    max_output_tokens: int = 1024,
    temperature: float = 0.2,
    timeout: float = 120.0,
    json_mode: bool = False,
    log_label: str = "app",
) -> str | None:
    """Generate text via Gemini when configured, else Ollama (with Gemini→Ollama fallback)."""
    from app.backend.services.llm_service import (
        gemini_generate_content,
        get_gemini_model,
        get_ollama_headers,
        get_ollama_semaphore,
        use_gemini_for_analysis,
    )

    if use_gemini_for_analysis():
        try:
            text = await gemini_generate_content(
                prompt,
                system=system,
                max_output_tokens=max_output_tokens,
                temperature=temperature,
                response_mime_type="application/json" if json_mode else None,
            )
            if text:
                logger.info(
                    "%s LLM via Google Gemini (model=%s)",
                    log_label,
                    get_gemini_model(),
                )
                return text
        except Exception as exc:
            logger.warning("%s Gemini call failed, trying Ollama: %s", log_label, exc)

    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
    try:
        semaphore = get_ollama_semaphore()
        async with semaphore:
            async with httpx.AsyncClient(timeout=timeout) as client:
                headers = get_ollama_headers(ollama_base)
                if system:
                    resp = await client.post(
                        f"{ollama_base}/api/chat",
                        headers=headers,
                        json={
                            "model": ollama_model,
                            "messages": [
                                {"role": "system", "content": system},
                                {"role": "user", "content": prompt},
                            ],
                            "stream": False,
                            "options": {
                                "temperature": temperature,
                                "num_predict": max_output_tokens,
                            },
                        },
                    )
                    resp.raise_for_status()
                    return resp.json().get("message", {}).get("content", "") or None

                payload: dict[str, Any] = {
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_output_tokens,
                    },
                }
                if json_mode:
                    payload["format"] = "json"
                resp = await client.post(
                    f"{ollama_base}/api/generate",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json().get("response", "") or None
    except Exception as exc:
        logger.warning("%s Ollama call failed: %s", log_label, exc)
        return None


async def generate_app_json(
    prompt: str,
    *,
    system: str | None = None,
    max_output_tokens: int = 1024,
    temperature: float = 0.2,
    timeout: float = 120.0,
    log_label: str = "app",
) -> dict[str, Any] | None:
    """Generate and parse a JSON object from the application LLM with retries."""
    from app.backend.services.hybrid_pipeline import _parse_llm_json_response
    from app.backend.services.llm_json_service import invoke_llm_json_resilient

    compact = prompt + "\n\nReturn ONLY valid JSON. No markdown."
    parsed = await invoke_llm_json_resilient(
        [prompt, compact],
        max_output_tokens=max_output_tokens,
        log_label=log_label,
        temperature=temperature,
    )
    if parsed is not None:
        return parsed

    text = await generate_app_llm(
        prompt,
        system=system,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        timeout=timeout,
        json_mode=True,
        log_label=log_label,
    )
    if not text:
        return None
    return parse_json_from_llm(text) or _parse_llm_json_response(text)
