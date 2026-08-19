"""Pydantic output schemas for Outlines structured LLM generation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class KitStepSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    text: str = ""
    spoken_text: str = ""
    intent: str = ""
    what_to_listen_for: list[str] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    follow_up_intents: list[str] = Field(default_factory=list)


class KitThreadSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = ""
    title: str = ""
    kind: str = ""
    steps: list[KitStepSchema] = Field(default_factory=list)


class InterviewQuestionsSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    kit_version: int = 3
    screen_objective: str = ""
    threads: list[KitThreadSchema] = Field(default_factory=list)
    technical_questions: list[KitStepSchema] = Field(default_factory=list)
    behavioral_questions: list[KitStepSchema] = Field(default_factory=list)
    experience_deep_dive_questions: list[KitStepSchema] = Field(default_factory=list)
    candidate_briefing: dict = Field(default_factory=dict)
    hypotheses: list = Field(default_factory=list)
    open: dict = Field(default_factory=dict)
    close: dict = Field(default_factory=dict)
    hm_debrief_template: dict = Field(default_factory=dict)
    recruiter_signals: dict = Field(default_factory=dict)


class InterviewKitLLMResponse(BaseModel):
    """Top-level JSON envelope returned by interview kit prompts."""

    interview_questions: InterviewQuestionsSchema


class HiringDecisionSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    verdict: str = ""
    confidence: float = 0.0
    key_factors: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)


class ExplainabilitySchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    skill_rationale: str = ""
    experience_rationale: str = ""
    overall_rationale: str = ""


class NarrativeLLMResponse(BaseModel):
    """Screening narrative JSON returned by explain_with_llm prompts."""

    model_config = ConfigDict(extra="allow")

    candidate_profile_summary: str = ""
    fit_summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    dealbreakers: list[str] = Field(default_factory=list)
    differentiators: list[str] = Field(default_factory=list)
    recommendation_rationale: str = ""
    hiring_decision: HiringDecisionSchema = Field(default_factory=HiringDecisionSchema)
    explainability: ExplainabilitySchema = Field(default_factory=ExplainabilitySchema)


def narrative_meets_minimum(parsed: dict) -> bool:
    """Reject empty or trivial narrative payloads before accepting."""
    fit = str(parsed.get("fit_summary") or "").strip()
    profile = str(parsed.get("candidate_profile_summary") or "").strip()
    return len(fit) >= 20 or len(profile) >= 20
