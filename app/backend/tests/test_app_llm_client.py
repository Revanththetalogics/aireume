"""Tests for shared application LLM client."""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_generate_app_json_uses_gemini_when_key_set(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from app.backend.services.app_llm_client import generate_app_json

    with patch(
        "app.backend.services.llm_service.gemini_generate_content",
        new_callable=AsyncMock,
    ) as mock_gemini:
        mock_gemini.return_value = '{"role_category": "technical", "confidence": 0.9}'

        result = await generate_app_json("Analyze this JD")

        assert result == {"role_category": "technical", "confidence": 0.9}
        mock_gemini.assert_awaited_once()
        assert mock_gemini.await_args.kwargs["response_mime_type"] == "application/json"


@pytest.mark.asyncio
async def test_generate_app_llm_falls_back_to_ollama_without_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    from app.backend.services.app_llm_client import generate_app_llm

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": "hello from ollama"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.backend.services.llm_service.get_ollama_semaphore",
        return_value=asyncio.Semaphore(1),
    ), patch(
        "app.backend.services.app_llm_client.httpx.AsyncClient",
        return_value=mock_client,
    ):
        text = await generate_app_llm("prompt", max_output_tokens=128)

    assert text == "hello from ollama"
    mock_client.post.assert_awaited_once()
    assert mock_client.post.await_args.args[0].endswith("/api/generate")


@pytest.mark.asyncio
async def test_generate_app_llm_falls_back_to_openrouter_when_gemini_and_ollama_fail(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

    from app.backend.services.app_llm_client import generate_app_llm

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "hello from openrouter"}}],
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.backend.services.llm_service.gemini_generate_content",
        new_callable=AsyncMock,
        side_effect=RuntimeError("429"),
    ), patch(
        "app.backend.services.llm_service.get_ollama_semaphore",
        return_value=asyncio.Semaphore(1),
    ), patch(
        "app.backend.services.app_llm_client.httpx.AsyncClient",
        return_value=mock_client,
    ) as mock_async_client:
        text = await generate_app_llm("prompt", max_output_tokens=128)

    assert text == "hello from openrouter"
    assert mock_client.post.await_count == 2
    urls = [call.args[0] for call in mock_client.post.await_args_list]
    assert any(u.endswith("/api/generate") for u in urls)
    assert any("openrouter.ai" in u for u in urls)
    assert mock_async_client.call_count == 2


@pytest.mark.asyncio
async def test_generate_app_llm_skips_fallbacks_when_disabled(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from app.backend.services.app_llm_client import generate_app_llm

    with patch(
        "app.backend.services.llm_service.gemini_generate_content",
        new_callable=AsyncMock,
        side_effect=RuntimeError("429"),
    ), patch(
        "app.backend.services.app_llm_client._try_ollama",
        new_callable=AsyncMock,
    ) as mock_ollama, patch(
        "app.backend.services.app_llm_client._try_openrouter",
        new_callable=AsyncMock,
    ) as mock_openrouter:
        text = await generate_app_llm(
            "prompt",
            max_output_tokens=128,
            allow_provider_fallback=False,
        )

    assert text is None
    mock_ollama.assert_not_awaited()
    mock_openrouter.assert_not_awaited()
