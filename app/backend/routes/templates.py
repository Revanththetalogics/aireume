"""
Role Templates — CRUD for saved JD templates scoped per tenant.
"""
import json
import logging
import re
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import RoleTemplate, SkillClassificationTemplate, User
from app.backend.models.schemas import TemplateCreate, TemplateOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _auto_generate_tags(jd_text: str) -> str:
    """Auto-generate skill-based tags from JD text.

    Returns a JSON string: {"domain": str, "skills": [str], "seniority": str}
    Wrapped in try/except by callers so tagging failures never block template creation.
    """
    from app.backend.services.hybrid_pipeline import parse_jd_rules
    from app.backend.services.skill_matcher import extract_top_skills, infer_domain_from_skills

    jd = parse_jd_rules(jd_text)
    required = jd.get("required_skills", [])
    nice_to_have = jd.get("nice_to_have_skills", [])
    top_skills = extract_top_skills(required, nice_to_have)
    domain = infer_domain_from_skills(required + nice_to_have)

    # Infer seniority from JD text
    text_lower = jd_text[:1000].lower()
    seniority = "Mid"  # default
    if any(w in text_lower for w in ("principal", "staff", "distinguished", "fellow")):
        seniority = "Lead"
    elif any(w in text_lower for w in ("senior", "sr.", "sr ", "lead ", "architect", "head of")):
        seniority = "Senior"
    elif any(w in text_lower for w in ("junior", "jr.", "jr ", "associate", "graduate", "entry", "intern")):
        seniority = "Entry"

    return json.dumps({"domain": domain, "skills": top_skills, "seniority": seniority})


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
        # Auto-generate tags if existing template has none
        if not existing.tags and body.jd_text:
            try:
                existing.tags = _auto_generate_tags(body.jd_text)
            except Exception as e:
                logger.warning("Auto-tagging failed for existing template %s: %s", existing.id, e)
        db.commit()
        db.refresh(existing)
        return existing

    # Auto-generate tags from JD text when no explicit tags provided
    auto_tags = body.tags
    if not auto_tags and body.jd_text:
        try:
            auto_tags = _auto_generate_tags(body.jd_text)
        except Exception as e:
            logger.warning("Auto-tagging failed for new template: %s", e)

    template = RoleTemplate(
        tenant_id=current_user.tenant_id,
        name=body.name,
        jd_text=body.jd_text,
        scoring_weights=json.dumps(body.scoring_weights, default=_json_default) if body.scoring_weights else None,
        tags=auto_tags,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.post("/from-file", response_model=TemplateOut)
async def create_template_from_file(
    name: str = Form(...),
    jd_file: UploadFile = File(...),
    tags: str | None = Form(None),
    scoring_weights: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a template by uploading a JD file (PDF/DOCX/TXT)."""
    from app.backend.services.parser_service import extract_jd_text

    jd_bytes = await jd_file.read()
    if not jd_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        jd_text = extract_jd_text(jd_bytes, jd_file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract text from file: {e}")

    if not jd_text or not jd_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from the uploaded file")

    # Parse scoring_weights from JSON string if provided
    weights = None
    if scoring_weights:
        try:
            weights = json.loads(scoring_weights)
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid scoring_weights JSON")

    # Check if identical JD already exists for this tenant
    existing = db.query(RoleTemplate).filter(
        RoleTemplate.tenant_id == current_user.tenant_id,
        RoleTemplate.jd_text == jd_text
    ).first()

    if existing:
        if weights:
            existing.scoring_weights = json.dumps(weights, default=_json_default)
        if tags:
            existing.tags = tags
        if not existing.tags:
            try:
                existing.tags = _auto_generate_tags(jd_text)
            except Exception as e:
                logger.warning("Auto-tagging failed for existing template %s: %s", existing.id, e)
        db.commit()
        db.refresh(existing)
        return existing

    # Auto-generate tags from JD text when no explicit tags provided
    auto_tags = tags
    if not auto_tags:
        try:
            auto_tags = _auto_generate_tags(jd_text)
        except Exception as e:
            logger.warning("Auto-tagging failed for new template from file: %s", e)

    template = RoleTemplate(
        tenant_id=current_user.tenant_id,
        name=name,
        jd_text=jd_text,
        scoring_weights=json.dumps(weights, default=_json_default) if weights else None,
        tags=auto_tags,
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


# ─── Skill Classification Template CRUD ───────────────────────────────────────

class SkillItem(BaseModel):
    skill: str
    proficiency: Optional[str] = None


class SkillClassificationCreate(BaseModel):
    name: str
    role_template_id: Optional[int] = None
    required_skills: List[SkillItem]
    nice_to_have_skills: List[SkillItem]


class SkillClassificationUpdate(BaseModel):
    name: Optional[str] = None
    required_skills: Optional[List[SkillItem]] = None
    nice_to_have_skills: Optional[List[SkillItem]] = None


def _serialize_skill_template(t):
    """Serialize a SkillClassificationTemplate row for API response."""
    import json as _json
    req = t.required_skills if isinstance(t.required_skills, list) else _json.loads(t.required_skills or "[]")
    nice = t.nice_to_have_skills if isinstance(t.nice_to_have_skills, list) else _json.loads(t.nice_to_have_skills or "[]")
    return {
        "id": t.id,
        "name": t.name,
        "role_template_id": t.role_template_id,
        "required_skills": req,
        "nice_to_have_skills": nice,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


@router.post("/skill-classifications")
def create_skill_classification(
    data: SkillClassificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = SkillClassificationTemplate(
        tenant_id=current_user.tenant_id,
        name=data.name,
        role_template_id=data.role_template_id,
        required_skills=json.dumps([s.dict() for s in data.required_skills]),
        nice_to_have_skills=json.dumps([s.dict() for s in data.nice_to_have_skills]),
        created_by=current_user.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _serialize_skill_template(template)


@router.get("/skill-classifications")
def list_skill_classifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    templates = (
        db.query(SkillClassificationTemplate)
        .filter(SkillClassificationTemplate.tenant_id == current_user.tenant_id)
        .order_by(SkillClassificationTemplate.updated_at.desc())
        .all()
    )
    return [_serialize_skill_template(t) for t in templates]


@router.get("/skill-classifications/{template_id}")
def get_skill_classification(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = (
        db.query(SkillClassificationTemplate)
        .filter(
            SkillClassificationTemplate.id == template_id,
            SkillClassificationTemplate.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _serialize_skill_template(template)


@router.put("/skill-classifications/{template_id}")
def update_skill_classification(
    template_id: int,
    data: SkillClassificationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = (
        db.query(SkillClassificationTemplate)
        .filter(
            SkillClassificationTemplate.id == template_id,
            SkillClassificationTemplate.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if data.name is not None:
        template.name = data.name
    if data.required_skills is not None:
        template.required_skills = json.dumps([s.dict() for s in data.required_skills])
    if data.nice_to_have_skills is not None:
        template.nice_to_have_skills = json.dumps([s.dict() for s in data.nice_to_have_skills])
    db.commit()
    db.refresh(template)
    return _serialize_skill_template(template)


@router.delete("/skill-classifications/{template_id}")
def delete_skill_classification(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = (
        db.query(SkillClassificationTemplate)
        .filter(
            SkillClassificationTemplate.id == template_id,
            SkillClassificationTemplate.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
    return {"deleted": True, "id": template_id}
