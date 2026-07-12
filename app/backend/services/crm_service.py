"""CRM: health scores, churn risk, account notes, NPS."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.backend.models.db_models import (
    Tenant, User, UsageLog, SecurityEvent, TenantAccountNote, TenantNpsResponse,
)

logger = logging.getLogger(__name__)


def compute_health_score(db: Session, tenant: Tenant) -> Dict[str, Any]:
    """Compute tenant health score (0-100) and churn risk from signals."""
    now = datetime.now(timezone.utc)
    signals: Dict[str, Any] = {}
    score = 50  # baseline

    # Onboarding complete (+15)
    if tenant.onboarding_completed:
        score += 15
        signals["onboarding_complete"] = True
    else:
        signals["onboarding_complete"] = False
        score -= 10

    # Subscription health (+/- 20)
    if tenant.subscription_status == "active":
        score += 15
    elif tenant.subscription_status == "trialing":
        score += 10
        if tenant.trial_ends_at:
            ends = tenant.trial_ends_at
            if ends.tzinfo is None:
                ends = ends.replace(tzinfo=timezone.utc)
            days_left = (ends - now).days
            signals["trial_days_left"] = max(0, days_left)
            if days_left <= 3:
                score -= 15
    elif tenant.subscription_status in ("past_due", "suspended"):
        score -= 25
    elif tenant.subscription_status == "cancelled":
        score -= 40

    # Usage in last 30 days (+/- 20)
    thirty_days_ago = now - timedelta(days=30)
    usage_count = (
        db.query(func.coalesce(func.sum(UsageLog.quantity), 0))
        .filter(
            UsageLog.tenant_id == tenant.id,
            UsageLog.created_at >= thirty_days_ago,
        )
        .scalar()
        or 0
    )
    signals["analyses_30d"] = int(usage_count)
    if usage_count >= 10:
        score += 20
    elif usage_count >= 3:
        score += 10
    elif usage_count == 0:
        score -= 15

    # Login activity last 14 days (+/- 15)
    fourteen_days_ago = now - timedelta(days=14)
    recent_logins = (
        db.query(func.count(SecurityEvent.id))
        .filter(
            SecurityEvent.event_type == "login_success",
            SecurityEvent.tenant_id == tenant.id,
            SecurityEvent.created_at >= fourteen_days_ago,
        )
        .scalar()
        or 0
    )
    # Fallback: count active users
    if recent_logins == 0:
        active_users = db.query(func.count(User.id)).filter(
            User.tenant_id == tenant.id, User.is_active == True
        ).scalar() or 0
        signals["active_users"] = active_users
        if active_users >= 3:
            score += 5
    else:
        signals["logins_14d"] = recent_logins
        score += min(15, recent_logins * 3)

    # NPS average (+/- 15)
    nps_avg = (
        db.query(func.avg(TenantNpsResponse.score))
        .filter(TenantNpsResponse.tenant_id == tenant.id)
        .scalar()
    )
    if nps_avg is not None:
        signals["nps_avg"] = round(float(nps_avg), 1)
        if nps_avg >= 9:
            score += 15
        elif nps_avg >= 7:
            score += 5
        elif nps_avg <= 6:
            score -= 15

    score = max(0, min(100, score))
    if score >= 70:
        churn_risk = "low"
    elif score >= 40:
        churn_risk = "medium"
    else:
        churn_risk = "high"

    tenant.health_score = score
    tenant.churn_risk = churn_risk
    db.flush()

    return {
        "health_score": score,
        "churn_risk": churn_risk,
        "signals": signals,
    }


def list_account_notes(db: Session, tenant_id: int, limit: int = 50) -> List[Dict]:
    notes = (
        db.query(TenantAccountNote)
        .filter(TenantAccountNote.tenant_id == tenant_id)
        .order_by(TenantAccountNote.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for n in notes:
        author_email = None
        if n.author_id:
            author = db.query(User).filter(User.id == n.author_id).first()
            author_email = author.email if author else None
        result.append({
            "id": n.id,
            "tenant_id": n.tenant_id,
            "note_type": n.note_type,
            "body": n.body,
            "author_email": author_email,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        })
    return result


def add_account_note(
    db: Session,
    *,
    tenant_id: int,
    author_id: int,
    body: str,
    note_type: str = "general",
) -> TenantAccountNote:
    note = TenantAccountNote(
        tenant_id=tenant_id,
        author_id=author_id,
        body=body.strip(),
        note_type=note_type,
    )
    db.add(note)
    db.flush()
    return note


def record_nps(
    db: Session,
    *,
    tenant_id: int,
    user_id: int,
    score: int,
    comment: Optional[str] = None,
) -> TenantNpsResponse:
    if not 0 <= score <= 10:
        raise ValueError("NPS score must be 0-10")
    response = TenantNpsResponse(
        tenant_id=tenant_id,
        user_id=user_id,
        score=score,
        comment=comment,
    )
    db.add(response)
    db.flush()
    return response


def get_nps_summary(db: Session, tenant_id: int) -> Dict[str, Any]:
    responses = (
        db.query(TenantNpsResponse)
        .filter(TenantNpsResponse.tenant_id == tenant_id)
        .order_by(TenantNpsResponse.created_at.desc())
        .limit(100)
        .all()
    )
    if not responses:
        return {"count": 0, "average": None, "nps": None, "recent": []}

    scores = [r.score for r in responses]
    avg = sum(scores) / len(scores)
    promoters = sum(1 for s in scores if s >= 9)
    detractors = sum(1 for s in scores if s <= 6)
    nps = round(((promoters - detractors) / len(scores)) * 100, 1)

    return {
        "count": len(scores),
        "average": round(avg, 1),
        "nps": nps,
        "recent": [
            {
                "score": r.score,
                "comment": r.comment,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in responses[:10]
        ],
    }
