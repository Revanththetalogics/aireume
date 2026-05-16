"""Unit tests for LLM JSON extraction (malformed tails from Gemma)."""

import json
from app.backend.services.hybrid_pipeline import _parse_llm_json_response, _fix_unescaped_control_chars


def test_parse_truncates_malformed_tail_after_first_object():
    # Model closed the root object too early, then continued with ,"explainability"
    raw = (
        '{"strengths":["a"],"weaknesses":["b"],'
        '"recommendation_rationale":"Hi."},'
        '"explainability":{"skill_rationale":"x"}}'
    )
    d = _parse_llm_json_response(raw)
    assert d is not None
    assert d["strengths"] == ["a"]
    assert d["recommendation_rationale"] == "Hi."
    # Tail after first balanced `}` is ignored; explainability may be missing
    assert d.get("explainability") in (None, {})


def test_parse_full_valid_json():
    raw = '{"strengths":[],"weaknesses":[],"recommendation_rationale":"","explainability":{}}'
    d = _parse_llm_json_response(raw)
    assert d["strengths"] == []


# ── New tests for robust JSON extraction ──────────────────────────────────────


def test_parse_valid_json_no_cleaning_needed():
    """Strategy 1: raw valid JSON should parse without any cleaning."""
    raw = json.dumps({"candidate_profile_summary": "Test", "strengths": ["a"], "weaknesses": ["b"]})
    d = _parse_llm_json_response(raw)
    assert d is not None
    assert d["candidate_profile_summary"] == "Test"


def test_parse_markdown_fence_wrapped():
    """JSON wrapped in ```json ... ``` should be extracted."""
    raw = '```json\n{"strengths": ["a"], "weaknesses": ["b"]}\n```'
    d = _parse_llm_json_response(raw)
    assert d is not None
    assert d["strengths"] == ["a"]


def test_parse_markdown_fence_no_language():
    """JSON wrapped in ``` ... ``` (no language tag) should be extracted."""
    raw = '```\n{"strengths": ["a"], "weaknesses": ["b"]}\n```'
    d = _parse_llm_json_response(raw)
    assert d is not None
    assert d["strengths"] == ["a"]


def test_parse_thinking_tags_gemma():
    """Gemma-style thinking tags should be stripped."""
    raw = '\u003cthink\u003eSome analysis here...\u003c/think\u003e{"strengths": ["a"], "weaknesses": ["b"]}'
    d = _parse_llm_json_response(raw)
    assert d is not None
    assert d["strengths"] == ["a"]


def test_parse_redacted_thinking_tags():
    """<redacted_thinking> tags should be stripped."""
    raw = '<redacted_thinking>thinking here</redacted_thinking>{"strengths": ["a"], "weaknesses": ["b"]}'
    d = _parse_llm_json_response(raw)
    assert d is not None
    assert d["strengths"] == ["a"]


def test_parse_leading_text_before_json():
    """Text before the JSON object should be stripped."""
    raw = 'Here is the JSON response:\n{"strengths": ["a"], "weaknesses": ["b"]}'
    d = _parse_llm_json_response(raw)
    assert d is not None
    assert d["strengths"] == ["a"]


def test_parse_trailing_text_after_json():
    """Trailing text after the JSON object should be ignored via balanced extraction."""
    raw = '{"strengths": ["a"], "weaknesses": ["b"]}\nEnd of response.'
    d = _parse_llm_json_response(raw)
    assert d is not None
    assert d["strengths"] == ["a"]


def test_parse_large_json_17k_chars():
    """Simulate a 17K+ char response (like the staging failure)."""
    # Build a large valid JSON
    large_data = {
        "candidate_profile_summary": "x" * 500,
        "strengths": [f"Strength {i} with a detailed explanation " * 10 for i in range(20)],
        "weaknesses": [f"Weakness {i} with a detailed explanation " * 10 for i in range(10)],
        "interview_questions": {
            "technical_questions": [
                {"text": f"Question {i}? " * 20, "what_to_listen_for": ["a"], "follow_ups": ["b"]}
                for i in range(15)
            ],
        },
    }
    raw = json.dumps(large_data)
    assert len(raw) > 17000, f"Test JSON only {len(raw)} chars, need >17000"
    d = _parse_llm_json_response(raw)
    assert d is not None
    assert len(d["strengths"]) == 20


def test_parse_trailing_commas():
    """Trailing commas (common LLM mistake) should be fixed."""
    raw = '{"strengths": ["a",], "weaknesses": ["b",],}'
    d = _parse_llm_json_response(raw)
    assert d is not None
    assert d["strengths"] == ["a"]
    assert d["weaknesses"] == ["b"]


def test_parse_empty_input():
    """Empty string should return None."""
    assert _parse_llm_json_response("") is None
    assert _parse_llm_json_response("   ") is None


def test_parse_no_json_at_all():
    """Response with no JSON at all should return None."""
    assert _parse_llm_json_response("Just some plain text without any JSON") is None


def test_parse_thinking_with_braces():
    """Thinking tags containing braces should not confuse the extractor."""
    # Use the actual Unicode think tags that Gemma produces
    think_open = "\u003cthink\u003e"
    think_close = "\u003c/think\u003e"
    raw = f'{think_open}Analysis: candidate has skill{think_close}{{"strengths": ["a"], "weaknesses": ["b"]}}'
    d = _parse_llm_json_response(raw)
    assert d is not None
    assert d["strengths"] == ["a"]


def test_parse_fence_plus_thinking_plus_json():
    """Full LLM output: fence + thinking + JSON + trailing text."""
    think_open = "\u003cthink\u003e"
    think_close = "\u003c/think\u003e"
    raw = f'```json\n{think_open}Let me analyze...{think_close}\n{{"strengths": ["a"], "weaknesses": ["b"]}}\nDone.\n```'
    d = _parse_llm_json_response(raw)
    assert d is not None
    assert d["strengths"] == ["a"]


# ── Tests for _fix_unescaped_control_chars ────────────────────────────────────


def test_fix_unescaped_newlines_in_strings():
    """Literal newlines inside JSON string values should be escaped."""
    raw = '{"text": "line1\nline2"}'
    fixed = _fix_unescaped_control_chars(raw)
    parsed = json.loads(fixed)
    assert parsed["text"] == "line1\nline2"


def test_fix_unescaped_tabs_in_strings():
    """Literal tabs inside JSON string values should be escaped."""
    raw = '{"text": "col1\tcol2"}'
    fixed = _fix_unescaped_control_chars(raw)
    parsed = json.loads(fixed)
    assert parsed["text"] == "col1\tcol2"


def test_fix_no_change_for_already_escaped():
    """Already-escaped control chars should not be double-escaped."""
    raw = '{"text": "line1\\nline2"}'
    fixed = _fix_unescaped_control_chars(raw)
    parsed = json.loads(fixed)
    assert parsed["text"] == "line1\nline2"


def test_fix_control_chars_outside_strings_unchanged():
    """Control chars outside string values (e.g., whitespace between keys) should be preserved."""
    raw = '{\n  "text": "value"\n}'
    fixed = _fix_unescaped_control_chars(raw)
    # Should still be valid JSON (newlines between keys are fine)
    parsed = json.loads(fixed)
    assert parsed["text"] == "value"


def test_parse_unescaped_newlines_in_json_string():
    """Full pipeline: JSON with literal newlines in string values."""
    # This is the kind of invalid JSON that cloud LLMs sometimes produce
    raw = '{"strengths": ["line1\nline2"], "weaknesses": ["b"]}'
    d = _parse_llm_json_response(raw)
    assert d is not None
    assert "line1" in d["strengths"][0]
