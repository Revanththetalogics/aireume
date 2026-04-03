"""
Tests for video_service.py:
  - extract_pause_signals
  - extract_audio_anomalies
  - analyze_communication (mocked Ollama)
  - analyze_malpractice (mocked Ollama)
  - _run_full_analysis (mocked transcription + Ollama)
"""
import json
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

from app.backend.services.video_service import (
    extract_pause_signals,
    extract_audio_anomalies,
    analyze_communication,
    analyze_malpractice,
    _default_communication,
    _default_malpractice,
    _fmt_time,
    SUSPICIOUS_PAUSE_THRESHOLD,
    CRITICAL_PAUSE_THRESHOLD,
)


# ─── _fmt_time ────────────────────────────────────────────────────────────────

class TestFmtTime:
    def test_zero_seconds(self):
        assert _fmt_time(0) == "0:00"

    def test_under_one_minute(self):
        assert _fmt_time(45) == "0:45"

    def test_over_one_minute(self):
        assert _fmt_time(90) == "1:30"

    def test_over_one_hour(self):
        assert _fmt_time(3661) == "61:01"


# ─── extract_pause_signals ────────────────────────────────────────────────────

class TestExtractPauseSignals:
    def _make_segments(self, timings):
        """timings: list of (start, end, text)"""
        return [
            {"start": s, "end": e, "text": t, "avg_logprob": -0.3, "no_speech_prob": 0.01}
            for s, e, t in timings
        ]

    def test_no_pauses_returns_empty(self):
        segs = self._make_segments([(0, 2, "Hello"), (2.1, 4, "World")])
        assert extract_pause_signals(segs) == []

    def test_pause_below_threshold_not_flagged(self):
        segs = self._make_segments([(0, 2, "Hello"), (2 + SUSPICIOUS_PAUSE_THRESHOLD - 1, 15, "World")])
        pauses = extract_pause_signals(segs)
        assert pauses == []

    def test_pause_at_threshold_is_flagged(self):
        gap = SUSPICIOUS_PAUSE_THRESHOLD
        segs = self._make_segments([(0, 2, "Question text here"), (2 + gap, 20, "Answer here")])
        pauses = extract_pause_signals(segs)
        assert len(pauses) == 1
        assert pauses[0]["severity"] == "medium"

    def test_critical_pause_flagged_as_high(self):
        gap = CRITICAL_PAUSE_THRESHOLD + 5
        segs = self._make_segments([(0, 2, "Tell me about yourself"), (2 + gap, 40, "I am a...")])
        pauses = extract_pause_signals(segs)
        assert len(pauses) == 1
        assert pauses[0]["severity"] == "high"

    def test_multiple_pauses_all_returned(self):
        segs = self._make_segments([
            (0, 2, "Seg1"),
            (2 + SUSPICIOUS_PAUSE_THRESHOLD + 2, 20, "Seg2"),
            (20.1, 22, "Seg3"),
            (22 + SUSPICIOUS_PAUSE_THRESHOLD + 5, 50, "Seg4"),
        ])
        pauses = extract_pause_signals(segs)
        assert len(pauses) == 2

    def test_pause_includes_context_text(self):
        segs = self._make_segments([(0, 2, "Before text here"), (2 + 15, 20, "After text here")])
        pause = extract_pause_signals(segs)[0]
        assert "Before text here" in pause["before_text"]
        assert "After text here" in pause["after_text"]
        assert pause["at_seconds"] == 2.0
        assert pause["duration_s"] == 15.0

    def test_empty_segments_returns_empty(self):
        assert extract_pause_signals([]) == []

    def test_single_segment_returns_empty(self):
        segs = [{"start": 0, "end": 5, "text": "only", "avg_logprob": -0.2, "no_speech_prob": 0.01}]
        assert extract_pause_signals(segs) == []


# ─── extract_audio_anomalies ──────────────────────────────────────────────────

class TestExtractAudioAnomalies:
    def test_empty_segments_returns_zeros(self):
        result = extract_audio_anomalies([])
        assert result["low_confidence_count"] == 0
        assert result["total_segments"] == 0

    def test_counts_low_confidence_segments(self):
        segs = [
            {"start": 0, "end": 2, "text": "normal", "avg_logprob": -0.5, "no_speech_prob": 0.01},
            {"start": 2, "end": 4, "text": "low conf", "avg_logprob": -1.5, "no_speech_prob": 0.01},
            {"start": 4, "end": 6, "text": "very low", "avg_logprob": -2.0, "no_speech_prob": 0.01},
        ]
        result = extract_audio_anomalies(segs)
        assert result["low_confidence_count"] == 2
        assert result["total_segments"] == 3

    def test_counts_high_no_speech_segments(self):
        segs = [
            {"start": 0, "end": 2, "text": "speech", "avg_logprob": -0.3, "no_speech_prob": 0.8},
            {"start": 2, "end": 4, "text": "silence", "avg_logprob": -0.3, "no_speech_prob": 0.7},
        ]
        result = extract_audio_anomalies(segs)
        assert result["high_no_speech_count"] == 2

    def test_speech_rate_variance_calculated(self):
        segs = [
            {"start": 0, "end": 2, "text": "fast fast fast fast fast fast", "avg_logprob": -0.3, "no_speech_prob": 0.01},
            {"start": 2, "end": 4, "text": "slow", "avg_logprob": -0.3, "no_speech_prob": 0.01},
            {"start": 4, "end": 6, "text": "medium medium medium", "avg_logprob": -0.3, "no_speech_prob": 0.01},
        ]
        result = extract_audio_anomalies(segs)
        assert result["speech_rate_variance"] > 0


# ─── analyze_communication (mocked Ollama) ────────────────────────────────────

class TestAnalyzeCommunication:
    def test_empty_transcript_returns_default(self):
        result = asyncio.get_event_loop().run_until_complete(
            analyze_communication("", 30.0)
        )
        assert result["communication_score"] == 50

    def test_short_transcript_returns_default(self):
        result = asyncio.get_event_loop().run_until_complete(
            analyze_communication("Hi.", 5.0)
        )
        assert result["communication_score"] == 50

    def test_successful_ollama_response(self):
        response_body = json.dumps({
            "communication_score": 82,
            "confidence_level": "high",
            "clarity_score": 85,
            "articulation_score": 80,
            "key_phrases": ["strong background", "team collaboration"],
            "strengths": ["Clear and concise"],
            "red_flags": [],
            "summary": "Excellent communicator.",
        })
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": response_body}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.backend.services.video_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            result = asyncio.get_event_loop().run_until_complete(
                analyze_communication("I have five years of experience building large scale systems at top tech companies.", 60.0)
            )

        assert result["communication_score"] == 82
        assert result["confidence_level"] == "high"
        assert result["clarity_score"] == 85
        assert "Excellent communicator" in result["summary"]

    def test_ollama_failure_returns_default(self):
        with patch("app.backend.services.video_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
            MockClient.return_value = mock_client

            result = asyncio.get_event_loop().run_until_complete(
                analyze_communication("Some reasonable transcript with enough words here.", 60.0)
            )

        assert result["communication_score"] == 50
        assert result["confidence_level"] == "medium"

    def test_wpm_calculated_correctly(self):
        response_body = json.dumps({"communication_score": 70, "confidence_level": "medium",
                                     "clarity_score": 70, "articulation_score": 70,
                                     "key_phrases": [], "strengths": [], "red_flags": [],
                                     "summary": "OK."})
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": response_body}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.backend.services.video_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            transcript = " ".join(["word"] * 120)  # 120 words
            result = asyncio.get_event_loop().run_until_complete(
                analyze_communication(transcript, 60.0)  # 60 seconds = 1 minute
            )

        assert result["words_per_minute"] == 120


# ─── analyze_malpractice (mocked Ollama) ─────────────────────────────────────

class TestAnalyzeMalpractice:
    def test_empty_transcript_uses_pause_based_default(self):
        pauses = [
            {"at_seconds": 30, "duration_s": 20, "before_text": "What is Python?", "after_text": "Python is...", "severity": "high", "formatted_at": "0:30"},
            {"at_seconds": 90, "duration_s": 15, "before_text": "Any experience?", "after_text": "Yes indeed", "severity": "medium", "formatted_at": "1:30"},
        ]
        result = asyncio.get_event_loop().run_until_complete(
            analyze_malpractice("", pauses, {"low_confidence_count": 0, "high_no_speech_count": 0, "speech_rate_variance": 0, "total_segments": 0}, 60)
        )
        assert result["pause_count"] == 2
        assert result["malpractice_risk"] == "medium"
        assert any(f["type"] == "suspicious_pause" for f in result["flags"])

    def test_successful_malpractice_analysis_low_risk(self):
        response_body = json.dumps({
            "malpractice_score": 10,
            "malpractice_risk": "low",
            "reliability_rating": "trustworthy",
            "flags": [],
            "positive_signals": ["Natural hesitation", "Self-corrections"],
            "overall_assessment": "No malpractice detected.",
            "follow_up_questions": [],
        })
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": response_body}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.backend.services.video_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            result = asyncio.get_event_loop().run_until_complete(
                analyze_malpractice(
                    "I um, yeah so basically I have about five years of, uh, experience.",
                    [],
                    {"low_confidence_count": 0, "high_no_speech_count": 0, "speech_rate_variance": 0.5, "total_segments": 5},
                    60,
                )
            )

        assert result["malpractice_score"] == 10
        assert result["malpractice_risk"] == "low"
        assert result["reliability_rating"] == "trustworthy"
        assert len(result["positive_signals"]) == 2

    def test_high_risk_malpractice_with_pauses_merged(self):
        response_body = json.dumps({
            "malpractice_score": 85,
            "malpractice_risk": "high",
            "reliability_rating": "unreliable",
            "flags": [{"type": "scripted_reading", "severity": "high", "evidence": "No filler words", "recommendation": "Ask follow-ups"}],
            "positive_signals": [],
            "overall_assessment": "High risk of malpractice.",
            "follow_up_questions": ["Explain your methodology in detail."],
        })
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": response_body}
        mock_resp.raise_for_status = MagicMock()
        pauses = [{"at_seconds": 45, "duration_s": 30, "before_text": "explain", "after_text": "sure", "severity": "high", "formatted_at": "0:45"}]

        with patch("app.backend.services.video_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            result = asyncio.get_event_loop().run_until_complete(
                analyze_malpractice(
                    "Every answer is perfectly structured with no hesitation whatsoever.",
                    pauses,
                    {"low_confidence_count": 3, "high_no_speech_count": 0, "speech_rate_variance": 0.1, "total_segments": 10},
                    120,
                )
            )

        assert result["malpractice_risk"] == "high"
        # Pause flags should be merged in
        pause_flags = [f for f in result["flags"] if f["type"] == "suspicious_pause"]
        assert len(pause_flags) >= 1

    def test_ollama_failure_returns_pause_default(self):
        pauses = [{"at_seconds": 30, "duration_s": 15, "before_text": "Q", "after_text": "A", "severity": "medium", "formatted_at": "0:30"}]
        with patch("app.backend.services.video_service.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=Exception("timeout"))
            MockClient.return_value = mock_client

            result = asyncio.get_event_loop().run_until_complete(
                analyze_malpractice("Some transcript text.", pauses,
                                    {"low_confidence_count": 0, "high_no_speech_count": 0, "speech_rate_variance": 0, "total_segments": 3}, 60)
            )

        assert result["pause_count"] == 1
        assert result["malpractice_risk"] in ("low", "medium", "high")


# ─── Default helpers ──────────────────────────────────────────────────────────

class TestDefaults:
    def test_default_communication_has_required_keys(self):
        result = _default_communication(130)
        assert "communication_score" in result
        assert "confidence_level" in result
        assert result["words_per_minute"] == 130

    def test_default_malpractice_no_pauses_is_low_risk(self):
        result = _default_malpractice([])
        assert result["malpractice_risk"] == "low"
        assert result["flags"] == []

    def test_default_malpractice_with_pauses_is_medium_risk(self):
        pauses = [
            {"at_seconds": 10, "duration_s": 15, "before_text": "A", "after_text": "B", "severity": "medium", "formatted_at": "0:10"},
            {"at_seconds": 60, "duration_s": 18, "before_text": "C", "after_text": "D", "severity": "medium", "formatted_at": "1:00"},
        ]
        result = _default_malpractice(pauses)
        assert result["malpractice_risk"] == "medium"
        assert len(result["flags"]) == 2
