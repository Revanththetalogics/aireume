"""Requisition routes — intake, calibration, pipeline, HM portal."""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user, require_admin
from app.backend.middleware.rbac import (
    can_manage_requisition,
    get_tenant_role,
    is_hiring_manager,
    is_tenant_admin,
    require_requisition_access,
    require_recruiter_or_admin,
    require_requisition_write,
    TENANT_ROLE_HIRING_MANAGER,
)
from app.backend.models.db_models import (
    Candidate,
    Requisition,
    RequisitionCandidate,
    RequisitionCriteriaVersion,
    RequisitionHiringManager,
    ScreeningResult,
    TenantRequisitionSettings,
    User,
)
from app.backend.models.schemas import (
    RequisitionCalibrateRequest,
    RequisitionCriteriaUpdate,
    RequisitionCandidateAdd,
    RequisitionCandidateOut,
    RequisitionCandidateStatusUpdate,
    RequisitionCreate,
    RequisitionHmApproval,
    RequisitionIntakeUpdate,
    RequisitionOutcomeUpdate,
    RequisitionOut,
    RequisitionSubmissionCreate,
    RequisitionUpdate,
    TenantRequisitionSettingsOut,
    TenantRequisitionSettingsUpdate,
)
from app.backend.services.audit_service import log_tenant_event
from app.backend.services.requisition_service import (
    assign_hiring_managers,
    backfill_pipeline_from_screenings,
    build_submission_packet,
    calibrate_requisition,
    create_requisition,
    get_or_create_tenant_settings,
    hm_assigned_to_requisition,
    intake_gate_blocks,
    intake_gate_message,
    migrate_legacy_data,
    requisition_to_dict,
    req_candidate_to_dict,
    update_criteria_manual,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/requisitions", tags=["requisitions"])

_ALLOWED_PIPELINE = {"pending", "shortlisted", "rejected", "in-review", "hired"}


def _ensure_migrated(db: Session, tenant_id: int) -> None:
    migrate_legacy_data(db, tenant_id)
    db.commit()


def _load_req(db: Session, req_id: int, tenant_id: int) -> Requisition:
    req = db.get(Requisition, req_id)
    if not req or req.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Requisition not found")
    return req


def _count_candidates(db: Session, req_id: int) -> int:
    return (
        db.query(func.count(RequisitionCandidate.id))
        .filter(RequisitionCandidate.requisition_id == req_id)
        .scalar()
        or 0
    )


def _to_out(db: Session, req: Requisition, tenant_id: int) -> RequisitionOut:
    settings = get_or_create_tenant_settings(db, tenant_id)
    data = requisition_to_dict(
        db,
        req,
        candidate_count=_count_candidates(db, req.id),
        gate_warning=intake_gate_message(settings, req),
    )
    return RequisitionOut(**data)


@router.get("/settings", response_model=TenantRequisitionSettingsOut)
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = get_or_create_tenant_settings(db, current_user.tenant_id)
    from app.backend.models.db_models import Tenant
    import json
    tenant = db.get(Tenant, current_user.tenant_id)
    hw = {}
    if tenant and tenant.metadata_json:
        try:
            meta = json.loads(tenant.metadata_json)
            hw = meta.get("hiring_signal_weights") or {}
        except (json.JSONDecodeError, TypeError):
            hw = {}
    db.commit()
    return TenantRequisitionSettingsOut(
        tenant_id=row.tenant_id,
        intake_gate_mode=row.intake_gate_mode,
        hm_pipeline_permission=row.hm_pipeline_permission,
        hiring_signal_weights=hw,
        updated_at=row.updated_at,
    )


@router.put("/settings", response_model=TenantRequisitionSettingsOut)
def update_settings(
    body: TenantRequisitionSettingsUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = get_or_create_tenant_settings(db, current_user.tenant_id)
    if body.intake_gate_mode is not None:
        row.intake_gate_mode = body.intake_gate_mode
    if body.hm_pipeline_permission is not None:
        row.hm_pipeline_permission = body.hm_pipeline_permission
    if body.hiring_signal_weights is not None:
        from app.backend.models.db_models import Tenant
        import json
        tenant = db.get(Tenant, current_user.tenant_id)
        if tenant:
            try:
                meta = json.loads(tenant.metadata_json or "{}")
            except (json.JSONDecodeError, TypeError):
                meta = {}
            meta["hiring_signal_weights"] = body.hiring_signal_weights
            tenant.metadata_json = json.dumps(meta)
    db.commit()
    db.refresh(row)
    log_tenant_event(
        db,
        actor=current_user,
        action="requisition.settings_update",
        resource_type="tenant",
        resource_id=current_user.tenant_id,
        details=body.model_dump(exclude_none=True),
    )
    db.commit()
    from app.backend.models.db_models import Tenant
    import json
    tenant = db.get(Tenant, current_user.tenant_id)
    hw = {}
    if tenant and tenant.metadata_json:
        try:
            meta = json.loads(tenant.metadata_json)
            hw = meta.get("hiring_signal_weights") or {}
        except (json.JSONDecodeError, TypeError):
            hw = {}
    return TenantRequisitionSettingsOut(
        tenant_id=row.tenant_id,
        intake_gate_mode=row.intake_gate_mode,
        hm_pipeline_permission=row.hm_pipeline_permission,
        hiring_signal_weights=hw,
        updated_at=row.updated_at,
    )


@router.post("", response_model=RequisitionOut, status_code=status.HTTP_201_CREATED)
def create_req(
    body: RequisitionCreate,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
):
    req = create_requisition(
        db,
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        title=body.title.strip(),
        jd_text=body.jd_text,
        description=body.description,
        client_name=body.client_name,
        headcount=body.headcount,
        location=body.location,
        scoring_weights=body.scoring_weights,
        tags=body.tags,
        required_skills_override=body.required_skills_override,
        nice_to_have_skills_override=body.nice_to_have_skills_override,
        primary_hiring_manager_id=body.primary_hiring_manager_id,
        hiring_manager_ids=body.hiring_manager_ids,
        status=body.status,
    )
    if body.primary_hiring_manager_id:
        req.intake_status = "pending_hm"
        req.status = "intake_in_progress"
    db.commit()
    db.refresh(req)
    log_tenant_event(
        db,
        actor=current_user,
        action="requisition.create",
        resource_type="requisition",
        resource_id=req.id,
        details={"title": req.title},
    )
    db.commit()
    return _to_out(db, req, current_user.tenant_id)


@router.get("", response_model=list[RequisitionOut])
def list_reqs(
    status_filter: Optional[str] = Query(None, alias="status"),
    mine_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_migrated(db, current_user.tenant_id)
    q = db.query(Requisition).filter(Requisition.tenant_id == current_user.tenant_id)
    role = get_tenant_role(current_user)
    if role == TENANT_ROLE_HIRING_MANAGER or (mine_only and is_hiring_manager(current_user)):
        assigned_ids = (
            db.query(RequisitionHiringManager.requisition_id)
            .filter(RequisitionHiringManager.user_id == current_user.id)
            .subquery()
        )
        q = q.filter(
            (Requisition.primary_hiring_manager_id == current_user.id)
            | Requisition.id.in_(select(assigned_ids))
        )
    elif mine_only and not is_tenant_admin(current_user):
        q = q.filter(Requisition.created_by == current_user.id)
    if status_filter:
        q = q.filter(Requisition.status == status_filter)
    q = q.order_by(Requisition.updated_at.desc())
    rows = q.all()
    return [_to_out(db, r, current_user.tenant_id) for r in rows]


@router.get("/{req_id}", response_model=RequisitionOut)
def get_req(
    req_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    require_requisition_access(current_user, req, db)
    return _to_out(db, req, current_user.tenant_id)


@router.put("/{req_id}", response_model=RequisitionOut)
def update_req(
    req_id: int,
    body: RequisitionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    require_requisition_write(current_user, req, db)
    if body.title is not None:
        req.title = body.title.strip()
    if body.jd_text is not None:
        req.jd_text = body.jd_text
    if body.description is not None:
        req.description = body.description
    if body.client_name is not None:
        req.client_name = body.client_name
    if body.headcount is not None:
        req.headcount = body.headcount
    if body.location is not None:
        req.location = body.location
    if body.status is not None:
        req.status = body.status
        if body.status in ("filled", "cancelled"):
            req.closed_at = datetime.now(timezone.utc)
    if body.scoring_weights is not None:
        req.scoring_weights = json.dumps(body.scoring_weights)
    if body.tags is not None:
        req.tags = body.tags
    if body.required_skills_override is not None:
        req.required_skills_override = json.dumps(body.required_skills_override)
    if body.nice_to_have_skills_override is not None:
        req.nice_to_have_skills_override = json.dumps(body.nice_to_have_skills_override)
    if body.search_brief_json is not None:
        req.search_brief_json = json.dumps(body.search_brief_json)
    if body.must_ask_questions_json is not None:
        req.must_ask_questions_json = json.dumps(body.must_ask_questions_json)
    if body.primary_hiring_manager_id is not None:
        assign_hiring_managers(db, req, body.primary_hiring_manager_id, None)
    db.commit()
    db.refresh(req)
    return _to_out(db, req, current_user.tenant_id)


@router.delete("/{req_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_req(
    req_id: int,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    if not can_manage_requisition(current_user, req):
        raise HTTPException(status_code=403, detail="Not allowed to delete this requisition")
    db.delete(req)
    db.commit()


@router.put("/{req_id}/intake", response_model=RequisitionOut)
def update_intake(
    req_id: int,
    body: RequisitionIntakeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    require_requisition_write(current_user, req, db)
    req.intake_json = json.dumps(body.intake_json)
    from app.backend.services.interview_kit_context import sync_must_ask_from_intake
    must_ask = sync_must_ask_from_intake(body.intake_json)
    if must_ask is not None:
        req.must_ask_questions_json = must_ask
    if body.intake_status:
        req.intake_status = body.intake_status
    if req.status == "draft":
        req.status = "intake_in_progress"
    db.commit()
    db.refresh(req)
    return _to_out(db, req, current_user.tenant_id)


@router.post("/{req_id}/calibrate", response_model=RequisitionOut)
def calibrate(
    req_id: int,
    body: RequisitionCalibrateRequest,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    if not can_manage_requisition(current_user, req):
        raise HTTPException(status_code=403, detail="Not allowed to calibrate this requisition")
    calibrate_requisition(
        db,
        req,
        user_id=current_user.id,
        criteria_override=body.criteria_json,
        merge_jd=body.merge_jd_parse,
    )
    db.commit()
    db.refresh(req)
    log_tenant_event(
        db,
        actor=current_user,
        action="requisition.calibrate",
        resource_type="requisition",
        resource_id=req.id,
        details={"version": req.current_criteria_version},
    )
    db.commit()
    return _to_out(db, req, current_user.tenant_id)


@router.put("/{req_id}/criteria", response_model=RequisitionOut)
def update_criteria(
    req_id: int,
    body: RequisitionCriteriaUpdate,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    if not can_manage_requisition(current_user, req):
        raise HTTPException(status_code=403, detail="Not allowed to edit criteria for this requisition")
    if not req.calibrated_criteria_json:
        raise HTTPException(status_code=400, detail="Calibrate criteria before editing")
    update_criteria_manual(
        db,
        req,
        user_id=current_user.id,
        criteria=body.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(req)
    log_tenant_event(
        db,
        actor=current_user,
        action="requisition.criteria_edit",
        resource_type="requisition",
        resource_id=req.id,
        details={"version": req.current_criteria_version},
    )
    db.commit()
    return _to_out(db, req, current_user.tenant_id)


@router.post("/{req_id}/hm-approval", response_model=RequisitionOut)
def hm_approval(
    req_id: int,
    body: RequisitionHmApproval,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    if not hm_assigned_to_requisition(db, current_user.id, req.id) and not is_tenant_admin(current_user):
        raise HTTPException(status_code=403, detail="Only assigned hiring managers can approve intake")
    if body.approved:
        req.intake_status = "approved"
        req.hm_approved_at = datetime.now(timezone.utc)
        req.hm_approved_by = current_user.id
        if not req.calibrated_criteria_json:
            calibrate_requisition(db, req, user_id=current_user.id)
    else:
        req.intake_status = "changes_requested"
    db.commit()
    db.refresh(req)
    return _to_out(db, req, current_user.tenant_id)


@router.get("/{req_id}/criteria-versions")
def list_criteria_versions(
    req_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    require_requisition_access(current_user, req, db)
    versions = (
        db.query(RequisitionCriteriaVersion)
        .filter(RequisitionCriteriaVersion.requisition_id == req_id)
        .order_by(RequisitionCriteriaVersion.version.desc())
        .all()
    )
    return [
        {
            "id": v.id,
            "requisition_id": v.requisition_id,
            "version": v.version,
            "criteria_json": json.loads(v.criteria_json),
            "source": v.source,
            "created_by": v.created_by,
            "created_at": v.created_at,
        }
        for v in versions
    ]


@router.post("/{req_id}/candidates", response_model=list[RequisitionCandidateOut])
def add_candidates(
    req_id: int,
    body: RequisitionCandidateAdd,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    if not can_manage_requisition(current_user, req):
        raise HTTPException(status_code=403, detail="Not allowed")
    result_map = body.screening_result_ids or {}
    out = []
    for cid in body.candidate_ids:
        cand = db.get(Candidate, cid)
        if not cand or cand.tenant_id != current_user.tenant_id:
            continue
        existing = (
            db.query(RequisitionCandidate)
            .filter(
                RequisitionCandidate.requisition_id == req_id,
                RequisitionCandidate.candidate_id == cid,
            )
            .first()
        )
        if existing:
            out.append(RequisitionCandidateOut(**req_candidate_to_dict(existing, cand)))
            continue
        rc = RequisitionCandidate(
            requisition_id=req_id,
            candidate_id=cid,
            screening_result_id=result_map.get(cid),
            added_by=current_user.id,
        )
        db.add(rc)
        db.flush()
        out.append(RequisitionCandidateOut(**req_candidate_to_dict(rc, cand)))
    db.commit()
    return out


@router.get("/{req_id}/pipeline")
def get_pipeline(
    req_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    require_requisition_access(current_user, req, db)
    sync = backfill_pipeline_from_screenings(db, req)
    db.commit()
    rows = (
        db.query(RequisitionCandidate)
        .options(
            selectinload(RequisitionCandidate.candidate),
            selectinload(RequisitionCandidate.screening_result),
        )
        .filter(RequisitionCandidate.requisition_id == req_id)
        .all()
    )
    pipeline: dict[str, list] = {s: [] for s in _ALLOWED_PIPELINE}
    for rc in rows:
        st = rc.pipeline_status if rc.pipeline_status in pipeline else "pending"
        pipeline[st].append(req_candidate_to_dict(rc, rc.candidate))
    return {
        "requisition_id": req_id,
        "pipeline": pipeline,
        "sync": sync,
    }


@router.put("/{req_id}/candidates/{candidate_id}", response_model=RequisitionCandidateOut)
def update_candidate_status(
    req_id: int,
    candidate_id: int,
    body: RequisitionCandidateStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    settings = get_or_create_tenant_settings(db, current_user.tenant_id)
    role = get_tenant_role(current_user)
    if role == TENANT_ROLE_HIRING_MANAGER:
        if not hm_assigned_to_requisition(db, current_user.id, req_id):
            raise HTTPException(status_code=403, detail="Not assigned to this requisition")
        perm = settings.hm_pipeline_permission or "view_only"
        if perm == "view_only":
            raise HTTPException(status_code=403, detail="Hiring managers have view-only pipeline access")
        if perm == "shortlist_reject" and body.pipeline_status not in ("shortlisted", "rejected", "pending"):
            raise HTTPException(status_code=403, detail="Hiring managers can only shortlist or reject")
    else:
        require_requisition_write(current_user, req, db)

    rc = (
        db.query(RequisitionCandidate)
        .options(
            selectinload(RequisitionCandidate.candidate),
            selectinload(RequisitionCandidate.screening_result),
        )
        .filter(
            RequisitionCandidate.requisition_id == req_id,
            RequisitionCandidate.candidate_id == candidate_id,
        )
        .first()
    )
    if not rc:
        raise HTTPException(status_code=404, detail="Candidate not on this requisition")
    rc.pipeline_status = body.pipeline_status
    db.commit()
    db.refresh(rc)
    return RequisitionCandidateOut(**req_candidate_to_dict(rc, rc.candidate))


@router.post("/{req_id}/candidates/{candidate_id}/submit")
def submit_to_hm(
    req_id: int,
    candidate_id: int,
    body: RequisitionSubmissionCreate,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    rc = (
        db.query(RequisitionCandidate)
        .options(selectinload(RequisitionCandidate.screening_result))
        .filter(
            RequisitionCandidate.requisition_id == req_id,
            RequisitionCandidate.candidate_id == candidate_id,
        )
        .first()
    )
    if not rc:
        raise HTTPException(status_code=404, detail="Candidate not on this requisition")
    packet = build_submission_packet(db, rc, req)
    packet.update(body.submission_json or {})
    rc.submission_json = json.dumps(packet)
    rc.submission_status = "submitted"
    rc.submitted_at = datetime.now(timezone.utc)
    db.commit()
    return packet


@router.put("/{req_id}/candidates/{candidate_id}/outcome")
def record_outcome(
    req_id: int,
    candidate_id: int,
    body: RequisitionOutcomeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    if not hm_assigned_to_requisition(db, current_user.id, req_id) and not is_tenant_admin(current_user):
        raise HTTPException(status_code=403, detail="Only hiring managers can record outcomes")
    rc = (
        db.query(RequisitionCandidate)
        .filter(
            RequisitionCandidate.requisition_id == req_id,
            RequisitionCandidate.candidate_id == candidate_id,
        )
        .first()
    )
    if not rc:
        raise HTTPException(status_code=404, detail="Candidate not found")
    rc.hm_outcome = body.hm_outcome
    rc.outcome_reason_code = body.outcome_reason_code
    rc.outcome_notes = body.outcome_notes
    rc.outcome_at = datetime.now(timezone.utc)
    rc.submission_status = "reviewed"
    if body.hm_outcome == "advance":
        rc.pipeline_status = "shortlisted"
    elif body.hm_outcome == "reject":
        rc.pipeline_status = "rejected"
    elif body.hm_outcome == "hire":
        rc.pipeline_status = "hired"
    db.commit()
    return {"status": "ok", "hm_outcome": body.hm_outcome}


@router.get("/{req_id}/analytics")
def req_analytics(
    req_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    require_requisition_access(current_user, req, db)
    rows = (
        db.query(RequisitionCandidate)
        .filter(RequisitionCandidate.requisition_id == req_id)
        .all()
    )
    funnel = {s: 0 for s in _ALLOWED_PIPELINE}
    outcomes: dict[str, int] = {}
    submitted = 0
    for rc in rows:
        st = rc.pipeline_status if rc.pipeline_status in funnel else "pending"
        funnel[st] += 1
        if rc.submission_status == "submitted":
            submitted += 1
        if rc.hm_outcome:
            outcomes[rc.hm_outcome] = outcomes.get(rc.hm_outcome, 0) + 1
    return {
        "requisition_id": req_id,
        "title": req.title,
        "status": req.status,
        "funnel": funnel,
        "submitted_to_hm": submitted,
        "hm_outcomes": outcomes,
        "criteria_version": req.current_criteria_version,
    }


@router.get("/{req_id}/intake-gate")
def check_intake_gate(
    req_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = _load_req(db, req_id, current_user.tenant_id)
    settings = get_or_create_tenant_settings(db, current_user.tenant_id)
    return {
        "blocks": intake_gate_blocks(settings, req),
        "warning": intake_gate_message(settings, req),
        "is_calibrated": bool(req.calibrated_criteria_json),
        "intake_gate_mode": settings.intake_gate_mode,
    }


@router.get("/playbook-registry")
def playbook_registry(current_user: User = Depends(get_current_user)):
    """Domain playbook families available for interview kits."""
    from app.backend.services.interview_playbook_templates import get_playbook_registry
    return get_playbook_registry()


@router.get("/{req_id}/handoff-package")
def get_handoff_package(
    req_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.backend.services.handoff_service import build_handoff_package

    req = _load_req(db, req_id, current_user.tenant_id)
    require_requisition_access(current_user, req, db)
    package = build_handoff_package(
        db,
        tenant_id=current_user.tenant_id,
        requisition_id=req_id,
        viewer_user_id=current_user.id,
        generated_by_email=current_user.email,
    )
    if not package:
        raise HTTPException(status_code=404, detail="Handoff package not found")
    return package


@router.post("/{req_id}/share-links")
def create_req_share_link(
    req_id: int,
    body: dict,
    request: Request,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
):
    import secrets
    from datetime import timedelta
    from app.backend.models.db_models import HandoffShareLink

    req = _load_req(db, req_id, current_user.tenant_id)
    expires_in = int(body.get("expires_in_days") or 14)
    token = secrets.token_urlsafe(32)
    link = HandoffShareLink(
        token=token,
        tenant_id=current_user.tenant_id,
        requisition_id=req_id,
        role_template_id=req.legacy_role_template_id,
        created_by=current_user.id,
        label=body.get("label") or f"HM Handoff — {req.title}",
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in),
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    base = str(request.base_url).rstrip("/")
    return {
        "id": link.id,
        "token": link.token,
        "url": f"{base}/handoff/{link.token}",
        "label": link.label,
        "expires_at": link.expires_at.isoformat() if link.expires_at else None,
    }


@router.get("/{req_id}/share-links")
def list_req_share_links(
    req_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.backend.models.db_models import HandoffShareLink

    req = _load_req(db, req_id, current_user.tenant_id)
    require_requisition_access(current_user, req, db)
    links = (
        db.query(HandoffShareLink)
        .filter(
            HandoffShareLink.requisition_id == req_id,
            HandoffShareLink.tenant_id == current_user.tenant_id,
        )
        .order_by(HandoffShareLink.created_at.desc())
        .all()
    )
    base = str(request.base_url).rstrip("/")
    return [
        {
            "id": l.id,
            "token": l.token,
            "url": f"{base}/handoff/{l.token}",
            "label": l.label,
            "view_count": l.view_count or 0,
        }
        for l in links
    ]
