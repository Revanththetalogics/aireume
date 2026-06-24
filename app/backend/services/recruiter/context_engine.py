"""Interview context engine — aggregates candidate, role, and screening context."""

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backend.models.db_models import (
    Candidate,
    RoleTemplate,
    ScreeningResult,
)

logger = logging.getLogger("aria.recruiter")


class InterviewContextEngine:
    """Aggregates all candidate context for interview planning."""

    def build_context(
        self,
        db: Session,
        candidate_id: int,
        screening_result_id: int | None,
        jd_id: int,
    ) -> dict[str, Any]:
        """
        Loads and aggregates candidate profile, screening result, role/JD,
        and skill-match data into a structured InterviewContext dict.
        """
        logger.info(
            "Building interview context: candidate=%s screening=%s jd=%s",
            candidate_id,
            screening_result_id,
            jd_id,
        )

        candidate = db.execute(
            select(Candidate).where(Candidate.id == candidate_id)
        ).scalar_one_or_none()

        jd = db.execute(
            select(RoleTemplate).where(RoleTemplate.id == jd_id)
        ).scalar_one_or_none()

        screening_result = None
        if screening_result_id:
            screening_result = db.execute(
                select(ScreeningResult).where(ScreeningResult.id == screening_result_id)
            ).scalar_one_or_none()

        if candidate is None:
            raise ValueError(f"Candidate {candidate_id} not found")
        if jd is None:
            raise ValueError(f"Role/JD {jd_id} not found")

        parsed_skills = self._load_json(candidate.parsed_skills, [])
        parsed_education = self._load_json(candidate.parsed_education, [])
        parsed_work_exp = self._load_json(candidate.parsed_work_exp, [])
        gap_analysis = self._load_json(candidate.gap_analysis_json, {})

        required_skills, nice_to_have_skills = self._extract_role_skills(jd)

        screening_data = self._extract_screening_data(screening_result)

        context = {
            "candidate": {
                "id": candidate.id,
                "tenant_id": candidate.tenant_id,
                "name": candidate.name,
                "email": candidate.email,
                "phone": candidate.phone,
                "current_role": candidate.current_role,
                "current_company": candidate.current_company,
                "total_years_exp": candidate.total_years_exp,
                "profile_quality": candidate.profile_quality,
                "parsed_skills": parsed_skills,
                "parsed_education": parsed_education,
                "parsed_work_experience": parsed_work_exp,
                "gap_analysis": gap_analysis,
                "ai_professional_summary": candidate.ai_professional_summary,
            },
            "role": {
                "id": jd.id,
                "tenant_id": jd.tenant_id,
                "title": jd.name,
                "jd_text": jd.jd_text,
                "required_skills": required_skills,
                "nice_to_have_skills": nice_to_have_skills,
                "scoring_weights": self._load_json(jd.scoring_weights, {}),
            },
            "screening_result": screening_data,
            "skill_match": self._extract_skill_match(screening_result),
            "probe_areas": [],
        }

        context["probe_areas"] = self.identify_probe_areas(context)

        logger.info(
            "Interview context built: candidate=%s probes=%d",
            candidate_id,
            len(context["probe_areas"]),
        )
        return context

    def identify_probe_areas(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Analyzes context to determine what needs validation during the interview.
        Returns a list of ProbeArea dicts with category, priority, and reasoning.
        """
        probes: list[dict[str, Any]] = []

        candidate = context.get("candidate", {})
        role = context.get("role", {})
        screening = context.get("screening_result", {}) or {}
        skill_match = context.get("skill_match", {}) or {}

        required_skills = role.get("required_skills", [])
        matched_skills = set(skill_match.get("matched", []))
        gap_skills = set(skill_match.get("gaps", []))

        # Skills claimed but not clearly evidenced
        claimed_or_required = {self._normalize_skill(s) for s in required_skills}
        for skill in sorted(claimed_or_required - matched_skills):
            probes.append({
                "category": "skill_validation",
                "priority": "high",
                "skill": skill,
                "reasoning": f"'{skill}' is required but not clearly evidenced in the resume/screening.",
            })

        # Employment gaps > 6 months
        gap_analysis = candidate.get("gap_analysis", {}) or {}
        gaps = gap_analysis.get("gaps", []) if isinstance(gap_analysis, dict) else []
        for gap in gaps:
            duration_months = 0
            if isinstance(gap, dict):
                duration_months = gap.get("duration_months", 0) or 0
            if duration_months >= 6:
                probes.append({
                    "category": "employment_gap",
                    "priority": "high",
                    "duration_months": duration_months,
                    "reasoning": f"Employment gap of {duration_months} months requires explanation.",
                })

        # Risk signals from fitment
        risk_signals = screening.get("risk_signals", []) or []
        for risk in risk_signals:
            if isinstance(risk, dict):
                risk_type = risk.get("type", "unknown")
                description = risk.get("description", "")
            else:
                risk_type = "unknown"
                description = str(risk)

            if risk_type in ("job_hopping", "overqualification", "short_tenures"):
                probes.append({
                    "category": "risk_validation",
                    "priority": "medium",
                    "risk_type": risk_type,
                    "reasoning": description or f"Validate risk signal: {risk_type}",
                })

        # Career transition / pivot detection
        work_exp = candidate.get("parsed_work_experience", []) or []
        if len(work_exp) >= 2:
            roles = [w.get("title", "") for w in work_exp if isinstance(w, dict)]
            if roles and not self._roles_similar(roles[0], roles[-1]):
                probes.append({
                    "category": "career_transition",
                    "priority": "medium",
                    "reasoning": f"Career pivot detected from '{roles[-1]}' to '{roles[0]}'. Probe motivation and transferability.",
                })

        # Weak scoring dimensions
        weak_dimensions = self._find_weak_dimensions(screening)
        for dim, score in weak_dimensions:
            probes.append({
                "category": "weak_dimension",
                "priority": "medium",
                "dimension": dim,
                "score": score,
                "reasoning": f"{dim} score is weak ({score}); allocate interview time to validate.",
            })

        # Education mismatch
        education = candidate.get("parsed_education", []) or []
        if not education:
            probes.append({
                "category": "education_validation",
                "priority": "low",
                "reasoning": "No education information extracted; verify minimum qualifications if required.",
            })

        # Sort by priority
        priority_rank = {"high": 0, "medium": 1, "low": 2}
        probes.sort(key=lambda p: priority_rank.get(p.get("priority", "low"), 3))

        return probes

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _load_json(self, raw: str | None, default: Any) -> Any:
        if not raw:
            return default
        try:
            parsed = json.loads(raw)
            return parsed if parsed is not None else default
        except (json.JSONDecodeError, TypeError):
            return default

    def _extract_role_skills(self, jd: RoleTemplate) -> tuple[list[str], list[str]]:
        required: list[str] = []
        nice_to_have: list[str] = []

        for raw_list, target in (
            (jd.required_skills_override, required),
            (jd.nice_to_have_skills_override, nice_to_have),
        ):
            if not raw_list:
                continue
            try:
                data = json.loads(raw_list)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, str):
                            target.append(item)
                        elif isinstance(item, dict) and "skill" in item:
                            target.append(item["skill"])
            except (json.JSONDecodeError, TypeError):
                continue

        return required, nice_to_have

    def _extract_screening_data(self, screening: ScreeningResult | None) -> dict[str, Any]:
        if screening is None:
            return {}

        parsed = self._load_json(screening.parsed_data, {})
        analysis = self._load_json(screening.analysis_result, {})
        narrative = self._load_json(screening.narrative_json, {})

        return {
            "id": screening.id,
            "fit_score": screening.deterministic_score,
            "eligibility": screening.eligibility_status,
            "eligibility_reason": screening.eligibility_reason,
            "core_skill_score": screening.core_skill_score,
            "domain_match_score": screening.domain_match_score,
            "status": screening.status,
            "risk_signals": analysis.get("risk_signals", []) if isinstance(analysis, dict) else [],
            "narrative": narrative,
            "parsed_data": parsed,
            "analysis_result": analysis,
        }

    def _extract_skill_match(self, screening: ScreeningResult | None) -> dict[str, Any]:
        if screening is None:
            return {"matched": [], "gaps": [], "core_skill_score": None}

        analysis = self._load_json(screening.analysis_result, {})
        if not isinstance(analysis, dict):
            analysis = {}

        return {
            "matched": analysis.get("matched_skills", []),
            "gaps": analysis.get("gap_skills", []),
            "core_skill_score": screening.core_skill_score,
        }

    def _normalize_skill(self, skill: Any) -> str:
        if isinstance(skill, dict):
            return str(skill.get("skill", "")).lower().strip()
        return str(skill).lower().strip()

    def _roles_similar(self, role_a: str, role_b: str) -> bool:
        if not role_a or not role_b:
            return True
        a = role_a.lower()
        b = role_b.lower()
        # Simple heuristic: share a major keyword family
        families = [
            {"engineer", "developer", "architect"},
            {"manager", "lead", "director", "head"},
            {"analyst", "scientist"},
            {"designer", "ux", "ui"},
            {"sales", "business development", "account executive"},
        ]
        return any(
            (any(f in a for f in family) and any(f in b for f in family))
            for family in families
        )

    def _find_weak_dimensions(self, screening: dict[str, Any]) -> list[tuple[str, Any]]:
        weak: list[tuple[str, Any]] = []
        analysis = screening.get("analysis_result", {}) or {}
        if not isinstance(analysis, dict):
            return weak

        for dim in ("skills", "experience", "education", "stability"):
            score = analysis.get(dim)
            if isinstance(score, (int, float)) and score < 50:
                weak.append((dim, score))
        return weak
