"""
Recruiter Copilot — generates per-answer observations for recruiters.

After each candidate answer, generates:
- Observation: what the candidate demonstrated
- Confidence Level: high / medium / low
- Concern: what was missing or weak
- Suggested Follow-up: what a human recruiter should ask next
"""

import logging
from typing import Any

from app.backend.services.recruiter.llm_client import generate_recruiter_json, parse_json_safely

logger = logging.getLogger("aria.recruiter")


class CopilotAgent:
    """Generates recruiter-facing observations for each interview answer."""

    async def generate_observation(
        self,
        question: str,
        answer: str,
        stage: str,
        answer_score: int,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a recruiter copilot observation for a single Q&A pair.

        Returns:
            {
                "observation": "Candidate has practical FastAPI experience.",
                "confidence_level": "high" | "medium" | "low",
                "concern": "Could not explain dependency injection.",
                "suggested_follow_up": "Ask about async endpoints.",
            }
        """
        role_title = ""
        if context:
            role_title = context.get("role", {}).get("title", "")

        prompt = f"""You are a recruiter's AI copilot analyzing an interview answer.

ROLE: {role_title or 'the position'}
STAGE: {stage}
QUESTION: {question}
CANDIDATE'S ANSWER: {answer}
ANSWER SCORE: {answer_score}/100

Write what a human recruiter would note after hearing this answer.

Return ONLY a JSON object:
{{
  "observation": "1 sentence: what the candidate demonstrated",
  "confidence_level": "high" | "medium" | "low",
  "concern": "1 sentence: what was missing or weak (or 'None' if no concern)",
  "suggested_follow_up": "1 sentence: what to ask next (or 'None' if no follow-up needed)"
}}

JSON:"""

        try:
            parsed = await generate_recruiter_json(
                prompt,
                max_output_tokens=256,
                temperature=0.3,
                timeout=30.0,
            )
            if parsed:
                return self._normalize(parsed)
        except Exception as e:
            logger.warning("Copilot LLM call failed: %s", e)

        # Fallback: generate from score
        return self._fallback_observation(question, answer, answer_score)

    def _parse_json(self, text: str) -> dict[str, Any] | None:
        return parse_json_safely(text)

    def _normalize(self, parsed: dict[str, Any]) -> dict[str, Any]:
        confidence = parsed.get("confidence_level", "medium")
        if confidence not in ("high", "medium", "low"):
            confidence = "medium"
        return {
            "observation": parsed.get("observation", ""),
            "confidence_level": confidence,
            "concern": parsed.get("concern", "None"),
            "suggested_follow_up": parsed.get("suggested_follow_up", "None"),
        }

    def _fallback_observation(
        self, question: str, answer: str, score: int
    ) -> dict[str, Any]:
        """Generate a basic observation from the score when LLM is unavailable."""
        word_count = len(answer.split())
        if score >= 80:
            return {
                "observation": f"Candidate provided a strong answer ({word_count} words, score {score}).",
                "confidence_level": "high",
                "concern": "None",
                "suggested_follow_up": "None",
            }
        elif score >= 40:
            return {
                "observation": f"Candidate provided an adequate answer ({word_count} words, score {score}).",
                "confidence_level": "medium",
                "concern": "Answer could be more detailed." if word_count < 30 else "None",
                "suggested_follow_up": "Ask for a specific example." if word_count < 30 else "None",
            }
        else:
            return {
                "observation": f"Candidate struggled with this question ({word_count} words, score {score}).",
                "confidence_level": "low",
                "concern": "Candidate could not demonstrate knowledge in this area.",
                "suggested_follow_up": "Try a simpler question in this topic or move to another area.",
            }
