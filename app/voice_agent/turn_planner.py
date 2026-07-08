"""
Unified Turn Planner — one LLM call per candidate answer.

Combines answer evaluation and next-question generation into a single request
to cut voice latency roughly in half vs sequential evaluator + planner calls.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.voice_agent.answer_evaluator import AnswerEvaluator
from app.voice_agent.question_planner import QuestionPlanner
from app.voice_agent.voice_llm import generate_json

logger = logging.getLogger("voice_agent.turn_planner")

SYSTEM_PROMPT = (
    "You are an expert phone interviewer. Return valid JSON only. "
    "Keep spoken lines conversational and under 30 words."
)


class TurnPlanner:
    """Evaluate an answer and plan the next question in one LLM round-trip."""

    def __init__(self) -> None:
        self._evaluator = AnswerEvaluator()
        self._planner = QuestionPlanner()

    async def plan_next_turn(
        self,
        *,
        question: str,
        answer: str,
        stage: str,
        context: dict[str, Any],
        conversation_history: list[dict[str, str]],
        answer_scores: list[int],
        questions_asked: list[str],
        time_remaining_s: int,
    ) -> dict[str, Any]:
        if not answer.strip() or len(answer.strip()) < 5:
            evaluation = await self._evaluator.evaluate(question, answer, stage, context)
            next_q = self._planner._fallback_question(stage, context, questions_asked)
            return {
                **evaluation,
                "question": next_q["question"],
                "category": next_q.get("category", stage),
                "context": next_q.get("context", ""),
            }

        candidate = context.get("candidate", {})
        role = context.get("role", {})
        resume_skills = candidate.get("parsed_skills", [])[:10]
        required_skills = role.get("required_skills", [])[:5]
        work_exp = candidate.get("parsed_work_experience", [])[:3]
        recent_qa = "\n".join(
            f"Q: {turn.get('question', '')}\nA: {turn.get('answer', '')[:200]}"
            for turn in conversation_history[-3:]
        )
        asked = "\n".join(f"- {q}" for q in questions_asked[-10:])
        score_trend = answer_scores[-5:] if answer_scores else []
        avg_score = sum(score_trend) / len(score_trend) if score_trend else 50

        prompt = f"""Evaluate the candidate's answer and generate the next interview question.

INTERVIEW STAGE: {stage}
QUESTION ASKED: {question}
CANDIDATE'S ANSWER: {answer}

CANDIDATE: {candidate.get('name', 'Candidate')}
ROLE: {role.get('title', 'the position')}
REQUIRED SKILLS: {', '.join(str(s) for s in required_skills)}
CANDIDATE SKILLS: {', '.join(str(s) for s in resume_skills)}
WORK EXPERIENCE: {json.dumps(work_exp, default=str)[:500]}

RECENT Q&A:
{recent_qa}

QUESTIONS ALREADY ASKED (do not repeat):
{asked}

CANDIDATE PERFORMANCE: avg score={avg_score:.0f}
TIME REMAINING: {time_remaining_s // 60} minutes

Return ONLY JSON:
{{
  "score": 0-100,
  "reasoning": "1-2 sentences",
  "difficulty_adjustment": "harder" | "same" | "simpler" | "switch_topic",
  "key_points": ["..."],
  "concerns": ["..."],
  "question": "next question, conversational, under 30 words, no transition phrase"
}}

Rules for difficulty_adjustment:
- score > 80: harder
- score 40-80: same
- score < 40: simpler
- candidate clearly doesn't know topic: switch_topic
"""

        parsed = await generate_json(
            prompt,
            system=SYSTEM_PROMPT,
            max_output_tokens=384,
            temperature=0.35,
        )
        if parsed and parsed.get("question"):
            return self._normalize(parsed, stage)

        logger.warning("Turn planner LLM failed — using local fallback")
        evaluation = self._evaluator._heuristic_evaluate(question, answer, stage)
        next_q = self._local_fallback_question(
            question=question,
            answer=answer,
            stage=stage,
            context=context,
            questions_asked=questions_asked,
        )
        return {**evaluation, **next_q}

    def _local_fallback_question(
        self,
        *,
        question: str,
        answer: str,
        stage: str,
        context: dict[str, Any],
        questions_asked: list[str],
    ) -> dict[str, Any]:
        """Rule-based next question when all LLM providers fail — never repeat verbatim."""
        word_count = len(answer.split())
        role = context.get("role", {})
        skills = role.get("required_skills", []) or []
        skill = str(skills[0]) if skills else "your core skills"

        if word_count >= 10 and question.strip() in [q.strip() for q in questions_asked]:
            follow_ups = {
                "resume_verification": (
                    "Thanks for sharing that. What was your biggest accomplishment in that role?"
                ),
                "technical": (
                    f"Got it. Can you describe a specific project where you used {skill}?"
                ),
                "behavioral": (
                    "Understood. What was the outcome, and what would you do differently next time?"
                ),
            }
            text = follow_ups.get(
                stage,
                "Thanks for explaining. Can you give me one concrete example from that experience?",
            )
        elif word_count >= 10:
            text = (
                f"Thanks. Building on that, how have you applied {skill} in your recent work?"
            )
        else:
            next_q = self._planner._fallback_question(stage, context, questions_asked)
            return next_q

        return {
            "question": text,
            "category": stage,
            "context": "Local fallback — LLM unavailable.",
            "expected_duration_s": 120,
        }

    def _normalize(self, parsed: dict[str, Any], stage: str) -> dict[str, Any]:
        score = max(0, min(100, int(parsed.get("score", 50))))
        adjustment = parsed.get("difficulty_adjustment", "same")
        if adjustment not in ("harder", "same", "simpler", "switch_topic"):
            adjustment = "harder" if score > 80 else "simpler" if score < 40 else "same"

        question = str(parsed.get("question", "")).strip()
        return {
            "score": score,
            "reasoning": str(parsed.get("reasoning", "")).strip(),
            "difficulty_adjustment": adjustment,
            "key_points": list(parsed.get("key_points", []))[:5],
            "concerns": list(parsed.get("concerns", []))[:3],
            "question": question,
            "category": str(parsed.get("category", stage)).strip() or stage,
            "context": str(parsed.get("context", "")).strip(),
            "expected_duration_s": 120,
        }
