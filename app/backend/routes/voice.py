"""
Voice screening routes.

Endpoints:
  GET    /api/voice/settings          — Get tenant's voice bot config
  PUT    /api/voice/settings          — Update tenant's voice bot config
  POST   /api/voice/schedule          — Schedule a voice screening call
  GET    /api/voice/sessions          — List voice sessions for tenant
  GET    /api/voice/sessions/{id}     — Get session detail with transcript
"""
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import (
    User, VoiceTenantConfig, VoiceScreeningSession, VoiceTranscriptEntry, Candidate, RoleTemplate,
)
from app.backend.models.schemas import (
    VoiceTenantConfigUpdate,
    VoiceTenantConfigOut,
    VoiceScreeningSessionOut,
    VoiceTranscriptEntryOut,
    ScheduleVoiceCallRequest,
    ScheduleVoiceCallResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice-screening"])

# ─── Default consent script ───────────────────────────────────────────────────

DEFAULT_CONSENT_SCRIPT = (
    "Before we begin, I need to let you know that this call is being recorded "
    "for hiring evaluation purposes. Your responses will be used to assess your "
    "fit for the position. Do you consent to proceed with this recorded screening?"
)


# ─── Settings ─────────────────────────────────────────────────────────────────

@router.get("/settings", response_model=VoiceTenantConfigOut)
def get_voice_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current tenant's voice screening bot configuration."""
    config = db.execute(
        select(VoiceTenantConfig).where(VoiceTenantConfig.tenant_id == user.tenant_id)
    ).scalar_one_or_none()

    if config is None:
        # Auto-create default config for this tenant
        config = VoiceTenantConfig(tenant_id=user.tenant_id)
        db.add(config)
        db.commit()
        db.refresh(config)

    return config


@router.put("/settings", response_model=VoiceTenantConfigOut)
def update_voice_settings(
    body: VoiceTenantConfigUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current tenant's voice screening bot configuration."""
    config = db.execute(
        select(VoiceTenantConfig).where(VoiceTenantConfig.tenant_id == user.tenant_id)
    ).scalar_one_or_none()

    if config is None:
        config = VoiceTenantConfig(tenant_id=user.tenant_id)
        db.add(config)

    # Apply only non-None fields from the update body
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    return config


# ─── Schedule Call ────────────────────────────────────────────────────────────

@router.post("/schedule", response_model=ScheduleVoiceCallResponse)
def schedule_voice_call(
    body: ScheduleVoiceCallRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Schedule a voice screening call for a candidate."""
    # Verify candidate belongs to this tenant
    candidate = db.execute(
        select(Candidate).where(
            Candidate.id == body.candidate_id,
            Candidate.tenant_id == user.tenant_id,
        )
    ).scalar_one_or_none()

    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found or not in your tenant")

    # Ensure config exists
    config = db.execute(
        select(VoiceTenantConfig).where(VoiceTenantConfig.tenant_id == user.tenant_id)
    ).scalar_one_or_none()
    if config is None:
        config = VoiceTenantConfig(tenant_id=user.tenant_id)
        db.add(config)
        db.commit()

    # Create session
    session = VoiceScreeningSession(
        tenant_id=user.tenant_id,
        candidate_id=body.candidate_id,
        jd_id=body.jd_id,
        phone_number=body.phone_number,
        direction="outbound",
        status="scheduled",
        scheduled_at=body.scheduled_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Schedule the call via APScheduler
    from app.backend.services.voice_call_scheduler import schedule_voice_call
    schedule_voice_call(session.id, body.scheduled_at)

    return ScheduleVoiceCallResponse(
        session_id=session.id,
        status=session.status,
        scheduled_at=session.scheduled_at,
        phone_number=session.phone_number,
    )


# ─── Sessions List ────────────────────────────────────────────────────────────

@router.get("/sessions")
def list_voice_sessions(
    candidate_id: int = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List voice screening sessions for the current tenant."""
    query = (
        select(VoiceScreeningSession)
        .where(VoiceScreeningSession.tenant_id == user.tenant_id)
        .options(
            selectinload(VoiceScreeningSession.candidate),
            selectinload(VoiceScreeningSession.jd),
        )
    )

    if candidate_id is not None:
        query = query.where(VoiceScreeningSession.candidate_id == candidate_id)
    if status is not None:
        query = query.where(VoiceScreeningSession.status == status)

    query = query.order_by(VoiceScreeningSession.created_at.desc()).limit(limit).offset(offset)
    sessions = db.execute(query).scalars().all()

    results = []
    for s in sessions:
        out = VoiceScreeningSessionOut.model_validate(s)
        out.candidate_name = s.candidate.name if s.candidate else None
        out.candidate_email = s.candidate.email if s.candidate else None
        out.jd_title = s.jd.name if s.jd else None
        results.append(out)
    return results


# ── Session Detail ───────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}")
def get_voice_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a voice screening session detail with transcript entries."""
    session = db.execute(
        select(VoiceScreeningSession)
        .where(
            VoiceScreeningSession.id == session_id,
            VoiceScreeningSession.tenant_id == user.tenant_id,
        )
        .options(
            selectinload(VoiceScreeningSession.candidate),
            selectinload(VoiceScreeningSession.jd),
        )
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="Voice session not found")

    # Load transcript entries
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
    result_dict["transcript"] = [VoiceTranscriptEntryOut.model_validate(e) for e in entries]

    return result_dict


# ─── Internal Endpoints (service-to-service, no auth) ─────────────────────────
# These are called by the voice-agent container over the internal Docker network.
# They are NOT exposed through Nginx (only /api/voice/* is proxied).

@router.get("/internal/config/{tenant_id}")
def get_voice_config_internal(tenant_id: int, db: Session = Depends(get_db)):
    """Get voice tenant config — called by voice-agent (internal, no auth)."""
    config = db.execute(
        select(VoiceTenantConfig).where(VoiceTenantConfig.tenant_id == tenant_id)
    ).scalar_one_or_none()

    if config is None:
        return {}

    return {
        "bot_name": config.bot_name,
        "bot_voice_gender": config.bot_voice_gender,
        "greeting_style": config.greeting_style,
        "call_duration_max": config.call_duration_max,
        "call_duration_min": config.call_duration_min,
        "consent_script": config.consent_script,
        "outbound_phone_number": config.outbound_phone_number,
        "caller_id_name": config.caller_id_name,
        "assessment_detail_level": config.assessment_detail_level,
        "follow_up_aggressiveness": config.follow_up_aggressiveness,
    }


@router.get("/internal/candidate/{tenant_id}/{candidate_id}")
def get_candidate_internal(tenant_id: int, candidate_id: int, db: Session = Depends(get_db)):
    """Get candidate info — called by voice-agent (internal, no auth)."""
    candidate = db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()

    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return {
        "id": candidate.id,
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
    }


@router.patch("/sessions/{session_id}")
def update_voice_session(
    session_id: int,
    body: dict,
    db: Session = Depends(get_db),
):
    """Update a voice screening session — called by voice-agent or internal use."""
    session = db.execute(
        select(VoiceScreeningSession).where(VoiceScreeningSession.id == session_id)
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="Voice session not found")

    allowed_fields = {
        "status", "started_at", "ended_at", "transcript_json", "assessment_json",
        "duration_seconds", "retry_count", "consent_recorded", "call_sid", "error_log",
    }

    for field_name, value in body.items():
        if field_name in allowed_fields:
            setattr(session, field_name, value)

    db.commit()
    db.refresh(session)
    return {"id": session.id, "status": session.status}


# ─── Reschedule / Cancel ─────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/reschedule")
def reschedule_voice_session(
    session_id: int,
    body: ScheduleVoiceCallRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reschedule a voice screening call to a new time."""
    session = db.execute(
        select(VoiceScreeningSession).where(
            VoiceScreeningSession.id == session_id,
            VoiceScreeningSession.tenant_id == user.tenant_id,
        )
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="Voice session not found")

    if session.status not in ("scheduled", "no_answer", "failed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reschedule session in '{session.status}' status",
        )

    # Cancel any existing APScheduler jobs for this session
    from app.backend.services.voice_call_scheduler import cancel_pending_retries, schedule_voice_call
    cancel_pending_retries(session_id)

    # Update session
    session.status = "scheduled"
    session.scheduled_at = body.scheduled_at
    session.phone_number = body.phone_number or session.phone_number
    if body.jd_id is not None:
        session.jd_id = body.jd_id
    db.commit()

    # Schedule the new call
    schedule_voice_call(session_id, body.scheduled_at)

    return {
        "session_id": session.id,
        "status": session.status,
        "scheduled_at": session.scheduled_at,
        "message": "Call rescheduled successfully",
    }


@router.post("/sessions/{session_id}/cancel")
def cancel_voice_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a voice screening call and all pending retries."""
    session = db.execute(
        select(VoiceScreeningSession).where(
            VoiceScreeningSession.id == session_id,
            VoiceScreeningSession.tenant_id == user.tenant_id,
        )
    ).scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="Voice session not found")

    if session.status in ("completed", "cancelled", "ended"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel session in '{session.status}' status",
        )

    # Cancel any pending APScheduler jobs
    from app.backend.services.voice_call_scheduler import cancel_pending_retries
    cancel_pending_retries(session_id)

    session.status = "cancelled"
    db.commit()

    return {"session_id": session.id, "status": "cancelled", "message": "Call cancelled"}
