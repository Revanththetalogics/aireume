"""
Enterprise Agent Pipeline for Resume Analysis.

Architecture:
- Agent 1 (instant): Extract structured profile from parsed resume data
- Agent 2 (instant): Deterministic scoring engine (skill/exp/stability/education)
                     Supports custom scoring weights per request.
- Agent 3 (smart):   ARIA custom recruiter model — baked-in persona means ultra-short prompts.
                     Falls back to plain llama3 if ARIA isn't built yet.
- Agent 4 (smart):   Interview Questions Generator — targeted questions from gaps & weaknesses.
"""

import json
import re
import asyncio
import httpx
import os
from typing import Dict, Any, List, Optional


DEFAULT_WEIGHTS = {
    "skills":     0.40,
    "experience": 0.35,
    "stability":  0.15,
    "education":  0.10,
}


class ResumeAnalysisAgent:
    """
    Agent 1: Extract structured recruiter-relevant intelligence from parsed data.
    Pure deterministic — zero LLM calls — runs instantly.
    """

    def extract_candidate_profile(
        self,
        parsed_data: Dict[str, Any],
        job_description: str,
        gap_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        skills    = parsed_data.get("skills", [])
        work_exp  = parsed_data.get("work_experience", [])
        education = parsed_data.get("education", [])

        jd_required_skills = self._extract_jd_skills(job_description)
        jd_years_required  = self._extract_required_years(job_description)
        jd_role            = self._extract_role_title(job_description)

        matched_skills = [s for s in skills if any(
            s.lower() in req.lower() or req.lower() in s.lower()
            for req in jd_required_skills
        )]
        missing_skills = [r for r in jd_required_skills if not any(
            r.lower() in s.lower() or s.lower() in r.lower()
            for s in skills
        )]

        return {
            "role_applied":          jd_role,
            "years_required":        jd_years_required,
            "years_actual":          gap_analysis.get("total_years", 0),
            "matched_skills":        matched_skills[:10],
            "missing_skills":        missing_skills[:8],
            "all_skills":            skills[:15],
            "required_skills_count": len(jd_required_skills),
            "job_count":             len(work_exp),
            "education_level":       self._get_highest_education(education),
            "employment_gaps":       gap_analysis.get("employment_gaps", []),
            "short_stints":          gap_analysis.get("short_stints", []),
            "overlapping_jobs":      gap_analysis.get("overlapping_jobs", []),
            "latest_role":           work_exp[0].get("title", "Unknown") if work_exp else "N/A",
            "latest_company":        work_exp[0].get("company", "Unknown") if work_exp else "N/A",
        }

    def _extract_jd_skills(self, jd: str) -> List[str]:
        common_skills = [
            "python", "java", "javascript", "typescript", "react", "vue", "angular",
            "node", "django", "flask", "fastapi", "spring", "sql", "postgresql",
            "mysql", "mongodb", "redis", "aws", "azure", "gcp", "docker", "kubernetes",
            "ci/cd", "git", "linux", "agile", "scrum", "machine learning", "ai",
            "data analysis", "excel", "tableau", "power bi", "management", "leadership",
            "communication", "c++", "c#", ".net", "golang", "rust", "scala",
            "spark", "hadoop", "kafka", "elasticsearch", "terraform", "ansible",
        ]
        jd_lower = jd.lower()
        return [s for s in common_skills if s in jd_lower]

    def _extract_required_years(self, jd: str) -> float:
        for pattern in [
            r'(\d+)\+?\s*years?\s+of\s+experience',
            r'(\d+)\+?\s*years?\s+experience',
            r'minimum\s+(\d+)\s*years?',
            r'at\s+least\s+(\d+)\s*years?',
        ]:
            m = re.search(pattern, jd, re.IGNORECASE)
            if m:
                return float(m.group(1))
        return 0.0

    def _extract_role_title(self, jd: str) -> str:
        for line in jd.strip().split('\n')[:5]:
            line = line.strip()
            if 5 < len(line) < 80 and not line.startswith(('•', '-', '*')):
                return line
        return "the role"

    def _get_highest_education(self, education: List[Dict]) -> str:
        if not education:
            return "Not specified"
        rank_map = {
            "phd": 5, "doctorate": 5,
            "master": 4, "mba": 4, "m.s": 4, "m.a": 4, "mtech": 4,
            "bachelor": 3, "b.s": 3, "b.a": 3, "btech": 3, "be": 3,
        }
        highest, highest_rank = "degree", 0
        for edu in education:
            degree = edu.get("degree", "").lower()
            for key, rank in rank_map.items():
                if key in degree and rank > highest_rank:
                    highest_rank = rank
                    highest = edu.get("degree", degree)
        return highest


class ScoringAgent:
    """
    Agent 2: Deterministic scoring engine.
    Supports custom scoring weights via the `weights` parameter.
    """

    def compute_scores(
        self,
        profile: Dict[str, Any],
        gap_analysis: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        w = {**DEFAULT_WEIGHTS, **(weights or {})}
        # Normalize weights to sum to 1.0
        total = sum(w.values())
        if total > 0:
            w = {k: v / total for k, v in w.items()}

        scores = {}

        # Skill match (0-100)
        matched  = len(profile.get("matched_skills", []))
        jd_total = matched + len(profile.get("missing_skills", []))
        scores["skill_match"] = round((matched / max(jd_total, 1)) * 100)

        # Experience match (0-100)
        actual   = profile.get("years_actual", 0)
        required = profile.get("years_required", 0)
        if required == 0:
            scores["experience_match"] = min(100, int(actual * 10))
        elif actual >= required:
            scores["experience_match"] = min(100, 70 + int((actual - required) * 5))
        else:
            scores["experience_match"] = int((actual / required) * 70)

        # Stability (0-100)
        stability  = 100
        stability -= len(gap_analysis.get("employment_gaps", [])) * 15
        stability -= len(gap_analysis.get("short_stints", [])) * 10
        stability -= len(gap_analysis.get("overlapping_jobs", [])) * 20
        scores["stability"] = max(0, stability)

        # Education (0-100)
        edu = profile.get("education_level", "").lower()
        edu_map = {
            "phd": 100, "doctorate": 100,
            "master": 85, "mba": 85, "mtech": 85,
            "bachelor": 70, "b.s": 70, "btech": 70, "be": 70,
        }
        scores["education"] = 60
        for key, val in edu_map.items():
            if key in edu:
                scores["education"] = val
                break

        # Composite fit score with custom weights
        scores["fit_score"] = int(
            scores["skill_match"]      * w["skills"] +
            scores["experience_match"] * w["experience"] +
            scores["stability"]        * w["stability"] +
            scores["education"]        * w["education"]
        )

        # Risk level
        risk_count = (
            len(gap_analysis.get("employment_gaps", [])) +
            len(gap_analysis.get("short_stints", [])) +
            len(gap_analysis.get("overlapping_jobs", []))
        )
        scores["risk_level"] = "Low" if risk_count == 0 else "Medium" if risk_count <= 2 else "High"

        if scores["fit_score"] >= 72:
            scores["preliminary_recommendation"] = "Shortlist"
        elif scores["fit_score"] >= 45:
            scores["preliminary_recommendation"] = "Consider"
        else:
            scores["preliminary_recommendation"] = "Reject"

        return scores


class LLMInsightAgent:
    """
    Agent 3: ARIA — custom recruiter model with baked-in persona.
    Falls back to llama3 if ARIA model isn't available.
    """

    PRIMARY_MODEL  = "aria-recruiter"
    FALLBACK_MODEL = "llama3"

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model    = os.getenv("OLLAMA_MODEL", self.PRIMARY_MODEL)

    def _build_aria_prompt(self, profile: Dict[str, Any], scores: Dict[str, Any]) -> str:
        matched  = ", ".join(profile.get("matched_skills", [])[:6]) or "none listed"
        missing  = ", ".join(profile.get("missing_skills", [])[:4]) or "none"
        gaps     = len(profile.get("employment_gaps", []))
        stints   = len(profile.get("short_stints", []))
        overlaps = len(profile.get("overlapping_jobs", []))

        stability_parts = []
        if gaps:     stability_parts.append(f"{gaps} gap(s)")
        if stints:   stability_parts.append(f"{stints} short-stint(s)")
        if overlaps: stability_parts.append(f"{overlaps} overlapping job(s)")
        stability = ", ".join(stability_parts) if stability_parts else "clean record"

        return (
            f"Role: {profile.get('role_applied', 'Not specified')} | "
            f"Exp: {profile.get('years_actual', 0):.1f}y actual vs "
            f"{profile.get('years_required', 0):.1f}y required | "
            f"Matched: {matched} | Missing: {missing} | "
            f"Latest: {profile.get('latest_role', 'N/A')} at {profile.get('latest_company', 'N/A')} | "
            f"Education: {profile.get('education_level', 'Not specified')} | "
            f"Stability: {stability} | Fit score: {scores.get('fit_score', 50)}"
        )

    def _build_fallback_prompt(self, profile: Dict[str, Any], scores: Dict[str, Any]) -> str:
        matched = ", ".join(profile.get("matched_skills", [])[:5]) or "none"
        missing = ", ".join(profile.get("missing_skills", [])[:3]) or "none"
        rec     = scores.get("preliminary_recommendation", "Consider")
        return (
            f"You are a senior recruiter. Analyze and return JSON only.\n\n"
            f"Role: {profile.get('role_applied', 'N/A')} | "
            f"Exp: {profile.get('years_actual', 0):.1f}y vs {profile.get('years_required', 0):.1f}y required | "
            f"Matched skills: {matched} | Missing: {missing} | "
            f"Latest: {profile.get('latest_role')} at {profile.get('latest_company')} | "
            f"Education: {profile.get('education_level')} | Fit score: {scores.get('fit_score')}/100\n\n"
            f'JSON: {{"strengths":["3 specific strengths"],"weaknesses":["3 specific gaps"],'
            f'"education_analysis":"1 sentence","risk_signals":[],"final_recommendation":"{rec}"}}'
        )

    async def _is_model_available(self, model_name: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                available = [m.get("name", "") for m in r.json().get("models", [])]
                return any(model_name in name for name in available)
        except Exception:
            return False

    async def get_insights(self, profile: Dict, scores: Dict) -> Dict[str, Any]:
        use_aria = (self.model == self.PRIMARY_MODEL) and await self._is_model_available(self.PRIMARY_MODEL)

        if use_aria:
            model   = self.PRIMARY_MODEL
            prompt  = self._build_aria_prompt(profile, scores)
            options = {"num_predict": 400, "num_ctx": 512}
        else:
            model   = self.FALLBACK_MODEL
            prompt  = self._build_fallback_prompt(profile, scores)
            options = {"temperature": 0.1, "top_p": 0.9, "num_predict": 350, "num_ctx": 768}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": options,
                    }
                )
                response.raise_for_status()
                raw = response.json().get("response", "{}")
                return self._parse_and_validate(raw, scores)
        except Exception as e:
            return self._fallback_insights(scores, str(e))

    def _parse_and_validate(self, raw: str, scores: Dict) -> Dict[str, Any]:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                except Exception:
                    return self._fallback_insights(scores, "JSON parse failed")
            else:
                return self._fallback_insights(scores, "No JSON in LLM response")

        valid_recs = {"Shortlist", "Consider", "Reject"}
        rec = parsed.get("final_recommendation", "")
        if rec not in valid_recs:
            rec = scores.get("preliminary_recommendation", "Consider")

        return {
            "strengths":            parsed.get("strengths", [])[:5],
            "weaknesses":           parsed.get("weaknesses", [])[:5],
            "education_analysis":   parsed.get("education_analysis", ""),
            "risk_signals":         parsed.get("risk_signals", []),
            "final_recommendation": rec,
        }

    def _fallback_insights(self, scores: Dict, reason: str) -> Dict[str, Any]:
        return {
            "strengths":            ["Profile meets baseline requirements — manual review recommended"],
            "weaknesses":           ["AI insight generation incomplete — review raw profile"],
            "education_analysis":   "Education assessment requires manual review.",
            "risk_signals":         [f"Partial analysis: {reason}"] if reason else [],
            "final_recommendation": scores.get("preliminary_recommendation", "Consider"),
        }


class InterviewQuestionsAgent:
    """
    Agent 4: Generates targeted interview questions from the candidate's skill gaps and weaknesses.
    """

    FALLBACK_MODEL = "llama3"

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def _build_prompt(self, profile: Dict, insights: Dict) -> str:
        missing  = ", ".join(profile.get("missing_skills", [])[:6]) or "general technical skills"
        weaknesses = "; ".join(insights.get("weaknesses", [])[:3]) or "gaps noted in profile"
        role     = profile.get("role_applied", "the role")
        return (
            f"You are an expert interviewer. Generate targeted interview questions as JSON only.\n"
            f"Role: {role}\n"
            f"Skill gaps: {missing}\n"
            f"Candidate weaknesses: {weaknesses}\n\n"
            f'Return JSON: {{"technical_questions":["5 specific technical questions targeting gaps"],'
            f'"behavioral_questions":["3 behavioral/STAR questions for risk signals"],'
            f'"culture_fit_questions":["2 culture/motivation questions"]}}'
        )

    async def generate_questions(self, profile: Dict, insights: Dict) -> Dict[str, Any]:
        prompt = self._build_prompt(profile, insights)
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.FALLBACK_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.3, "num_predict": 400, "num_ctx": 768},
                    }
                )
                response.raise_for_status()
                raw = response.json().get("response", "{}")
                return self._parse(raw)
        except Exception:
            return self._fallback_questions(profile)

    def _parse(self, raw: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(raw)
            return {
                "technical_questions":   parsed.get("technical_questions", [])[:5],
                "behavioral_questions":  parsed.get("behavioral_questions", [])[:3],
                "culture_fit_questions": parsed.get("culture_fit_questions", [])[:2],
            }
        except Exception:
            return self._fallback_questions({})

    def _fallback_questions(self, profile: Dict) -> Dict[str, Any]:
        missing = profile.get("missing_skills", [])
        return {
            "technical_questions": [
                f"Can you walk us through your experience with {skill}?" for skill in missing[:3]
            ] or ["Describe a challenging technical problem you solved recently."],
            "behavioral_questions": [
                "Tell me about a time you had to quickly learn a new technology.",
                "Describe a situation where you handled a difficult stakeholder.",
            ],
            "culture_fit_questions": [
                "What motivates you in your work?",
                "How do you prefer to receive feedback?",
            ],
        }


# ─── Pipeline orchestrator ────────────────────────────────────────────────────

async def run_agent_pipeline(
    resume_text: str,
    job_description: str,
    parsed_data: Dict[str, Any],
    gap_analysis: Dict[str, Any],
    scoring_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Runs the full 4-agent pipeline and returns a complete analysis result dict.
    """
    # Agent 1 — profile extraction (instant)
    profile_agent = ResumeAnalysisAgent()
    profile = profile_agent.extract_candidate_profile(parsed_data, job_description, gap_analysis)

    # Agent 2 — deterministic scoring (instant, optional custom weights)
    scoring_agent = ScoringAgent()
    scores = scoring_agent.compute_scores(profile, gap_analysis, weights=scoring_weights)

    # Agent 3 + 4 — run in parallel to save time
    llm_agent       = LLMInsightAgent()
    interview_agent = InterviewQuestionsAgent()

    insights, questions = await asyncio.gather(
        llm_agent.get_insights(profile, scores),
        interview_agent.generate_questions(profile, {}),
    )

    return {
        "fit_score":            scores["fit_score"],
        "strengths":            insights["strengths"],
        "weaknesses":           insights["weaknesses"],
        "employment_gaps":      gap_analysis.get("employment_gaps", []),
        "education_analysis":   insights["education_analysis"],
        "risk_signals":         insights["risk_signals"],
        "final_recommendation": insights["final_recommendation"],
        "score_breakdown": {
            "skill_match":      scores["skill_match"],
            "experience_match": scores["experience_match"],
            "stability":        scores["stability"],
            "education":        scores["education"],
        },
        "matched_skills":        profile["matched_skills"],
        "missing_skills":        profile["missing_skills"],
        "risk_level":            scores["risk_level"],
        "required_skills_count": profile.get("required_skills_count", 0),
        "interview_questions":   questions,
    }
