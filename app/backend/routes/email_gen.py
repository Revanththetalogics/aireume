"""
Email template generation — draft shortlist/rejection/screening-call emails.
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import Candidate, ScreeningResult, User
from app.backend.models.schemas import EmailGenRequest, EmailGenResponse
from app.backend.services.app_llm_client import generate_app_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/email", tags=["email"])

EMAIL_PROMPTS = {
    "shortlist": (
        "Write a professional shortlisting email to {name} for the {role} position. "
        "Mention their score of {score}/100 and key strengths: {strengths}. "
        "Invite them to a next-step interview. Be warm and concise. Return JSON: "
        '{"subject": "...", "body": "..."}'
    ),
    "rejection": (
        "Write a professional, empathetic rejection email to {name} for the {role} position. "
        "Thank them for their time. Keep it kind and brief. Return JSON: "
        '{"subject": "...", "body": "..."}'
    ),
    "screening_call": (
        "Write a professional email to {name} inviting them to a 30-minute screening call for the {role} position. "
        "Mention their fit score of {score}/100. Include a placeholder for scheduling link. Return JSON: "
        '{"subject": "...", "body": "..."}'
    ),
}


@router.post("/generate", response_model=EmailGenResponse)
async def generate_email(
    body: EmailGenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if body.type not in EMAIL_PROMPTS:
        raise HTTPException(status_code=400, detail="Email type must be: shortlist, rejection, screening_call")

    candidate = db.query(Candidate).filter(
        Candidate.id == body.candidate_id,
        Candidate.tenant_id == current_user.tenant_id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    latest_result = (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.candidate_id == body.candidate_id,
            ScreeningResult.tenant_id == current_user.tenant_id,
        )
        .order_by(ScreeningResult.timestamp.desc())
        .first()
    )

    analysis  = json.loads(latest_result.analysis_result) if latest_result else {}
    jd_text   = latest_result.jd_text if latest_result else "the position"
    role_line = jd_text.strip().split("\n")[0][:60] if jd_text else "the position"
    strengths = "; ".join(analysis.get("strengths", [])[:2]) or "their demonstrated skills"

    prompt = EMAIL_PROMPTS[body.type].format(
        name=candidate.name or "Candidate",
        role=role_line,
        score=analysis.get("fit_score", "N/A"),
        strengths=strengths,
    )

    try:
        parsed = await generate_app_json(
            prompt,
            max_output_tokens=350,
            temperature=0.4,
            timeout=30.0,
            log_label="email_gen",
        )
        if parsed:
            return EmailGenResponse(
                subject=parsed.get("subject", f"Regarding your application for {role_line}"),
                body=parsed.get("body", "Thank you for applying. We will be in touch shortly."),
            )
        raise ValueError("empty email LLM response")
    except Exception as e:
        # Fallback templates
        logger.warning("Ollama email generation failed, using fallback template: %s", e)
        templates = {
            "shortlist":      (f"Your application for {role_line}", f"Dear {candidate.name or 'Candidate'},\n\nCongratulations! We were impressed by your profile and would like to move forward.\n\nBest regards"),
            "rejection":      (f"Your application for {role_line}", f"Dear {candidate.name or 'Candidate'},\n\nThank you for your interest. After careful consideration, we will not be moving forward at this time.\n\nWe appreciate your time and wish you the best."),
            "screening_call": (f"Screening Call Invitation — {role_line}", f"Dear {candidate.name or 'Candidate'},\n\nWe'd like to schedule a brief 30-minute call. Please use the following link to book: [SCHEDULING_LINK]\n\nBest regards"),
        }
        subj, b = templates[body.type]
        return EmailGenResponse(subject=subj, body=b)
