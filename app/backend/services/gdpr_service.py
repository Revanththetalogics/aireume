"""GDPR data retention and right-to-be-forgotten service.

Provides:
- Configurable retention periods per data category
- Automated cleanup of expired candidate data
- Right-to-be-forgotten (hard delete) implementation
- Data export for portability (GDPR Article 20)
- Audit trail for all deletion operations
"""

import logging
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Default retention periods (in days) per data category
DEFAULT_RETENTION_DAYS = {
    "candidate_data": 730,       # 2 years
    "screening_results": 730,    # 2 years
    "voice_screening": 365,      # 1 year
    "audit_logs": 2555,          # 7 years (legal compliance)
    "jd_cache": 180,             # 6 months
    "resume_text": 730,          # 2 years
    "analysis_results": 730,     # 2 years
}

# Fields to anonymize (replace with placeholder) vs hard-delete
PII_FIELDS_TO_ANONYMIZE = [
    "name", "email", "phone", "address", "linkedin_url",
    "github_url", "website", "current_company", "current_title",
]


def get_retention_config(tenant_id: Optional[int] = None, db: Optional[Session] = None) -> Dict[str, int]:
    """Get retention configuration, optionally tenant-specific.

    Falls back to DEFAULT_RETENTION_DAYS if no tenant config exists.
    """
    if tenant_id and db:
        try:
            from app.backend.models.db_models import TenantConfig
            config = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
            if config and config.retention_policy:
                custom = json.loads(config.retention_policy)
                return {**DEFAULT_RETENTION_DAYS, **custom}
        except Exception as e:
            logger.warning("Failed to load tenant retention config: %s", e)

    return DEFAULT_RETENTION_DAYS.copy()


def hard_delete_candidate(db: Session, candidate_id: int, tenant_id: int, reason: str = "gdpr_request") -> Dict[str, Any]:
    """Execute right-to-be-forgotten: permanently delete candidate and all associated data.

    This is irreversible. All screening results, voice sessions, and resume data
    are deleted. An audit log entry is preserved (without PII) for compliance.

    Returns summary of deleted records.
    """
    from app.backend.models.db_models import (
        Candidate, ScreeningResult, VoiceScreeningSession,
        FieldAuditLog, AuditLog,
    )

    deleted = {"candidate": False, "screening_results": 0, "voice_sessions": 0, "resume_text": False}

    try:
        # Get candidate for audit info (before deletion)
        candidate = db.query(Candidate).filter(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
        ).first()

        if not candidate:
            return {"error": "Candidate not found", **deleted}

        # Store anonymized audit info
        candidate_hash = hashlib.sha256(f"{candidate.email}|{candidate_id}".encode()).hexdigest()[:16]

        # Delete screening results
        results = db.query(ScreeningResult).filter(
            ScreeningResult.candidate_id == candidate_id
        ).all()
        for r in results:
            db.delete(r)
            deleted["screening_results"] += 1

        # Delete voice screening sessions
        sessions = db.query(VoiceScreeningSession).filter(
            VoiceScreeningSession.candidate_id == candidate_id
        ).all()
        for s in sessions:
            db.delete(s)
            deleted["voice_sessions"] += 1

        # Delete candidate record (cascade should handle remaining)
        db.delete(candidate)
        deleted["candidate"] = True
        deleted["resume_text"] = True

        # Create audit log entry (no PII)
        audit = AuditLog(
            actor_user_id=None,
            actor_email="system",
            tenant_id=tenant_id,
            action="gdpr.right_to_be_forgotten",
            resource_type="candidate",
            resource_id=candidate_id,
            details=json.dumps({
                "reason": reason,
                "candidate_hash": candidate_hash,
                "deleted": deleted,
            }),
        )
        db.add(audit)
        db.commit()

        logger.info("GDPR hard delete completed for candidate %d (tenant %d): %s",
                     candidate_id, tenant_id, deleted)
        return deleted

    except Exception as e:
        db.rollback()
        logger.error("GDPR hard delete failed for candidate %d: %s", candidate_id, e)
        return {"error": str(e), **deleted}


def anonymize_candidate(db: Session, candidate_id: int, tenant_id: int, reason: str = "retention_expiry") -> Dict[str, Any]:
    """Anonymize a candidate's PII while preserving aggregate analytics.

    Replaces PII fields with placeholders but keeps screening results
    for statistical/bias auditing purposes.
    """
    from app.backend.models.db_models import Candidate, AuditLog

    anonymized = {"fields": 0}

    try:
        candidate = db.query(Candidate).filter(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
        ).first()

        if not candidate:
            return {"error": "Candidate not found", **anonymized}

        candidate_hash = hashlib.sha256(f"{candidate.email or 'unknown'}|{candidate_id}".encode()).hexdigest()[:16]

        for field in PII_FIELDS_TO_ANONYMIZE:
            if hasattr(candidate, field):
                setattr(candidate, field, f"[ANONYMIZED_{candidate_hash}]")
                anonymized["fields"] += 1

        # Mark as anonymized
        if hasattr(candidate, "status"):
            candidate.status = "anonymized"

        # Audit log
        audit = AuditLog(
            actor_user_id=None,
            actor_email="system",
            tenant_id=tenant_id,
            action="gdpr.anonymize",
            resource_type="candidate",
            resource_id=candidate_id,
            details=json.dumps({
                "reason": reason,
                "candidate_hash": candidate_hash,
                "fields_anonymized": anonymized["fields"],
            }),
        )
        db.add(audit)
        db.commit()

        logger.info("GDPR anonymization completed for candidate %d (tenant %d)", candidate_id, tenant_id)
        return anonymized

    except Exception as e:
        db.rollback()
        logger.error("GDPR anonymization failed for candidate %d: %s", candidate_id, e)
        return {"error": str(e), **anonymized}


def cleanup_expired_data(db: Session, tenant_id: Optional[int] = None) -> Dict[str, int]:
    """Find and anonymize/delete candidates whose data has exceeded retention period.

    This should be called by a scheduled job (e.g. APScheduler) daily.

    Returns summary of processed records.
    """
    from app.backend.models.db_models import Candidate

    config = get_retention_config(tenant_id, db)
    retention_days = config.get("candidate_data", 730)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    summary = {"anonymized": 0, "deleted": 0, "errors": 0}

    try:
        query = db.query(Candidate).filter(
            Candidate.created_at < cutoff,
            Candidate.status != "anonymized",
        )
        if tenant_id:
            query = query.filter(Candidate.tenant_id == tenant_id)

        expired = query.all()

        for candidate in expired:
            try:
                # Anonymize rather than hard-delete (preserves analytics)
                result = anonymize_candidate(db, candidate.id, candidate.tenant_id, reason="retention_expiry")
                if "error" in result:
                    summary["errors"] += 1
                else:
                    summary["anonymized"] += 1
            except Exception as e:
                logger.error("Failed to process expired candidate %d: %s", candidate.id, e)
                summary["errors"] += 1

        logger.info("Retention cleanup completed: %s", summary)
        return summary

    except Exception as e:
        logger.error("Retention cleanup failed: %s", e)
        return {"error": str(e), **summary}


def export_candidate_data(db: Session, candidate_id: int, tenant_id: int) -> Dict[str, Any]:
    """Export all candidate data for GDPR Article 20 (data portability).

    Returns a dict with all candidate information, screening results,
    and voice screening sessions.
    """
    from app.backend.models.db_models import (
        Candidate, ScreeningResult, VoiceScreeningSession,
    )

    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.tenant_id == tenant_id,
    ).first()

    if not candidate:
        return {"error": "Candidate not found"}

    export = {
        "candidate": {
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "current_title": candidate.current_title,
            "current_company": candidate.current_company,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
        },
        "screening_results": [],
        "voice_sessions": [],
    }

    results = db.query(ScreeningResult).filter(
        ScreeningResult.candidate_id == candidate_id
    ).all()

    for r in results:
        export["screening_results"].append({
            "id": r.id,
            "fit_score": r.fit_score,
            "deterministic_score": r.deterministic_score,
            "eligibility_status": r.eligibility_status,
            "matched_skills": r.matched_skills,
            "missing_skills": r.missing_skills,
            "final_recommendation": r.final_recommendation,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    sessions = db.query(VoiceScreeningSession).filter(
        VoiceScreeningSession.candidate_id == candidate_id
    ).all()

    for s in sessions:
        export["voice_sessions"].append({
            "id": s.id,
            "status": s.status,
            "overall_score": s.overall_score,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    return export
