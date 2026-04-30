"""
Role Templates — CRUD for saved JD templates scoped per tenant.
"""
import json
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import RoleTemplate, User
from app.backend.models.schemas import TemplateCreate, TemplateOut

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _json_default(obj):
    """Handle non-serializable types for json.dumps (datetime, date, Decimal)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


@router.get("")
def list_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    query = (
        db.query(RoleTemplate)
        .filter(RoleTemplate.tenant_id == current_user.tenant_id)
        .order_by(RoleTemplate.created_at.desc())
    )

    total = query.count()
    templates = query.offset(offset).limit(limit).all()

    return {
        "templates": templates,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("", response_model=TemplateOut)
def create_template(
    body: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if identical JD already exists for this tenant
    existing = db.query(RoleTemplate).filter(
        RoleTemplate.tenant_id == current_user.tenant_id,
        RoleTemplate.jd_text == body.jd_text
    ).first()

    if existing:
        # Update weights/tags if provided (user may have changed them)
        if body.scoring_weights:
            existing.scoring_weights = json.dumps(body.scoring_weights, default=_json_default)
        if body.tags:
            existing.tags = body.tags
        db.commit()
        db.refresh(existing)
        return existing

    template = RoleTemplate(
        tenant_id=current_user.tenant_id,
        name=body.name,
        jd_text=body.jd_text,
        scoring_weights=json.dumps(body.scoring_weights, default=_json_default) if body.scoring_weights else None,
        tags=body.tags,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.put("/{template_id}", response_model=TemplateOut)
def update_template(
    template_id: int,
    body: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    template = db.query(RoleTemplate).filter(
        RoleTemplate.id == template_id,
        RoleTemplate.tenant_id == current_user.tenant_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template.name = body.name
    template.jd_text = body.jd_text
    template.scoring_weights = json.dumps(body.scoring_weights) if body.scoring_weights else None
    template.tags = body.tags
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    template = db.query(RoleTemplate).filter(
        RoleTemplate.id == template_id,
        RoleTemplate.tenant_id == current_user.tenant_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
    return {"deleted": template_id}
