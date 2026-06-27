"""
Recruiter Copilot — generates per-answer observations for recruiters.

After each candidate answer, generates:
- Observation: what the candidate demonstrated
- Confidence Level: high / medium / low
- Concern: what was missing or weak
- Suggested Follow-up: what a human recruiter should ask next
"""

import json
import logging
import os
from typing import Any

import httpx

from app.backend.services.llm_service import get_ollama_semaphore, get_ollama_headers

logger = logging.getLogger("aria.recruiter")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")


class CopilotAgent:
    """Generates recruiter-facing observations for each interview answer."""

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL

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
            semaphore = get_ollama_semaphore()
            async with semaphore:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False,
                            "format": "json",
                            "options": {"temperature": 0.3, "num_predict": 256},
                        },
                        headers=get_ollama_headers(self.base_url),
                    )
                    resp.raise_for_status()
                    response_text = resp.json().get("response", "")
                    parsed = self._parse_json(response_text)
                    if parsed:
                        return self._normalize(parsed)
        except Exception as e:
            logger.warning("Copilot LLM call failed: %s", e)

        # Fallback: generate from score
        return self._fallback_observation(question, answer, answer_score)

    def _parse_json(self, text: str) -> dict[str, Any] | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        import re
        for pattern in (r'```json\s*(\{.*?\})\s*```', r'(\{.*\})'):
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        return None

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
