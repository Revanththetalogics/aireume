"""
Screening Project routes — lightweight hiring push management.

Endpoints:
  POST   /api/projects                          — Create a screening project
  GET    /api/projects                          — List projects for tenant
  GET    /api/projects/{id}                     — Get project detail
  PUT    /api/projects/{id}                     — Update project
  DELETE /api/projects/{id}                     — Delete project
  POST   /api/projects/{id}/candidates          — Add candidates to project
  DELETE /api/projects/{id}/candidates/{cand_id} — Remove candidate from project
  PUT    /api/projects/{id}/candidates/{cand_id} — Update candidate status in project
  GET    /api/projects/{id}/pipeline            — Kanban pipeline view grouped by status
"""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import (
    Candidate,
    InterviewTemplate,
    RoleTemplate,
    ScreeningProject,
    ScreeningProjectCandidate,
    ScreeningResult,
    User,
)
from app.backend.models.schemas import (
    InterviewTemplateCreate,
    InterviewTemplateOut,
    InterviewTemplateUpdate,
    ScreeningProjectCandidateAdd,
    ScreeningProjectCandidateOut,
    ScreeningProjectCandidateStatusUpdate,
    ScreeningProjectCreate,
    ScreeningProjectOut,
    ScreeningProjectUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])

_ALLOWED_PROJECT_STATUSES = {"draft", "active", "paused", "closed"}
_ALLOWED_CANDIDATE_STATUSES = {"pending", "shortlisted", "rejected", "in-review", "hired"}


def _project_to_out(project: ScreeningProject, candidate_count: int = 0) -> ScreeningProjectOut:
    return ScreeningProjectOut(
        id=project.id,
        tenant_id=project.tenant_id,
        role_template_id=project.role_template_id,
        name=project.name,
        description=project.description,
        status=project.status,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        closed_at=project.closed_at,
        candidate_count=candidate_count,
    )


def _pc_to_out(pc: ScreeningProjectCandidate) -> ScreeningProjectCandidateOut:
    fit_score = None
    if pc.screening_result:
        fit_score = pc.screening_result.deterministic_score
    return ScreeningProjectCandidateOut(
        id=pc.id,
        project_id=pc.project_id,
        candidate_id=pc.candidate_id,
        screening_result_id=pc.screening_result_id,
        status=pc.status,
        added_at=pc.added_at,
        updated_at=pc.updated_at,
        candidate_name=pc.candidate.name if pc.candidate else None,
        candidate_email=pc.candidate.email if pc.candidate else None,
        fit_score=fit_score,
    )


# ─── Project CRUD ─────────────────────────────────────────────────────────────

@router.post("", response_model=ScreeningProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ScreeningProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = db.query(RoleTemplate).filter(
        RoleTemplate.id == body.role_template_id,
        RoleTemplate.tenant_id == current_user.tenant_id,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Role template not found")

    project = ScreeningProject(
        tenant_id=current_user.tenant_id,
        role_template_id=body.role_template_id,
        name=body.name,
        description=body.description,
        status=body.status,
        created_by=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_to_out(project, 0)


@router.get("", response_model=list[ScreeningProjectOut])
def list_projects(
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ScreeningProject).filter(
        ScreeningProject.tenant_id == current_user.tenant_id
    )
    if status_filter:
        if status_filter not in _ALLOWED_PROJECT_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status filter")
        query = query.filter(ScreeningProject.status == status_filter)
    query = query.order_by(ScreeningProject.created_at.desc())
    projects = query.all()

    result = []
    for p in projects:
        count = db.query(func.count(ScreeningProjectCandidate.id)).filter(
            ScreeningProjectCandidate.project_id == p.id
        ).scalar() or 0
        result.append(_project_to_out(p, count))
    return result


@router.get("/{project_id}", response_model=ScreeningProjectOut)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(ScreeningProject).filter(
        ScreeningProject.id == project_id,
        ScreeningProject.tenant_id == current_user.tenant_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    count = db.query(func.count(ScreeningProjectCandidate.id)).filter(
        ScreeningProjectCandidate.project_id == project.id
    ).scalar() or 0
    return _project_to_out(project, count)


@router.put("/{project_id}", response_model=ScreeningProjectOut)
def update_project(
    project_id: int,
    body: ScreeningProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(ScreeningProject).filter(
        ScreeningProject.id == project_id,
        ScreeningProject.tenant_id == current_user.tenant_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    if body.status is not None:
        project.status = body.status
        if body.status == "closed" and project.closed_at is None:
            project.closed_at = datetime.now(timezone.utc)
        elif body.status != "closed":
            project.closed_at = None
    if body.role_template_id is not None:
        template = db.query(RoleTemplate).filter(
            RoleTemplate.id == body.role_template_id,
            RoleTemplate.tenant_id == current_user.tenant_id,
        ).first()
        if not template:
            raise HTTPException(status_code=404, detail="Role template not found")
        project.role_template_id = body.role_template_id

    db.commit()
    db.refresh(project)
    count = db.query(func.count(ScreeningProjectCandidate.id)).filter(
        ScreeningProjectCandidate.project_id == project.id
    ).scalar() or 0
    return _project_to_out(project, count)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(ScreeningProject).filter(
        ScreeningProject.id == project_id,
        ScreeningProject.tenant_id == current_user.tenant_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()


# ─── Project Candidates ───────────────────────────────────────────────────────

@router.post("/{project_id}/candidates", response_model=list[ScreeningProjectCandidateOut])
def add_candidates(
    project_id: int,
    body: ScreeningProjectCandidateAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(ScreeningProject).filter(
        ScreeningProject.id == project_id,
        ScreeningProject.tenant_id == current_user.tenant_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result_ids = body.screening_result_ids or {}

    added = []
    for cand_id in body.candidate_ids:
        candidate = db.query(Candidate).filter(
            Candidate.id == cand_id,
            Candidate.tenant_id == current_user.tenant_id,
        ).first()
        if not candidate:
            raise HTTPException(
                status_code=404,
                detail=f"Candidate {cand_id} not found",
            )

        existing = db.query(ScreeningProjectCandidate).filter(
            ScreeningProjectCandidate.project_id == project_id,
            ScreeningProjectCandidate.candidate_id == cand_id,
        ).first()
        if existing:
            added.append(existing)
            continue

        sr_id = result_ids.get(cand_id)
        if sr_id:
            sr = db.query(ScreeningResult).filter(
                ScreeningResult.id == sr_id,
                ScreeningResult.candidate_id == cand_id,
                ScreeningResult.tenant_id == current_user.tenant_id,
            ).first()
            if not sr:
                sr_id = None

        pc = ScreeningProjectCandidate(
            project_id=project_id,
            candidate_id=cand_id,
            screening_result_id=sr_id,
            status="pending",
            added_by=current_user.id,
        )
        db.add(pc)
        db.flush()
        db.refresh(pc)
        added.append(pc)

    db.commit()
    return [_pc_to_out(pc) for pc in added]


@router.delete("/{project_id}/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_candidate(
    project_id: int,
    candidate_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pc = db.query(ScreeningProjectCandidate).filter(
        ScreeningProjectCandidate.project_id == project_id,
        ScreeningProjectCandidate.candidate_id == candidate_id,
    ).first()
    if not pc:
        raise HTTPException(status_code=404, detail="Candidate not in project")

    project = db.query(ScreeningProject).filter(
        ScreeningProject.id == project_id,
        ScreeningProject.tenant_id == current_user.tenant_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(pc)
    db.commit()


@router.put("/{project_id}/candidates/{candidate_id}", response_model=ScreeningProjectCandidateOut)
def update_candidate_status(
    project_id: int,
    candidate_id: int,
    body: ScreeningProjectCandidateStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pc = db.query(ScreeningProjectCandidate).filter(
        ScreeningProjectCandidate.project_id == project_id,
        ScreeningProjectCandidate.candidate_id == candidate_id,
    ).first()
    if not pc:
        raise HTTPException(status_code=404, detail="Candidate not in project")

    project = db.query(ScreeningProject).filter(
        ScreeningProject.id == project_id,
        ScreeningProject.tenant_id == current_user.tenant_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    pc.status = body.status
    db.commit()
    db.refresh(pc)
    return _pc_to_out(pc)


@router.get("/{project_id}/pipeline")
def get_pipeline(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(ScreeningProject).filter(
        ScreeningProject.id == project_id,
        ScreeningProject.tenant_id == current_user.tenant_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    pcs = db.query(ScreeningProjectCandidate).options(
        selectinload(ScreeningProjectCandidate.candidate),
        selectinload(ScreeningProjectCandidate.screening_result),
    ).filter(
        ScreeningProjectCandidate.project_id == project_id,
    ).all()

    pipeline = {s: [] for s in _ALLOWED_CANDIDATE_STATUSES}
    for pc in pcs:
        pipeline.setdefault(pc.status, []).append(_pc_to_out(pc))

    return {
        "project_id": project_id,
        "project_name": project.name,
        "pipeline": pipeline,
        "total": len(pcs),
    }


# ─── Interview Templates ──────────────────────────────────────────────────────

def _template_to_out(template: InterviewTemplate) -> InterviewTemplateOut:
    questions = []
    if template.questions_json:
        try:
            questions = json.loads(template.questions_json)
        except (json.JSONDecodeError, TypeError):
            questions = []
    return InterviewTemplateOut(
        id=template.id,
        tenant_id=template.tenant_id,
        project_id=template.project_id,
        name=template.name,
        description=template.description,
        questions=questions,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.post("/templates", response_model=InterviewTemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(
    body: InterviewTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create an interview template with must-ask questions."""
    if body.project_id:
        project = db.query(ScreeningProject).filter(
            ScreeningProject.id == body.project_id,
            ScreeningProject.tenant_id == current_user.tenant_id,
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

    questions_data = [q.model_dump() for q in body.questions]
    template = InterviewTemplate(
        tenant_id=current_user.tenant_id,
        project_id=body.project_id,
        name=body.name,
        description=body.description,
        questions_json=json.dumps(questions_data, default=str),
        created_by=current_user.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _template_to_out(template)


@router.get("/templates", response_model=list[InterviewTemplateOut])
def list_templates(
    project_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List interview templates for the tenant, optionally filtered by project."""
    query = db.query(InterviewTemplate).filter(
        InterviewTemplate.tenant_id == current_user.tenant_id,
    )
    if project_id is not None:
        query = query.filter(InterviewTemplate.project_id == project_id)
    templates = query.order_by(InterviewTemplate.created_at.desc()).all()
    return [_template_to_out(t) for t in templates]


@router.get("/templates/{template_id}", response_model=InterviewTemplateOut)
def get_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = db.query(InterviewTemplate).filter(
        InterviewTemplate.id == template_id,
        InterviewTemplate.tenant_id == current_user.tenant_id,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_to_out(template)


@router.put("/templates/{template_id}", response_model=InterviewTemplateOut)
def update_template(
    template_id: int,
    body: InterviewTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = db.query(InterviewTemplate).filter(
        InterviewTemplate.id == template_id,
        InterviewTemplate.tenant_id == current_user.tenant_id,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if body.name is not None:
        template.name = body.name
    if body.description is not None:
        template.description = body.description
    if body.project_id is not None:
        template.project_id = body.project_id
    if body.is_active is not None:
        template.is_active = body.is_active
    if body.questions is not None:
        template.questions_json = json.dumps(
            [q.model_dump() for q in body.questions], default=str
        )

    db.commit()
    db.refresh(template)
    return _template_to_out(template)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = db.query(InterviewTemplate).filter(
        InterviewTemplate.id == template_id,
        InterviewTemplate.tenant_id == current_user.tenant_id,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
