"""
Team composition service — CRUD for TeamSkillProfile and JD gap analysis.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.backend.models.db_models import TeamSkillProfile

logger = logging.getLogger(__name__)


# ─── Helpers ────────────────────────────────────────────────────────────────────

def _profile_to_dict(profile: TeamSkillProfile) -> Dict[str, Any]:
    """Serialise a TeamSkillProfile row to a JSON-friendly dict."""
    return {
        "id": profile.id,
        "team_name": profile.team_name,
        "skills": json.loads(profile.skills_json) if profile.skills_json else [],
        "job_functions": json.loads(profile.job_functions) if profile.job_functions else [],
        "member_count": profile.member_count,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
    }


# ─── CRUD ───────────────────────────────────────────────────────────────────────

def create_team_profile(
    db: Session,
    tenant_id: int,
    team_name: str,
    skills: List[Dict[str, Any]],
    job_functions: List[str],
    user_id: int,
    member_count: Optional[int] = None,
) -> TeamSkillProfile:
    """Create a new TeamSkillProfile and return it."""
    profile = TeamSkillProfile(
        tenant_id=tenant_id,
        team_name=team_name,
        skills_json=json.dumps(skills),
        job_functions=json.dumps(job_functions),
        member_count=member_count,
        created_by_user_id=user_id,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_team_profile(
    db: Session,
    profile_id: int,
    tenant_id: int,
    skills: Optional[List[Dict[str, Any]]] = None,
    team_name: Optional[str] = None,
    job_functions: Optional[List[str]] = None,
    member_count: Optional[int] = None,
) -> Optional[TeamSkillProfile]:
    """Update an existing TeamSkillProfile. Returns None if not found / wrong tenant."""
    profile = (
        db.query(TeamSkillProfile)
        .filter(TeamSkillProfile.id == profile_id, TeamSkillProfile.tenant_id == tenant_id)
        .first()
    )
    if not profile:
        return None

    if team_name is not None:
        profile.team_name = team_name
    if skills is not None:
        profile.skills_json = json.dumps(skills)
    if job_functions is not None:
        profile.job_functions = json.dumps(job_functions)
    if member_count is not None:
        profile.member_count = member_count

    db.commit()
    db.refresh(profile)
    return profile


def get_team_profiles(db: Session, tenant_id: int) -> List[TeamSkillProfile]:
    """Return all TeamSkillProfiles for a tenant."""
    return (
        db.query(TeamSkillProfile)
        .filter(TeamSkillProfile.tenant_id == tenant_id)
        .order_by(TeamSkillProfile.created_at.desc())
        .all()
    )


def get_team_profile(db: Session, profile_id: int, tenant_id: int) -> Optional[TeamSkillProfile]:
    """Return a single TeamSkillProfile, scoped to tenant."""
    return (
        db.query(TeamSkillProfile)
        .filter(TeamSkillProfile.id == profile_id, TeamSkillProfile.tenant_id == tenant_id)
        .first()
    )


def delete_team_profile(db: Session, profile_id: int, tenant_id: int) -> bool:
    """Delete a TeamSkillProfile. Returns True if deleted, False if not found."""
    profile = (
        db.query(TeamSkillProfile)
        .filter(TeamSkillProfile.id == profile_id, TeamSkillProfile.tenant_id == tenant_id)
        .first()
    )
    if not profile:
        return False
    db.delete(profile)
    db.commit()
    return True


# ─── Gap Analysis ───────────────────────────────────────────────────────────────

def compute_team_gaps(
    db: Session,
    profile_id: int,
    tenant_id: int,
    jd_analysis: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Compare JD required/nice-to-have skills against a team profile.

    Returns a gap-analysis dict, or None if the profile is not found.
    """
    profile = get_team_profile(db, profile_id, tenant_id)
    if not profile:
        return None

    # Extract team skill names (case-insensitive lookup set)
    team_skills_raw: List[Dict[str, Any]] = (
        json.loads(profile.skills_json) if profile.skills_json else []
    )
    # Build lookup: skill_name_lower -> {level, members}
    team_skill_map: Dict[str, Dict[str, Any]] = {}
    for entry in team_skills_raw:
        name_lower = entry.get("skill", "").lower().strip()
        if name_lower:
            team_skill_map[name_lower] = {
                "level": (entry.get("level") or "").lower(),
                "members": entry.get("members", 0),
            }

    # JD skill lists
    jd_required = [s.lower().strip() for s in (jd_analysis.get("required_skills") or [])]
    jd_nice = [s.lower().strip() for s in (jd_analysis.get("nice_to_have_skills") or [])]

    # ── Team has: skills from the JD that the team already covers ───────────
    team_has: List[str] = []
    for skill in jd_required + jd_nice:
        if skill in team_skill_map:
            # Preserve original casing from team profile
            for entry in team_skills_raw:
                if entry.get("skill", "").lower().strip() == skill:
                    team_has.append(entry["skill"])
                    break

    # ── Redundant in JD: team is already strong (expert/advanced with 2+ members) ──
    redundant_in_jd: List[str] = []
    for skill_lower, info in team_skill_map.items():
        if info["level"] in ("expert", "advanced") and (info.get("members") or 0) >= 2:
            if skill_lower in jd_required or skill_lower in jd_nice:
                # Preserve original casing
                for entry in team_skills_raw:
                    if entry.get("skill", "").lower().strip() == skill_lower:
                        redundant_in_jd.append(entry["skill"])
                        break

    # ── Team gaps: required skills NOT in team ──────────────────────────────
    team_gaps: List[str] = []
    for skill in jd_required:
        if skill not in team_skill_map:
            team_gaps.append(skill)

    # ── Priority skills: gaps + nice-to-have not in team ────────────────────
    priority_skills: List[str] = list(team_gaps)  # start with required gaps
    for skill in jd_nice:
        if skill not in team_skill_map and skill not in priority_skills:
            priority_skills.append(skill)

    # ── Recommendation text ─────────────────────────────────────────────────
    if team_gaps:
        gaps_str = ", ".join(team_gaps[:5])
        recommendation = f"Prioritize {gaps_str} to close critical skill gaps."
    elif priority_skills:
        nice_str = ", ".join(priority_skills[:5])
        recommendation = f"Consider hiring for {nice_str} to strengthen the team."
    else:
        recommendation = "The team already covers all required and preferred skills for this role."

    return {
        "team_name": profile.team_name,
        "team_has": team_has,
        "team_gaps": team_gaps,
        "redundant_in_jd": redundant_in_jd,
        "priority_skills": priority_skills,
        "recommendation": recommendation,
    }
