"""
Transcript analysis routes.

POST /api/transcript/analyze  — upload a transcript file or paste text,
                                 select a candidate profile and job description (role template),
                                 receive an unbiased AI analysis.
GET  /api/transcript/analyses  — list all transcript analyses for the tenant.
GET  /api/transcript/analyses/{id} — retrieve a single analysis.
"""
import json
import logging
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import (
    Candidate, RoleTemplate, TranscriptAnalysis, User
)
from app.backend.services.transcript_service import parse_transcript, analyze_transcript

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transcript", tags=["transcript"])

ALLOWED_TRANSCRIPT_EXTENSIONS = ('.txt', '.vtt', '.srt')
MAX_TRANSCRIPT_SIZE = 5 * 1024 * 1024  # 5 MB


def _json_default(obj):
    """Handle non-serializable types for json.dumps (datetime, date, Decimal)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


@router.post("/analyze")
async def analyze_transcript_endpoint(
    transcript_file: Optional[UploadFile] = File(None),
    transcript_text: Optional[str]       = Form(None),
    candidate_id:    Optional[int]       = Form(None),
    role_template_id: Optional[int]      = Form(None),
    source_platform: Optional[str]       = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session        = Depends(get_db),
):
    # ── Resolve transcript raw text ──────────────────────────────────────────
    raw_text = ""
    filename = ""

    if transcript_file and transcript_file.filename:
        filename = transcript_file.filename
        if not filename.lower().endswith(ALLOWED_TRANSCRIPT_EXTENSIONS):
            raise HTTPException(
                status_code=400,
                detail=f"Only {ALLOWED_TRANSCRIPT_EXTENSIONS} files are supported"
            )
        content = await transcript_file.read()
        if len(content) > MAX_TRANSCRIPT_SIZE:
            raise HTTPException(status_code=400, detail="Transcript file too large (max 5 MB)")
        raw_text = content.decode("utf-8", errors="replace")

    elif transcript_text:
        raw_text = transcript_text.strip()
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either a transcript_file or transcript_text"
        )

    # ── Resolve job description ───────────────────────────────────────────────
    jd_text = ""
    template_name = None
    if role_template_id:
        template = db.query(RoleTemplate).filter(
            RoleTemplate.id == role_template_id,
            RoleTemplate.tenant_id == current_user.tenant_id
        ).first()
        if not template:
            raise HTTPException(status_code=404, detail="Job description template not found")
        jd_text = template.jd_text
        template_name = template.name

    if not jd_text:
        raise HTTPException(
            status_code=400,
            detail="A job description (role_template_id) is required for transcript analysis"
        )

    # ── Resolve candidate name ────────────────────────────────────────────────
    candidate_name = ""
    if candidate_id:
        candidate = db.query(Candidate).filter(
            Candidate.id == candidate_id,
            Candidate.tenant_id == current_user.tenant_id
        ).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        candidate_name = candidate.name or ""

    # ── Parse and analyse ─────────────────────────────────────────────────────
    clean_text = parse_transcript(raw_text, filename)
    result     = await analyze_transcript(clean_text, jd_text, candidate_name)

    # ── Persist ───────────────────────────────────────────────────────────────
    record = TranscriptAnalysis(
        tenant_id        = current_user.tenant_id,
        candidate_id     = candidate_id,
        role_template_id = role_template_id,
        transcript_text  = clean_text,
        source_platform  = source_platform or "manual",
        analysis_result  = json.dumps(result, default=_json_default),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id":                 record.id,
        "candidate_id":       candidate_id,
        "candidate_name":     candidate_name or None,
        "role_template_id":   role_template_id,
        "role_template_name": template_name,
        "source_platform":    record.source_platform,
        "analysis_result":    result,
        "created_at":         record.created_at,
    }


@router.get("/analyses")
def list_transcript_analyses(
    current_user: User = Depends(get_current_user),
    db: Session        = Depends(get_db),
):
    analyses = (
        db.query(TranscriptAnalysis)
        .filter(TranscriptAnalysis.tenant_id == current_user.tenant_id)
        .order_by(TranscriptAnalysis.created_at.desc())
        .all()
    )

    items = []
    for a in analyses:
        result = {}
        try:
            result = json.loads(a.analysis_result)
        except Exception as e:
            logger.warning("Non-critical: Failed to parse analysis_result for analysis %s: %s", a.id, e)

        candidate_name = None
        if a.candidate_id:
            c = db.query(Candidate).filter(Candidate.id == a.candidate_id).first()
            candidate_name = c.name if c else None

        template_name = None
        if a.role_template_id:
            t = db.query(RoleTemplate).filter(RoleTemplate.id == a.role_template_id).first()
            template_name = t.name if t else None

        items.append({
            "id":                 a.id,
            "candidate_id":       a.candidate_id,
            "candidate_name":     candidate_name,
            "role_template_id":   a.role_template_id,
            "role_template_name": template_name,
            "source_platform":    a.source_platform,
            "fit_score":          result.get("fit_score"),
            "recommendation":     result.get("recommendation"),
            "created_at":         a.created_at,
        })

    return {"analyses": items, "total": len(items)}


@router.get("/analyses/{analysis_id}")
def get_transcript_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session        = Depends(get_db),
):
    a = db.query(TranscriptAnalysis).filter(
        TranscriptAnalysis.id == analysis_id,
        TranscriptAnalysis.tenant_id == current_user.tenant_id
    ).first()

    if not a:
        raise HTTPException(status_code=404, detail="Transcript analysis not found")

    result = {}
    try:
        result = json.loads(a.analysis_result)
    except Exception as e:
        logger.warning("Non-critical: Failed to parse analysis_result for analysis %s: %s", a.id, e)

    candidate_name = None
    if a.candidate_id:
        c = db.query(Candidate).filter(Candidate.id == a.candidate_id).first()
        candidate_name = c.name if c else None

    template_name = None
    if a.role_template_id:
        t = db.query(RoleTemplate).filter(RoleTemplate.id == a.role_template_id).first()
        template_name = t.name if t else None

    return {
        "id":                 a.id,
        "candidate_id":       a.candidate_id,
        "candidate_name":     candidate_name,
        "role_template_id":   a.role_template_id,
        "role_template_name": template_name,
        "source_platform":    a.source_platform,
        "analysis_result":    result,
        "created_at":         a.created_at,
    }
