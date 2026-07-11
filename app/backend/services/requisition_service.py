"""Requisition lifecycle — intake, calibration, migration, HM scoping."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.backend.models.db_models import (
    Candidate,
    Requisition,
    RequisitionCandidate,
    RequisitionCriteriaVersion,
    RequisitionHiringManager,
    RoleTemplate,
    ScreeningProject,
    ScreeningProjectCandidate,
    ScreeningResult,
    TenantRequisitionSettings,
    User,
)
from app.backend.services.hybrid_pipeline import parse_jd_rules

logger = logging.getLogger(__name__)

REQ_ACTIVE_STATUSES = {"sourcing", "interviewing", "offer", "calibrated"}
CALIBRATED_STATUSES = {"calibrated", "sourcing", "interviewing", "offer", "filled"}


def _json_loads(raw: str | None, default: Any = None) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _json_dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value)


def get_or_create_tenant_settings(db: Session, tenant_id: int) -> TenantRequisitionSettings:
    row = db.get(TenantRequisitionSettings, tenant_id)
    if row:
        return row
    row = TenantRequisitionSettings(tenant_id=tenant_id)
    db.add(row)
    db.flush()
    return row


def is_requisition_calibrated(req: Requisition) -> bool:
    return (
        req.status in CALIBRATED_STATUSES
        or req.intake_status == "approved"
        or bool(req.calibrated_criteria_json)
    )


def hm_assigned_to_requisition(db: Session, user_id: int, requisition_id: int) -> bool:
    req = db.get(Requisition, requisition_id)
    if not req:
        return False
    if req.primary_hiring_manager_id == user_id:
        return True
    return (
        db.query(RequisitionHiringManager)
        .filter(
            RequisitionHiringManager.requisition_id == requisition_id,
            RequisitionHiringManager.user_id == user_id,
        )
        .first()
        is not None
    )


def ensure_legacy_role_template(db: Session, req: Requisition) -> int:
    """Ensure shadow RoleTemplate exists for interview/transcript FK compatibility."""
    if req.legacy_role_template_id:
        tpl = db.get(RoleTemplate, req.legacy_role_template_id)
        if tpl and tpl.tenant_id == req.tenant_id:
            tpl.name = req.title
            tpl.jd_text = req.jd_text
            if req.scoring_weights is not None:
                tpl.scoring_weights = req.scoring_weights
            if req.required_skills_override is not None:
                tpl.required_skills_override = req.required_skills_override
            if req.nice_to_have_skills_override is not None:
                tpl.nice_to_have_skills_override = req.nice_to_have_skills_override
            db.flush()
            return tpl.id

    tpl = RoleTemplate(
        tenant_id=req.tenant_id,
        name=req.title,
        jd_text=req.jd_text,
        scoring_weights=req.scoring_weights,
        tags=req.tags,
        required_skills_override=req.required_skills_override,
        nice_to_have_skills_override=req.nice_to_have_skills_override,
        created_by=req.created_by,
    )
    db.add(tpl)
    db.flush()
    req.legacy_role_template_id = tpl.id
    db.flush()
    return tpl.id


def resolve_role_picker_id(
    db: Session,
    tenant_id: int,
    picker_id: int | None,
) -> tuple[str | None, str | None, int | None, int | None]:
    """
    Resolve picker id — may be requisition id (preferred) or legacy role template id.
    Returns (jd_text, display_name, role_template_id, requisition_id).
    """
    if not picker_id:
        return None, None, None, None

    req = (
        db.query(Requisition)
        .filter(Requisition.id == picker_id, Requisition.tenant_id == tenant_id)
        .first()
    )
    if req:
        tpl_id = ensure_legacy_role_template(db, req)
        return req.jd_text, req.title, tpl_id, req.id

    tpl = (
        db.query(RoleTemplate)
        .filter(RoleTemplate.id == picker_id, RoleTemplate.tenant_id == tenant_id)
        .first()
    )
    if tpl:
        return tpl.jd_text, tpl.name, tpl.id, None

    return None, None, None, None


def build_skill_evidence(parsed_data: dict | None, matched_skills: list | None) -> list[dict[str, Any]]:
    """Link matched skills to resume snippets for evidence display (P2)."""
    work = (parsed_data or {}).get("work_experience") or []
    evidence: list[dict[str, Any]] = []
    for skill in matched_skills or []:
        name = skill.get("skill") if isinstance(skill, dict) else str(skill)
        if not name:
            continue
        needle = name.lower()
        snippet = None
        for entry in work:
            if not isinstance(entry, dict):
                continue
            for b in entry.get("responsibilities") or entry.get("bullets") or []:
                if needle in str(b).lower():
                    snippet = str(b)[:240]
                    break
            if not snippet and needle in str(entry.get("title") or "").lower():
                snippet = str(entry.get("title"))[:240]
            if snippet:
                break
        evidence.append({
            "skill": name,
            "snippet": snippet or "Matched in candidate profile",
        })
    return evidence


def build_default_intake(title: str, jd_text: str) -> dict[str, Any]:
    return {
        "role_title": title,
        "must_haves": [],
        "good_to_haves": [],
        "deal_breakers": [],
        "environment": "",
        "seniority_bar": "",
        "team_context": "",
        "success_criteria_90d": "",
        "hm_notes": "",
        "jd_excerpt": (jd_text or "")[:2000],
    }


def merge_calibration_from_jd_and_intake(
    jd_text: str,
    intake: dict[str, Any],
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parsed = parse_jd_rules(jd_text or "")
    must_haves = list(intake.get("must_haves") or [])
    good_to_haves = list(intake.get("good_to_haves") or [])
    deal_breakers = list(intake.get("deal_breakers") or [])

    for skill in parsed.get("required_skills") or []:
        name = skill if isinstance(skill, str) else skill.get("skill") or skill.get("name")
        if name and name not in must_haves:
            must_haves.append(name)
    for skill in parsed.get("nice_to_have_skills") or []:
        name = skill if isinstance(skill, str) else skill.get("skill") or skill.get("name")
        if name and name not in good_to_haves:
            good_to_haves.append(name)

    criteria = {
        "must_haves": must_haves,
        "good_to_haves": good_to_haves,
        "deal_breakers": deal_breakers,
        "environment": intake.get("environment") or "",
        "seniority_bar": intake.get("seniority_bar") or "",
        "team_context": intake.get("team_context") or "",
        "success_criteria_90d": intake.get("success_criteria_90d") or "",
        "role_title": intake.get("role_title") or "",
        "jd_skills": {
            "required": parsed.get("required_skills") or [],
            "nice_to_have": parsed.get("nice_to_have_skills") or [],
        },
        "calibrated_at": datetime.now(timezone.utc).isoformat(),
    }
    if overrides:
        criteria.update(overrides)
    return criteria


def intake_gate_message(settings: TenantRequisitionSettings, req: Requisition) -> str | None:
    if is_requisition_calibrated(req):
        return None
    mode = settings.intake_gate_mode or "warn"
    if mode == "optional":
        return None
    msg = "This requisition is not calibrated. Complete HM intake and calibration before screening."
    return msg if mode == "warn" else msg


def intake_gate_blocks(settings: TenantRequisitionSettings, req: Requisition) -> bool:
    if is_requisition_calibrated(req):
        return False
    return (settings.intake_gate_mode or "warn") == "block"


def assign_hiring_managers(
    db: Session,
    req: Requisition,
    primary_id: int | None,
    extra_ids: list[int] | None,
) -> None:
    db.query(RequisitionHiringManager).filter(
        RequisitionHiringManager.requisition_id == req.id
    ).delete()
    seen: set[int] = set()
    if primary_id:
        req.primary_hiring_manager_id = primary_id
        seen.add(primary_id)
        db.add(RequisitionHiringManager(
            requisition_id=req.id, user_id=primary_id, is_primary=True,
        ))
    all_ids = list(extra_ids or [])
    for uid in all_ids:
        if uid in seen:
            continue
        seen.add(uid)
        db.add(RequisitionHiringManager(
            requisition_id=req.id, user_id=uid, is_primary=False,
        ))


def requisition_to_dict(
    db: Session,
    req: Requisition,
    *,
    candidate_count: int = 0,
    gate_warning: str | None = None,
) -> dict[str, Any]:
    hm_ids = [
        row.user_id
        for row in db.query(RequisitionHiringManager)
        .filter(RequisitionHiringManager.requisition_id == req.id)
        .all()
    ]
    primary_email = None
    if req.primary_hiring_manager_id:
        u = db.get(User, req.primary_hiring_manager_id)
        primary_email = u.email if u else None

    return {
        "id": req.id,
        "tenant_id": req.tenant_id,
        "title": req.title,
        "jd_text": req.jd_text,
        "description": req.description,
        "client_name": req.client_name,
        "headcount": req.headcount,
        "location": req.location,
        "status": req.status,
        "intake_status": req.intake_status,
        "intake_json": _json_loads(req.intake_json, {}),
        "search_brief_json": _json_loads(req.search_brief_json),
        "calibrated_criteria_json": _json_loads(req.calibrated_criteria_json),
        "current_criteria_version": req.current_criteria_version or 0,
        "scoring_weights": _json_loads(req.scoring_weights),
        "tags": req.tags,
        "required_skills_override": _json_loads(req.required_skills_override, []),
        "nice_to_have_skills_override": _json_loads(req.nice_to_have_skills_override, []),
        "must_ask_questions_json": _json_loads(req.must_ask_questions_json, []),
        "primary_hiring_manager_id": req.primary_hiring_manager_id,
        "primary_hiring_manager_email": primary_email,
        "hiring_manager_ids": hm_ids,
        "created_by": req.created_by,
        "legacy_role_template_id": req.legacy_role_template_id,
        "external_ats_id": req.external_ats_id,
        "ats_provider": req.ats_provider,
        "hm_approved_at": req.hm_approved_at,
        "calibrated_at": req.calibrated_at,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
        "closed_at": req.closed_at,
        "candidate_count": candidate_count,
        "intake_gate_warning": gate_warning,
        "is_calibrated": is_requisition_calibrated(req),
    }


def create_requisition(
    db: Session,
    *,
    tenant_id: int,
    created_by: int | None,
    title: str,
    jd_text: str,
    **fields: Any,
) -> Requisition:
    intake = build_default_intake(title, jd_text)
    req = Requisition(
        tenant_id=tenant_id,
        title=title,
        jd_text=jd_text,
        description=fields.get("description"),
        client_name=fields.get("client_name"),
        headcount=fields.get("headcount"),
        location=fields.get("location"),
        status=fields.get("status") or "draft",
        intake_status="draft",
        intake_json=_json_dumps(intake),
        scoring_weights=_json_dumps(fields.get("scoring_weights")),
        tags=fields.get("tags"),
        required_skills_override=_json_dumps(fields.get("required_skills_override")),
        nice_to_have_skills_override=_json_dumps(fields.get("nice_to_have_skills_override")),
        created_by=created_by,
    )
    db.add(req)
    db.flush()
    ensure_legacy_role_template(db, req)
    assign_hiring_managers(
        db,
        req,
        fields.get("primary_hiring_manager_id"),
        fields.get("hiring_manager_ids"),
    )
    return req


def calibrate_requisition(
    db: Session,
    req: Requisition,
    *,
    user_id: int | None,
    criteria_override: dict[str, Any] | None = None,
    merge_jd: bool = True,
) -> RequisitionCriteriaVersion:
    intake = _json_loads(req.intake_json, {})
    if merge_jd:
        criteria = merge_calibration_from_jd_and_intake(req.jd_text, intake, criteria_override)
    else:
        criteria = criteria_override or merge_calibration_from_jd_and_intake(req.jd_text, intake)

    version_num = (req.current_criteria_version or 0) + 1
    version = RequisitionCriteriaVersion(
        requisition_id=req.id,
        version=version_num,
        criteria_json=_json_dumps(criteria),
        source="calibration",
        created_by=user_id,
    )
    db.add(version)
    req.current_criteria_version = version_num
    req.calibrated_criteria_json = _json_dumps(criteria)
    req.calibrated_at = datetime.now(timezone.utc)
    req.calibrated_by = user_id
    if req.status in ("draft", "intake_in_progress"):
        req.status = "calibrated"
    db.flush()
    return version


def migrate_legacy_data(db: Session, tenant_id: int) -> int:
    """One-time migration: role templates + projects → requisitions."""
    existing = (
        db.query(Requisition)
        .filter(Requisition.tenant_id == tenant_id)
        .count()
    )
    if existing:
        return 0

    created = 0
    templates = (
        db.query(RoleTemplate)
        .filter(RoleTemplate.tenant_id == tenant_id)
        .all()
    )
    template_to_req: dict[int, int] = {}

    for tpl in templates:
        intake = build_default_intake(tpl.name, tpl.jd_text)
        req = Requisition(
            tenant_id=tenant_id,
            title=tpl.name,
            jd_text=tpl.jd_text,
            status="draft",
            intake_status="draft",
            intake_json=_json_dumps(intake),
            scoring_weights=tpl.scoring_weights,
            tags=tpl.tags,
            required_skills_override=tpl.required_skills_override,
            nice_to_have_skills_override=tpl.nice_to_have_skills_override,
            created_by=tpl.created_by,
            legacy_role_template_id=tpl.id,
        )
        db.add(req)
        db.flush()
        template_to_req[tpl.id] = req.id
        created += 1

        db.query(ScreeningResult).filter(
            ScreeningResult.tenant_id == tenant_id,
            ScreeningResult.role_template_id == tpl.id,
            ScreeningResult.requisition_id.is_(None),
        ).update({"requisition_id": req.id}, synchronize_session=False)

    projects = (
        db.query(ScreeningProject)
        .filter(ScreeningProject.tenant_id == tenant_id)
        .all()
    )
    for proj in projects:
        req_id = template_to_req.get(proj.role_template_id)
        if not req_id:
            tpl = db.get(RoleTemplate, proj.role_template_id)
            if tpl:
                intake = build_default_intake(tpl.name, tpl.jd_text)
                req = Requisition(
                    tenant_id=tenant_id,
                    title=proj.name or tpl.name,
                    jd_text=tpl.jd_text,
                    status=_map_project_status(proj.status),
                    intake_status="draft",
                    intake_json=_json_dumps(intake),
                    must_ask_questions_json=proj.must_ask_questions_json,
                    created_by=proj.created_by,
                    legacy_role_template_id=proj.role_template_id,
                    legacy_project_id=proj.id,
                )
                db.add(req)
                db.flush()
                req_id = req.id
                created += 1
            else:
                continue
        else:
            req = db.get(Requisition, req_id)
            if req:
                if proj.name:
                    req.title = proj.name
                req.must_ask_questions_json = proj.must_ask_questions_json or req.must_ask_questions_json
                req.legacy_project_id = proj.id
                if proj.status == "active" and req.status == "draft":
                    req.status = "sourcing"
                elif proj.status == "closed":
                    req.status = "filled"
                    req.closed_at = proj.closed_at

        pcs = (
            db.query(ScreeningProjectCandidate)
            .filter(ScreeningProjectCandidate.project_id == proj.id)
            .all()
        )
        for pc in pcs:
            exists = (
                db.query(RequisitionCandidate)
                .filter(
                    RequisitionCandidate.requisition_id == req_id,
                    RequisitionCandidate.candidate_id == pc.candidate_id,
                )
                .first()
            )
            if exists:
                continue
            db.add(RequisitionCandidate(
                requisition_id=req_id,
                candidate_id=pc.candidate_id,
                screening_result_id=pc.screening_result_id,
                pipeline_status=pc.status,
                added_by=pc.added_by,
                added_at=pc.added_at,
            ))

    db.flush()
    logger.info("Migrated %s requisitions for tenant %s", created, tenant_id)
    return created


def _map_project_status(status: str) -> str:
    return {
        "draft": "draft",
        "active": "sourcing",
        "paused": "sourcing",
        "closed": "filled",
    }.get(status or "draft", "draft")


def req_candidate_to_dict(rc: RequisitionCandidate, candidate: Candidate | None = None) -> dict[str, Any]:
    fit_score = None
    if rc.screening_result:
        fit_score = rc.screening_result.deterministic_score
    return {
        "id": rc.id,
        "requisition_id": rc.requisition_id,
        "candidate_id": rc.candidate_id,
        "screening_result_id": rc.screening_result_id,
        "pipeline_status": rc.pipeline_status,
        "submission_status": rc.submission_status,
        "hm_outcome": rc.hm_outcome,
        "outcome_reason_code": rc.outcome_reason_code,
        "outcome_notes": rc.outcome_notes,
        "submission_json": _json_loads(rc.submission_json),
        "parse_confidence_json": _json_loads(rc.parse_confidence_json),
        "added_at": rc.added_at,
        "updated_at": rc.updated_at,
        "submitted_at": rc.submitted_at,
        "outcome_at": rc.outcome_at,
        "candidate_name": getattr(candidate, "name", None) if candidate else None,
        "candidate_email": getattr(candidate, "email", None) if candidate else None,
        "fit_score": fit_score,
    }


def get_calibrated_skills_for_matching(req: Requisition) -> dict[str, list]:
    """Skills for analyze/matching from calibrated criteria + overrides."""
    criteria = _json_loads(req.calibrated_criteria_json, {})
    required = list(criteria.get("must_haves") or [])
    nice = list(criteria.get("good_to_haves") or [])

    override_req = _json_loads(req.required_skills_override, [])
    override_nice = _json_loads(req.nice_to_have_skills_override, [])
    for item in override_req or []:
        name = item if isinstance(item, str) else item.get("skill")
        if name and name not in required:
            required.append(name)
    for item in override_nice or []:
        name = item if isinstance(item, str) else item.get("skill")
        if name and name not in nice:
            nice.append(name)

    if not required and not nice:
        parsed = parse_jd_rules(req.jd_text or "")
        for skill in parsed.get("required_skills") or []:
            name = skill if isinstance(skill, str) else skill.get("skill")
            if name:
                required.append(name)
        for skill in parsed.get("nice_to_have_skills") or []:
            name = skill if isinstance(skill, str) else skill.get("skill")
            if name:
                nice.append(name)

    return {"required_skills": required, "nice_to_have_skills": nice}


def compute_parse_confidence(parsed_data: dict[str, Any]) -> dict[str, Any]:
    """Phase 2 — trust signals for resume/JD parsing (evidence-linked UI)."""
    skills = parsed_data.get("skills") or []
    work = parsed_data.get("work_experience") or []
    contact = parsed_data.get("contact_info") or {}
    raw_len = len((parsed_data.get("raw_text") or "").strip())

    scores = {
        "contact": 0.9 if contact.get("email") else (0.5 if contact.get("phone") else 0.2),
        "skills": min(1.0, len(skills) / 8) if skills else 0.1,
        "experience": min(1.0, len(work) / 3) if work else 0.15,
        "dates": 0.7 if work and all(w.get("start_date") or w.get("dates") for w in work[:2]) else 0.35,
        "text_quality": min(1.0, raw_len / 1500) if raw_len else 0.0,
    }
    overall = round(sum(scores.values()) / len(scores), 2)
    level = "high" if overall >= 0.7 else ("medium" if overall >= 0.45 else "low")
    return {
        "overall": overall,
        "level": level,
        "dimensions": scores,
        "evidence_hint": "Verify contact and tenure before advancing — parser confidence is triage-only.",
    }


def build_submission_packet(
    db: Session,
    rc: RequisitionCandidate,
    req: Requisition,
) -> dict[str, Any]:
    """HM submission packet — screening summary + playbook hints."""
    result = rc.screening_result
    analysis = _json_loads(result.analysis_result, {}) if result else {}
    narrative = _json_loads(result.narrative_json, {}) if result and result.narrative_json else {}
    criteria = _json_loads(req.calibrated_criteria_json, {})
    return {
        "candidate_id": rc.candidate_id,
        "requisition_id": req.id,
        "requisition_title": req.title,
        "fit_score": result.deterministic_score if result else None,
        "recommendation": analysis.get("recommendation"),
        "skill_gaps": analysis.get("skill_gaps") or analysis.get("gaps"),
        "evidence": analysis.get("evidence") or analysis.get("skill_evidence"),
        "parse_confidence": _json_loads(rc.parse_confidence_json),
        "narrative_summary": narrative.get("summary") or narrative.get("executive_summary"),
        "calibrated_must_haves": criteria.get("must_haves") or [],
        "hm_debrief_prompts": [
            "Did the candidate demonstrate ownership on must-have skills?",
            "Any deal-breakers observed?",
            "Would you advance to next round?",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
