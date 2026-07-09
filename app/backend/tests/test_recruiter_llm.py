"""Tests for recruiter LLM routing."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_generate_recruiter_json_uses_gemini_when_key_set(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from app.backend.services.recruiter.llm_client import generate_recruiter_json

    with patch(
        "app.backend.services.llm_service.gemini_generate_content",
        new_callable=AsyncMock,
    ) as mock_gemini:
        mock_gemini.return_value = '{"score": 82, "evidence": ["strong answer"]}'

        result = await generate_recruiter_json("Evaluate this answer")

        assert result == {"score": 82, "evidence": ["strong answer"]}
        mock_gemini.assert_awaited_once()
        assert mock_gemini.await_args.kwargs["response_mime_type"] == "application/json"


@pytest.mark.asyncio
async def test_generate_recruiter_llm_falls_back_to_ollama_without_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    from app.backend.services.llm_service import generate_recruiter_llm

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": '{"score": 70}'}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.backend.services.llm_service.httpx.AsyncClient", return_value=mock_client):
        text = await generate_recruiter_llm("prompt", max_output_tokens=512)

    assert text == '{"score": 70}'
    mock_client.post.assert_awaited_once()
    assert mock_client.post.await_args.args[0].endswith("/api/generate")
