"""Tests for speech pipeline helpers."""
from app.voice_agent.speech_pipeline import clean_tts_text, split_sentences
from app.voice_agent.turn_telemetry import TurnTelemetryCollector
from app.voice_agent.tts_warmup import build_kit_warm_phrases
from app.voice_agent.orchestrator import OrchestratorContext


def test_clean_tts_text_strips_markdown_and_urls():
    raw = "Check **SAP MM** at https://example.com for details."
    assert clean_tts_text(raw) == "Check SAP MM at for details."


def test_split_sentences():
    assert split_sentences("Hi there. Ready to begin?") == ["Hi there.", "Ready to begin?"]


def test_turn_telemetry_summary():
    t = TurnTelemetryCollector()
    t.begin_turn()
    t.record("stt_ms", 400)
    t.record("tts_ms", 200)
    t.end_turn()
    summary = t.summary()
    assert summary["turn_count"] == 1
    assert summary["stt_ms_p50"] == 400


def test_build_kit_warm_phrases_includes_intro_and_first_question():
    ctx = OrchestratorContext(
        session_id="1",
        candidate_name="Alex",
        jd_title="Analyst",
        total_duration_s=600,
    )
    phrases = build_kit_warm_phrases(
        ctx,
        [{"id": "t1", "category": "technical", "text": "Describe your Excel work."}],
    )
    assert any("Alex" in p for p in phrases)
    assert any("Excel" in p for p in phrases)
