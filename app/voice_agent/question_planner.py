"""
Dynamic Question Planner — generates interview questions in real-time.

Replaces the pre-generated strategy with live question planning based on:
- Current interview stage
- Answer scores from the AnswerEvaluator
- Conversation history
- Resume data and JD requirements
- Time remaining

The planner uses the LLM to generate contextually relevant questions that
adapt to the candidate's performance.
"""

import asyncio
import json
import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger("voice_agent.planner")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

_ollama_semaphore: asyncio.Semaphore | None = None


def _get_ollama_semaphore() -> asyncio.Semaphore:
    global _ollama_semaphore
    if _ollama_semaphore is None:
        env_val = os.getenv("OLLAMA_MAX_CONCURRENT")
        if env_val is not None:
            max_concurrent = int(env_val)
        elif OLLAMA_BASE_URL.startswith("https://") or "ollama.com" in OLLAMA_BASE_URL.lower():
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


class QuestionPlanner:
    """Generates dynamic interview questions based on context and performance."""

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL

    async def generate_question(
        self,
        stage: str,
        context: dict[str, Any],
        conversation_history: list[dict[str, str]],
        answer_scores: list[int],
        difficulty_adjustment: str = "same",
        questions_asked: list[str] | None = None,
        time_remaining_s: int = 600,
    ) -> dict[str, Any]:
        """
        Generate the next interview question.

        Returns:
            {
                "question": "...",
                "category": "technical" | "behavioral" | "motivation" | ...,
                "context": "why this question matters",
                "expected_duration_s": 120,
            }
        """
        candidate = context.get("candidate", {})
        role = context.get("role", {})
        resume_skills = candidate.get("parsed_skills", [])[:10]
        required_skills = role.get("required_skills", [])[:5]
        work_exp = candidate.get("parsed_work_experience", [])[:3]

        # Build conversation summary
        recent_qa = "\n".join(
            f"Q: {turn.get('question', '')}\nA: {turn.get('answer', '')[:200]}"
            for turn in conversation_history[-3:]
        )

        # Build questions already asked
        asked = "\n".join(f"- {q}" for q in (questions_asked or [])[-10:])

        # Score trend
        score_trend = answer_scores[-5:] if answer_scores else []
        avg_score = sum(score_trend) / len(score_trend) if score_trend else 50

        prompt = f"""You are an expert interviewer conducting a {stage} interview.

CANDIDATE: {candidate.get('name', 'Candidate')}
ROLE: {role.get('title', 'the position')}
REQUIRED SKILLS: {', '.join(str(s) for s in required_skills)}
CANDIDATE SKILLS: {', '.join(str(s) for s in resume_skills)}
WORK EXPERIENCE: {json.dumps(work_exp, default=str)[:500]}

RECENT Q&A:
{recent_qa}

QUESTIONS ALREADY ASKED (do not repeat):
{asked}

CANDIDATE PERFORMANCE: avg score={avg_score:.0f}, last adjustment={difficulty_adjustment}
TIME REMAINING: {time_remaining_s // 60} minutes

Generate ONE question for the {stage} stage. Rules:
- If difficulty_adjustment is "harder": ask a more challenging question
- If "simpler": ask an easier, more fundamental question
- If "switch_topic": move to a different skill/topic area
- If "same": continue at the same difficulty level
- Do NOT repeat questions already asked
- Keep the question conversational and under 30 words
- For resume_verification: ask about specific work experience claims
- For technical: test depth of knowledge in required skills
- For behavioral: use STAR-format questions
- For motivation: ask about career goals, why this company, etc.

Return ONLY a JSON object:
{{
  "question": "...",
  "category": "{stage}",
  "context": "why this question matters (1 sentence)",
  "expected_duration_s": 120
}}

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
                            "options": {"temperature": 0.5, "num_predict": 256},
                        },
                        headers=_get_ollama_headers(),
                    )
                    resp.raise_for_status()
                    response_text = resp.json().get("response", "")
                    parsed = self._parse_json(response_text)
                    if parsed:
                        return self._normalize(parsed, stage)
        except Exception as e:
            logger.warning("Question planning LLM call failed: %s", e)

        # Fallback: generate a stage-appropriate question
        return self._fallback_question(stage, context, questions_asked or [])

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

    def _normalize(self, parsed: dict[str, Any], stage: str) -> dict[str, Any]:
        return {
            "question": parsed.get("question", "").strip(),
            "category": parsed.get("category", stage),
            "context": parsed.get("context", "").strip(),
            "expected_duration_s": min(300, max(30, int(parsed.get("expected_duration_s", 120)))),
        }

    def _fallback_question(
        self, stage: str, context: dict[str, Any], questions_asked: list[str]
    ) -> dict[str, Any]:
        """Generate a fallback question when LLM is unavailable."""
        candidate = context.get("candidate", {})
        role = context.get("role", {})
        skills = role.get("required_skills", [])

        stage_questions = {
            "introduction": f"Hi {candidate.get('name', 'there')}, thanks for taking the time. Could you briefly walk me through your background and what interests you about this role?",
            "resume_verification": f"I'd like to understand your experience better. Can you tell me about your most recent role and your key responsibilities?",
            "technical": f"Can you describe a recent project where you used {skills[0] if skills else 'your core skills'}? What was your specific contribution?",
            "behavioral": "Tell me about a time you faced a significant challenge on a project. What was the situation, what did you do, and what was the result?",
            "communication": "Can you explain a complex technical concept to me as if I'm non-technical? This helps me understand how you communicate with stakeholders.",
            "motivation": f"What are you looking for in your next role, and why does {role.get('title', 'this position')} appeal to you?",
            "closing": "We've covered a lot today. Is there anything else you'd like to share or any questions you have about the role?",
        }

        question = stage_questions.get(stage, stage_questions["technical"])
        return {
            "question": question,
            "category": stage,
            "context": f"Fallback question for {stage} stage.",
            "expected_duration_s": 120,
        }
