"""Voice LLM client — Gemini API (preferred) with Ollama fallback."""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger("voice_agent.voice_llm")

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL_VOICE", os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL_VOICE", os.getenv("OLLAMA_MODEL", "qwen2.5:3b"))
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

_http_client: httpx.AsyncClient | None = None


def use_gemini_for_voice() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def get_voice_llm_model() -> str:
    if use_gemini_for_voice():
        return os.getenv("GEMINI_MODEL_VOICE", os.getenv("GEMINI_MODEL", "gemini-2.5-flash")).strip()
    return OLLAMA_MODEL


async def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=45.0)
    return _http_client


def _parse_json(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for pattern in (r"```json\s*(\{.*?\})\s*```", r"(\{.*\})"):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    return None


async def generate_json(
    prompt: str,
    *,
    system: str | None = None,
    max_output_tokens: int = 384,
    temperature: float = 0.3,
) -> dict[str, Any] | None:
    """Single LLM call returning a parsed JSON object."""
    if use_gemini_for_voice():
        return await _gemini_json(
            prompt,
            system=system,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )
    return await _ollama_json(
        prompt,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
    )


async def _gemini_json(
    prompt: str,
    *,
    system: str | None,
    max_output_tokens: int,
    temperature: float,
) -> dict[str, Any] | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = get_voice_llm_model()
    url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
    body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
        },
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    client = await _get_client()
    try:
        resp = await client.post(
            url,
            params={"key": api_key},
            json=body,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = parts[0].get("text", "") if parts else ""
        return _parse_json(text)
    except Exception as exc:
        logger.warning("Gemini voice LLM failed: %s", exc)
        return None


async def _ollama_json(
    prompt: str,
    *,
    max_output_tokens: int,
    temperature: float,
) -> dict[str, Any] | None:
    headers = {}
    if OLLAMA_API_KEY.strip():
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY.strip()}"

    client = await _get_client()
    try:
        resp = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": temperature,
                    "num_predict": max_output_tokens,
                },
            },
            headers=headers,
        )
        resp.raise_for_status()
        text = resp.json().get("response", "")
        return _parse_json(text)
    except Exception as exc:
        logger.warning("Ollama voice LLM failed: %s", exc)
        return None
