"""
Role Templates — CRUD for saved JD templates scoped per tenant.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import RoleTemplate, User
from app.backend.models.schemas import TemplateCreate, TemplateOut

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[TemplateOut])
def list_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return (
        db.query(RoleTemplate)
        .filter(RoleTemplate.tenant_id == current_user.tenant_id)
        .order_by(RoleTemplate.created_at.desc())
        .all()
    )


@router.post("", response_model=TemplateOut)
def create_template(
    body: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    template = RoleTemplate(
        tenant_id=current_user.tenant_id,
        name=body.name,
        jd_text=body.jd_text,
        scoring_weights=json.dumps(body.scoring_weights) if body.scoring_weights else None,
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
