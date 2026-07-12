"""CRM routes for platform admins — notes, health scores, NPS."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import require_readonly_platform, require_platform_write, require_product_owner
from app.backend.models.db_models import Tenant, User
from app.backend.services.crm_service import (
    compute_health_score,
    list_account_notes,
    add_account_note,
    get_nps_summary,
    record_nps,
)

router = APIRouter(prefix="/api/admin/crm", tags=["admin-crm"])


class AccountNoteRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)
    note_type: str = "general"


class NpsRequest(BaseModel):
    score: int = Field(..., ge=0, le=10)
    comment: Optional[str] = None


@router.get("/tenants/{tenant_id}/health")
def get_tenant_health(
    tenant_id: int,
    admin: User = Depends(require_readonly_platform),
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.deleted_at.is_(None)).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    result = compute_health_score(db, tenant)
    db.commit()
    return {
        "tenant_id": tenant_id,
        **result,
        "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
        "subscription_status": tenant.subscription_status,
    }


@router.get("/tenants/{tenant_id}/notes")
def get_tenant_notes(
    tenant_id: int,
    admin: User = Depends(require_readonly_platform),
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"notes": list_account_notes(db, tenant_id)}


@router.post("/tenants/{tenant_id}/notes")
def create_tenant_note(
    tenant_id: int,
    body: AccountNoteRequest,
    admin: User = Depends(require_platform_write),
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    note = add_account_note(
        db, tenant_id=tenant_id, author_id=admin.id,
        body=body.body, note_type=body.note_type,
    )
    db.commit()
    return {"id": note.id, "message": "Note added"}


@router.get("/tenants/{tenant_id}/nps")
def get_tenant_nps(
    tenant_id: int,
    admin: User = Depends(require_readonly_platform),
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return get_nps_summary(db, tenant_id)


@router.post("/tenants/{tenant_id}/nps")
def submit_tenant_nps_admin(
    tenant_id: int,
    body: NpsRequest,
    admin: User = Depends(require_product_owner),
    db: Session = Depends(get_db),
):
    """Record NPS on behalf of a tenant (e.g. from support call)."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    record_nps(db, tenant_id=tenant_id, user_id=admin.id, score=body.score, comment=body.comment)
    compute_health_score(db, tenant)
    db.commit()
    return {"message": "NPS recorded"}


@router.get("/health-overview")
def crm_health_overview(
    admin: User = Depends(require_readonly_platform),
    db: Session = Depends(get_db),
):
    """All tenants with health scores for CRM dashboard."""
    tenants = db.query(Tenant).filter(Tenant.deleted_at.is_(None)).order_by(Tenant.health_score.asc().nullsfirst()).limit(200).all()
    items = []
    for t in tenants:
        if t.health_score is None:
            compute_health_score(db, t)
        items.append({
            "tenant_id": t.id,
            "name": t.name,
            "slug": t.slug,
            "health_score": t.health_score,
            "churn_risk": t.churn_risk,
            "subscription_status": t.subscription_status,
            "trial_ends_at": t.trial_ends_at.isoformat() if t.trial_ends_at else None,
        })
    db.commit()
    at_risk = [i for i in items if i.get("churn_risk") == "high"]
    return {"tenants": items, "at_risk_count": len(at_risk), "at_risk": at_risk[:20]}
