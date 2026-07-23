"""Evaluation agents — assess interview responses across dimensions."""

import logging
from typing import Any

from app.backend.services.recruiter.llm_client import generate_recruiter_json

logger = logging.getLogger("aria.recruiter")


def _format_transcript(transcript: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"{'Interviewer' if t.get('speaker') == 'bot' else 'Candidate'}: {t.get('text', '')}"
        for t in transcript
    )


async def _call_evaluator_llm(prompt: str, num_predict: int = 1024) -> dict[str, Any] | None:
    return await generate_recruiter_json(
        prompt,
        max_output_tokens=num_predict,
        temperature=0.2,
    )


def _format_qa_pairs(questions_responses: list[dict[str, Any]]) -> str:
    lines = []
    for item in questions_responses:
        if not isinstance(item, dict):
            continue
        q = item.get("question", "")
        a = item.get("response", "")
        category = item.get("category", "")
        lines.append(f"[{category}] Q: {q}\nA: {a}")
    return "\n\n".join(lines)


def _format_hypotheses_block(jd_context: dict[str, Any]) -> str:
    hypotheses = jd_context.get("hypotheses") or []
    lines = []
    for h in hypotheses[:6]:
        if isinstance(h, dict) and h.get("label"):
            lines.append(f"- {h.get('label')}")
    if not lines:
        return ""
    return "HYPOTHESES TO VALIDATE:\n" + "\n".join(lines) + "\n"


class TechnicalEvaluator:
    """Evaluates technical dimension from interview responses."""

    async def evaluate(
        self,
        questions_responses: list[dict[str, Any]],
        jd_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        LLM evaluates technical answers against JD requirements.
        Falls back to deterministic scoring if LLM unavailable.
        """
        required_skills = jd_context.get("required_skills", [])
        qa_text = _format_qa_pairs(questions_responses)
        hypothesis_block = _format_hypotheses_block(jd_context)

        prompt = f"""You are a technical interviewer evaluating a candidate.
{hypothesis_block}
REQUIRED SKILLS: {', '.join(str(s) for s in required_skills)}

INTERVIEW Q&A:
{qa_text[:4000]}

Return ONLY a JSON object:
{{
  "score": 0-100,
  "evidence": ["specific quote or observation 1", "..."],
  "strengths": ["strength 1", "..."],
  "gaps": ["gap 1", "..."]
}}

JSON:"""

        parsed = await _call_evaluator_llm(prompt, num_predict=1024)
        if parsed:
            return self._normalize(parsed)

        return self._deterministic_fallback(questions_responses, required_skills)

    def _normalize(self, parsed: dict[str, Any]) -> dict[str, Any]:
        return {
            "score": min(100, max(0, int(parsed.get("score", 50)))),
            "evidence": parsed.get("evidence", [])[:5],
            "strengths": parsed.get("strengths", [])[:5],
            "gaps": parsed.get("gaps", [])[:5],
        }

    def _deterministic_fallback(
        self,
        questions_responses: list[dict[str, Any]],
        required_skills: list[str],
    ) -> dict[str, Any]:
        answered = [qr for qr in questions_responses if isinstance(qr, dict) and qr.get("response")]
        technical = [
            qr for qr in answered
            if isinstance(qr, dict) and qr.get("category") == "technical"
        ]

        score = 50
        if technical:
            score = 60
            for qr in technical:
                response = str(qr.get("response", "")).lower()
                for skill in required_skills:
                    if self._normalize_skill(skill) in response:
                        score += 5

        score = min(100, score)

        return {
            "score": score,
            "evidence": [f"{len(technical)} technical questions answered"],
            "strengths": ["Technical answers provided"] if technical else [],
            "gaps": ["Could not perform deep LLM evaluation"] if score < 60 else [],
        }

    def _normalize_skill(self, skill: Any) -> str:
        if isinstance(skill, dict):
            return str(skill.get("skill", "")).lower().strip()
        return str(skill).lower().strip()


class BehavioralEvaluator:
    """Evaluates behavioral dimension."""

    async def evaluate(
        self,
        questions_responses: list[dict[str, Any]],
        role_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Evaluates STAR responses, leadership, teamwork, problem-solving.
        """
        qa_text = _format_qa_pairs(questions_responses)
        title = role_context.get("title", "the position")

        prompt = f"""You are a behavioral interviewer evaluating a candidate for {title}.

INTERVIEW Q&A:
{qa_text[:4000]}

Return ONLY a JSON object:
{{
  "score": 0-100,
  "evidence": ["STAR example or behavioral observation 1", "..."],
  "patterns": ["pattern 1: description", "..."]
}}

JSON:"""

        parsed = await _call_evaluator_llm(prompt, num_predict=1024)
        if parsed:
            return self._normalize(parsed)

        return self._deterministic_fallback(questions_responses)

    def _normalize(self, parsed: dict[str, Any]) -> dict[str, Any]:
        return {
            "score": min(100, max(0, int(parsed.get("score", 50)))),
            "evidence": parsed.get("evidence", [])[:5],
            "patterns": parsed.get("patterns", [])[:5],
        }

    def _deterministic_fallback(
        self,
        questions_responses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        behavioral = [
            qr for qr in questions_responses
            if isinstance(qr, dict) and qr.get("category") == "behavioral" and qr.get("response")
        ]
        score = 55 if behavioral else 40
        return {
            "score": score,
            "evidence": [f"{len(behavioral)} behavioral responses available"] if behavioral else ["No behavioral responses available"],
            "patterns": ["Deterministic fallback: limited pattern detection"] if not behavioral else [],
        }


class CommunicationEvaluator:
    """Evaluates communication quality from transcript patterns."""

    async def evaluate(
        self,
        transcript: list[dict[str, Any]],
        response_patterns: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Evaluates clarity, conciseness, articulation, active listening.
        """
        candidate_turns = [
            t.get("text", "") for t in transcript
            if isinstance(t, dict) and t.get("speaker") != "bot"
        ]

        total_words = sum(len(str(t).split()) for t in candidate_turns)
        avg_words = total_words / len(candidate_turns) if candidate_turns else 0

        # Basic heuristics
        score = 60
        observations = []

        if avg_words > 80:
            observations.append("Responses tend to be long; may need more conciseness.")
            score -= 10
        elif avg_words < 15:
            observations.append("Responses are very brief; may lack depth.")
            score -= 10
        else:
            observations.append("Response length appears balanced.")
            score += 10

        # Look for clarifying questions / acknowledgments
        acknowledgment_words = {"yes", "sure", "absolutely", "got it", "makes sense", "understood"}
        ack_count = sum(
            1 for t in candidate_turns
            if any(w in str(t).lower() for w in acknowledgment_words)
        )
        if ack_count >= len(candidate_turns) / 3:
            observations.append("Candidate shows active listening signals.")
            score += 10

        # Hesitation markers
        hesitation = {"um", "uh", "like", "you know"}
        hes_count = sum(
            str(t).lower().count(f" {h} ") for t in candidate_turns for h in hesitation
        )
        if hes_count > 5:
            observations.append("Frequent filler words detected.")
            score -= 10

        score = min(100, max(0, score))

        # Optional LLM refinement
        prompt = f"""You are assessing communication quality from a transcript.

CANDIDATE TURNS:
{' '.join(candidate_turns)[:2000]}

Return ONLY a JSON object:
{{
  "score": 0-100,
  "evidence": ["observation 1", "..."],
  "observations": ["observation 1", "..."]
}}

JSON:"""

        parsed = await _call_evaluator_llm(prompt, num_predict=512)
        if parsed:
            return {
                "score": min(100, max(0, int(parsed.get("score", score)))),
                "evidence": parsed.get("evidence", observations)[:5],
                "observations": parsed.get("observations", observations)[:5],
            }

        return {
            "score": score,
            "evidence": [f"Average response length: {avg_words:.0f} words"],
            "observations": observations,
        }


class CulturalFitEvaluator:
    """Evaluates cultural fit and motivation."""

    async def evaluate(
        self,
        questions_responses: list[dict[str, Any]],
        company_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Evaluates alignment with role, motivation, values fit.
        """
        qa_text = _format_qa_pairs(questions_responses)
        role_title = company_context.get("title", "the position")

        prompt = f"""You are evaluating cultural fit and motivation for {role_title}.

INTERVIEW Q&A:
{qa_text[:4000]}

Return ONLY a JSON object:
{{
  "score": 0-100,
  "evidence": ["motivation or fit observation 1", "..."],
  "fit_indicators": ["indicator 1: description", "..."]
}}

JSON:"""

        parsed = await _call_evaluator_llm(prompt, num_predict=1024)
        if parsed:
            return self._normalize(parsed)

        return self._deterministic_fallback(questions_responses)

    def _normalize(self, parsed: dict[str, Any]) -> dict[str, Any]:
        return {
            "score": min(100, max(0, int(parsed.get("score", 50)))),
            "evidence": parsed.get("evidence", [])[:5],
            "fit_indicators": parsed.get("fit_indicators", [])[:5],
        }

    def _deterministic_fallback(
        self,
        questions_responses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        cultural = [
            qr for qr in questions_responses
            if isinstance(qr, dict)
            and qr.get("category") in ("cultural_fit", "motivation")
            and qr.get("response")
        ]
        score = 60 if cultural else 45
        return {
            "score": score,
            "evidence": [f"{len(cultural)} motivation/culture responses available"] if cultural else ["No motivation/culture responses available"],
            "fit_indicators": ["Deterministic fallback: limited cultural analysis"] if not cultural else [],
        }
