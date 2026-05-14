"""Skill trending service — computes and queries monthly skill frequency snapshots."""
import json
from datetime import datetime, date
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.backend.models.db_models import (
    SkillTrendSnapshot, ScreeningResult, HiringOutcome
)


# ── Date helpers (no dateutil dependency) ──────────────────────────────────────

def _add_months(dt: date, months: int) -> date:
    """Add *months* to a date, clamping the day to the target month's last day."""
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, _days_in_month(year, month))
    return date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - date(year, month, 1)).days


# ── Compute ────────────────────────────────────────────────────────────────────

def compute_monthly_snapshot(db: Session, tenant_id: int,
                             target_date: date = None) -> int:
    """Compute skill frequency snapshot for a given month.

    Scans all ScreeningResults from the target month, extracts skills from
    JD analyses and candidate profiles, writes to skill_trend_snapshots.

    Returns number of snapshot records created.
    """
    if target_date is None:
        target_date = date.today().replace(day=1)  # First of current month

    period_start = target_date.replace(day=1)
    period_end = _add_months(period_start, 1)

    # Get all screening results for this tenant in the period
    results = db.query(ScreeningResult).filter(
        ScreeningResult.tenant_id == tenant_id,
        ScreeningResult.is_active == True,
        ScreeningResult.timestamp >= period_start,
        ScreeningResult.timestamp < period_end
    ).all()

    # Aggregate skills
    # {(role_category, skill_name): {jd_count, resume_count, hired_count}}
    skill_data: Dict[tuple, Dict[str, int]] = {}

    for result in results:
        role_cat = result.role_category or "other"

        try:
            analysis = json.loads(result.analysis_result) if result.analysis_result else {}
        except (json.JSONDecodeError, TypeError):
            continue

        # JD skills (from jd_analysis)
        jd_analysis = analysis.get("jd_analysis", {})
        jd_skills = (jd_analysis.get("required_skills", []) +
                     jd_analysis.get("nice_to_have_skills", []))

        # Candidate skills (from skill_analysis matched)
        skill_analysis = analysis.get("skill_analysis", {})
        resume_skills = skill_analysis.get("matched_skills", [])

        # Check if this result has a "hired" outcome
        is_hired = db.query(HiringOutcome).filter(
            HiringOutcome.screening_result_id == result.id,
            HiringOutcome.decision == "hired"
        ).first() is not None

        for skill in jd_skills:
            skill_lower = skill.lower().strip() if isinstance(skill, str) else str(skill).lower().strip()
            key = (role_cat, skill_lower)
            if key not in skill_data:
                skill_data[key] = {"jd_count": 0, "resume_count": 0, "hired_count": 0}
            skill_data[key]["jd_count"] += 1

        for skill in resume_skills:
            skill_lower = skill.lower().strip() if isinstance(skill, str) else str(skill).lower().strip()
            key = (role_cat, skill_lower)
            if key not in skill_data:
                skill_data[key] = {"jd_count": 0, "resume_count": 0, "hired_count": 0}
            skill_data[key]["resume_count"] += 1
            if is_hired:
                skill_data[key]["hired_count"] += 1

    # Count total hired per category
    hired_by_category: Dict[str, int] = {}
    hired_outcomes = db.query(HiringOutcome).join(
        ScreeningResult, HiringOutcome.screening_result_id == ScreeningResult.id
    ).filter(
        HiringOutcome.tenant_id == tenant_id,
        HiringOutcome.decision == "hired",
        HiringOutcome.decision_date >= period_start,
        HiringOutcome.decision_date < period_end
    ).all()
    for ho in hired_outcomes:
        sr = db.query(ScreeningResult).get(ho.screening_result_id)
        cat = sr.role_category or "other" if sr else "other"
        hired_by_category[cat] = hired_by_category.get(cat, 0) + 1

    # Get previous month for trend calculation
    prev_period = _add_months(period_start, -1)
    prev_snapshots = db.query(SkillTrendSnapshot).filter(
        SkillTrendSnapshot.tenant_id == tenant_id,
        SkillTrendSnapshot.period_date == prev_period
    ).all()
    prev_data = {(s.role_category, s.skill_name): s.jd_mention_count for s in prev_snapshots}

    # Clear existing snapshots for this period
    db.query(SkillTrendSnapshot).filter(
        SkillTrendSnapshot.tenant_id == tenant_id,
        SkillTrendSnapshot.period_date == period_start
    ).delete()

    # Write new snapshots
    snapshots = []
    for (role_cat, skill_name), counts in skill_data.items():
        prev_count = prev_data.get((role_cat, skill_name), 0)
        current_count = counts["jd_count"]

        if prev_count > 0:
            growth = ((current_count - prev_count) / prev_count) * 100
        elif current_count > 0:
            growth = 100.0
        else:
            growth = 0.0

        if growth > 10:
            direction = "rising"
        elif growth < -10:
            direction = "falling"
        else:
            direction = "stable"

        snapshot = SkillTrendSnapshot(
            tenant_id=tenant_id,
            role_category=role_cat,
            skill_name=skill_name,
            period_date=period_start,
            jd_mention_count=counts["jd_count"],
            resume_present_count=counts["resume_count"],
            hired_with_skill=counts["hired_count"],
            total_hired=hired_by_category.get(role_cat, 0),
            trend_direction=direction,
            growth_pct=round(growth, 1),
            created_at=datetime.utcnow()
        )
        snapshots.append(snapshot)

    db.add_all(snapshots)
    db.commit()
    return len(snapshots)


# ── Query ──────────────────────────────────────────────────────────────────────

def get_skill_trends(db: Session, tenant_id: int, role_category: str = None,
                     months: int = 6) -> Dict:
    """Get skill trend time-series data."""
    end_date = date.today().replace(day=1)
    start_date = _add_months(end_date, -(months - 1))

    query = db.query(SkillTrendSnapshot).filter(
        SkillTrendSnapshot.tenant_id == tenant_id,
        SkillTrendSnapshot.period_date >= start_date,
        SkillTrendSnapshot.period_date <= end_date
    )
    if role_category:
        query = query.filter(SkillTrendSnapshot.role_category == role_category)

    snapshots = query.order_by(
        SkillTrendSnapshot.skill_name, SkillTrendSnapshot.period_date
    ).all()

    # Graceful empty result
    if not snapshots:
        return {
            "role_category": role_category or "all",
            "period_months": months,
            "skills": [],
            "top_rising": [],
            "top_falling": [],
        }

    # Group by skill
    skills_timeline: Dict[str, list] = {}
    for s in snapshots:
        if s.skill_name not in skills_timeline:
            skills_timeline[s.skill_name] = []
        skills_timeline[s.skill_name].append({
            "month": s.period_date.strftime("%Y-%m"),
            "jd_count": s.jd_mention_count,
            "resume_count": s.resume_present_count,
            "hired_pct": round(
                (s.hired_with_skill / max(s.total_hired, 1)) * 100, 1
            ) if s.total_hired else 0,
        })

    # Determine current trend for each skill (from latest snapshot)
    # Build a quick lookup for the last snapshot per skill
    skill_latest: Dict[str, SkillTrendSnapshot] = {}
    for s in snapshots:
        skill_latest[s.skill_name] = s  # ordered by period_date ASC, last wins

    skill_results = []
    for skill_name, timeline in skills_timeline.items():
        latest = skill_latest[skill_name]
        skill_results.append({
            "skill": skill_name,
            "timeline": timeline,
            "trend": latest.trend_direction or "stable",
            "growth_pct": latest.growth_pct or 0,
        })

    # Sort by absolute growth for top rising/falling
    rising = [s["skill"] for s in sorted(skill_results, key=lambda x: x["growth_pct"], reverse=True) if s["trend"] == "rising"][:10]
    falling = [s["skill"] for s in sorted(skill_results, key=lambda x: x["growth_pct"]) if s["trend"] == "falling"][:10]

    return {
        "role_category": role_category or "all",
        "period_months": months,
        "skills": sorted(skill_results, key=lambda x: abs(x["growth_pct"]), reverse=True)[:30],
        "top_rising": rising,
        "top_falling": falling,
    }


def get_trending_skills(db: Session, tenant_id: int, role_category: str = None,
                        direction: str = "rising", limit: int = 10) -> List[Dict]:
    """Get top trending skills in a specific direction."""
    latest_date = db.query(func.max(SkillTrendSnapshot.period_date)).filter(
        SkillTrendSnapshot.tenant_id == tenant_id
    ).scalar()

    if not latest_date:
        return []

    query = db.query(SkillTrendSnapshot).filter(
        SkillTrendSnapshot.tenant_id == tenant_id,
        SkillTrendSnapshot.period_date == latest_date,
        SkillTrendSnapshot.trend_direction == direction
    )
    if role_category:
        query = query.filter(SkillTrendSnapshot.role_category == role_category)

    if direction == "rising":
        query = query.order_by(SkillTrendSnapshot.growth_pct.desc())
    else:
        query = query.order_by(SkillTrendSnapshot.growth_pct.asc())

    results = query.limit(limit).all()
    return [{"skill": s.skill_name, "growth_pct": s.growth_pct,
             "jd_count": s.jd_mention_count, "trend": s.trend_direction} for s in results]
