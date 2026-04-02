import json
from typing import Dict, Any, List
from app.backend.services.llm_service import analyze_with_llm


class AnalysisService:
    def __init__(self):
        pass

    async def analyze(
        self,
        resume_text: str,
        job_description: str,
        parsed_data: Dict[str, Any],
        gap_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Compute skill match percentage
        skill_match_percent = self._calculate_skill_match(
            parsed_data.get("skills", []),
            job_description
        )

        # Get total years from gap analysis
        total_years = gap_analysis.get("total_years", 0)

        # Prepare risk signals from gap analysis
        risks = self._prepare_risk_signals(gap_analysis)

        # Get employment gaps for response
        employment_gaps = gap_analysis.get("employment_gaps", [])

        # Call LLM for qualitative analysis
        llm_result = await analyze_with_llm(
            resume_text=resume_text,
            job_description=job_description,
            skill_match_percent=skill_match_percent,
            total_years=total_years,
            gaps=employment_gaps,
            risks=risks
        )

        # Build final response
        result = {
            "fit_score": llm_result["fit_score"],
            "strengths": llm_result["strengths"],
            "weaknesses": llm_result["weaknesses"],
            "employment_gaps": employment_gaps,
            "education_analysis": llm_result["education_analysis"],
            "risk_signals": llm_result["risk_signals"] + risks,
            "final_recommendation": llm_result["final_recommendation"]
        }

        return result

    def _calculate_skill_match(self, candidate_skills: List[str], job_description: str) -> float:
        if not candidate_skills:
            return 0.0

        job_lower = job_description.lower()

        # Count how many candidate skills appear in job description
        matched = 0
        for skill in candidate_skills:
            if skill.lower() in job_lower:
                matched += 1

        # Also extract skills from job description and check inverse
        job_skills = self._extract_skills_from_jd(job_description)

        total_unique_skills = len(set([s.lower() for s in candidate_skills] + [s.lower() for s in job_skills]))

        if total_unique_skills == 0:
            return 0.0

        return (matched / total_unique_skills) * 100

    def _extract_skills_from_jd(self, job_description: str) -> List[str]:
        # Common technical skills to look for
        common_skills = [
            "python", "javascript", "java", "c++", "c#", "go", "rust",
            "react", "vue", "angular", "node", "express", "django", "flask",
            "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
            "sql", "postgresql", "mysql", "mongodb", "redis",
            "machine learning", "ai", "data science", "analytics",
            "leadership", "management", "agile", "scrum", "project management"
        ]

        jd_lower = job_description.lower()
        found = [skill for skill in common_skills if skill in jd_lower]

        return found

    def _prepare_risk_signals(self, gap_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        risks = []

        # Overlapping jobs
        for overlap in gap_analysis.get("overlapping_jobs", []):
            risks.append({
                "type": "overlapping_employment",
                "description": f"Overlapping positions: {overlap['job1']} and {overlap['job2']}"
            })

        # Short stints
        for stint in gap_analysis.get("short_stints", []):
            risks.append({
                "type": "job_hopper",
                "description": f"Short tenure at {stint['company']}: {stint['duration_months']} months"
            })

        return risks


async def analyze_resume(
    resume_text: str,
    job_description: str,
    parsed_data: Dict[str, Any],
    gap_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    service = AnalysisService()
    return await service.analyze(resume_text, job_description, parsed_data, gap_analysis)
