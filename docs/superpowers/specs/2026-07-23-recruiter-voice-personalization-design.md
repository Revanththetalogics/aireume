# Recruiter Voice Personalization — Design Spec

**Date:** 2026-07-23  
**Status:** Approved for implementation  
**Goal:** Interview kits and live voice screens sound like a senior recruiter, not template fill-in-the-blank.

## Problem

- Deterministic kit generation (`interview_playbook_templates.py`) produces repetitive stems.
- Voice bot reads kit text verbatim with minimal phrasing swaps.
- Follow-ups are static (`follow_ups[0]`) and ignore answer content.
- `probe_areas` from `InterviewContextEngine` are not fed into kit generation.
- Sync analysis returns placeholder kits before async LLM enrichment completes.

## Solution (Hybrid Voice Model)

1. **Pre-generate** personalized kit with `intent` + `spoken_text` separation (kit v3).
2. **In-call LLM** only for follow-ups and thread transitions (`TurnPersonalizer`).
3. **Persist** `candidate_intelligence` artifact for reuse across kit, strategy, and evaluators.

## Architecture

```
ScreeningResult
  → CandidateIntelligenceService.build()
  → candidate_intelligence.json (stored on ScreeningResult)
  → Interview kit skeleton (threads + hypotheses)
  → RecruiterVoicePersonalizer.personalize() [LLM batch]
  → interview_kit v3 (spoken_text, follow_up_intents, thread_transitions)
  → Recruiter UI + Voice dispatch
  → KitDrivenOrchestrator + TurnPersonalizer [light in-call LLM]
  → Post-call evaluators (unchanged, plan-aware in Phase 5)
```

## Kit v3 Step Schema

```json
{
  "intent": "Validate personal SAP MM ownership at go-live",
  "text": "At Acme you were on the S/4 cutover — what did you personally own through go-live?",
  "spoken_text": "Same as text unless voice-specific override",
  "probe_target": {
    "type": "ownership",
    "skill": "SAP MM",
    "company": "Acme",
    "hypothesis_id": "H1",
    "probe_category": "skill_validation"
  },
  "what_to_listen_for": ["personal deliverables"],
  "follow_ups": ["legacy spoken follow-up for fallback"],
  "follow_up_intents": ["If vague on personal role, ask what they configured vs supported"],
  "scoring_criteria": { "strong": "...", "adequate": "...", "weak": "..." }
}
```

Backward compatibility: consumers use `spoken_text or text` for voice; `text` remains for legacy UI.

## Candidate Intelligence Schema

```json
{
  "version": 1,
  "screening_result_id": 123,
  "strengths": [{ "claim": "...", "evidence": "...", "confidence": 0.85 }],
  "gaps": [{ "skill": "...", "severity": "high", "interview_priority": 1 }],
  "claims_to_validate": [{ "claim": "...", "source": "resume", "risk": "medium" }],
  "probe_areas": [],
  "interview_priorities": ["..."],
  "resume_anchors": {
    "name": "...",
    "current_company": "...",
    "current_role": "...",
    "latest_roles": [{ "company": "...", "title": "...", "duration": "..." }]
  },
  "hiring_confidence_pre_interview": 0.62
}
```

## Voice Rules (Personalizer + TurnPersonalizer)

- Reference candidate name, latest company/role when known.
- 15–35 words per phone question; one probe per question.
- Forbidden stems (lint): "This role needs", repeated "Walk me through", skill-only questions.
- Gap probes: curiosity tone, not accusation.
- Follow-ups reference what candidate just said.

## Non-Goals

- Full dynamic questioning every turn (QuestionPlanner as primary path).
- New role-family template libraries.
- Replacing post-call evaluator architecture.

## Success Criteria

1. Two candidates for same role get different `spoken_text` lines.
2. Anti-template lint catches forbidden patterns in CI.
3. Voice follow-ups reference prior answer content.
4. Placeholder kit hidden until `interview_kit_status === "ready"`.
5. Each step maps to `hypothesis_id` or `probe_category`.

## Execution

See implementation plan: `docs/superpowers/plans/2026-07-23-recruiter-voice-personalization.md`
