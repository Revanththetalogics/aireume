"""
AI Recruiter routes.

Endpoints:
  POST /api/recruiter/sessions                       — Initiate an AI recruiter interview
  GET  /api/recruiter/sessions                       — List AI recruiter sessions for tenant
  GET  /api/recruiter/sessions/{session_id}          — Get session detail
  GET  /api/recruiter/sessions/{session_id}/transcript — Get session transcript questions
  GET  /api/recruiter/sessions/{session_id}/scorecard — Get session scorecard
  POST /api/recruiter/sessions/{session_id}/cancel   — Cancel a session
  POST /api/recruiter/sessions/{session_id}/retry    — Retry a failed session
  GET  /api/recruiter/config                         — Get auto-trigger config
  PUT  /api/recruiter/config                         — Update auto-trigger config
  GET  /api/recruiter/candidates/{candidate_id}/sessions — List sessions for a candidate
  GET  /api/recruiter/analytics                      — Aggregated analytics
  POST /api/recruiter/sessions/export                — Export sessions as CSV
"""
import csv
import io
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import (
    Candidate,
    RecruiterAutoTriggerConfig,
    RecruiterInterviewQuestion,
    RecruiterInterviewSession,
    RecruiterScorecard,
    RoleTemplate,
    ScreeningResult,
    User,
)
from app.backend.models.schemas import (
    RecruiterAnalyticsOut,
    RecruiterAutoTriggerConfigOut,
    RecruiterAutoTriggerConfigUpdate,
    RecruiterQuestionOut,
    RecruiterScorecardOut,
    RecruiterSessionCreate,
    RecruiterSessionDetail,
    RecruiterSessionOut,
)
from app.backend.services.recruiter.orchestrator import RecruiterOrchestrator

logger = logging.getLogger("aria.recruiter")

router = APIRouter(prefix="/api/recruiter", tags=["recruiter"])

# Feature flag for the AI Recruiter module
RECRUITER_ENABLED = os.getenv("RECRUITER_INTERVIEW_ENABLED", "true").lower() == "true"


def require_recruiter_enabled() -> None:
    """Raise 404 if the AI Recruiter feature is disabled."""
    if not RECRUITER_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI Recruiter feature is not enabled",
        )


# Apply the feature flag to every route in this module
router.dependencies.append(Depends(require_recruiter_enabled))

# Roles allowed to initiate / cancel / retry AI recruiter sessions
_RECRUITER_ADMIN_ROLES = {"admin", "recruiter"}

# Cancellable lifecycle statuses
_CANCELLABLE_STATUSES = {"pending_strategy", "strategy_ready", "scheduled"}


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
    if current_user.role not in _RECRUITER_ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiter or admin access required",
        )


def _require_admin(current_user: User) -> None:
    """Raise 403 if the user is not an admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


# ─── Session Management ───────────────────────────────────────────────────────

@router.post(
    "/sessions",
    response_model=RecruiterSessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_recruiter_session(
    body: RecruiterSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Initiate a new AI recruiter interview session."""
    _require_recruiter_or_admin(current_user)

    # Verify candidate belongs to the current tenant
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

    orchestrator = RecruiterOrchestrator(db)
    try:
        session_id = await orchestrator.initiate_interview(
            tenant_id=current_user.tenant_id,
            candidate_id=body.candidate_id,
            jd_id=body.jd_id,
            screening_result_id=body.screening_result_id,
            trigger_type=body.trigger_type or "manual",
            config=body.interview_config_json or {},
            created_by=current_user.id,
        )
    except ValueError as exc:
        logger.warning("Failed to initiate recruiter interview: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    session = db.execute(
        select(RecruiterInterviewSession).where(
            RecruiterInterviewSession.id == session_id,
            RecruiterInterviewSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session creation failed",
        )

    return RecruiterSessionOut.model_validate(session)


@router.get("/sessions")
def list_recruiter_sessions(
    status: Optional[str] = Query(None),
    candidate_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List AI recruiter sessions for the current tenant."""
    base_query = select(RecruiterInterviewSession).where(
        RecruiterInterviewSession.tenant_id == current_user.tenant_id
    )

    if status:
        base_query = base_query.where(RecruiterInterviewSession.status == status)
    if candidate_id is not None:
        base_query = base_query.where(
            RecruiterInterviewSession.candidate_id == candidate_id
        )

    count_query = select(func.count()).select_from(base_query.subquery())
    total = db.execute(count_query).scalar() or 0

    sessions = db.execute(
        base_query.order_by(RecruiterInterviewSession.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    return {
        "sessions": [RecruiterSessionOut.model_validate(s) for s in sessions],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/sessions/{session_id}", response_model=RecruiterSessionDetail)
def get_recruiter_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full detail for an AI recruiter session, including strategy and config."""
    session = db.execute(
        select(RecruiterInterviewSession).where(
            RecruiterInterviewSession.id == session_id,
            RecruiterInterviewSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    data = {
        **RecruiterSessionOut.model_validate(session).model_dump(),
        "interview_strategy_json": _load_json(
            session.interview_strategy_json, default={}
        ),
        "interview_config_json": _load_json(
            session.interview_config_json, default={}
        ),
    }
    return RecruiterSessionDetail.model_validate(data)


@router.get("/sessions/{session_id}/transcript")
def get_recruiter_transcript(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the ordered list of questions for a session."""
    session = db.execute(
        select(RecruiterInterviewSession).where(
            RecruiterInterviewSession.id == session_id,
            RecruiterInterviewSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    questions = db.execute(
        select(RecruiterInterviewQuestion)
        .where(RecruiterInterviewQuestion.session_id == session_id)
        .order_by(RecruiterInterviewQuestion.sequence_number.asc())
    ).scalars().all()

    return {
        "questions": [RecruiterQuestionOut.model_validate(q) for q in questions]
    }


@router.get("/sessions/{session_id}/scorecard", response_model=RecruiterScorecardOut)
def get_recruiter_scorecard(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the scorecard for a completed AI recruiter session."""
    session = db.execute(
        select(RecruiterInterviewSession).where(
            RecruiterInterviewSession.id == session_id,
            RecruiterInterviewSession.tenant_id == current_user.tenant_id,
        )
        .options(selectinload(RecruiterInterviewSession.scorecard))
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    scorecard = session.scorecard
    if scorecard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scorecard not yet generated",
        )

    data = {
        **RecruiterScorecardOut.model_validate(scorecard).model_dump(),
        "technical_evidence": _load_json(
            scorecard.technical_evidence, default={}
        ),
        "behavioral_evidence": _load_json(
            scorecard.behavioral_evidence, default={}
        ),
        "communication_evidence": _load_json(
            scorecard.communication_evidence, default={}
        ),
        "cultural_fit_evidence": _load_json(
            scorecard.cultural_fit_evidence, default={}
        ),
        "motivation_evidence": _load_json(
            scorecard.motivation_evidence, default={}
        ),
        "risk_signals_validated": _load_json(
            scorecard.risk_signals_validated, default={}
        ),
        "gaps_explained": _load_json(scorecard.gaps_explained, default={}),
    }
    return RecruiterScorecardOut.model_validate(data)


@router.post(
    "/sessions/{session_id}/cancel",
    response_model=RecruiterSessionOut,
)
async def cancel_recruiter_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a recruiter session that has not yet started."""
    _require_recruiter_or_admin(current_user)

    session = db.execute(
        select(RecruiterInterviewSession).where(
            RecruiterInterviewSession.id == session_id,
            RecruiterInterviewSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.status not in _CANCELLABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel session in '{session.status}' status",
        )

    orchestrator = RecruiterOrchestrator(db)
    await orchestrator.cancel_interview(session_id)

    db.refresh(session)
    return RecruiterSessionOut.model_validate(session)


@router.post(
    "/sessions/{session_id}/retry",
    response_model=RecruiterSessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def retry_recruiter_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retry a failed AI recruiter interview by creating a new session."""
    _require_recruiter_or_admin(current_user)

    session = db.execute(
        select(RecruiterInterviewSession).where(
            RecruiterInterviewSession.id == session_id,
            RecruiterInterviewSession.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry session in '{session.status}' status",
        )

    orchestrator = RecruiterOrchestrator(db)
    try:
        new_session_id = await orchestrator.retry_interview(session_id)
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


# ─── Auto-Trigger Configuration ───────────────────────────────────────────────

@router.get("/config", response_model=RecruiterAutoTriggerConfigOut)
def get_recruiter_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the tenant's AI recruiter auto-trigger configuration."""
    _require_admin(current_user)

    config = db.execute(
        select(RecruiterAutoTriggerConfig).where(
            RecruiterAutoTriggerConfig.tenant_id == current_user.tenant_id
        )
    ).scalar_one_or_none()

    if config is None:
        config = RecruiterAutoTriggerConfig(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    data = {
        **RecruiterAutoTriggerConfigOut.model_validate(config).model_dump(),
        "focus_areas": _load_json(config.focus_areas, default=[]),
    }
    return RecruiterAutoTriggerConfigOut.model_validate(data)


@router.put("/config", response_model=RecruiterAutoTriggerConfigOut)
def update_recruiter_config(
    body: RecruiterAutoTriggerConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the tenant's AI recruiter auto-trigger configuration."""
    _require_admin(current_user)

    config = db.execute(
        select(RecruiterAutoTriggerConfig).where(
            RecruiterAutoTriggerConfig.tenant_id == current_user.tenant_id
        )
    ).scalar_one_or_none()

    if config is None:
        config = RecruiterAutoTriggerConfig(
            id=str(uuid.uuid4()),
            tenant_id=current_user.tenant_id,
        )
        db.add(config)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "focus_areas" and isinstance(value, list):
            value = json.dumps(value)
        setattr(config, field, value)

    db.commit()
    db.refresh(config)

    data = {
        **RecruiterAutoTriggerConfigOut.model_validate(config).model_dump(),
        "focus_areas": _load_json(config.focus_areas, default=[]),
    }
    return RecruiterAutoTriggerConfigOut.model_validate(data)


# ─── Candidate Sessions ───────────────────────────────────────────────────────

@router.get(
    "/candidates/{candidate_id}/sessions",
    response_model=List[RecruiterSessionOut],
)
def list_candidate_recruiter_sessions(
    candidate_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all AI recruiter sessions for a specific candidate."""
    candidate = db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found or not in your tenant",
        )

    sessions = db.execute(
        select(RecruiterInterviewSession)
        .where(
            RecruiterInterviewSession.tenant_id == current_user.tenant_id,
            RecruiterInterviewSession.candidate_id == candidate_id,
        )
        .order_by(RecruiterInterviewSession.created_at.desc())
    ).scalars().all()

    return [RecruiterSessionOut.model_validate(s) for s in sessions]


# ─── Analytics ────────────────────────────────────────────────────────────────

@router.get("/analytics", response_model=RecruiterAnalyticsOut)
def get_recruiter_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return aggregated analytics for AI recruiter sessions."""
    tenant_id = current_user.tenant_id

    session_stats = db.execute(
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
            func.avg(RecruiterInterviewSession.duration_seconds)
            .filter(RecruiterInterviewSession.duration_seconds.isnot(None))
            .label("avg_duration"),
        ).where(RecruiterInterviewSession.tenant_id == tenant_id)
    ).one()

    total = session_stats.total or 0
    completed = session_stats.completed or 0
    failed = session_stats.failed or 0
    cancelled = session_stats.cancelled or 0
    avg_duration = round(session_stats.avg_duration, 1) if session_stats.avg_duration else None

    # Status distribution
    status_rows = db.execute(
        select(
            RecruiterInterviewSession.status,
            func.count(RecruiterInterviewSession.id).label("cnt"),
        )
        .where(RecruiterInterviewSession.tenant_id == tenant_id)
        .group_by(RecruiterInterviewSession.status)
    ).all()
    sessions_by_status = {r.status: r.cnt for r in status_rows}

    # Recommendation distribution and average overall score from scorecards
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
    recommendation_distribution = {r.recommendation: r.cnt for r in recommendation_rows}

    avg_score_row = db.execute(
        select(
            func.avg(RecruiterScorecard.overall_score)
            .filter(RecruiterScorecard.overall_score.isnot(None))
            .label("avg_score")
        ).where(RecruiterScorecard.tenant_id == tenant_id)
    ).scalar_one_or_none()
    average_overall_score = round(avg_score_row, 1) if avg_score_row else None

    # Score distribution buckets
    scorecard_rows = db.execute(
        select(RecruiterScorecard.overall_score)
        .where(
            RecruiterScorecard.tenant_id == tenant_id,
            RecruiterScorecard.overall_score.isnot(None),
        )
    ).scalars().all()

    score_distribution = {
        "0-49": 0,
        "50-69": 0,
        "70-84": 0,
        "85-100": 0,
    }
    for score in scorecard_rows:
        if score < 50:
            score_distribution["0-49"] += 1
        elif score < 70:
            score_distribution["50-69"] += 1
        elif score < 85:
            score_distribution["70-84"] += 1
        else:
            score_distribution["85-100"] += 1

    # Sessions created this calendar month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    sessions_this_month = db.execute(
        select(func.count(RecruiterInterviewSession.id))
        .where(
            RecruiterInterviewSession.tenant_id == tenant_id,
            RecruiterInterviewSession.created_at >= month_start,
        )
    ).scalar() or 0

    return RecruiterAnalyticsOut(
        tenant_id=tenant_id,
        total_sessions=total,
        completed_sessions=completed,
        failed_sessions=failed,
        cancelled_sessions=cancelled,
        average_duration_seconds=avg_duration,
        average_overall_score=average_overall_score,
        recommendation_distribution=recommendation_distribution,
        sessions_by_status=sessions_by_status,
        score_distribution=score_distribution,
        sessions_this_month=sessions_this_month,
    )


# ─── Export ───────────────────────────────────────────────────────────────────

@router.post("/sessions/export")
def export_recruiter_sessions(
    format: str = Query("csv"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export AI recruiter sessions as CSV."""
    if format.lower() != "csv":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV export is supported",
        )

    sessions = db.execute(
        select(RecruiterInterviewSession)
        .where(RecruiterInterviewSession.tenant_id == current_user.tenant_id)
        .options(
            selectinload(RecruiterInterviewSession.candidate),
            selectinload(RecruiterInterviewSession.jd),
        )
        .order_by(RecruiterInterviewSession.created_at.desc())
    ).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Session ID",
        "Candidate",
        "Email",
        "Job Title",
        "Status",
        "Trigger Type",
        "Started At",
        "Ended At",
        "Duration (s)",
        "Created At",
    ])

    for s in sessions:
        writer.writerow([
            s.id,
            s.candidate.name if s.candidate else "",
            s.candidate.email if s.candidate else "",
            s.jd.name if s.jd else "",
            s.status,
            s.trigger_type,
            str(s.started_at) if s.started_at else "",
            str(s.ended_at) if s.ended_at else "",
            s.duration_seconds or "",
            str(s.created_at) if s.created_at else "",
        ])

    output.seek(0)
    filename = f"recruiter_sessions_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
