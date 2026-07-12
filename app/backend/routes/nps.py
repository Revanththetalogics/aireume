"""Tenant-facing NPS survey submission."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user, require_active_subscription
from app.backend.models.db_models import User
from app.backend.services.crm_service import record_nps, compute_health_score

router = APIRouter(prefix="/api/nps", tags=["nps"])


class NpsSubmitRequest(BaseModel):
    score: int = Field(..., ge=0, le=10)
    comment: Optional[str] = Field(None, max_length=2000)


@router.post("", dependencies=[Depends(require_active_subscription)])
def submit_nps(
    body: NpsSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record_nps(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        score=body.score,
        comment=body.comment,
    )
    from app.backend.models.db_models import Tenant
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if tenant:
        compute_health_score(db, tenant)
    db.commit()
    return {"message": "Thank you for your feedback!"}
