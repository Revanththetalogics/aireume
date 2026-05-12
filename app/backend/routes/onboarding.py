import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import RoleTemplate, ScreeningResult, Candidate

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


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
