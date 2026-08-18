"""Batch LLM personalization of interview kit spoken lines."""

from __future__ import annotations

import copy
import json
import logging
import re
from typing import Any

from app.backend.services.interview_kit_context import format_resume_anchors_text
from app.backend.services.interview_kit_quality import get_spoken_line, lint_interview_kit

logger = logging.getLogger("aria.kit_personalizer")

PERSONALIZER_RULES = """
VOICE RULES — senior recruiter on a live phone screen:
- Reference THIS candidate: name, latest company, role title when known
- One question = one probe; 15-35 words; conversational contractions OK
- Populate intent (internal coaching) and follow_up_intents (coaching bullets, not full sentences)
- Forbidden: "This role needs", "The role calls for", repeated "Walk me through"
- Gap probes: curious tone, not accusation
"""


def _apply_minimal_personalization(kit: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Rule-based fallback when LLM unavailable."""
    out = copy.deepcopy(kit)
    anchors = context.get("resume_anchors") or {}
    company = (anchors.get("current_company") or "").strip()
    role = (anchors.get("current_role") or "").strip()
    if not company and not role:
        return out

    for thread in out.get("threads") or []:
        if not isinstance(thread, dict):
            continue
        for step in thread.get("steps") or []:
            if not isinstance(step, dict):
                continue
            text = get_spoken_line(step)
            if company and company.lower() not in text.lower():
                if thread.get("kind") == "ownership" and role:
                    step["spoken_text"] = (
                        f"At {company} as {role} — what did you personally own day to day?"
                    )[:200]
                elif company:
                    step["spoken_text"] = f"At {company}, {text[0].lower()}{text[1:]}"[:200]
            if not step.get("intent"):
                step["intent"] = f"Validate: {text[:120]}"
            if not step.get("follow_up_intents") and step.get("follow_ups"):
                step["follow_up_intents"] = [
                    f"If vague: {fu}" for fu in step["follow_ups"][:2] if isinstance(fu, str)
                ]
    return out


def _merge_personalized_steps(kit: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    """Merge LLM output steps into original kit by thread id + step index."""
    out = copy.deepcopy(kit)
    parsed_threads = {
        t.get("id"): t for t in (parsed.get("threads") or []) if isinstance(t, dict) and t.get("id")
    }
    # Compact personalizer returns step_updates list
    updates = parsed.get("step_updates")
    if isinstance(updates, list):
        for upd in updates:
            if not isinstance(upd, dict):
                continue
            tid = upd.get("thread_id")
            idx = upd.get("step_index")
            spoken = (upd.get("spoken_text") or upd.get("text") or "").strip()
            if tid is None or idx is None or not spoken:
                continue
            for thread in out.get("threads") or []:
                if thread.get("id") != tid:
                    continue
                steps = thread.get("steps") or []
                if 0 <= int(idx) < len(steps) and isinstance(steps[int(idx)], dict):
                    steps[int(idx)]["spoken_text"] = spoken
                    steps[int(idx)]["text"] = spoken
                    if upd.get("intent"):
                        steps[int(idx)]["intent"] = upd["intent"]
                    if upd.get("follow_up_intents"):
                        steps[int(idx)]["follow_up_intents"] = list(upd["follow_up_intents"])
                break
        if parsed.get("thread_transitions"):
            out["thread_transitions"] = dict(parsed["thread_transitions"])
        return out

    for thread in out.get("threads") or []:
        if not isinstance(thread, dict):
            continue
        tid = thread.get("id")
        p_thread = parsed_threads.get(tid)
        if not p_thread:
            continue
        p_steps = p_thread.get("steps") or []
        for idx, step in enumerate(thread.get("steps") or []):
            if not isinstance(step, dict) or idx >= len(p_steps):
                continue
            p_step = p_steps[idx]
            if not isinstance(p_step, dict):
                continue
            spoken = (p_step.get("spoken_text") or p_step.get("text") or "").strip()
            if spoken:
                step["spoken_text"] = spoken
                step["text"] = spoken
            if p_step.get("intent"):
                step["intent"] = p_step["intent"]
            if p_step.get("follow_up_intents"):
                step["follow_up_intents"] = list(p_step["follow_up_intents"])
            if p_step.get("probe_target"):
                step["probe_target"] = dict(p_step["probe_target"])
    if parsed.get("thread_transitions"):
        out["thread_transitions"] = dict(parsed["thread_transitions"])
    return out


def _compact_step_outline(kit: dict[str, Any]) -> list[dict[str, Any]]:
    """Small outline for personalizer — avoids sending 6k chars of full skeleton."""
    outline: list[dict[str, Any]] = []
    for thread in kit.get("threads") or []:
        if not isinstance(thread, dict):
            continue
        for idx, step in enumerate(thread.get("steps") or []):
            if not isinstance(step, dict):
                continue
            outline.append({
                "thread_id": thread.get("id"),
                "step_index": idx,
                "kind": thread.get("kind"),
                "spoken_text": get_spoken_line(step),
                "intent": (step.get("intent") or "")[:120],
            })
    return outline[:24]


def _build_personalizer_prompt(kit: dict[str, Any], context: dict[str, Any]) -> str:
    anchors = context.get("resume_anchors") or {}
    ci = context.get("candidate_intelligence") or {}
    priorities = ci.get("interview_priorities") or context.get("interview_priorities") or []
    outline = _compact_step_outline(kit)

    return f"""IMPORTANT: Respond with ONLY valid JSON. No markdown.{PERSONALIZER_RULES}

RESUME ANCHORS:
{format_resume_anchors_text(anchors)}

INTERVIEW PRIORITIES:
{chr(10).join(f"- {p}" for p in priorities[:6]) or "None"}

Rewrite spoken lines for this phone screen. Return JSON:
{{
  "step_updates": [
    {{"thread_id": "...", "step_index": 0, "spoken_text": "15-35 word question", "intent": "...", "follow_up_intents": ["..."]}}
  ],
  "thread_transitions": {{}}
}}

Steps to personalize ({len(outline)} total):
{json.dumps(outline, default=str)}

Keep thread_id and step_index unchanged. Every spoken_text must be 15-35 words, phone-ready."""


async def personalize_kit(kit: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Personalize kit spoken lines via LLM with deterministic fallback."""
    if not kit or not kit.get("threads"):
        return kit

    try:
        from app.backend.services.llm_json_service import invoke_llm_json_resilient

        prompt = _build_personalizer_prompt(kit, context)
        compact = (
            prompt
            + "\n\nCRITICAL: Return ONLY JSON with step_updates array. "
            "One entry per step. Max 35 words per spoken_text."
        )

        def _personalizer_valid(parsed: dict[str, Any]) -> bool:
            updates = parsed.get("step_updates")
            if isinstance(updates, list) and updates:
                return any(
                    isinstance(u, dict) and (u.get("spoken_text") or u.get("text"))
                    for u in updates
                )
            threads = parsed.get("threads")
            if isinstance(threads, list):
                for thread in threads:
                    for step in (thread.get("steps") or []) if isinstance(thread, dict) else []:
                        if isinstance(step, dict) and get_spoken_line(step):
                            return True
            return False

        parsed = await invoke_llm_json_resilient(
            [prompt, compact],
            max_output_tokens=1800,
            log_label="kit_personalizer",
            validate_parsed=_personalizer_valid,
        )
        if parsed:
            merged = _merge_personalized_steps(kit, parsed)
            lint = lint_interview_kit(merged)
            if lint["ok"]:
                logger.info("Kit personalized via LLM (lint score=%s)", lint["score"])
                return merged
            logger.warning("Personalized kit failed lint: %s", lint["issues"][:3])
    except Exception as err:
        logger.warning("Kit personalizer LLM failed: %s", err)

    return _apply_minimal_personalization(kit, context)


async def personalize_step(
    kit: dict[str, Any],
    *,
    thread_id: str,
    step_index: int,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Re-personalize a single step (for regen API)."""
    out = copy.deepcopy(kit)
    for thread in out.get("threads") or []:
        if thread.get("id") != thread_id:
            continue
        steps = thread.get("steps") or []
        if step_index < 0 or step_index >= len(steps):
            return out
        mini = {"threads": [{"id": thread_id, "steps": [steps[step_index]]}]}
        personalized = await personalize_kit(mini, context)
        p_steps = (personalized.get("threads") or [{}])[0].get("steps") or []
        if p_steps:
            steps[step_index] = {**steps[step_index], **p_steps[0]}
        break
    return out
