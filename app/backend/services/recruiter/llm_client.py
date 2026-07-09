"""Shared LLM client for recruiter agents (Gemini primary, Ollama fallback)."""

import json
import re
from typing import Any

from app.backend.services.llm_service import generate_recruiter_llm


def parse_json_safely(text: str) -> dict[str, Any] | None:
    """Parse JSON from an LLM response, tolerating markdown fences."""
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


async def generate_recruiter_json(
    prompt: str,
    *,
    max_output_tokens: int = 1024,
    temperature: float = 0.2,
    timeout: float = 120.0,
) -> dict[str, Any] | None:
    """Generate and parse a JSON object from the recruiter LLM."""
    response_text = await generate_recruiter_llm(
        prompt,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        timeout=timeout,
    )
    if not response_text:
        return None
    return parse_json_safely(response_text)
