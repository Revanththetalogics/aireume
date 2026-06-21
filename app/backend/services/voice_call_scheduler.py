"""
Voice Call Scheduler — APScheduler integration for voice screening calls.

Handles:
  - Scheduling outbound calls at specific times
  - Business hours enforcement (timezone-aware)
  - 3-tier retry logic (24h → 48h → escalate)
  - Callback cancellation (inbound call cancels pending retries)
  - Escalation notification

Follows the same APScheduler pattern as scheduler.py.
"""
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select, and_, or_

from app.backend.db.database import SessionLocal
from app.backend.models.db_models import (
    VoiceTenantConfig, VoiceScreeningSession, Candidate,
)

logger = logging.getLogger(__name__)

# Shared scheduler instance (started by main.py lifespan)
voice_scheduler = BackgroundScheduler()

# Voice Agent dispatch URL
VOICE_AGENT_URL = os.environ.get("VOICE_AGENT_URL", "http://voice-agent:8002")


# ─── Business Hours Enforcement ───────────────────────────────────────────────

def is_within_business_hours(
    dt: datetime,
    config: VoiceTenantConfig,
) -> bool:
    """
    Check if a datetime falls within the tenant's business hours.

    Uses tenant's timezone, business_hours_start/end, and allowed_days.
    """
    import zoneinfo

    tz_name = config.timezone or "UTC"
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except (zoneinfo.ZoneInfoNotFoundError, Exception):
        tz = timezone.utc

    local_dt = dt.astimezone(tz)

    # Check day of week (Monday=1 .. Sunday=7)
    allowed_days = config.allowed_days or [1, 2, 3, 4, 5]
    if isinstance(allowed_days, str):
        try:
            allowed_days = json.loads(allowed_days)
        except (json.JSONDecodeError, TypeError):
            allowed_days = [1, 2, 3, 4, 5]

    if local_dt.isoweekday() not in allowed_days:
        return False

    # Check time of day
    try:
        start_h, start_m = map(int, (config.business_hours_start or "09:00").split(":"))
        end_h, end_m = map(int, (config.business_hours_end or "18:00").split(":"))
    except (ValueError, AttributeError):
        start_h, start_m = 9, 0
        end_h, end_m = 18, 0

    current_minutes = local_dt.hour * 60 + local_dt.minute
    start_minutes = start_h * 60 + start_m
    end_minutes = end_h * 60 + end_m

    return start_minutes <= current_minutes <= end_minutes


def adjust_to_business_hours(
    dt: datetime,
    config: VoiceTenantConfig,
) -> datetime:
    """
    If dt is outside business hours, move it to the next valid slot.
    """
    import zoneinfo

    tz_name = config.timezone or "UTC"
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except (zoneinfo.ZoneInfoNotFoundError, Exception):
        tz = timezone.utc

    if is_within_business_hours(dt, config):
        return dt

    # Move to next day's start
    local_dt = dt.astimezone(tz)
    next_day = (local_dt + timedelta(days=1)).replace(
        hour=int((config.business_hours_start or "09:00").split(":")[0]),
        minute=int((config.business_hours_start or "09:00").split(":")[1]),
        second=0,
        microsecond=0,
    )

    # Skip non-allowed days
    allowed_days = config.allowed_days or [1, 2, 3, 4, 5]
    if isinstance(allowed_days, str):
        try:
            allowed_days = json.loads(allowed_days)
        except (json.JSONDecodeError, TypeError):
            allowed_days = [1, 2, 3, 4, 5]

    for _ in range(7):
        if next_day.isoweekday() in allowed_days:
            return next_day.astimezone(timezone.utc)
        next_day += timedelta(days=1)

    return next_day.astimezone(timezone.utc)


# ─── Call Execution ────────────────────────────────────────────────────────────

def execute_scheduled_call(session_id: int):
    """
    Execute a scheduled voice screening call.

    Called by APScheduler at the scheduled time.
    Dispatches the call via the voice-agent's HTTP /dispatch endpoint,
    which creates a LiveKit room and initiates a SIP outbound call.
    """
    db = SessionLocal()
    try:
        session = db.execute(
            select(VoiceScreeningSession).where(VoiceScreeningSession.id == session_id)
        ).scalar_one_or_none()

        if session is None:
            logger.error("Scheduled call session %d not found", session_id)
            return

        # Skip if already completed/cancelled
        if session.status in ("completed", "failed", "voicemail"):
            logger.info("Session %d already in terminal state: %s", session_id, session.status)
            return

        # Update status to ringing
        session.status = "ringing"
        session.started_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "Executing voice screening call: session=%d candidate=%d phone=%s",
            session_id, session.candidate_id, session.phone_number,
        )

        # Fetch candidate name for context
        candidate = db.execute(
            select(Candidate).where(Candidate.id == session.candidate_id)
        ).scalar_one_or_none()
        candidate_name = candidate.name if candidate else "Candidate"

        # Get JD title if available
        jd_title = None
        if session.jd_id:
            try:
                from app.backend.models.db_models import RoleTemplate
                jd = db.execute(
                    select(RoleTemplate).where(RoleTemplate.id == session.jd_id)
                ).scalar_one_or_none()
                jd_title = jd.name if jd else None
            except Exception:
                pass

        # Dispatch via voice-agent HTTP API
        dispatch_payload = {
            "session_id": session.id,
            "phone_number": session.phone_number,
            "candidate_name": candidate_name,
            "tenant_id": session.tenant_id,
            "candidate_id": session.candidate_id,
            "jd_title": jd_title,
            "jd_must_have_skills": [],
        }

        resp = httpx.post(
            f"{VOICE_AGENT_URL}/dispatch",
            json=dispatch_payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        result = resp.json()

        if result.get("success"):
            session.status = "in_progress"
            logger.info(
                "Call dispatched: session=%d room=%s",
                session_id, result.get("room_name"),
            )
        else:
            session.status = "failed"
            session.error_log = result.get("message", "Dispatch returned failure")
            logger.error("Dispatch failed for session %d: %s", session_id, result.get("message"))

        db.commit()

    except Exception as e:
        logger.error("Failed to execute scheduled call %d: %s", session_id, e, exc_info=True)
        try:
            session.status = "failed"
            session.error_log = str(e)
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ─── Retry Logic ──────────────────────────────────────────────────────────────

def process_voice_retries():
    """
    Process all due voice call retries.

    Checks for sessions in 'no_answer' or 'failed' status where:
    - retry_count < max_retries
    - Next retry time has elapsed (based on retry_intervals)
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # Find sessions needing retry
        sessions = db.execute(
            select(VoiceScreeningSession).where(
                VoiceScreeningSession.status.in_(["no_answer", "failed"]),
                VoiceScreeningSession.direction == "outbound",
            )
        ).scalars().all()

        retried = 0
        escalated = 0

        for session in sessions:
            config = db.execute(
                select(VoiceTenantConfig).where(
                    VoiceTenantConfig.tenant_id == session.tenant_id
                )
            ).scalar_one_or_none()

            if config is None:
                continue

            max_retries = config.max_retries or 3
            retry_intervals = config.retry_intervals or [24, 48]
            if isinstance(retry_intervals, str):
                try:
                    retry_intervals = json.loads(retry_intervals)
                except (json.JSONDecodeError, TypeError):
                    retry_intervals = [24, 48]

            if session.retry_count >= max_retries:
                # All retries exhausted — escalate
                session.status = "escalated"
                db.commit()
                if config.escalation_contact_id:
                    logger.warning(
                        "Session %d: all retries exhausted, escalating to contact %d",
                        session.id, config.escalation_contact_id,
                    )
                # Send escalation notification
                try:
                    from app.backend.services.voice_screening_service import _notify_escalation
                    candidate = db.execute(
                        select(Candidate).where(Candidate.id == session.candidate_id)
                    ).scalar_one_or_none()
                    _notify_escalation(db, session, candidate, config)
                except Exception as notify_err:
                    logger.warning("Failed to send escalation notification: %s", notify_err)
                escalated += 1
                continue

            # Check if enough time has elapsed since last attempt
            interval_hours = retry_intervals[min(session.retry_count, len(retry_intervals) - 1)]
            last_attempt = session.updated_at or session.created_at
            if last_attempt and (now - last_attempt).total_seconds() < interval_hours * 3600:
                continue  # Not yet time to retry

            # Schedule retry
            session.retry_count += 1
            session.status = "scheduled"
            db.commit()

            # Schedule the retry call via APScheduler
            retry_time = now + timedelta(minutes=5)  # Immediate re-schedule
            adjusted_time = adjust_to_business_hours(retry_time, config)

            voice_scheduler.add_job(
                execute_scheduled_call,
                trigger="date",
                run_date=adjusted_time,
                args=[session.id],
                id=f"voice_retry_{session.id}_{session.retry_count}",
                replace_existing=True,
            )

            logger.info(
                "Session %d: retry %d/%d scheduled for %s",
                session.id, session.retry_count, max_retries, adjusted_time.isoformat(),
            )
            retried += 1

        if retried or escalated:
            logger.info("Voice retry processing: %d retried, %d escalated", retried, escalated)

    except Exception as e:
        logger.error("Voice retry processing failed: %s", e, exc_info=True)
    finally:
        db.close()


def cancel_pending_retries(session_id: int):
    """
    Cancel all pending retries for a session.

    Called when a candidate calls back (inbound callback cancels remaining retries).
    """
    db = SessionLocal()
    try:
        session = db.execute(
            select(VoiceScreeningSession).where(VoiceScreeningSession.id == session_id)
        ).scalar_one_or_none()

        if session is None:
            return

        # Remove any scheduled APScheduler jobs for this session
        for job in voice_scheduler.get_jobs():
            if f"voice_call_{session_id}" in job.id or f"voice_retry_{session_id}" in job.id:
                job.remove()
                logger.info("Cancelled scheduled job %s", job.id)

        logger.info("Cancelled all pending retries for session %d", session_id)

    except Exception as e:
        logger.error("Failed to cancel retries for session %d: %s", session_id, e)
    finally:
        db.close()


# ─── Scheduling API ───────────────────────────────────────────────────────────

def schedule_voice_call(session_id: int, scheduled_at: Optional[datetime] = None):
    """
    Schedule a voice screening call.

    If scheduled_at is None, schedules for now (immediate).
    When a recruiter explicitly provides scheduled_at, the time is respected
    as-is — business hours adjustment only applies to auto/immediate scheduling
    and retries, never to a deliberate user choice.
    """
    db = SessionLocal()
    try:
        session = db.execute(
            select(VoiceScreeningSession).where(VoiceScreeningSession.id == session_id)
        ).scalar_one_or_none()

        if session is None:
            logger.error("Cannot schedule — session %d not found", session_id)
            return

        config = db.execute(
            select(VoiceTenantConfig).where(VoiceTenantConfig.tenant_id == session.tenant_id)
        ).scalar_one_or_none()

        # Determine call time
        if scheduled_at:
            # Recruiter explicitly chose a time — respect it without adjustment
            call_time = scheduled_at
        else:
            # Immediate / auto — apply business hours guard rail
            call_time = datetime.now(timezone.utc)
            if config:
                call_time = adjust_to_business_hours(call_time, config)

        # Update session
        session.scheduled_at = call_time
        session.status = "scheduled"
        db.commit()

        # Schedule via APScheduler
        voice_scheduler.add_job(
            execute_scheduled_call,
            trigger="date",
            run_date=call_time,
            args=[session_id],
            id=f"voice_call_{session_id}",
            replace_existing=True,
        )

        logger.info(
            "Voice call scheduled: session=%d time=%s phone=%s",
            session_id, call_time.isoformat(), session.phone_number,
        )

    except Exception as e:
        logger.error("Failed to schedule voice call %d: %s", session_id, e, exc_info=True)
    finally:
        db.close()


# ─── Scheduler Lifecycle ──────────────────────────────────────────────────────

def start_voice_scheduler():
    """Start the voice call scheduler with periodic retry processing."""
    if voice_scheduler.running:
        return

    # Process retries every 15 minutes
    voice_scheduler.add_job(
        process_voice_retries,
        trigger="date",  # Run once at startup to catch any due retries
        id="voice_retry_initial",
        replace_existing=True,
    )

    voice_scheduler.add_job(
        process_voice_retries,
        trigger="interval",
        minutes=15,
        id="voice_retry_periodic",
        replace_existing=True,
        misfire_grace_time=300,
    )

    voice_scheduler.start()
    logger.info("Voice call scheduler started (retry check: every 15 min)")


def stop_voice_scheduler():
    """Gracefully stop the voice call scheduler."""
    if voice_scheduler.running:
        voice_scheduler.shutdown(wait=False)
        logger.info("Voice call scheduler stopped")
