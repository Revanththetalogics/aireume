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
