"""Outcome tracking service for historical learning."""
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

from app.backend.models.db_models import (
    HiringOutcome, OutcomeSkillPattern, ScreeningResult, Candidate
)

logger = logging.getLogger(__name__)

_VALID_DECISIONS = {"hired", "rejected", "withdrawn", "no_decision"}


def record_outcome(db: Session, tenant_id: int, screening_result_id: int,
                   candidate_id: int, decision: str, stage: str = None,
                   user_id: int = None, notes: str = None,
                   role_template_id: int = None) -> HiringOutcome:
    """Record a hiring outcome (hired/rejected/withdrawn)."""
    # Validate decision
    if decision not in _VALID_DECISIONS:
        raise ValueError(f"Invalid decision '{decision}'. Must be one of: {', '.join(sorted(_VALID_DECISIONS))}")

    # Check if outcome already exists for this screening_result
    existing = db.query(HiringOutcome).filter(
        HiringOutcome.screening_result_id == screening_result_id,
        HiringOutcome.tenant_id == tenant_id
    ).first()

    if existing:
        # Update existing
        existing.decision = decision
        existing.decision_stage = stage
        existing.decision_date = datetime.utcnow()
        existing.decision_by_user_id = user_id
        existing.feedback_notes = notes
        existing.updated_at = datetime.utcnow()
        db.commit()
        return existing

    # Create new
    outcome = HiringOutcome(
        tenant_id=tenant_id,
        screening_result_id=screening_result_id,
        candidate_id=candidate_id,
        role_template_id=role_template_id,
        decision=decision,
        decision_stage=stage,
        decision_date=datetime.utcnow(),
        decision_by_user_id=user_id,
        feedback_notes=notes,
        source="manual",
        created_at=datetime.utcnow()
    )
    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return outcome


def record_feedback(db: Session, outcome_id: int, tenant_id: int,
                    rating: int, notes: str = None) -> Optional[HiringOutcome]:
    """Record post-hire quality feedback."""
    if not (1 <= rating <= 5):
        raise ValueError("Rating must be between 1 and 5")

    outcome = db.query(HiringOutcome).filter(
        HiringOutcome.id == outcome_id,
        HiringOutcome.tenant_id == tenant_id
    ).first()
    if not outcome:
        return None

    outcome.feedback_rating = rating
    if notes:
        outcome.feedback_notes = notes
    outcome.updated_at = datetime.utcnow()
    db.commit()
    return outcome


def get_outcomes_for_jd(db: Session, tenant_id: int,
                        role_template_id: int) -> List[HiringOutcome]:
    """Get all outcomes for a specific JD/role template."""
    return db.query(HiringOutcome).filter(
        HiringOutcome.tenant_id == tenant_id,
        HiringOutcome.role_template_id == role_template_id
    ).order_by(HiringOutcome.created_at.desc()).all()


def get_outcome_for_result(db: Session, tenant_id: int,
                           screening_result_id: int) -> Optional[HiringOutcome]:
    """Get outcome for a specific screening result."""
    return db.query(HiringOutcome).filter(
        HiringOutcome.tenant_id == tenant_id,
        HiringOutcome.screening_result_id == screening_result_id
    ).first()


def compute_skill_patterns(db: Session, tenant_id: int,
                           role_template_id: int = None,
                           role_category: str = None) -> Dict:
    """Compute which skills correlate with hire success.

    Returns patterns dict and writes to outcome_skill_patterns table.
    """
    # Query outcomes with their screening results
    query = db.query(HiringOutcome).join(
        ScreeningResult,
        HiringOutcome.screening_result_id == ScreeningResult.id
    ).filter(
        HiringOutcome.tenant_id == tenant_id,
        HiringOutcome.decision.in_(["hired", "rejected"])
    )

    if role_template_id:
        query = query.filter(HiringOutcome.role_template_id == role_template_id)

    outcomes = query.all()

    if len(outcomes) < 3:  # Need minimum sample
        return {"has_data": False, "sample_size": len(outcomes)}

    # Collect skills from hired vs rejected candidates
    hired_skills = {}   # skill -> count
    rejected_skills = {}
    hired_count = 0
    rejected_count = 0

    for outcome in outcomes:
        result = db.query(ScreeningResult).get(outcome.screening_result_id)
        if not result or not result.analysis_result:
            continue

        try:
            analysis = json.loads(result.analysis_result)
        except (json.JSONDecodeError, TypeError):
            continue

        # Get matched skills from analysis
        skill_analysis = analysis.get("skill_analysis", {})
        matched = skill_analysis.get("matched_skills", [])

        # Also check candidate parsed skills
        candidate = db.query(Candidate).get(outcome.candidate_id)
        candidate_skills = []
        if candidate and candidate.parsed_skills:
            try:
                candidate_skills = json.loads(candidate.parsed_skills)
                if isinstance(candidate_skills, list):
                    candidate_skills = [str(s) for s in candidate_skills]
                else:
                    candidate_skills = []
            except (json.JSONDecodeError, TypeError):
                pass

        all_skills = set(s.lower() for s in (matched + candidate_skills) if isinstance(s, str))

        if outcome.decision == "hired":
            hired_count += 1
            for skill in all_skills:
                hired_skills[skill] = hired_skills.get(skill, 0) + 1
        else:
            rejected_count += 1
            for skill in all_skills:
                rejected_skills[skill] = rejected_skills.get(skill, 0) + 1

    if hired_count == 0 and rejected_count == 0:
        return {"has_data": False, "sample_size": len(outcomes)}

    # Compute correlations
    all_skills_set = set(list(hired_skills.keys()) + list(rejected_skills.keys()))
    patterns = []

    for skill in all_skills_set:
        hired_pct = (hired_skills.get(skill, 0) / max(hired_count, 1)) * 100
        rejected_pct = (rejected_skills.get(skill, 0) / max(rejected_count, 1)) * 100

        # Simple correlation: difference in presence rates
        correlation = (hired_pct - rejected_pct) / 100  # Normalize to -1 to 1

        pattern = OutcomeSkillPattern(
            tenant_id=tenant_id,
            role_template_id=role_template_id,
            role_category=role_category,
            skill_name=skill,
            correlation_score=round(correlation, 3),
            present_in_hired_pct=round(hired_pct, 1),
            present_in_rejected_pct=round(rejected_pct, 1),
            sample_size=hired_count + rejected_count,
            last_computed_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        patterns.append(pattern)

    # Clear old patterns for this scope and write new ones
    delete_query = db.query(OutcomeSkillPattern).filter(
        OutcomeSkillPattern.tenant_id == tenant_id
    )
    if role_template_id:
        delete_query = delete_query.filter(OutcomeSkillPattern.role_template_id == role_template_id)
    delete_query.delete()

    db.add_all(patterns)
    db.commit()

    # Build response
    sorted_patterns = sorted(patterns, key=lambda p: p.correlation_score, reverse=True)
    critical = [{"skill": p.skill_name, "correlation": p.correlation_score,
                 "hired_pct": p.present_in_hired_pct}
                for p in sorted_patterns if p.correlation_score > 0.3]
    acceptable_gaps = [{"skill": p.skill_name, "correlation": p.correlation_score,
                        "hired_pct": p.present_in_hired_pct}
                       for p in sorted_patterns if -0.1 <= p.correlation_score <= 0.3]

    return {
        "has_data": True,
        "total_outcomes": hired_count + rejected_count,
        "hired": hired_count,
        "rejected": rejected_count,
        "critical_skills": critical[:10],
        "acceptable_gaps": acceptable_gaps[:10],
        "sample_size": hired_count + rejected_count
    }
