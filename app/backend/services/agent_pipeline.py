"""
Enterprise Agent Pipeline for Resume Analysis.

Architecture:
- Agent 1 (instant): Extract structured profile from parsed resume data
- Agent 2 (instant): Deterministic scoring engine (skill/exp/stability/education)
- Agent 3 (smart):   ARIA custom recruiter model — baked-in persona means ultra-short prompts
                     Falls back to plain llama3 if ARIA isn't built yet.

The LLM never sees raw resume text. It receives only structured facts (~60 tokens).
"""

import json
import re
import asyncio
import httpx
import os
from typing import Dict, Any, List


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
        skills   = parsed_data.get("skills", [])
        work_exp = parsed_data.get("work_experience", [])
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
            "role_applied":     jd_role,
            "years_required":   jd_years_required,
            "years_actual":     gap_analysis.get("total_years", 0),
            "matched_skills":   matched_skills[:10],
            "missing_skills":   missing_skills[:5],
            "all_skills":       skills[:15],
            "job_count":        len(work_exp),
            "education_level":  self._get_highest_education(education),
            "employment_gaps":  gap_analysis.get("employment_gaps", []),
            "short_stints":     gap_analysis.get("short_stints", []),
            "overlapping_jobs": gap_analysis.get("overlapping_jobs", []),
            "latest_role":      work_exp[0].get("title", "Unknown") if work_exp else "N/A",
            "latest_company":   work_exp[0].get("company", "Unknown") if work_exp else "N/A",
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
    Produces objective sub-scores and composite fit score without any LLM. Instant.
    """

    def compute_scores(
        self,
        profile: Dict[str, Any],
        gap_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        scores = {}

        # Skill match (0-100)
        matched   = len(profile.get("matched_skills", []))
        jd_total  = matched + len(profile.get("missing_skills", []))
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

        # Stability (0-100) — penalise gaps, short stints, overlaps
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

        # Composite fit score
        scores["fit_score"] = int(
            scores["skill_match"]       * 0.40 +
            scores["experience_match"]  * 0.35 +
            scores["stability"]         * 0.15 +
            scores["education"]         * 0.10
        )

        # Risk level
        risk_count = (
            len(gap_analysis.get("employment_gaps", [])) +
            len(gap_analysis.get("short_stints", [])) +
            len(gap_analysis.get("overlapping_jobs", []))
        )
        scores["risk_level"] = "Low" if risk_count == 0 else "Medium" if risk_count <= 2 else "High"

        # Preliminary recommendation
        if scores["fit_score"] >= 72:
            scores["preliminary_recommendation"] = "Shortlist"
        elif scores["fit_score"] >= 45:
            scores["preliminary_recommendation"] = "Consider"
        else:
            scores["preliminary_recommendation"] = "Reject"

        return scores


class LLMInsightAgent:
    """
    Agent 3: ARIA — custom recruiter model with baked-in persona and decision framework.

    When aria-recruiter model is available (built from ollama/Modelfile):
      - Sends a single-line structured fact string (~60 tokens)
      - The system prompt is permanently loaded in the model weights
      - Ultra-fast, highly consistent recruiter-grade output

    When aria-recruiter is not yet built:
      - Falls back to llama3 with a short explicit prompt
      - Slightly less personality but same JSON structure
    """

    PRIMARY_MODEL  = "aria-recruiter"
    FALLBACK_MODEL = "llama3"

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model    = os.getenv("OLLAMA_MODEL", self.PRIMARY_MODEL)

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def _build_aria_prompt(self, profile: Dict[str, Any], scores: Dict[str, Any]) -> str:
        """
        Single-line fact string for ARIA.
        Mirrors the example format in the Modelfile so the model pattern-matches instantly.
        """
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
            f"Matched: {matched} | "
            f"Missing: {missing} | "
            f"Latest: {profile.get('latest_role', 'N/A')} at {profile.get('latest_company', 'N/A')} | "
            f"Education: {profile.get('education_level', 'Not specified')} | "
            f"Stability: {stability} | "
            f"Fit score: {scores.get('fit_score', 50)}"
        )

    def _build_fallback_prompt(self, profile: Dict[str, Any], scores: Dict[str, Any]) -> str:
        """Short explicit prompt for plain llama3 when ARIA isn't built yet."""
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

    # ------------------------------------------------------------------
    # Model availability check
    # ------------------------------------------------------------------

    async def _is_model_available(self, model_name: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                available = [m.get("name", "") for m in r.json().get("models", [])]
                return any(model_name in name for name in available)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------

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


# ------------------------------------------------------------------
# Pipeline orchestrator
# ------------------------------------------------------------------

async def run_agent_pipeline(
    resume_text: str,
    job_description: str,
    parsed_data: Dict[str, Any],
    gap_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Runs the full 3-agent pipeline and returns a complete analysis result dict.
    """
    # Agent 1 — profile extraction (instant)
    profile_agent = ResumeAnalysisAgent()
    profile = profile_agent.extract_candidate_profile(parsed_data, job_description, gap_analysis)

    # Agent 2 — deterministic scoring (instant)
    scoring_agent = ScoringAgent()
    scores = scoring_agent.compute_scores(profile, gap_analysis)

    # Agent 3 — ARIA/llama3 qualitative insights
    llm_agent = LLMInsightAgent()
    insights  = await llm_agent.get_insights(profile, scores)

    return {
        "fit_score":             scores["fit_score"],
        "strengths":             insights["strengths"],
        "weaknesses":            insights["weaknesses"],
        "employment_gaps":       gap_analysis.get("employment_gaps", []),
        "education_analysis":    insights["education_analysis"],
        "risk_signals":          insights["risk_signals"],
        "final_recommendation":  insights["final_recommendation"],
        # Enterprise breakdown
        "score_breakdown": {
            "skill_match":       scores["skill_match"],
            "experience_match":  scores["experience_match"],
            "stability":         scores["stability"],
            "education":         scores["education"],
        },
        "matched_skills": profile["matched_skills"],
        "missing_skills":  profile["missing_skills"],
        "risk_level":      scores["risk_level"],
    }
