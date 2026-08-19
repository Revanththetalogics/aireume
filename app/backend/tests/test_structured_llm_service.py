"""Tests for Outlines structured LLM generation."""

import json

import pytest

from app.backend.schemas.llm_structured import InterviewKitLLMResponse
from app.backend.services.structured_llm_service import (
    invoke_outlines_json_resilient,
    is_structured_llm_enabled,
    parse_outlines_json_text,
)


def _valid_kit_payload() -> dict:
    steps = [{"text": f"Question {i}?", "spoken_text": f"Question {i}?"} for i in range(1, 5)]
    return {
        "interview_questions": {
            "kit_version": 3,
            "screen_objective": "Validate fit",
            "threads": [{"id": "t1", "title": "Focus", "kind": "technical", "steps": steps}],
            "technical_questions": steps,
            "behavioral_questions": [],
            "experience_deep_dive_questions": [],
        }
    }


def test_parse_outlines_json_text_validates_schema():
    raw = json.dumps(_valid_kit_payload())
    parsed = parse_outlines_json_text(raw, InterviewKitLLMResponse)
    assert parsed is not None
    assert parsed["interview_questions"]["kit_version"] == 3


def test_parse_outlines_json_text_rejects_invalid():
    assert parse_outlines_json_text('{"wrong": true}', InterviewKitLLMResponse) is None


@pytest.mark.asyncio
async def test_invoke_outlines_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("OUTLINES_STRUCTURED_JSON", "0")
    result = await invoke_outlines_json_resilient(
        ["prompt"],
        output_type=InterviewKitLLMResponse,
        log_label="test",
    )
    assert result is None


@pytest.mark.asyncio
async def test_invoke_outlines_gemini_success(monkeypatch):
    monkeypatch.setenv("OUTLINES_STRUCTURED_JSON", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def _fake_gemini(prompt, **kwargs):
        return json.dumps(_valid_kit_payload())

    async def _fake_ollama(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.backend.services.structured_llm_service._try_outlines_gemini",
        _fake_gemini,
    )
    monkeypatch.setattr(
        "app.backend.services.structured_llm_service._try_outlines_ollama",
        _fake_ollama,
    )

    from app.backend.services.background_enrichment import _kit_meets_minimum

    result = await invoke_outlines_json_resilient(
        ["prompt"],
        output_type=InterviewKitLLMResponse,
        log_label="interview_kit",
        validate_parsed=_kit_meets_minimum,
    )
    assert result is not None
    assert result["interview_questions"]["threads"]


@pytest.mark.asyncio
async def test_invoke_llm_json_prefers_outlines_when_schema_set(monkeypatch):
    monkeypatch.setenv("OUTLINES_STRUCTURED_JSON", "1")

    async def _fake_outlines(*args, **kwargs):
        return _valid_kit_payload()

    async def _fake_gemini(*args, **kwargs):
        raise AssertionError("legacy gemini should not run when outlines succeeds")

    monkeypatch.setattr(
        "app.backend.services.structured_llm_service.invoke_outlines_json_resilient",
        _fake_outlines,
    )
    monkeypatch.setattr(
        "app.backend.services.app_llm_client._try_gemini",
        _fake_gemini,
    )

    from app.backend.services.llm_json_service import invoke_llm_json_resilient

    result = await invoke_llm_json_resilient(
        ["prompt"],
        output_type=InterviewKitLLMResponse,
        log_label="interview_kit",
    )
    assert result is not None
    assert "interview_questions" in result


def test_is_structured_llm_enabled_default_true(monkeypatch):
    monkeypatch.delenv("OUTLINES_STRUCTURED_JSON", raising=False)
    assert is_structured_llm_enabled() is True
