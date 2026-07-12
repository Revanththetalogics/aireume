import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import RoleTemplate, ScreeningResult, Candidate, Tenant, SubscriptionPlan, User
from app.backend.services.metadata_utils import safe_parse_metadata

VALID_INDUSTRIES = [
    "technology", "finance", "healthcare", "education", "retail",
    "manufacturing", "consulting", "legal", "media", "government",
    "nonprofit", "other",
]

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


# ─── Pydantic request models ────────────────────────────────────────────────────

class OrganizationRequest(BaseModel):
    name: str
    industry: str | None = None
    company_size: str | None = None

class SelectPlanRequest(BaseModel):
    plan_id: int


class InviteTeamRequest(BaseModel):
    emails: list[str]
    role: str = "recruiter"


class ChecklistUpdateRequest(BaseModel):
    key: str
    completed: bool = True


DEFAULT_CHECKLIST = {
    "createdJob": False,
    "analyzedResume": False,
    "shortlistedCandidate": False,
    "invitedTeamMember": False,
    "sharedWithHM": False,
}


def _load_checklist(user) -> dict:
    raw = getattr(user, "getting_started_progress", None) or "{}"
    try:
        data = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        data = {}
    merged = {**DEFAULT_CHECKLIST, **data}
    return merged


def _save_checklist(user, checklist: dict, db: Session):
    user.getting_started_progress = json.dumps(checklist)
    db.commit()


def _ensure_free_plan(db: Session, tenant: Tenant) -> None:
    if tenant.plan_id:
        return
    free_plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.name == "free",
        SubscriptionPlan.is_active == True,
    ).first()
    if not free_plan:
        raise HTTPException(status_code=400, detail="No default plan available. Please select a plan.")
    tenant.plan_id = free_plan.id
    db.flush()


# ─── Onboarding status & flow endpoints ─────────────────────────────────────────

@router.get("/status")
async def get_onboarding_status(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns onboarding status for the current tenant.
    Includes which steps have been completed.
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Determine step completion from tenant metadata
    metadata = safe_parse_metadata(tenant.metadata_json)

    completed_at = tenant.onboarding_completed_at.isoformat() if tenant.onboarding_completed_at else None

    return {
        "completed": tenant.onboarding_completed,
        "completed_at": completed_at,
        "checklist": _load_checklist(current_user),
        "steps": {
            "organization": bool(metadata.get("industry") or metadata.get("company_size")),
            "plan_selected": tenant.plan_id is not None,
            "first_jd": db.query(RoleTemplate).filter(
                RoleTemplate.tenant_id == tenant.id,
                ~RoleTemplate.name.like("%[Sample]%"),
            ).count() > 0,
        },
    }


@router.post("/organization")
async def update_organization(
    body: OrganizationRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Updates tenant organization name and metadata during onboarding.
    """
    # Validate organization name
    name = body.name.strip()
    if len(name) < 2 or len(name) > 200:
        raise HTTPException(status_code=400, detail="Organization name must be 2-200 characters")

    # Validate industry if provided
    if body.industry and body.industry.lower() not in VALID_INDUSTRIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid industry. Allowed: {', '.join(VALID_INDUSTRIES)}",
        )

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Update tenant name
    tenant.name = name

    # Update metadata with industry and company_size
    metadata = safe_parse_metadata(tenant.metadata_json)

    if body.industry:
        metadata["industry"] = body.industry
    if body.company_size:
        metadata["company_size"] = body.company_size

    tenant.metadata_json = json.dumps(metadata)
    db.commit()
    db.refresh(tenant)

    return {
        "success": True,
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "onboarding_completed": tenant.onboarding_completed,
        },
    }


@router.post("/select-plan")
async def select_onboarding_plan(
    body: SelectPlanRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Selects a subscription plan during onboarding.
    Only works during onboarding (tenant.onboarding_completed is False).
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate the plan exists and is active
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == body.plan_id,
        SubscriptionPlan.is_active == True,
    ).first()
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid or inactive plan")

    tenant.plan_id = plan.id

    # Start self-serve trial for paid plans (no immediate payment required)
    if plan.price_monthly and plan.price_monthly > 0 and plan.name != "enterprise":
        from app.backend.services.trial_service import start_trial
        start_trial(db, tenant, plan_name=plan.name)

    db.commit()
    db.refresh(tenant)

    return {
        "success": True,
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "display_name": plan.display_name,
        },
    }


@router.post("/complete")
async def complete_onboarding(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Marks onboarding as complete for the current tenant.
    Uses optimistic locking to prevent race conditions from double-calls.
    """
    # Enforce prerequisites before completion
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if not tenant.name or tenant.name.strip() == "":
        raise HTTPException(status_code=400, detail="Organization name must be set before completing onboarding")
    if not tenant.plan_id:
        raise HTTPException(status_code=400, detail="A subscription plan must be selected before completing onboarding")

    # Optimistic locking: only update if not already completed
    result = db.query(Tenant).filter(
        and_(
            Tenant.id == current_user.tenant_id,
            Tenant.onboarding_completed == False,
        )
    ).update({
        "onboarding_completed": True,
        "onboarding_completed_at": datetime.now(timezone.utc),
    })

    if result == 0:
        # Already completed (race condition or double-call)
        return {"message": "Onboarding already completed", "already_completed": True}

    db.commit()

    return {
        "completed": True,
        "redirect_to": "/",
    }


@router.post("/skip")
async def skip_onboarding(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Skip onboarding wizard — auto-selects free plan and marks complete."""
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if tenant.onboarding_completed:
        return {"completed": True, "already_completed": True}

    _ensure_free_plan(db, tenant)

    tenant.onboarding_completed = True
    tenant.onboarding_completed_at = datetime.now(timezone.utc)
    db.commit()

    return {"completed": True, "skipped": True}


@router.post("/invite-team")
async def invite_team_during_onboarding(
    body: InviteTeamRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send team invites during onboarding wizard."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    from app.backend.routes.auth import _hash_password
    from app.backend.services.invite_service import send_team_invite_email
    import secrets

    results = []
    valid_roles = {"admin", "recruiter", "viewer", "hiring_manager"}
    role = body.role if body.role in valid_roles else "recruiter"

    for raw_email in body.emails:
        email = raw_email.strip().lower()
        if not email or "@" not in email:
            continue
        if db.query(User).filter(User.email == email).first():
            results.append({"email": email, "status": "already_exists"})
            continue

        temp_password = secrets.token_urlsafe(12)
        new_user = User(
            tenant_id=tenant.id,
            email=email,
            hashed_password=_hash_password(temp_password),
            role=role,
            email_verified=False,
        )
        db.add(new_user)
        db.flush()

        email_sent = send_team_invite_email(
            db,
            invitee=new_user,
            inviter_name=current_user.email,
            tenant_name=tenant.name,
            tenant_slug=tenant.slug,
        )
        results.append({
            "email": email,
            "status": "invited" if email_sent else "created_no_email",
            "user_id": new_user.id,
            "invite_email_sent": email_sent,
        })

    if results:
        checklist = _load_checklist(current_user)
        if any(r.get("status") in ("invited", "created_no_email") for r in results):
            checklist["invitedTeamMember"] = True
            _save_checklist(current_user, checklist, db)

    db.commit()
    return {"results": results, "invited_count": sum(1 for r in results if r.get("status") == "invited")}


@router.get("/checklist")
async def get_checklist(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.refresh(current_user)
    return {"checklist": _load_checklist(current_user)}


@router.patch("/checklist")
async def update_checklist_item(
    body: ChecklistUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.key not in DEFAULT_CHECKLIST:
        raise HTTPException(status_code=400, detail=f"Invalid checklist key: {body.key}")
    checklist = _load_checklist(current_user)
    checklist[body.key] = body.completed
    _save_checklist(current_user, checklist, db)
    return {"checklist": checklist}


def _build_parsed_data(name: str, email: str, skills: list, work_exp: list, education: list) -> str:
    return json.dumps({
        "raw_text": f"Sample resume for {name}.",
        "contact_info": {"name": name, "email": email, "phone": ""},
        "skills": skills,
        "work_experience": work_exp,
        "education": education,
    })


def _build_analysis_result(
    fit_score: int,
    final_recommendation: str,
    status: str,
    skills: list,
    strengths: list,
    concerns: list,
    name: str,
    email: str,
    work_exp: list,
    education: list,
    total_years: int,
) -> str:
    return json.dumps({
        "fit_score": fit_score,
        "final_recommendation": final_recommendation,
        "matched_skills": skills,
        "strengths": strengths,
        "concerns": concerns,
        "weaknesses": [],
        "candidate_profile": {
            "name": name,
            "email": email,
            "skills_identified": skills,
            "work_experience": work_exp,
            "education": education,
            "total_effective_years": total_years,
            "current_role": work_exp[0]["title"] if work_exp else "",
            "current_company": work_exp[0]["company"] if work_exp else "",
        },
        "contact_info": {"name": name, "email": email, "phone": ""},
        "score_breakdown": {
            "skills": min(100, fit_score + 5),
            "experience": min(100, fit_score + 2),
            "education": min(100, fit_score - 2),
            "stability": min(100, fit_score + 3),
        },
        "status": status,
        "risk_level": "low" if fit_score >= 70 else ("medium" if fit_score >= 50 else "high"),
        "score_rationales": {},
        "risk_summary": {},
        "skill_depth": {},
        "skill_analysis": {},
        "jd_analysis": {},
        "edu_timeline_analysis": {},
        "employment_gaps": [],
        "risk_signals": [],
        "missing_skills": [],
        "adjacent_skills": [],
        "required_skills_count": len(skills),
        "analysis_quality": "high" if fit_score >= 70 else "medium",
        "pipeline_errors": [],
    })


@router.post("/seed-sample")
async def seed_sample_data(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Seeds sample data for new user onboarding.
    Creates:
    - 1 sample JD ("Senior Software Engineer")
    - 3 pre-analyzed sample candidates with different scores

    Returns the created JD and candidates for the wizard to display.
    Only seeds if no sample data exists for this tenant.
    """
    tenant_id = current_user.tenant_id

    # Idempotency check: look for existing sample RoleTemplate for this tenant
    existing_jd = (
        db.query(RoleTemplate)
        .filter(
            RoleTemplate.tenant_id == tenant_id,
            RoleTemplate.name.like("%[Sample]%"),
        )
        .first()
    )

    if existing_jd:
        # Return existing sample data
        existing_results = (
            db.query(ScreeningResult)
            .filter(
                ScreeningResult.tenant_id == tenant_id,
                ScreeningResult.role_template_id == existing_jd.id,
            )
            .all()
        )
        candidates = []
        for r in existing_results:
            try:
                analysis = json.loads(r.analysis_result or "{}")
            except Exception:
                analysis = {}
            cand = db.query(Candidate).filter(Candidate.id == r.candidate_id).first()
            candidates.append({
                "name": cand.name if cand else None,
                "fit_score": analysis.get("fit_score"),
                "status": r.status,
            })
        return {
            "success": True,
            "jd": {"id": existing_jd.id, "title": existing_jd.name},
            "candidates": candidates,
            "already_exists": True,
        }

    # ── Create sample JD ──────────────────────────────────────────────────────
    jd_text = (
        "We are looking for a Senior Software Engineer with 5+ years of experience.\n"
        "Requirements:\n"
        "- Python, JavaScript, React\n"
        "- Cloud platforms (AWS/GCP)\n"
        "- Database design\n"
        "- Team leadership experience\n"
        "- CI/CD and DevOps practices"
    )

    sample_jd = RoleTemplate(
        tenant_id=tenant_id,
        name="[Sample] Senior Software Engineer",
        jd_text=jd_text,
    )
    db.add(sample_jd)
    db.commit()
    db.refresh(sample_jd)

    # ── Sample candidate definitions ──────────────────────────────────────────
    sample_candidates = [
        {
            "name": "[Sample] Alex Johnson",
            "email": "sample.alex@example.com",
            "fit_score": 87,
            "recommendation": "Shortlist",
            "status": "shortlisted",
            "skills": ["Python", "React", "AWS", "PostgreSQL", "Docker"],
            "strengths": [
                "8 years Python/React experience",
                "Led team of 5 engineers at previous role",
            ],
            "concerns": ["No GCP experience mentioned"],
            "work_exp": [
                {"title": "Senior Software Engineer", "company": "TechCorp", "years": 5},
                {"title": "Software Engineer", "company": "StartupX", "years": 3},
            ],
            "education": [
                {"degree": "BS Computer Science", "school": "State University"},
            ],
            "total_years": 8,
        },
        {
            "name": "[Sample] Maria Santos",
            "email": "sample.maria@example.com",
            "fit_score": 65,
            "recommendation": "Consider",
            "status": "in-review",
            "skills": ["JavaScript", "React", "Node.js"],
            "strengths": ["Strong frontend expertise"],
            "concerns": [
                "Limited backend experience",
                "No cloud platform exposure",
            ],
            "work_exp": [
                {"title": "Frontend Developer", "company": "WebAgency", "years": 3},
            ],
            "education": [
                {"degree": "BS Information Technology", "school": "City College"},
            ],
            "total_years": 3,
        },
        {
            "name": "[Sample] James Wilson",
            "email": "sample.james@example.com",
            "fit_score": 42,
            "recommendation": "Reject",
            "status": "rejected",
            "skills": ["HTML", "CSS", "jQuery"],
            "strengths": ["Strong design sense"],
            "concerns": [
                "No Python or modern JS framework experience",
                "Only 2 years total experience",
            ],
            "work_exp": [
                {"title": "Junior Web Developer", "company": "DesignStudio", "years": 2},
            ],
            "education": [
                {"degree": "Associates Web Design", "school": "Community College"},
            ],
            "total_years": 2,
        },
    ]

    created_results = []
    for spec in sample_candidates:
        # Create Candidate record
        candidate = Candidate(
            tenant_id=tenant_id,
            name=spec["name"],
            email=spec["email"],
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        # Create ScreeningResult record
        result = ScreeningResult(
            tenant_id=tenant_id,
            candidate_id=candidate.id,
            role_template_id=sample_jd.id,
            resume_text=f"Sample resume for {spec['name']}.",
            jd_text=jd_text,
            parsed_data=_build_parsed_data(
                spec["name"],
                spec["email"],
                spec["skills"],
                spec["work_exp"],
                spec["education"],
            ),
            analysis_result=_build_analysis_result(
                fit_score=spec["fit_score"],
                final_recommendation=spec["recommendation"],
                status=spec["status"],
                skills=spec["skills"],
                strengths=spec["strengths"],
                concerns=spec["concerns"],
                name=spec["name"],
                email=spec["email"],
                work_exp=spec["work_exp"],
                education=spec["education"],
                total_years=spec["total_years"],
            ),
            status=spec["status"],
            deterministic_score=spec["fit_score"],
            role_category="technical",
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        created_results.append({
            "name": spec["name"],
            "fit_score": spec["fit_score"],
            "status": spec["status"],
        })

    return {
        "success": True,
        "jd": {"id": sample_jd.id, "title": sample_jd.name},
        "candidates": created_results,
        "already_exists": False,
    }
