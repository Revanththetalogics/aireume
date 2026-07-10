"""Tenant-scoped audit log for admins."""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import require_admin
from app.backend.models.db_models import AuditLog, User

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


class TenantAuditEntry(BaseModel):
    id: int
    actor_email: str
    action: str
    resource_type: str
    resource_id: Optional[int] = None
    details: Optional[dict] = None
    created_at: str


class TenantAuditListResponse(BaseModel):
    entries: List[TenantAuditEntry]
    total: int
    limit: int
    offset: int


@router.get("", response_model=TenantAuditListResponse)
def list_tenant_audit_logs(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: Optional[str] = Query(None),
):
    """List audit events for the current tenant (admin only)."""
    query = db.query(AuditLog).filter(AuditLog.tenant_id == current_user.tenant_id)
    if action:
        query = query.filter(AuditLog.action == action)

    total = query.count()
    rows = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    entries = []
    for row in rows:
        details = None
        if row.details:
            try:
                details = json.loads(row.details)
            except (json.JSONDecodeError, TypeError):
                details = {"raw": row.details}
        entries.append(TenantAuditEntry(
            id=row.id,
            actor_email=row.actor_email,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            details=details,
            created_at=row.created_at.isoformat() if row.created_at else "",
        ))

    return TenantAuditListResponse(
        entries=entries,
        total=total,
        limit=limit,
        offset=offset,
    )
