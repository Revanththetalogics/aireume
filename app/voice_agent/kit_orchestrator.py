"""
Kit-Driven Interview Orchestrator — asks pre-generated interview kit questions.

Pre-generated spoken lines from kit v3; light in-call LLM only for follow-ups
and thread transitions (TurnPersonalizer).
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app.voice_agent.orchestrator import InterviewStage, OrchestratorContext

logger = logging.getLogger("voice_agent.kit_orchestrator")

_CATEGORY_INTROS = {
    "technical": "Now let's dive into some technical questions. ",
    "behavioral": "I'd like to understand how you handle real-world situations. ",
    "culture_fit": "Let's talk about your motivation for this role. ",
    "experience_deep_dive": "I'd like to dig deeper into your experience. ",
}

_MIN_ANSWER_WORDS = 10

_THIN_ANSWER_MARKERS = {
    "yes", "yeah", "yep", "sure", "okay", "ok",
    "no", "nope", "nah",
    "not sure", "i don't know", "dont know", "no idea",
}

_TRANSITION_PHRASES = [
    "Thanks for sharing. ",
    "Got it. ",
    "Understood. ",
]


@dataclass
class KitQuestion:
    id: str
    category: str
    text: str
    spoken_text: str = ""
    intent: str = ""
    thread_id: str = ""
    what_to_listen_for: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    follow_up_intents: list[str] = field(default_factory=list)
    probe_target: dict[str, Any] = field(default_factory=dict)
    scoring_criteria: dict[str, str] = field(default_factory=dict)


class KitDrivenOrchestrator:
    """Walks through a pre-built interview kit during a phone screen."""

    _CONSENT_POSITIVE = {"yes", "yeah", "sure", "okay", "ok", "yep", "go ahead", "i consent"}
    _CONSENT_NEGATIVE = {"no", "nope", "don't", "not now", "i don't consent"}
    _RESCHEDULE_MARKERS = ["not a good time", "can we reschedule", "call back later", "busy right now"]

    def __init__(
        self,
        ctx: OrchestratorContext,
        kit_questions: list[dict[str, Any]],
        *,
        thread_transitions: dict[str, str] | None = None,
    ):
        self.ctx = ctx
        self.questions = [self._to_kit_question(q) for q in kit_questions if q.get("text")]
        self.thread_transitions = thread_transitions or {}
        self._introduction_step = 0
        self._question_index = 0
        self._awaiting_follow_up = False
        self._current_follow_up: Optional[str] = None
        self._pending_follow_up_generation = False
        self._last_category: Optional[str] = None
        self._last_thread_id: Optional[str] = None
        self._current_question: Optional[KitQuestion] = None
        self._last_answer_snippet: str = ""
        self.ctx.current_stage = InterviewStage.INTRODUCTION

    @staticmethod
    def _to_kit_question(raw: dict[str, Any]) -> KitQuestion:
        spoken = str(raw.get("spoken_text") or raw.get("text", "")).strip()
        text = spoken or str(raw.get("text", "")).strip()
        intents = [str(i) for i in (raw.get("follow_up_intents") or []) if str(i).strip()]
        return KitQuestion(
            id=str(raw.get("id", "")),
            category=str(raw.get("category", "technical")),
            text=text,
            spoken_text=spoken or text,
            intent=str(raw.get("intent") or text).strip(),
            thread_id=str(raw.get("thread_id") or raw.get("category_key") or ""),
            what_to_listen_for=list(raw.get("what_to_listen_for") or []),
            follow_ups=[f for f in (raw.get("follow_ups") or []) if str(f).strip()],
            follow_up_intents=intents,
            probe_target=dict(raw.get("probe_target") or {}),
            scoring_criteria=dict(raw.get("scoring_criteria") or {}),
        )

    def _score_answer(self, question: KitQuestion, answer: str, *, is_thin: bool) -> dict[str, Any]:
        """Score answer against kit rubric (strong / adequate / weak)."""
        from app.backend.services.consolidated_recommendation import rubric_to_score

        if is_thin:
            return {"score": 25, "rubric_rating": "weak", "reasoning": "Answer too brief."}

        word_count = len(answer.split())
        lower = answer.lower()
        example_markers = ["for example", "for instance", "in my project", "at my previous", "i built", "i led"]
        has_example = any(m in lower for m in example_markers)

        if word_count >= 60 and has_example:
            rubric = "strong"
        elif word_count >= 25 or has_example:
            rubric = "adequate"
        else:
            rubric = "weak"

        return {
            "score": rubric_to_score(rubric),
            "rubric_rating": rubric,
            "reasoning": f"Rubric={rubric}, words={word_count}, examples={has_example}",
        }

    def should_play_filler(self) -> bool:
        return self._pending_follow_up_generation

    def pick_filler(self) -> str:
        from app.voice_agent.speech_pipeline import pick_immediate_ack

        return pick_immediate_ack()

    async def start(self) -> str:
        self.ctx.started_at = time.time()
        greeting = self._intro_message(0)
        self._record_bot(greeting, "introduction")
        return greeting

    def _intro_message(self, step: int) -> str:
        from app.backend.services.interview_opening_service import (
            resolve_consent_for_call,
            resolve_opening_for_call,
        )

        opening_config = {
            "use_custom_interview_opening": self.ctx.use_custom_interview_opening,
            "interview_opening_script": self.ctx.interview_opening_script,
            "consent_script": self.ctx.consent_script,
            "company_name": self.ctx.company_name,
            "bot_name": self.ctx.bot_name,
        }

        if step == 0:
            return resolve_opening_for_call(
                opening_config,
                candidate_name=self.ctx.candidate_name,
                role_title=self.ctx.jd_title,
            )
        if step == 1:
            return resolve_consent_for_call(
                opening_config,
                candidate_name=self.ctx.candidate_name,
                role_title=self.ctx.jd_title,
            )
        return ""

    def _record_bot(self, text: str, stage: str) -> None:
        self.ctx.transcript.append(
            {"speaker": "bot", "text": text, "timestamp": self.ctx.elapsed, "stage": stage}
        )

    def _record_candidate(self, text: str, stage: str) -> None:
        self.ctx.transcript.append(
            {"speaker": "candidate", "text": text, "timestamp": self.ctx.elapsed, "stage": stage}
        )

    async def handle_candidate_response(self, text: str) -> Optional[str]:
        text = (text or "").strip()
        if not text:
            return "I didn't quite catch that. Could you repeat what you said?"

        if self.ctx.current_stage == InterviewStage.INTRODUCTION:
            return await self._handle_introduction(text)

        if self.ctx.current_stage in (InterviewStage.CLOSING, InterviewStage.ENDED):
            return await self._handle_closing(text)

        return await self._handle_kit_answer(text)

    async def _handle_introduction(self, text: str) -> Optional[str]:
        lower = text.lower().strip()
        self._record_candidate(text, "introduction")

        if self._introduction_step == 0:
            if any(m in lower for m in self._RESCHEDULE_MARKERS):
                self.ctx.current_stage = InterviewStage.ENDED
                msg = "No problem at all. We'll reach out at a better time. Thank you!"
                self._record_bot(msg, "introduction")
                return msg
            self._introduction_step = 1
            msg = self._intro_message(1)
            self._record_bot(msg, "introduction")
            return msg

        if self._introduction_step == 1:
            if any(w in lower for w in self._CONSENT_POSITIVE):
                self.ctx.consent_recorded = True
                return await self._start_kit_questions()
            if any(w in lower for w in self._CONSENT_NEGATIVE):
                self.ctx.current_stage = InterviewStage.ENDED
                msg = (
                    "I understand. Unfortunately, I cannot proceed without recording consent. "
                    "Thank you for your time. Goodbye."
                )
                self._record_bot(msg, "introduction")
                return msg
            return "I'm sorry, I didn't quite catch that. Do you consent to this call being recorded? Please say yes or no."

        return await self._start_kit_questions()

    async def _start_kit_questions(self) -> Optional[str]:
        if not self.questions:
            self.ctx.current_stage = InterviewStage.CLOSING
            msg = (
                "Thank you for your time today. We have everything we need for now. "
                "We'll be in touch with next steps soon."
            )
            self._record_bot(msg, "closing")
            return msg

        self.ctx.current_stage = InterviewStage.TECHNICAL
        self._question_index = 0
        return self._ask_current_question()

    def _ask_current_question(self) -> Optional[str]:
        if self._question_index >= len(self.questions):
            return self._start_closing()

        question = self.questions[self._question_index]
        self._current_question = question
        self._awaiting_follow_up = False
        self._current_follow_up = None

        prefix = ""
        if question.thread_id and question.thread_id != self._last_thread_id:
            key = f"{self._last_thread_id}->{question.thread_id}" if self._last_thread_id else ""
            transition = self.thread_transitions.get(key, "")
            if transition:
                prefix = transition + " "
            elif question.category != self._last_category:
                prefix = _CATEGORY_INTROS.get(question.category, "")
            self._last_thread_id = question.thread_id
            self._last_category = question.category
        elif question.category != self._last_category:
            prefix = _CATEGORY_INTROS.get(question.category, "")
            self._last_category = question.category
        elif self._question_index > 0:
            prefix = random.choice(_TRANSITION_PHRASES)

        response = prefix + self._spoken_question(question)
        self._record_bot(response, question.category)
        return response

    def _spoken_question(self, question: KitQuestion) -> str:
        """Prefer pre-personalized spoken_text from kit v3."""
        text = question.spoken_text or question.text
        swaps = (
            ("Walk me through", "Can you walk me through"),
            ("You list", "I see you list"),
            ("isn't on your resume", "doesn't appear on your resume"),
        )
        for src, dst in swaps:
            if text.startswith(src):
                return dst + text[len(src):]
        return text

    async def _resolve_follow_up(self, question: KitQuestion, answer: str) -> Optional[str]:
        from app.voice_agent.turn_personalizer import answer_has_specifics, phrase_follow_up

        if answer_has_specifics(answer):
            return None
        intents = question.follow_up_intents or question.follow_ups
        if not intents:
            return None
        intent = str(intents[0])
        self._pending_follow_up_generation = True
        try:
            follow_up = await phrase_follow_up(
                intent=intent,
                last_question=question.spoken_text or question.text,
                last_answer=answer,
                candidate_name=self.ctx.candidate_name,
                probe_target=question.probe_target or None,
            )
        finally:
            self._pending_follow_up_generation = False
        return follow_up or intent

    async def _handle_kit_answer(self, text: str) -> Optional[str]:
        question = self._current_question
        if question is None:
            return self._ask_current_question()

        self._record_candidate(text, question.category)
        word_count = len(text.split())
        lower = text.lower().strip()
        is_thin = (
            word_count < _MIN_ANSWER_WORDS
            or lower in _THIN_ANSWER_MARKERS
            or (word_count <= 4 and "?" not in text)
        )

        evaluation = self._score_answer(question, text, is_thin=is_thin)

        entry = {
            "stage": question.category,
            "question_id": question.id,
            "question": question.text,
            "intent": question.intent,
            "answer": text,
            "score": evaluation["score"],
            "rubric_rating": evaluation["rubric_rating"],
            "score_reasoning": evaluation["reasoning"],
            "what_to_listen_for": question.what_to_listen_for,
            "scoring_criteria": question.scoring_criteria,
            "is_follow_up": bool(self._awaiting_follow_up),
            "follow_up_text": self._current_follow_up,
            "timestamp": self.ctx.elapsed,
        }
        self.ctx.questions_responses.append(entry)
        if hasattr(self.ctx, "answer_scores"):
            self.ctx.answer_scores.append(evaluation["score"])

        self._last_answer_snippet = text[:200]

        if not self._awaiting_follow_up:
            needs_follow_up = is_thin or not self._answer_is_specific(text)
            if needs_follow_up:
                follow_up = await self._resolve_follow_up(question, text)
                if follow_up:
                    self._awaiting_follow_up = True
                    self._current_follow_up = follow_up
                    self._record_bot(follow_up, question.category)
                    return follow_up

        self._awaiting_follow_up = False
        self._current_follow_up = None
        self._question_index += 1

        if self.ctx.time_remaining < 45 and self._question_index < len(self.questions):
            return self._start_closing()

        if self._question_index >= len(self.questions):
            return self._start_closing()

        return self._ask_current_question()

    def _start_closing(self) -> str:
        self.ctx.current_stage = InterviewStage.CLOSING
        name = self.ctx.candidate_name.split()[0] if self.ctx.candidate_name else ""
        name_clause = f", {name}" if name else ""
        msg = (
            f"Thank you for your time today{name_clause}. "
            f"We'll review your responses and be in touch with next steps within a few days. "
            f"Have a great day!"
        )
        self._record_bot(msg, "closing")
        return msg

    async def _handle_closing(self, text: str) -> Optional[str]:
        if text.strip():
            self._record_candidate(text, "closing")
        self.ctx.current_stage = InterviewStage.ENDED
        return None

    def force_closing_message(self) -> Optional[str]:
        """Speak a farewell when the call ends abruptly (e.g. time budget)."""
        if self.ctx.current_stage == InterviewStage.ENDED:
            return None
        if self.ctx.current_stage == InterviewStage.CLOSING:
            self.ctx.current_stage = InterviewStage.ENDED
            return None
        msg = self._start_closing()
        self.ctx.current_stage = InterviewStage.ENDED
        return msg

    def is_complete(self) -> bool:
        return self.ctx.current_stage == InterviewStage.ENDED

    def get_result(self) -> dict[str, Any]:
        result = {
            "session_id": self.ctx.session_id,
            "duration_seconds": int(self.ctx.elapsed),
            "consent_recorded": self.ctx.consent_recorded,
            "transcript": self.ctx.transcript,
            "questions_responses": self.ctx.questions_responses,
            "answer_scores": self.ctx.answer_scores,
            "avg_answer_score": (
                sum(self.ctx.answer_scores) / len(self.ctx.answer_scores)
                if self.ctx.answer_scores
                else 0
            ),
            "resume_inconsistencies": self.ctx.resume_inconsistencies,
            "communication_metrics": {},
            "completion_reason": "kit_complete",
            "stages_completed": list({qr.get("stage") for qr in self.ctx.questions_responses}),
            "interview_mode": "kit_driven",
            "kit_question_count": len(self.questions),
            "kit_questions_answered": len(self.ctx.questions_responses),
        }
        telemetry = getattr(self.ctx, "turn_telemetry", None)
        if telemetry is not None and hasattr(telemetry, "as_result_payload"):
            result["turn_telemetry"] = telemetry.as_result_payload()
        return result

    @staticmethod
    def _answer_is_specific(text: str) -> bool:
        from app.voice_agent.turn_personalizer import answer_has_specifics

        return answer_has_specifics(text)
