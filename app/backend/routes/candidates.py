"""
Candidate history tracking — list candidates, view history per candidate.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import Candidate, ScreeningResult, User
from app.backend.models.schemas import CandidateNameUpdate

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("")
def list_candidates(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Candidate).filter(Candidate.tenant_id == current_user.tenant_id)
    if search:
        q = f"%{search}%"
        query = query.filter(
            (Candidate.name.ilike(q)) | (Candidate.email.ilike(q))
        )

    total = query.count()
    candidates = query.order_by(Candidate.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for c in candidates:
        result_count = db.query(ScreeningResult).filter(ScreeningResult.candidate_id == c.id).count()
        best = (
            db.query(ScreeningResult)
            .filter(ScreeningResult.candidate_id == c.id)
            .order_by(ScreeningResult.timestamp.desc())
            .first()
        )
        best_score = None
        if best:
            try:
                best_score = json.loads(best.analysis_result).get("fit_score")
            except Exception:
                pass

        result.append({
            "id":           c.id,
            "name":         c.name,
            "email":        c.email,
            "phone":        c.phone,
            "created_at":   c.created_at,
            "result_count": result_count,
            "best_score":   best_score,
        })

    return {"candidates": result, "total": total, "page": page, "page_size": page_size}


@router.patch("/{candidate_id}")
def update_candidate(
    candidate_id: int,
    body: CandidateNameUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.tenant_id == current_user.tenant_id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate.name = body.name
    db.commit()
    db.refresh(candidate)
    return {"id": candidate.id, "name": candidate.name}


@router.get("/{candidate_id}")
def get_candidate(
    candidate_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.tenant_id == current_user.tenant_id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    results = (
        db.query(ScreeningResult)
        .filter(ScreeningResult.candidate_id == candidate_id)
        .order_by(ScreeningResult.timestamp.desc())
        .all()
    )

    history = []
    for r in results:
        analysis = json.loads(r.analysis_result)
        history.append({
            "id":                   r.id,
            "timestamp":            r.timestamp,
            "status":               r.status,
            "fit_score":            analysis.get("fit_score"),
            "final_recommendation": analysis.get("final_recommendation"),
            "risk_level":           analysis.get("risk_level"),
            "score_breakdown":      analysis.get("score_breakdown", {}),
            "matched_skills":       analysis.get("matched_skills", []),
            "missing_skills":       analysis.get("missing_skills", []),
        })

    return {
        "id":         candidate.id,
        "name":       candidate.name,
        "email":      candidate.email,
        "phone":      candidate.phone,
        "created_at": candidate.created_at,
        "history":    history,
    }
