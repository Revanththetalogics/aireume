"""Pre-synthesize common kit-call phrases to reduce time-to-first-audio."""
from __future__ import annotations

from typing import Any

from app.voice_agent.kit_orchestrator import KitDrivenOrchestrator, _CATEGORY_INTROS
from app.voice_agent.orchestrator import OrchestratorContext
from app.voice_agent.speech_pipeline import IMMEDIATE_ACKS, clean_tts_text


def build_kit_warm_phrases(
    ctx: OrchestratorContext,
    kit_questions: list[dict[str, Any]],
) -> list[str]:
    """Phrases likely to be spoken early in a kit-driven screening call."""
    orch = KitDrivenOrchestrator(ctx, kit_questions)
    phrases: list[str] = []

    for step in range(3):
        phrases.append(orch._intro_message(step))

    if orch.questions:
        first = orch.questions[0]
        prefix = _CATEGORY_INTROS.get(first.category, "")
        phrases.append(prefix + first.text)
        if len(orch.questions) > 1:
            second = orch.questions[1]
            prefix2 = _CATEGORY_INTROS.get(second.category, "")
            if prefix2 != prefix:
                phrases.append(prefix2 + second.text)
            else:
                phrases.append(second.text)

    phrases.extend(IMMEDIATE_ACKS)
    phrases.append("I'm sorry, I didn't catch that. Could you please repeat?")
    phrases.append("I didn't quite catch that. Could you repeat what you said?")

    seen: set[str] = set()
    out: list[str] = []
    for raw in phrases:
        clean = clean_tts_text(raw)
        if not clean or clean in seen:
            continue
        seen.add(clean)
        out.append(clean)
    return out
