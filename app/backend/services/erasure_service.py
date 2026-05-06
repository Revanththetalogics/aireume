"""GDPR data erasure service — anonymizes or deletes tenant-scoped personal data."""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.backend.models.db_models import (
    Candidate,
    CandidateNote,
    Comment,
    ErasureLog,
    ScreeningResult,
    Tenant,
    TranscriptAnalysis,
    TrainingExample,
    User,
)

logger = logging.getLogger(__name__)


def request_erasure(db: Session, tenant_id: int, actor_user_id: int) -> ErasureLog:
    """Create an erasure log entry and return it."""
    log = ErasureLog(
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        status="requested",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    logger.info("Erasure requested: tenant=%s actor=%s log=%s", tenant_id, actor_user_id, log.id)
    return log


def execute_erasure(db: Session, erasure_log_id: int) -> int:
    """Execute data erasure for a tenant. Returns number of records affected.

    WARNING: This operation is IRREVERSIBLE.
    """
    log = db.query(ErasureLog).filter(ErasureLog.id == erasure_log_id).first()
    if not log:
        raise ValueError("Erasure log not found")

    tenant_id = log.tenant_id
    log.status = "in_progress"
    log.started_at = datetime.now(timezone.utc)
    db.commit()

    records_affected = 0
    details = {"tables": {}}

    try:
        # ── 1. Candidates ──────────────────────────────────────────────────────
        candidates = db.query(Candidate).filter(Candidate.tenant_id == tenant_id).all()
        for c in candidates:
            c.name = f"Candidate-{c.id}"
            c.email = f"erased@{tenant_id}.local"
            c.phone = None
            c.raw_resume_text = None
            c.resume_file_data = None
            c.resume_converted_pdf_data = None
            c.parser_snapshot_json = None
            c.ai_professional_summary = None
        records_affected += len(candidates)
        details["tables"]["candidates"] = len(candidates)

        # ── 2. Users (non-admins only) ─────────────────────────────────────────
        users = (
            db.query(User)
            .filter(User.tenant_id == tenant_id, User.role != "admin", User.platform_role.is_(None))
            .all()
        )
        for u in users:
            u.email = f"erased-{u.id}@{tenant_id}.local"
            u.hashed_password = "ERASED"
            u.is_active = False
        records_affected += len(users)
        details["tables"]["users"] = len(users)

        # ── 3. Screening Results ───────────────────────────────────────────────
        results = db.query(ScreeningResult).filter(ScreeningResult.tenant_id == tenant_id).all()
        for r in results:
            r.resume_text = "[erased]"
            r.jd_text = "[erased]"
            r.narrative_json = None
        records_affected += len(results)
        details["tables"]["screening_results"] = len(results)

        # ── 4. Candidate Notes ─────────────────────────────────────────────────
        notes = (
            db.query(CandidateNote)
            .filter(CandidateNote.tenant_id == tenant_id)
            .all()
        )
        for n in notes:
            n.text = "[erased]"
        records_affected += len(notes)
        details["tables"]["candidate_notes"] = len(notes)

        # ── 5. Comments ────────────────────────────────────────────────────────
        comments = (
            db.query(Comment)
            .join(ScreeningResult, Comment.result_id == ScreeningResult.id)
            .filter(ScreeningResult.tenant_id == tenant_id)
            .all()
        )
        for c in comments:
            c.text = "[erased]"
        records_affected += len(comments)
        details["tables"]["comments"] = len(comments)

        # ── 6. Transcript Analyses ─────────────────────────────────────────────
        transcripts = (
            db.query(TranscriptAnalysis)
            .filter(TranscriptAnalysis.tenant_id == tenant_id)
            .all()
        )
        for t in transcripts:
            t.transcript_text = "[erased]"
        records_affected += len(transcripts)
        details["tables"]["transcript_analyses"] = len(transcripts)

        # ── 7. Training Examples ───────────────────────────────────────────────
        training_count = (
            db.query(TrainingExample)
            .filter(TrainingExample.tenant_id == tenant_id)
            .delete(synchronize_session=False)
        )
        records_affected += training_count
        details["tables"]["training_examples"] = training_count

        # ── 8. Suspend tenant ──────────────────────────────────────────────────
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant:
            tenant.subscription_status = "suspended"
            tenant.suspended_at = datetime.now(timezone.utc)
            tenant.suspended_reason = "GDPR data erasure"

        log.status = "completed"
        log.completed_at = datetime.now(timezone.utc)
        log.records_affected = records_affected
        log.details = json.dumps(details)
        db.commit()

        logger.info("Erasure completed: log=%s tenant=%s records=%s", erasure_log_id, tenant_id, records_affected)
        return records_affected

    except Exception as exc:
        log.status = "failed"
        log.details = json.dumps({"error": str(exc), **details})
        db.commit()
        logger.exception("Erasure failed: log=%s tenant=%s", erasure_log_id, tenant_id)
        raise


def get_erasure_status(db: Session, erasure_log_id: int) -> Optional[ErasureLog]:
    """Get the status of an erasure request."""
    return db.query(ErasureLog).filter(ErasureLog.id == erasure_log_id).first()
