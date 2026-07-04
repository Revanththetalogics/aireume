"""
Real-time Answer Evaluator — scores candidate answers during the interview.

After each candidate answer, the LLM evaluates it on a 0-100 scale with
reasoning. The score drives adaptive difficulty:
  score > 80  → harder question
  40-80       → same level
  score < 40  → simpler or switch topic
"""

import asyncio
import json
import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger("voice_agent.evaluator")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL_VOICE", os.getenv("OLLAMA_MODEL", "qwen2.5:3b"))
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

_ollama_semaphore: asyncio.Semaphore | None = None


def _get_ollama_semaphore() -> asyncio.Semaphore:
    global _ollama_semaphore
    if _ollama_semaphore is None:
        base_url = OLLAMA_BASE_URL
        env_val = os.getenv("OLLAMA_MAX_CONCURRENT")
        if env_val is not None:
            max_concurrent = int(env_val)
        elif base_url.startswith("https://") or "ollama.com" in base_url.lower():
            max_concurrent = 4
        else:
            max_concurrent = 1
        _ollama_semaphore = asyncio.Semaphore(max_concurrent)
    return _ollama_semaphore


def _get_ollama_headers() -> dict[str, str]:
    headers = {}
    if "ollama.com" in OLLAMA_BASE_URL.lower():
        api_key = OLLAMA_API_KEY.strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
    return headers


class AnswerEvaluator:
    """Evaluates candidate answers in real-time during the interview."""

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL

    async def evaluate(
        self,
        question: str,
        answer: str,
        stage: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate a candidate's answer.

        Returns:
            {
                "score": 0-100,
                "reasoning": "...",
                "difficulty_adjustment": "harder" | "same" | "simpler" | "switch_topic",
                "key_points": ["point 1", "..."],
                "concerns": ["concern 1", "..."],
            }
        """
        if not answer.strip() or len(answer.strip()) < 5:
            return {
                "score": 0,
                "reasoning": "Answer too short or empty.",
                "difficulty_adjustment": "simpler",
                "key_points": [],
                "concerns": ["No substantive answer provided."],
            }

        context_str = ""
        if context:
            role = context.get("role", {})
            candidate = context.get("candidate", {})
            context_str = f"\nROLE: {role.get('title', 'N/A')}\nCANDIDATE: {candidate.get('name', 'N/A')}, {candidate.get('current_role', 'N/A')}"

        prompt = f"""You are an expert interviewer evaluating a candidate's answer in real-time.

INTERVIEW STAGE: {stage}
QUESTION ASKED: {question}
CANDIDATE'S ANSWER: {answer}
{context_str}

Evaluate the answer on a 0-100 scale. Consider:
- Relevance to the question
- Depth of knowledge demonstrated
- Clarity and structure
- Use of specific examples
- Accuracy of technical claims (if applicable)

Return ONLY a JSON object:
{{
  "score": 0-100,
  "reasoning": "1-2 sentence explanation",
  "difficulty_adjustment": "harder" | "same" | "simpler" | "switch_topic",
  "key_points": ["what the candidate demonstrated", "..."],
  "concerns": ["what was missing or weak", "..."]
}}

Rules for difficulty_adjustment:
- score > 80: "harder" (candidate handled this well, increase difficulty)
- score 40-80: "same" (adequate answer, continue at same level)
- score < 40: "simpler" (struggled, try an easier question in this area)
- If the candidate clearly doesn't know the topic at all: "switch_topic"

JSON:"""

        try:
            semaphore = _get_ollama_semaphore()
            async with semaphore:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False,
                            "format": "json",
                            "options": {"temperature": 0.2, "num_predict": 512},
                        },
                        headers=_get_ollama_headers(),
                    )
                    resp.raise_for_status()
                    response_text = resp.json().get("response", "")
                    parsed = self._parse_json(response_text)
                    if parsed:
                        return self._normalize(parsed)
        except Exception as e:
            logger.warning("Answer evaluation LLM call failed: %s", e)

        # Fallback: heuristic-based scoring
        return self._heuristic_evaluate(question, answer, stage)

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
        score = max(0, min(100, int(parsed.get("score", 50))))
        adjustment = parsed.get("difficulty_adjustment", "same")
        if adjustment not in ("harder", "same", "simpler", "switch_topic"):
            if score > 80:
                adjustment = "harder"
            elif score < 40:
                adjustment = "simpler"
            else:
                adjustment = "same"

        return {
            "score": score,
            "reasoning": parsed.get("reasoning", ""),
            "difficulty_adjustment": adjustment,
            "key_points": parsed.get("key_points", [])[:5],
            "concerns": parsed.get("concerns", [])[:3],
        }

    def _heuristic_evaluate(
        self, question: str, answer: str, stage: str
    ) -> dict[str, Any]:
        """Fallback scoring when LLM is unavailable."""
        word_count = len(answer.split())
        score = 50
        concerns = []
        key_points = []

        if word_count < 10:
            score = 20
            concerns.append("Answer is very brief.")
        elif word_count < 30:
            score = 40
            concerns.append("Answer lacks detail.")
        elif word_count > 100:
            score = 65
            key_points.append("Provided a detailed response.")
        else:
            score = 55
            key_points.append("Provided a reasonable length response.")

        # Check for specific examples
        example_markers = ["for example", "for instance", "in my project", "at my previous", "i worked on"]
        if any(marker in answer.lower() for marker in example_markers):
            score += 15
            key_points.append("Used specific examples.")

        # Check for hedging
        hedge_words = ["i think", "maybe", "sort of", "kind of", "not sure"]
        hedge_count = sum(1 for w in hedge_words if w in answer.lower())
        if hedge_count > 2:
            score -= 10
            concerns.append("Response shows uncertainty.")

        score = max(0, min(100, score))
        adjustment = "harder" if score > 80 else "simpler" if score < 40 else "same"

        return {
            "score": score,
            "reasoning": f"Heuristic evaluation: {word_count} words, score={score}.",
            "difficulty_adjustment": adjustment,
            "key_points": key_points,
            "concerns": concerns,
        }
