"""Unit tests for LLM JSON extraction (malformed tails from Gemma)."""

from app.backend.services.hybrid_pipeline import _parse_llm_json_response


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
