"""Single-step interview kit regeneration API."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.rbac import require_recruiter_or_admin
from app.backend.models.db_models import ScreeningResult, User
from app.backend.routes.interview_kit import _verify_result_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interview-kit", tags=["interview-kit"])


class RegenerateStepRequest(BaseModel):
    thread_id: str = Field(..., min_length=1)
    step_index: int = Field(..., ge=0)


class RegenerateStepResponse(BaseModel):
    ok: bool
    kit: dict[str, Any]
    lint_ok: bool
    lint_score: int


@router.post("/{screening_result_id}/regenerate-step", response_model=RegenerateStepResponse)
async def regenerate_interview_kit_step(
    screening_result_id: int,
    body: RegenerateStepRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter_or_admin),
):
    """Re-personalize one kit step, re-lint, and persist."""
    from app.backend.services.candidate_intelligence_service import (
        ci_from_screening_row,
        merge_ci_into_kit_context,
    )
    from app.backend.services.interview_kit_quality import lint_interview_kit
    from app.backend.services.recruiter_voice_personalizer import personalize_step

    result = _verify_result_access(screening_result_id, current_user, db)

    analysis: dict[str, Any] = {}
    if result.analysis_result:
        try:
            analysis = json.loads(result.analysis_result)
        except (json.JSONDecodeError, TypeError):
            analysis = {}

    kit = analysis.get("interview_questions") or {}
    if not kit.get("threads"):
        raise HTTPException(status_code=404, detail="Interview kit not found")

    parsed_data: dict[str, Any] = {}
    if result.parsed_data:
        try:
            parsed_data = json.loads(result.parsed_data)
        except (json.JSONDecodeError, TypeError):
            parsed_data = {}

    ci = ci_from_screening_row(result) or {}
    ctx = merge_ci_into_kit_context(
        {
            "candidate_profile": analysis.get("candidate_profile") or {},
            "jd_analysis": analysis.get("jd_analysis") or {},
            "skill_analysis": analysis.get("skill_analysis") or {},
            "parsed_data": parsed_data,
            "gap_analysis": analysis.get("gap_analysis") or {},
            "probe_areas": kit.get("probe_areas") or analysis.get("probe_areas"),
        },
        ci,
    )

    updated = await personalize_step(
        kit,
        thread_id=body.thread_id,
        step_index=body.step_index,
        context=ctx,
    )
    lint = lint_interview_kit(updated)
    updated["kit_version"] = updated.get("kit_version") or 3

    analysis["interview_questions"] = updated
    result.analysis_result = json.dumps(analysis, default=str)
    if result.narrative_json:
        try:
            narrative = json.loads(result.narrative_json)
            narrative["interview_questions"] = updated
            result.narrative_json = json.dumps(narrative, default=str)
        except (json.JSONDecodeError, TypeError):
            pass
    db.commit()

    logger.info(
        "Regenerated kit step thread=%s index=%s for screening_result_id=%s lint_ok=%s",
        body.thread_id,
        body.step_index,
        screening_result_id,
        lint["ok"],
    )
    return RegenerateStepResponse(
        ok=True,
        kit=updated,
        lint_ok=lint["ok"],
        lint_score=lint["score"],
    )
