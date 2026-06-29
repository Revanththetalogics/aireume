"""
Unified interview routes.

Endpoints:
  POST /api/interviews/sessions                       — Create an interview session
  GET  /api/interviews/sessions                       — List interview sessions
  GET  /api/interviews/sessions/{id}                  — Get session detail
  GET  /api/interviews/sessions/{id}/transcript       — Get session transcript
  GET  /api/interviews/sessions/{id}/scorecard        — Get session scorecard
  POST /api/interviews/sessions/{id}/cancel           — Cancel a session
  POST /api/interviews/sessions/{id}/retry            — Retry a failed session
  GET  /api/interviews/config                         — Get merged interview config
  PUT  /api/interviews/config                         — Update merged interview config
  GET  /api/interviews/analytics                      — Aggregated analytics
  POST /api/interviews/sessions/export                — Export sessions as CSV
  POST /api/interviews/internal/complete              — Voice agent completion callback
"""
import csv
import io
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import (
    Candidate,
    RecruiterAutoTriggerConfig,
    RecruiterInterviewSession,
    RecruiterScorecard,
    RoleTemplate,
    ScreeningResult,
    User,
    VoiceScreeningSession,
    VoiceTenantConfig,
    VoiceTranscriptEntry,
)
from app.backend.models.schemas import (
    InterviewCreateRequest,
    RecruiterAutoTriggerConfigOut,
    RecruiterAutoTriggerConfigUpdate,
    RecruiterScorecardOut,
    RecruiterSessionOut,
    VoiceScreeningSessionOut,
    VoiceTenantConfigOut,
    VoiceTenantConfigUpdate,
)
from app.backend.services.recruiter.orchestrator import RecruiterOrchestrator

logger = logging.getLogger("aria.interviews")

router = APIRouter(prefix="/api/interviews", tags=["interviews"])

RECRUITER_ENABLED = os.getenv("RECRUITER_INTERVIEW_ENABLED", "true").lower() == "true"

_ALLOWED_DEPTHS = {"quick", "standard", "deep"}
_RECRUITER_DEPTHS = {"standard", "deep"}
_CANCELLABLE_STATUSES = {"scheduled", "pending_strategy", "strategy_ready", "no_answer", "failed"}


def _load_json(raw: Optional[str], default: Any = None) -> Any:
    """Safely load a JSON string; return default on empty/invalid input."""
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _require_recruiter_or_admin(current_user: User) -> None:
    """Raise 403 if the user is not a recruiter or admin."""
    if current_user.role not in {"admin", "recruiter"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiter or admin access required",
        )


def _parse_scheduled_at(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO datetime string into a timezone-aware datetime."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


# ─── Session Management ───────────────────────────────────────────────────────

@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_interview_session(
    body: InterviewCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a unified interview session (quick, standard, or deep)."""
    _require_recruiter_or_admin(current_user)

    depth = (body.depth or "quick").lower()
    if depth not in _ALLOWED_DEPTHS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid depth '{body.depth}'. Must be one of: quick, standard, deep",
        )

    # Verify candidate belongs to this tenant
    candidate = db.execute(
        select(Candidate).where(
            Candidate.id == body.candidate_id,
            Candidate.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found or not in your tenant",
        )

    scheduled_at = _parse_scheduled_at(body.scheduled_at)

    if depth == "quick":
        return await _create_quick_session(db, current_user, candidate, body, scheduled_at)

    # standard/deep require the recruiter feature
    if not RECRUITER_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Standard/deep interviews are not enabled",
        )

    return await _create_recruiter_session(db, current_user, candidate, body, scheduled_at, depth)


async def _create_quick_session(
    db: Session,
    current_user: User,
    candidate: Candidate,
    body: InterviewCreateRequest,
    scheduled_at: Optional[datetime],
):
    """Create a quick voice screening session and schedule the call."""
    # Ensure config exists
    config = db.execute(
        select(VoiceTenantConfig).where(VoiceTenantConfig.tenant_id == current_user.tenant_id)
    ).scalar_one_or_none()
    if config is None:
        config = VoiceTenantConfig(tenant_id=current_user.tenant_id)
        db.add(config)
        db.commit()

    session = VoiceScreeningSession(
        tenant_id=current_user.tenant_id,
        candidate_id=body.candidate_id,
        jd_id=body.jd_id,
        phone_number=body.phone_number,
        direction="outbound",
        status="scheduled",
        interview_depth="quick",
        scheduled_at=scheduled_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    from app.backend.services.voice_call_scheduler import schedule_voice_call
    schedule_voice_call(session.id, scheduled_at)

    return {
        "session_id": session.id,
        "depth": "quick",
        "status": session.status,
        "scheduled_at": session.scheduled_at,
        "phone_number": session.phone_number,
    }


async def _create_recruiter_session(
    db: Session,
    current_user: User,
    candidate: Candidate,
    body: InterviewCreateRequest,
    scheduled_at: Optional[datetime],
    depth: str,
):
    """Create a standard/deep recruiter interview session."""
    # Find latest active screening result for (candidate, jd) to seed context
    screening_result_id = None
    if body.jd_id:
        sr = db.execute(
            select(ScreeningResult)
            .where(
                ScreeningResult.tenant_id == current_user.tenant_id,
                ScreeningResult.candidate_id == body.candidate_id,
                ScreeningResult.role_template_id == body.jd_id,
                ScreeningResult.is_active == True,
            )
            .order_by(ScreeningResult.timestamp.desc())
        ).scalar_one_or_none()
        if sr:
            screening_result_id = sr.id

    # Map unified depth to a concrete duration so the voice agent respects it
    depth_duration_minutes = {"quick": 5, "standard": 15, "deep": 20}.get(depth, 20)

    config: dict[str, Any] = {
        "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
        "phone_number": body.phone_number,
        "focus_areas": body.focus_areas or [],
        "interview_depth": depth,
        "duration_minutes": depth_duration_minutes,
    }

    orchestrator = RecruiterOrchestrator(db)
    try:
        session_id = await orchestrator.initiate_interview(
            tenant_id=current_user.tenant_id,
            candidate_id=body.candidate_id,
            jd_id=body.jd_id,
            screening_result_id=screening_result_id,
            trigger_type="manual",
            config=config,
            created_by=current_user.id,
        )
    except ValueError as exc:
        logger.warning("Failed to initiate recruiter interview: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    interview_session = db.execute(
        select(RecruiterInterviewSession).where(
            RecruiterInterviewSession.id == session_id,
            RecruiterInterviewSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if interview_session is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session creation failed",
        )

    # Update the voice session depth to reflect unified depth
    if interview_session.voice_session_id:
        voice_session = db.execute(
            select(VoiceScreeningSession).where(
                VoiceScreeningSession.id == interview_session.voice_session_id
            )
        ).scalar_one_or_none()
        if voice_session:
            voice_session.interview_depth = "deep"  # DB only supports quick/deep
            db.commit()

    return {
        "session_id": interview_session.id,
        "voice_session_id": interview_session.voice_session_id,
        "depth": depth,
        "status": interview_session.status,
        "scheduled_at": interview_session.voice_session.scheduled_at if interview_session.voice_session else None,
        "phone_number": body.phone_number,
    }


@router.get("/sessions")
def list_interview_sessions(
    depth: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    candidate_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List unified interview sessions for the current tenant."""
    query = select(VoiceScreeningSession).where(
        VoiceScreeningSession.tenant_id == current_user.tenant_id
    ).options(
        selectinload(VoiceScreeningSession.candidate),
        selectinload(VoiceScreeningSession.jd),
    )

    if depth is not None:
        # DB stores quick/deep; standard maps to deep
        db_depth = "deep" if depth.lower() in {"standard", "deep"} else depth.lower()
        query = query.where(VoiceScreeningSession.interview_depth == db_depth)
    if status is not None:
        query = query.where(VoiceScreeningSession.status == status)
    if candidate_id is not None:
        query = query.where(VoiceScreeningSession.candidate_id == candidate_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    sessions = db.execute(
        query.order_by(VoiceScreeningSession.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    results = []
    for s in sessions:
        out = VoiceScreeningSessionOut.model_validate(s)
        out.candidate_name = s.candidate.name if s.candidate else None
        out.candidate_email = s.candidate.email if s.candidate else None
        out.jd_title = s.jd.name if s.jd else None
        # Resolve depth label: deep sessions may have been created as "standard"
        out.interview_depth = s.interview_depth
        results.append(out)

    return {
        "sessions": [r.model_dump() for r in results],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/sessions/{session_id}")
def get_interview_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a unified interview session detail with transcript."""
    session = db.execute(
        select(VoiceScreeningSession)
        .where(
            VoiceScreeningSession.id == session_id,
            VoiceScreeningSession.tenant_id == current_user.tenant_id,
        )
        .options(
            selectinload(VoiceScreeningSession.candidate),
            selectinload(VoiceScreeningSession.jd),
        )
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    entries = db.execute(
        select(VoiceTranscriptEntry)
        .where(VoiceTranscriptEntry.session_id == session_id)
        .order_by(VoiceTranscriptEntry.timestamp.asc())
    ).scalars().all()

    result = VoiceScreeningSessionOut.model_validate(session)
    result.candidate_name = session.candidate.name if session.candidate else None
    result.candidate_email = session.candidate.email if session.candidate else None
    result.jd_title = session.jd.name if session.jd else None

    result_dict = result.model_dump()
    result_dict["transcript"] = [e.__dict__ for e in entries]
    for entry in result_dict["transcript"]:
        entry.pop("_sa_instance_state", None)

    # Attach recruiter session metadata if present
    recruiter_session = db.execute(
        select(RecruiterInterviewSession).where(
            RecruiterInterviewSession.voice_session_id == session_id,
            RecruiterInterviewSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()
    if recruiter_session:
        result_dict["recruiter_session_id"] = recruiter_session.id
        result_dict["recruiter_status"] = recruiter_session.status

    return result_dict


@router.get("/sessions/{session_id}/transcript")
def get_interview_transcript(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the transcript for an interview session."""
    session = db.execute(
        select(VoiceScreeningSession).where(
            VoiceScreeningSession.id == session_id,
            VoiceScreeningSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    entries = db.execute(
        select(VoiceTranscriptEntry)
        .where(VoiceTranscriptEntry.session_id == session_id)
        .order_by(VoiceTranscriptEntry.timestamp.asc())
    ).scalars().all()

    return {
        "session_id": session_id,
        "transcript": [
            {
                "id": e.id,
                "speaker": e.speaker,
                "text": e.text,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "audio_url": e.audio_url,
            }
            for e in entries
        ],
    }


@router.get("/sessions/{session_id}/scorecard")
def get_interview_scorecard(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the scorecard for an interview session."""
    session = db.execute(
        select(VoiceScreeningSession).where(
            VoiceScreeningSession.id == session_id,
            VoiceScreeningSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.interview_depth == "quick":
        assessment = _load_json(session.assessment_json, default=None)
        if assessment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scorecard not yet generated",
            )
        return {
            "session_id": session_id,
            "depth": "quick",
            "assessment": assessment,
        }

    recruiter_session = db.execute(
        select(RecruiterInterviewSession)
        .where(
            RecruiterInterviewSession.voice_session_id == session_id,
            RecruiterInterviewSession.tenant_id == current_user.tenant_id,
        )
        .options(selectinload(RecruiterInterviewSession.scorecard))
    ).scalar_one_or_none()

    if recruiter_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recruiter session not found for this voice session",
        )

    scorecard = recruiter_session.scorecard
    if scorecard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scorecard not yet generated",
        )

    data = {
        **RecruiterScorecardOut.model_validate(scorecard).model_dump(),
        "technical_evidence": _load_json(scorecard.technical_evidence, default={}),
        "behavioral_evidence": _load_json(scorecard.behavioral_evidence, default={}),
        "communication_evidence": _load_json(scorecard.communication_evidence, default={}),
        "cultural_fit_evidence": _load_json(scorecard.cultural_fit_evidence, default={}),
        "motivation_evidence": _load_json(scorecard.motivation_evidence, default={}),
        "risk_signals_validated": _load_json(scorecard.risk_signals_validated, default={}),
        "gaps_explained": _load_json(scorecard.gaps_explained, default={}),
    }
    return data


@router.post("/sessions/{session_id}/cancel")
async def cancel_interview_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel an interview session and any pending calls."""
    _require_recruiter_or_admin(current_user)

    session = db.execute(
        select(VoiceScreeningSession).where(
            VoiceScreeningSession.id == session_id,
            VoiceScreeningSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.status in ("completed", "cancelled", "ended"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel session in '{session.status}' status",
        )

    from app.backend.services.voice_call_scheduler import cancel_pending_retries
    cancel_pending_retries(session_id)

    session.status = "cancelled"
    session.ended_at = datetime.now(timezone.utc)

    # Cancel associated recruiter session if present
    recruiter_session = db.execute(
        select(RecruiterInterviewSession).where(
            RecruiterInterviewSession.voice_session_id == session_id,
            RecruiterInterviewSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if recruiter_session and recruiter_session.status not in ("completed", "cancelled"):
        orchestrator = RecruiterOrchestrator(db)
        await orchestrator.cancel_interview(recruiter_session.id)

    db.commit()
    return {"session_id": session.id, "status": "cancelled", "message": "Session cancelled"}


@router.post("/sessions/{session_id}/retry", status_code=status.HTTP_201_CREATED)
async def retry_interview_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retry a failed interview session."""
    _require_recruiter_or_admin(current_user)

    session = db.execute(
        select(VoiceScreeningSession).where(
            VoiceScreeningSession.id == session_id,
            VoiceScreeningSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry session in '{session.status}' status",
        )

    if session.interview_depth == "quick":
        from app.backend.services.voice_call_scheduler import schedule_voice_call
        session.status = "scheduled"
        session.retry_count += 1
        db.commit()
        schedule_voice_call(session.id, None)
        return {
            "session_id": session.id,
            "status": session.status,
            "message": "Quick session retry scheduled",
        }

    if not RECRUITER_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Standard/deep interviews are not enabled",
        )

    recruiter_session = db.execute(
        select(RecruiterInterviewSession).where(
            RecruiterInterviewSession.voice_session_id == session_id,
            RecruiterInterviewSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if recruiter_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recruiter session not found for this voice session",
        )

    orchestrator = RecruiterOrchestrator(db)
    try:
        new_session_id = await orchestrator.retry_interview(recruiter_session.id)
    except ValueError as exc:
        logger.warning("Failed to retry recruiter interview: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    new_session = db.execute(
        select(RecruiterInterviewSession).where(
            RecruiterInterviewSession.id == new_session_id,
            RecruiterInterviewSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if new_session is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Retry session creation failed",
        )

    return RecruiterSessionOut.model_validate(new_session)


# ─── Configuration ────────────────────────────────────────────────────────────

@router.get("/config")
def get_interview_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get merged voice + recruiter interview configuration."""
    voice_config = db.execute(
        select(VoiceTenantConfig).where(VoiceTenantConfig.tenant_id == current_user.tenant_id)
    ).scalar_one_or_none()

    if voice_config is None:
        voice_config = VoiceTenantConfig(tenant_id=current_user.tenant_id)
        db.add(voice_config)
        db.commit()
        db.refresh(voice_config)

    recruiter_config = db.execute(
        select(RecruiterAutoTriggerConfig).where(
            RecruiterAutoTriggerConfig.tenant_id == current_user.tenant_id
        )
    ).scalar_one_or_none()

    if recruiter_config is None:
        recruiter_config = RecruiterAutoTriggerConfig(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
        )
        db.add(recruiter_config)
        db.commit()
        db.refresh(recruiter_config)

    return {
        "voice": VoiceTenantConfigOut.model_validate(voice_config).model_dump(),
        "recruiter": {
            **RecruiterAutoTriggerConfigOut.model_validate(recruiter_config).model_dump(),
            "focus_areas": _load_json(recruiter_config.focus_areas, default=[]),
        },
        "recruiter_enabled": RECRUITER_ENABLED,
    }


@router.put("/config")
def update_interview_config(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update merged voice + recruiter interview configuration."""
    _require_recruiter_or_admin(current_user)

    voice_data = body.get("voice")
    recruiter_data = body.get("recruiter")

    voice_config = db.execute(
        select(VoiceTenantConfig).where(VoiceTenantConfig.tenant_id == current_user.tenant_id)
    ).scalar_one_or_none()
    if voice_config is None:
        voice_config = VoiceTenantConfig(tenant_id=current_user.tenant_id)
        db.add(voice_config)

    if voice_data:
        update = VoiceTenantConfigUpdate(**voice_data).model_dump(exclude_unset=True)
        for field, value in update.items():
            setattr(voice_config, field, value)

    recruiter_config = db.execute(
        select(RecruiterAutoTriggerConfig).where(
            RecruiterAutoTriggerConfig.tenant_id == current_user.tenant_id
        )
    ).scalar_one_or_none()
    if recruiter_config is None:
        recruiter_config = RecruiterAutoTriggerConfig(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
        )
        db.add(recruiter_config)

    if recruiter_data:
        update = RecruiterAutoTriggerConfigUpdate(**recruiter_data).model_dump(exclude_unset=True)
        for field, value in update.items():
            if field == "focus_areas" and isinstance(value, list):
                value = json.dumps(value)
            setattr(recruiter_config, field, value)

    db.commit()
    db.refresh(voice_config)
    db.refresh(recruiter_config)

    return {
        "voice": VoiceTenantConfigOut.model_validate(voice_config).model_dump(),
        "recruiter": {
            **RecruiterAutoTriggerConfigOut.model_validate(recruiter_config).model_dump(),
            "focus_areas": _load_json(recruiter_config.focus_areas, default=[]),
        },
        "recruiter_enabled": RECRUITER_ENABLED,
    }


# ─── Analytics ────────────────────────────────────────────────────────────────

@router.get("/analytics")
def get_interview_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return combined analytics for voice and recruiter interviews."""
    tenant_id = current_user.tenant_id

    voice_stats = db.execute(
        select(
            func.count(VoiceScreeningSession.id).label("total"),
            func.count(VoiceScreeningSession.id)
            .filter(VoiceScreeningSession.status == "completed")
            .label("completed"),
            func.count(VoiceScreeningSession.id)
            .filter(VoiceScreeningSession.interview_depth == "quick")
            .label("quick_count"),
            func.count(VoiceScreeningSession.id)
            .filter(VoiceScreeningSession.interview_depth == "deep")
            .label("deep_count"),
            func.avg(VoiceScreeningSession.duration_seconds)
            .filter(VoiceScreeningSession.duration_seconds.isnot(None))
            .label("avg_duration"),
        ).where(VoiceScreeningSession.tenant_id == tenant_id)
    ).one()

    voice_status_rows = db.execute(
        select(
            VoiceScreeningSession.status,
            func.count(VoiceScreeningSession.id).label("cnt"),
        )
        .where(VoiceScreeningSession.tenant_id == tenant_id)
        .group_by(VoiceScreeningSession.status)
    ).all()

    recruiter_stats = db.execute(
        select(
            func.count(RecruiterInterviewSession.id).label("total"),
            func.count(RecruiterInterviewSession.id)
            .filter(RecruiterInterviewSession.status == "completed")
            .label("completed"),
            func.count(RecruiterInterviewSession.id)
            .filter(RecruiterInterviewSession.status == "failed")
            .label("failed"),
            func.count(RecruiterInterviewSession.id)
            .filter(RecruiterInterviewSession.status == "cancelled")
            .label("cancelled"),
        ).where(RecruiterInterviewSession.tenant_id == tenant_id)
    ).one()

    recommendation_rows = db.execute(
        select(
            RecruiterScorecard.recommendation,
            func.count(RecruiterScorecard.id).label("cnt"),
        )
        .where(
            RecruiterScorecard.tenant_id == tenant_id,
            RecruiterScorecard.recommendation.isnot(None),
        )
        .group_by(RecruiterScorecard.recommendation)
    ).all()

    return {
        "tenant_id": tenant_id,
        "voice": {
            "total": voice_stats.total or 0,
            "completed": voice_stats.completed or 0,
            "quick_count": voice_stats.quick_count or 0,
            "deep_count": voice_stats.deep_count or 0,
            "average_duration_seconds": int(voice_stats.avg_duration) if voice_stats.avg_duration else 0,
            "status_breakdown": {r.status: r.cnt for r in voice_status_rows},
        },
        "recruiter": {
            "total": recruiter_stats.total or 0,
            "completed": recruiter_stats.completed or 0,
            "failed": recruiter_stats.failed or 0,
            "cancelled": recruiter_stats.cancelled or 0,
            "recommendation_distribution": {
                r.recommendation: r.cnt for r in recommendation_rows
            },
        },
        "recruiter_enabled": RECRUITER_ENABLED,
    }


# ─── Export ───────────────────────────────────────────────────────────────────

@router.post("/sessions/export")
def export_interview_sessions(
    format: str = Query("csv"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export interview sessions as CSV."""
    if format.lower() != "csv":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV export is supported",
        )

    sessions = db.execute(
        select(VoiceScreeningSession)
        .where(VoiceScreeningSession.tenant_id == current_user.tenant_id)
        .options(
            selectinload(VoiceScreeningSession.candidate),
            selectinload(VoiceScreeningSession.jd),
        )
        .order_by(VoiceScreeningSession.created_at.desc())
    ).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Session ID",
        "Depth",
        "Candidate",
        "Email",
        "Phone",
        "Job Title",
        "Status",
        "Scheduled",
        "Started",
        "Ended",
        "Duration (s)",
        "Retries",
        "Created",
    ])

    for s in sessions:
        writer.writerow([
            s.id,
            s.interview_depth,
            s.candidate.name if s.candidate else "",
            s.candidate.email if s.candidate else "",
            s.phone_number,
            s.jd.name if s.jd else "",
            s.status,
            str(s.scheduled_at) if s.scheduled_at else "",
            str(s.started_at) if s.started_at else "",
            str(s.ended_at) if s.ended_at else "",
            s.duration_seconds or "",
            s.retry_count,
            str(s.created_at) if s.created_at else "",
        ])

    output.seek(0)
    filename = f"interview_sessions_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─── Candidate Comparison ─────────────────────────────────────────────────────

@router.get("/compare")
def compare_interview_scorecards(
    jd_id: int = Query(...),
    candidate_ids: str = Query(...),  # comma-separated: "1,2,3"
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compare completed recruiter scorecards for 1-5 candidates on the same JD."""
    candidate_id_list = []
    for raw in candidate_ids.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            candidate_id_list.append(int(raw))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid candidate_id: {raw}",
            )

    if len(candidate_id_list) < 1 or len(candidate_id_list) > 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must provide between 1 and 5 candidate IDs",
        )

    scorecards = db.execute(
        select(RecruiterScorecard)
        .join(
            RecruiterInterviewSession,
            RecruiterScorecard.session_id == RecruiterInterviewSession.id,
        )
        .where(
            RecruiterScorecard.tenant_id == current_user.tenant_id,
            RecruiterScorecard.candidate_id.in_(candidate_id_list),
            RecruiterInterviewSession.jd_id == jd_id,
            RecruiterInterviewSession.status == "completed",
        )
        .options(
            selectinload(RecruiterScorecard.candidate),
            selectinload(RecruiterScorecard.session),
        )
    ).scalars().all()

    results = []
    for sc in scorecards:
        results.append(
            {
                "candidate_id": sc.candidate_id,
                "candidate_name": sc.candidate.name if sc.candidate else None,
                "candidate_email": sc.candidate.email if sc.candidate else None,
                "recommendation": sc.recommendation,
                "overall_score": sc.overall_score,
                "confidence_level": sc.confidence_level,
                "technical_score": sc.technical_score,
                "behavioral_score": sc.behavioral_score,
                "communication_score": sc.communication_score,
                "cultural_fit_score": sc.cultural_fit_score,
                "motivation_score": sc.motivation_score,
                "executive_summary": sc.executive_summary,
            }
        )

    return {"scorecards": results}


# ─── Internal Callback (Voice Agent → Backend) ────────────────────────────────


def _handle_quick_screen_escalation(session: VoiceScreeningSession, db: Session) -> None:
    """Auto-escalate quick screen to standard interview if score exceeds threshold."""
    # Get tenant config
    config = db.execute(
        select(VoiceTenantConfig).where(VoiceTenantConfig.tenant_id == session.tenant_id)
    ).scalar_one_or_none()

    if not config or not config.auto_escalation_enabled:
        return

    # Check assessment score
    assessment = session.assessment_json
    if isinstance(assessment, str):
        try:
            assessment = json.loads(assessment)
        except (json.JSONDecodeError, TypeError):
            return

    if not assessment:
        return

    score = (
        assessment.get('overall_score')
        or assessment.get('score')
        or assessment.get('match_score')
    )
    if score is None or score < config.auto_escalation_threshold:
        return

    # Auto-create standard interview
    logger.info(
        "Auto-escalating quick screen %s (score=%s) to standard interview",
        session.id, score,
    )

    scheduled_time = datetime.now(timezone.utc) + timedelta(hours=1)

    new_session = VoiceScreeningSession(
        tenant_id=session.tenant_id,
        candidate_id=session.candidate_id,
        jd_id=session.jd_id,
        phone_number=session.phone_number,
        direction="outbound",
        status="scheduled",
        interview_depth="deep",  # DB uses quick/deep; deep == standard
        scheduled_at=scheduled_time,
    )
    db.add(new_session)
    db.flush()

    from app.backend.services.voice_call_scheduler import schedule_voice_call
    schedule_voice_call(new_session.id, scheduled_time)

    db.commit()
    logger.info(
        "Auto-escalation: created session %s scheduled at %s",
        new_session.id, scheduled_time,
    )


async def _generate_scorecard_background(session_id: str) -> None:
    """Background task to generate recruiter scorecard after interview completes."""
    from app.backend.db.database import SessionLocal

    db = SessionLocal()
    try:
        orchestrator = RecruiterOrchestrator(db)
        await orchestrator.on_interview_completed(session_id)
    except Exception as e:
        logger.error(
            "Scorecard generation failed for session %s: %s",
            session_id, e, exc_info=True,
        )
        db.rollback()
        session = db.execute(
            select(RecruiterInterviewSession).where(
                RecruiterInterviewSession.id == session_id
            )
        ).scalar_one_or_none()
        if session and session.status != "completed":
            session.status = "completed"
            db.commit()
    finally:
        db.close()


@router.post("/internal/complete")
async def on_interview_complete(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Internal callback from the voice agent when any interview finishes.

    NOT authenticated via user JWT — uses internal service-to-service trust.

    Payload:
        {
            "session_id": int,      # voice screening session ID
            "result": { ... }       # call result metadata
        }
    """
    body = await request.json()
    session_id = body.get("session_id")
    result = body.get("result", {})

    if not session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session_id required")

    try:
        voice_session_id = int(session_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id must be an integer voice session ID",
        )

    voice_session = db.execute(
        select(VoiceScreeningSession).where(VoiceScreeningSession.id == voice_session_id)
    ).scalar_one_or_none()

    if voice_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice session not found")

    # Update common call metadata
    duration = result.get("duration_seconds")
    if duration is not None:
        voice_session.duration_seconds = duration
    if result.get("consent_recorded") is not None:
        voice_session.consent_recorded = bool(result["consent_recorded"])

    # Store transcript entries if provided
    transcript = result.get("transcript", [])
    if transcript and isinstance(transcript, list):
        started_at = voice_session.started_at or datetime.now(timezone.utc)
        for entry in transcript:
            if not isinstance(entry, dict):
                continue
            ts = entry.get("timestamp")
            if ts is None:
                abs_ts = started_at
            elif isinstance(ts, (int, float)):
                if ts > 1e10:
                    abs_ts = datetime.fromtimestamp(ts, tz=timezone.utc)
                else:
                    abs_ts = started_at + timedelta(seconds=ts)
            else:
                abs_ts = started_at

            db.add(VoiceTranscriptEntry(
                session_id=voice_session_id,
                speaker=entry.get("speaker", "candidate"),
                text=entry.get("text", ""),
                timestamp=abs_ts,
            ))

    db.commit()

    if voice_session.interview_depth == "quick":
        from app.backend.services.voice_screening_service import process_completed_call
        await process_completed_call(db, voice_session_id)

        # Adaptive depth escalation: auto-schedule standard interview if score exceeds threshold
        try:
            _handle_quick_screen_escalation(voice_session, db)
        except Exception as e:
            logger.warning("Auto-escalation check failed: %s", e)

        return {"status": "ok", "session_id": voice_session_id, "depth": "quick"}

    # standard/deep — dispatch to recruiter orchestrator
    recruiter_session = db.execute(
        select(RecruiterInterviewSession).where(
            RecruiterInterviewSession.voice_session_id == voice_session_id
        )
    ).scalar_one_or_none()

    if recruiter_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recruiter session not found for this voice session",
        )

    # Update recruiter session with call data
    recruiter_session.status = "completed"
    recruiter_session.ended_at = datetime.now(timezone.utc)
    if duration is not None:
        recruiter_session.duration_seconds = duration
        if not recruiter_session.started_at:
            recruiter_session.started_at = recruiter_session.ended_at - timedelta(seconds=duration)

    # Store / update questions with candidate responses
    questions_responses = result.get("questions_responses", [])
    if questions_responses:
        from app.backend.models.db_models import RecruiterInterviewQuestion
        existing_questions = {
            q.question_text: q
            for q in db.execute(
                select(RecruiterInterviewQuestion).where(
                    RecruiterInterviewQuestion.session_id == recruiter_session.id
                )
            ).scalars().all()
        }

        for idx, qr in enumerate(questions_responses):
            if not isinstance(qr, dict):
                continue
            question_text = qr.get("question", "")
            existing = existing_questions.get(question_text)

            if existing:
                existing.candidate_response = qr.get("response", "")
                existing.response_duration_seconds = qr.get("response_duration")
                if qr.get("is_follow_up", False):
                    existing.is_follow_up = True
            else:
                db.add(RecruiterInterviewQuestion(
                    id=str(uuid.uuid4()),
                    session_id=recruiter_session.id,
                    sequence_number=idx + 1,
                    category=qr.get("category", "technical"),
                    question_text=question_text,
                    question_context=qr.get("context", ""),
                    candidate_response=qr.get("response", ""),
                    response_duration_seconds=qr.get("response_duration"),
                    is_follow_up=qr.get("is_follow_up", False),
                ))

    db.commit()

    background_tasks.add_task(
        _generate_scorecard_background,
        session_id=recruiter_session.id,
    )

    return {"status": "ok", "session_id": recruiter_session.id, "depth": "deep"}
