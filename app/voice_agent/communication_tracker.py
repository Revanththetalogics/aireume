"""
Communication Metrics Tracker — real-time communication analysis during interview.

Tracks per-answer and aggregate metrics:
- Speaking speed (words/min)
- Filler word count
- Silence duration
- Answer length
- Confidence indicators
- Interruption detection
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("voice_agent.comm_tracker")

FILLER_WORDS = {"um", "uh", "like", "you know", "sort of", "kind of", "basically", "actually", "literally"}
CONFIDENCE_MARKERS = {"absolutely", "definitely", "certainly", "i'm confident", "i know", "in my experience"}
HESITATION_MARKERS = {"i think", "maybe", "i'm not sure", "i guess", "perhaps", "possibly"}


@dataclass
class AnswerMetrics:
    """Metrics for a single candidate answer."""
    question: str = ""
    answer: str = ""
    answer_start_time: float = 0.0
    answer_end_time: float = 0.0
    word_count: int = 0
    speaking_speed_wpm: float = 0.0
    filler_count: int = 0
    filler_words_used: list[str] = field(default_factory=list)
    confidence_markers: list[str] = field(default_factory=list)
    hesitation_markers: list[str] = field(default_factory=list)
    silence_before_answer_s: float = 0.0
    answer_duration_s: float = 0.0
    confidence_score: int = 50  # 0-100


@dataclass
class AggregateMetrics:
    """Aggregate communication metrics across the entire interview."""
    total_answers: int = 0
    total_words: int = 0
    avg_speaking_speed_wpm: float = 0.0
    avg_answer_length: float = 0.0
    total_fillers: int = 0
    avg_silence_before_answer: float = 0.0
    confidence_trend: list[int] = field(default_factory=list)
    speaking_speed_trend: list[float] = field(default_factory=list)
    overall_confidence_score: int = 50


class CommunicationTracker:
    """
    Tracks communication metrics in real-time during the interview.

    Call record_answer() after each candidate response to accumulate metrics.
    Call get_aggregate_metrics() at the end for the full picture.
    """

    def __init__(self):
        self._answers: list[AnswerMetrics] = []
        self._question_end_time: float = 0.0

    def record_question_end(self) -> None:
        """Call when the bot finishes speaking a question (to measure silence before answer)."""
        self._question_end_time = time.time()

    def record_answer(self, question: str, answer: str, answer_start_time: float | None = None) -> AnswerMetrics:
        """
        Record a candidate's answer and compute communication metrics.

        Args:
            question: The question that was asked
            answer: The candidate's transcribed answer
            answer_start_time: When the candidate started speaking (optional, defaults to now)
        """
        now = time.time()
        if answer_start_time is None:
            answer_start_time = now

        answer_duration = max(0.1, now - answer_start_time)
        silence_before = max(0.0, answer_start_time - self._question_end_time) if self._question_end_time > 0 else 0.0

        words = answer.split()
        word_count = len(words)
        speaking_speed = (word_count / answer_duration) * 60 if answer_duration > 0 else 0

        answer_lower = answer.lower()
        fillers_used = [w for w in FILLER_WORDS if w in answer_lower]
        confidence_used = [w for w in CONFIDENCE_MARKERS if w in answer_lower]
        hesitation_used = [w for w in HESITATION_MARKERS if w in answer_lower]

        # Confidence score calculation
        confidence = 50
        if word_count > 50:
            confidence += 10
        if confidence_used:
            confidence += 15
        if hesitation_used:
            confidence -= 10
        if len(fillers_used) > 3:
            confidence -= 10
        if silence_before > 5.0:
            confidence -= 5  # Long pause may indicate uncertainty
        confidence = max(0, min(100, confidence))

        metrics = AnswerMetrics(
            question=question,
            answer=answer,
            answer_start_time=answer_start_time,
            answer_end_time=now,
            word_count=word_count,
            speaking_speed_wpm=round(speaking_speed, 1),
            filler_count=len(fillers_used),
            filler_words_used=fillers_used,
            confidence_markers=confidence_used,
            hesitation_markers=hesitation_used,
            silence_before_answer_s=round(silence_before, 2),
            answer_duration_s=round(answer_duration, 2),
            confidence_score=confidence,
        )

        self._answers.append(metrics)
        logger.info(
            "Comm metrics: %d words, %.0f wpm, %d fillers, confidence=%d, silence=%.1fs",
            word_count, speaking_speed, len(fillers_used), confidence, silence_before,
        )
        return metrics

    def get_aggregate_metrics(self) -> AggregateMetrics:
        """Compute aggregate communication metrics across all answers."""
        if not self._answers:
            return AggregateMetrics()

        total_words = sum(a.word_count for a in self._answers)
        total_fillers = sum(a.filler_count for a in self._answers)
        avg_speed = sum(a.speaking_speed_wpm for a in self._answers) / len(self._answers)
        avg_length = total_words / len(self._answers)
        avg_silence = sum(a.silence_before_answer_s for a in self._answers) / len(self._answers)
        confidence_trend = [a.confidence_score for a in self._answers]
        speed_trend = [a.speaking_speed_wpm for a in self._answers]
        overall_confidence = sum(confidence_trend) // len(confidence_trend)

        return AggregateMetrics(
            total_answers=len(self._answers),
            total_words=total_words,
            avg_speaking_speed_wpm=round(avg_speed, 1),
            avg_answer_length=round(avg_length, 1),
            total_fillers=total_fillers,
            avg_silence_before_answer=round(avg_silence, 2),
            confidence_trend=confidence_trend,
            speaking_speed_trend=speed_trend,
            overall_confidence_score=overall_confidence,
        )

    def get_per_answer_metrics(self) -> list[dict[str, Any]]:
        """Return per-answer metrics as dicts for storage/API."""
        return [
            {
                "question": a.question,
                "answer": a.answer,
                "word_count": a.word_count,
                "speaking_speed_wpm": a.speaking_speed_wpm,
                "filler_count": a.filler_count,
                "filler_words": a.filler_words_used,
                "confidence_markers": a.confidence_markers,
                "hesitation_markers": a.hesitation_markers,
                "silence_before_answer_s": a.silence_before_answer_s,
                "answer_duration_s": a.answer_duration_s,
                "confidence_score": a.confidence_score,
            }
            for a in self._answers
        ]
