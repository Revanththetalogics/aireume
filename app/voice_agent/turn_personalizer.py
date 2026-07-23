"""In-call follow-up and transition phrasing for voice screening."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("voice_agent.turn_personalizer")

_EXAMPLE_MARKERS = (
    "for example", "for instance", "i built", "i led", "i designed",
    "i implemented", "my project", "my team and i", "i personally",
)
_THIN_MARKERS = {"yes", "yeah", "sure", "okay", "ok", "no", "nope", "not sure", "i don't know"}


def answer_has_specifics(answer: str) -> bool:
    """Heuristic: answer is specific enough to move on."""
    text = (answer or "").strip()
    if not text:
        return False
    lower = text.lower()
    if lower in _THIN_MARKERS:
        return False
    words = text.split()
    if len(words) >= 25:
        return True
    if len(words) >= 12 and any(m in lower for m in _EXAMPLE_MARKERS):
        return True
    return False


def _heuristic_follow_up(intent: str, last_answer: str, candidate_name: str) -> str:
    name = (candidate_name or "there").split()[0]
    lower = (last_answer or "").lower()
    if "we " in lower or lower.startswith("we"):
        return f"When you say 'we' — what part did you handle yourself, {name}?"
    if len((last_answer or "").split()) < 8:
        return f"Could you give me one specific example, {name}?"
    return intent[:120] if intent else "Can you be more specific about your personal contribution?"


async def phrase_follow_up(
    *,
    intent: str,
    last_question: str,
    last_answer: str,
    candidate_name: str = "",
    probe_target: dict[str, Any] | None = None,
) -> str:
    """Generate a natural follow-up line from coaching intent."""
    prompt = f"""You are a senior recruiter mid-call. Phrase ONE short follow-up (under 25 words).
Reference what they just said. Don't repeat the original question.
If they said "we", ask what they personally did.

Candidate: {candidate_name or "Candidate"}
Last question: {last_question[:200]}
Their answer: {last_answer[:400]}
Follow-up intent: {intent}
Probe: {probe_target or {}}

Return ONLY JSON: {{"spoken_text": "..."}}"""

    try:
        from app.backend.services.app_llm_client import generate_app_json

        parsed = await generate_app_json(
            prompt,
            max_output_tokens=128,
            temperature=0.35,
            timeout=15.0,
            log_label="turn_personalizer",
        )
        if isinstance(parsed, dict):
            spoken = (parsed.get("spoken_text") or "").strip()
            if spoken and len(spoken.split()) <= 35:
                return spoken
    except Exception as err:
        logger.warning("Turn personalizer LLM failed: %s", err)

    return _heuristic_follow_up(intent, last_answer, candidate_name)


async def phrase_transition(
    *,
    transition_template: str,
    last_answer_snippet: str,
    candidate_name: str = "",
) -> str:
    """Optional LLM polish for thread transitions."""
    template = (transition_template or "").strip()
    if not template:
        return ""
    snippet = (last_answer_snippet or "")[:120].strip()
    if not snippet or len(snippet.split()) < 6:
        return template

    prompt = f"""Bridge to the next interview topic in one sentence (under 30 words).
Acknowledge briefly what they shared, then transition.

Candidate: {candidate_name or "Candidate"}
They said: {snippet}
Transition hint: {template}

Return ONLY JSON: {{"spoken_text": "..."}}"""

    try:
        from app.backend.services.app_llm_client import generate_app_json

        parsed = await generate_app_json(
            prompt,
            max_output_tokens=96,
            temperature=0.3,
            timeout=12.0,
            log_label="turn_transition",
        )
        if isinstance(parsed, dict):
            spoken = (parsed.get("spoken_text") or "").strip()
            if spoken:
                return spoken
    except Exception as err:
        logger.debug("Transition personalizer skipped: %s", err)

    return template
