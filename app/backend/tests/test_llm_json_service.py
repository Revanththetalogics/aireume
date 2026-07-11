"""Tests for resilient LLM JSON invocation."""

import pytest

from app.backend.services.llm_json_service import invoke_llm_json_resilient


@pytest.mark.asyncio
async def test_invoke_returns_none_when_all_tiers_empty(monkeypatch):
    async def _fake_llm(*args, **kwargs):
        return ""

    monkeypatch.setattr(
        "app.backend.services.app_llm_client.generate_app_llm",
        _fake_llm,
    )
    result = await invoke_llm_json_resilient(["prompt a", "prompt b"], log_label="test")
    assert result is None


@pytest.mark.asyncio
async def test_invoke_parses_json_on_second_tier(monkeypatch):
    calls = {"n": 0}

    async def _fake_llm(prompt, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return "not json"
        return '{"fit_summary": "Strong match", "strengths": ["Python"]}'

    monkeypatch.setattr(
        "app.backend.services.app_llm_client.generate_app_llm",
        _fake_llm,
    )
    result = await invoke_llm_json_resilient(["full", "compact"], log_label="test")
    assert result is not None
    assert result["fit_summary"] == "Strong match"
