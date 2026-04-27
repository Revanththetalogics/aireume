"""
Tests for hybrid_pipeline.py — all pure Python (no LLM calls for Components 1-7).
Component 8 (explain_with_llm) is tested with a mocked LLM.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── Import the module under test ─────────────────────────────────────────────
from app.backend.services.hybrid_pipeline import (
    parse_jd_rules,
    parse_resume_rules,
    _infer_total_years_from_resume_text,
    score_education_rules,
    score_experience_rules,
    domain_architecture_rules,
    compute_fit_score,
    _build_fallback_narrative,
    _merge_llm_into_result,
    _run_python_phase,
    run_hybrid_pipeline,
    _assess_quality,
)
from app.backend.services.skill_matcher import (
    match_skills,
    _normalize_skill,
    _expand_skill,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Component 1: parse_jd_rules
# ═══════════════════════════════════════════════════════════════════════════════

class TestInferResumeMetadata:
    def test_infer_years_from_prose(self):
        t = "Embedded engineer with 7+ years of experience in automotive systems."
        assert _infer_total_years_from_resume_text(t) == 7.0

    def test_parse_resume_rules_uses_inferred_years_when_gap_zero(self):
        gap = {
            "total_years": 0.0,
            "employment_gaps": [],
            "overlapping_jobs": [],
            "short_stints": [],
        }
        parsed = {
            "contact_info": {},
            "work_experience": [],
            "raw_text": "I bring over 6 years of professional software development experience.",
            "skills": ["python"],
            "education": [],
        }
        prof = parse_resume_rules(parsed, gap)
        assert prof["total_effective_years"] == 6.0


class TestParseJdRules:

    def test_years_pattern_plus(self):
        jd = "We need 5+ years of Python experience."
        result = parse_jd_rules(jd * 10)  # multiply to pass word count
        assert result["required_years"] == 5

    def test_years_pattern_minimum(self):
        jd = "Minimum of 3 years working with React. " * 10
        result = parse_jd_rules(jd)
        assert result["required_years"] == 3

    def test_years_pattern_range_takes_lower(self):
        jd = "3-7 years of experience required. " * 10
        result = parse_jd_rules(jd)
        assert result["required_years"] == 3

    def test_years_zero_when_not_mentioned(self):
        jd = "We are looking for a talented engineer to join our team and build great products. " * 5
        result = parse_jd_rules(jd)
        assert result["required_years"] == 0

    def test_domain_backend(self):
        jd = ("Senior Backend Engineer. We use FastAPI, PostgreSQL, Redis, microservices, "
              "REST API, docker, kubernetes. " * 5)
        result = parse_jd_rules(jd)
        assert result["domain"] == "backend"

    def test_domain_ml_ai(self):
        jd = ("Machine learning engineer role. Must know PyTorch, TensorFlow, deep learning, "
              "NLP, neural network, transformers, LLM. " * 5)
        result = parse_jd_rules(jd)
        assert result["domain"] == "ml_ai"

    def test_domain_devops(self):
        jd = ("DevOps engineer. Kubernetes, docker, terraform, ansible, jenkins, ci/cd, "
              "prometheus, grafana, infrastructure as code. " * 5)
        result = parse_jd_rules(jd)
        assert result["domain"] == "devops"

    def test_seniority_from_title(self):
        jd = "Senior Python Developer\n\nWe need 5 years experience in backend development. " * 5
        result = parse_jd_rules(jd)
        assert result["seniority"] == "senior"

    def test_seniority_junior_from_title(self):
        jd = "Junior Software Engineer\nEntry-level position. 0-1 years experience. " * 5
        result = parse_jd_rules(jd)
        assert result["seniority"] in ("junior", "mid")

    def test_seniority_lead_from_years(self):
        jd = "Software Engineer with 10+ years experience managing large teams. " * 5
        result = parse_jd_rules(jd)
        assert result["seniority"] in ("lead", "senior")

    def test_required_vs_nice_to_have_split(self):
        jd = (
            "Required: Python, FastAPI, PostgreSQL. "
            "Nice to have: GraphQL, Redis, Kubernetes. "
        ) * 10
        result = parse_jd_rules(jd)
        # required should contain python/fastapi
        req_lower = [s.lower() for s in result["required_skills"]]
        nice_lower = [s.lower() for s in result["nice_to_have_skills"]]
        assert any("python" in s for s in req_lower)
        # nice-to-have should be separate (no duplication)
        assert set(result["required_skills"]).isdisjoint(set(result["nice_to_have_skills"]))

    def test_role_title_extraction(self):
        jd = "Senior Backend Engineer\n\nWe are looking for a skilled engineer " * 5
        result = parse_jd_rules(jd)
        assert "engineer" in result["role_title"].lower()

    def test_default_domain_other(self):
        jd = "Creative director needed with strong leadership skills. " * 10
        result = parse_jd_rules(jd)
        # Should not crash and should return a domain
        assert result["domain"] in (
            "backend", "frontend", "fullstack", "data_science", "ml_ai",
            "devops", "embedded", "mobile", "management", "other"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Component 3: match_skills
# ═══════════════════════════════════════════════════════════════════════════════

class TestMatchSkills:

    def test_exact_match(self):
        result = match_skills(["python"], ["python"], "python developer")
        assert "python" in result["matched_skills"]
        assert result["skill_score"] == 100

    def test_alias_match_postgres(self):
        """'postgres' in candidate should match 'postgresql' in JD."""
        result = match_skills(["postgres"], ["postgresql"], "")
        assert result["matched_skills"]
        assert result["missing_skills"] == [] or "postgresql" not in result["missing_skills"]

    def test_alias_match_js(self):
        """'js' in candidate should match 'javascript' in JD."""
        result = match_skills(["js"], ["javascript"], "")
        assert result["matched_skills"]

    def test_substring_match(self):
        """'react' in candidate should match 'react native' in JD."""
        result = match_skills(["react"], ["react native"], "")
        assert result["matched_skills"]

    def test_missing_skill_tracked(self):
        result = match_skills(["python"], ["python", "kubernetes"], "")
        assert "kubernetes" in result["missing_skills"]

    def test_empty_required_defaults_50(self):
        """If JD has no required skills, skill_score defaults to 50 (neutral)."""
        result = match_skills(["python"], [], "")
        assert result["skill_score"] == 50

    def test_adjacent_skills(self):
        result = match_skills(
            ["python", "redis"],
            ["python"],
            "",
            ["redis", "graphql"],
        )
        assert "redis" in result["adjacent_skills"]
        assert "graphql" not in result["adjacent_skills"]

    def test_skill_score_partial(self):
        result = match_skills(
            ["python"],
            ["python", "java", "c++"],
            "",
        )
        # 1 of 3 matched = 33%
        assert result["skill_score"] == pytest.approx(33, abs=2)

    def test_rawtext_fallback_scan(self):
        """Skills found in raw resume text even if not in skills_identified."""
        raw_text = "Worked extensively with kubernetes and docker in production."
        result = match_skills(
            [],
            ["kubernetes"],
            raw_text,
        )
        assert result["matched_skills"]


# ═══════════════════════════════════════════════════════════════════════════════
# Component 4: score_education_rules
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoreEducationRules:

    def _profile(self, edu):
        return {"education": edu, "skills_identified": []}

    def test_phd_score(self):
        profile = self._profile([{"degree": "PhD Computer Science", "field": "computer science"}])
        score = score_education_rules(profile, "backend")
        assert score >= 90

    def test_masters_relevant_field(self):
        profile = self._profile([{"degree": "Master of Computer Science", "field": "computer science"}])
        score = score_education_rules(profile, "backend")
        assert score >= 80

    def test_bachelors_relevant(self):
        profile = self._profile([{"degree": "Bachelor of Science in Computer Engineering", "field": "computer engineering"}])
        score = score_education_rules(profile, "backend")
        assert 60 <= score <= 80

    def test_irrelevant_degree_penalised(self):
        profile = self._profile([{"degree": "Bachelor of Arts in History", "field": "history"}])
        score_rel = score_education_rules(
            self._profile([{"degree": "Bachelor Computer Science", "field": "computer science"}]),
            "backend"
        )
        score_irrel = score_education_rules(profile, "backend")
        assert score_rel > score_irrel

    def test_no_education_returns_neutral(self):
        """Missing education data should not penalise — return 60."""
        score = score_education_rules(self._profile([]), "backend")
        assert score == 60

    def test_mba_management(self):
        profile = self._profile([{"degree": "MBA", "field": "business administration"}])
        score = score_education_rules(profile, "management")
        assert score >= 75

    def test_embedded_domain_electronics(self):
        profile = self._profile([{"degree": "BE Electronics Engineering", "field": "electronics"}])
        score = score_education_rules(profile, "embedded")
        assert score >= 60


# ═══════════════════════════════════════════════════════════════════════════════
# Component 5: score_experience_rules
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoreExperienceRules:

    def _profile(self, years):
        return {"total_effective_years": years, "education": [], "skills_identified": []}

    def _jd(self, required_years):
        return {"required_years": required_years, "domain": "backend", "role_title": "Eng"}

    def _gap(self, gaps=None, stints=None, overlaps=None):
        return {
            "employment_gaps":  gaps or [],
            "short_stints":     stints or [],
            "overlapping_jobs": overlaps or [],
            "total_years":      0,
        }

    def test_exact_years_match(self):
        result = score_experience_rules(self._profile(5), self._jd(5), self._gap())
        assert result["exp_score"] == 70  # exact match = 70

    def test_over_years_bonus(self):
        result = score_experience_rules(self._profile(8), self._jd(5), self._gap())
        assert result["exp_score"] > 70  # above required → bonus

    def test_under_years_penalty(self):
        result = score_experience_rules(self._profile(2), self._jd(5), self._gap())
        assert result["exp_score"] < 70

    def test_zero_required_years_scales_with_actual(self):
        r1 = score_experience_rules(self._profile(5), self._jd(0), self._gap())
        r2 = score_experience_rules(self._profile(10), self._jd(0), self._gap())
        assert r2["exp_score"] >= r1["exp_score"]

    def test_critical_gap_deducts_timeline(self):
        gaps = [{"severity": "critical", "duration_months": 15, "start_date": "2020-01", "end_date": "2021-04"}]
        result = score_experience_rules(self._profile(5), self._jd(5), self._gap(gaps=gaps))
        assert result["timeline_score"] <= 63   # 85 - 22

    def test_minor_gaps_moderate_deduction(self):
        gaps = [
            {"severity": "minor", "duration_months": 4},
            {"severity": "moderate", "duration_months": 8},
        ]
        result = score_experience_rules(self._profile(5), self._jd(5), self._gap(gaps=gaps))
        assert result["timeline_score"] <= 68   # 85 - 5 - 12

    def test_short_stints_deduction(self):
        stints = [{"duration_months": 2}, {"duration_months": 3}]
        result = score_experience_rules(self._profile(5), self._jd(5), self._gap(stints=stints))
        assert result["timeline_score"] <= 75   # 85 - 10

    def test_no_gaps_full_timeline(self):
        result = score_experience_rules(self._profile(7), self._jd(5), self._gap())
        assert result["timeline_score"] == 85
        assert "Continuous" in result["timeline_text"]

    def test_timeline_text_mentions_gaps(self):
        gaps = [{"severity": "critical", "duration_months": 14}]
        result = score_experience_rules(self._profile(5), self._jd(5), self._gap(gaps=gaps))
        assert "gap" in result["timeline_text"].lower()

    def test_timeline_score_floor_10(self):
        many_gaps = [{"severity": "critical"}] * 10
        result = score_experience_rules(self._profile(0), self._jd(5), self._gap(gaps=many_gaps))
        assert result["timeline_score"] >= 10


# ═══════════════════════════════════════════════════════════════════════════════
# Component 6: domain_architecture_rules
# ═══════════════════════════════════════════════════════════════════════════════

class TestDomainArchitectureRules:

    def test_high_domain_match(self):
        text = ("Worked with FastAPI, PostgreSQL, Redis, microservices, REST API, Docker, "
                "Kubernetes. Backend developer with 7 years experience. ")
        result = domain_architecture_rules(text * 3, "backend", "Senior Backend Engineer")
        assert result["domain_score"] >= 60

    def test_wrong_domain_low_score(self):
        text = ("Mobile app developer building iOS and Android apps with Flutter and Swift. "
                "App Store deployments, push notifications, Xcode. ")
        result = domain_architecture_rules(text * 3, "backend", "iOS Developer")
        assert result["domain_score"] < 60  # no backend keywords

    def test_architecture_signals_increase_score(self):
        text_basic = "Developed features using Python and FastAPI. "
        text_arch  = ("Architected microservices, led design reviews, scalable distributed "
                      "system, tech lead, mentored team, system design. ")
        r_basic = domain_architecture_rules(text_basic * 5, "backend", None)
        r_arch  = domain_architecture_rules(text_arch  * 5, "backend", None)
        assert r_arch["arch_score"] > r_basic["arch_score"]

    def test_current_role_bonus(self):
        text = "FastAPI REST API microservices PostgreSQL. " * 5
        r_match    = domain_architecture_rules(text, "backend", "Backend Engineer")
        r_mismatch = domain_architecture_rules(text, "backend", "Marketing Manager")
        assert r_match["domain_score"] >= r_mismatch["domain_score"]


# ═══════════════════════════════════════════════════════════════════════════════
# Component 7: compute_fit_score
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeFitScore:

    def _scores(self, **kwargs):
        defaults = {
            "skill_score": 80, "exp_score": 75, "arch_score": 70,
            "edu_score": 70, "timeline_score": 85, "domain_score": 70,
            "actual_years": 6, "required_years": 5,
            "matched_skills": ["python"], "missing_skills": [],
            "required_count": 1,
            "employment_gaps": [], "short_stints": [],
        }
        defaults.update(kwargs)
        return defaults

    def test_high_scores_shortlist(self):
        result = compute_fit_score(self._scores())
        assert result["final_recommendation"] == "Shortlist"
        assert result["fit_score"] >= 72

    def test_low_scores_reject(self):
        result = compute_fit_score(self._scores(
            skill_score=10, exp_score=10, arch_score=20,
            edu_score=30, timeline_score=30, domain_score=10,
            missing_skills=["python", "java", "kubernetes", "docker"],
            required_count=4,
        ))
        assert result["final_recommendation"] == "Reject"
        assert result["fit_score"] < 45

    def test_medium_scores_consider(self):
        result = compute_fit_score(self._scores(
            skill_score=50, exp_score=45, arch_score=45,
            edu_score=50, timeline_score=50, domain_score=50,
        ))
        assert result["final_recommendation"] in ("Consider", "Reject")

    def test_fit_score_clamped_0_100(self):
        result = compute_fit_score(self._scores(
            skill_score=200, exp_score=200,
        ))
        assert 0 <= result["fit_score"] <= 100

    def test_critical_gap_risk_signal(self):
        gaps = [{"severity": "critical", "duration_months": 14}]
        result = compute_fit_score(self._scores(employment_gaps=gaps))
        types = [r["type"] for r in result["risk_signals"]]
        assert "gap" in types

    def test_skill_gap_50pct_risk_high(self):
        result = compute_fit_score(self._scores(
            matched_skills=["python"],
            missing_skills=["java", "docker", "kubernetes"],
            required_count=4,
        ))
        gap_signals = [r for r in result["risk_signals"] if r["type"] == "skill_gap"]
        assert gap_signals
        assert gap_signals[0]["severity"] in ("high", "medium")

    def test_domain_mismatch_risk_signal(self):
        result = compute_fit_score(self._scores(domain_score=30))
        types = [r["type"] for r in result["risk_signals"]]
        assert "domain_mismatch" in types

    def test_overqualified_risk_signal(self):
        result = compute_fit_score(self._scores(actual_years=15, required_years=3))
        types = [r["type"] for r in result["risk_signals"]]
        assert "overqualified" in types

    def test_score_breakdown_contains_all_dimensions(self):
        result = compute_fit_score(self._scores())
        bd = result["score_breakdown"]
        assert "skill_match" in bd
        assert "experience_match" in bd
        assert "education" in bd
        assert "architecture" in bd
        assert "timeline" in bd
        assert "domain_fit" in bd

    def test_custom_weights_ignored_locked_system(self):
        """Custom weights are ignored — the weight system is locked for deterministic scoring."""
        scores = self._scores(skill_score=100, exp_score=0)
        r_default  = compute_fit_score(scores)
        r_custom = compute_fit_score(scores, {"skills": 0.10, "experience": 0.50,
                                               "architecture": 0.10, "education": 0.05,
                                               "timeline": 0.10, "domain": 0.05, "risk": 0.10})
        # Both should produce identical scores because custom weights are ignored
        assert r_custom["fit_score"] == r_default["fit_score"]


# ═══════════════════════════════════════════════════════════════════════════════
# Quality assessment
# ═══════════════════════════════════════════════════════════════════════════════

class TestAssessQuality:

    def test_high_quality(self):
        profile = {
            "skills_identified": ["python", "fastapi", "postgresql", "docker"],
            "education": [{"degree": "BSc"}],
            "total_effective_years": 5.0,
        }
        assert _assess_quality(profile) == "high"

    def test_low_quality_no_data(self):
        profile = {"skills_identified": [], "total_effective_years": 0, "education": []}
        assert _assess_quality(profile) == "low"

    def test_medium_quality_few_skills(self):
        profile = {
            "skills_identified": ["python"],
            "total_effective_years": 0,
            "education": [],
        }
        assert _assess_quality(profile) == "medium"


# ═══════════════════════════════════════════════════════════════════════════════
# Fallback narrative
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildFallbackNarrative:

    def test_strengths_include_matched_skills(self):
        python_result = {"fit_score": 65, "score_breakdown": {}, "_required_years": 5}
        skill_analysis = {"matched_skills": ["python", "fastapi"], "missing_skills": [], "required_count": 2}
        result = _build_fallback_narrative(python_result, skill_analysis)
        assert result["strengths"]
        assert any("python" in s.lower() or "fastapi" in s.lower() for s in result["strengths"])

    def test_weaknesses_include_missing_skills(self):
        python_result = {"fit_score": 40, "score_breakdown": {}, "_required_years": 5}
        skill_analysis = {"matched_skills": [], "missing_skills": ["kubernetes", "terraform"], "required_count": 2}
        result = _build_fallback_narrative(python_result, skill_analysis)
        assert result["weaknesses"]
        assert any("kubernetes" in w.lower() or "terraform" in w.lower() for w in result["weaknesses"])

    def test_interview_questions_generated(self):
        python_result = {"fit_score": 60, "score_breakdown": {}, "_required_years": 3}
        skill_analysis = {"matched_skills": ["python"], "missing_skills": ["java", "spring"], "required_count": 3}
        result = _build_fallback_narrative(python_result, skill_analysis)
        assert len(result["interview_questions"]["technical_questions"]) >= 1
        assert len(result["interview_questions"]["behavioral_questions"]) >= 1
        assert len(result["interview_questions"]["culture_fit_questions"]) >= 1

    def test_rationale_mentions_score(self):
        python_result = {"fit_score": 72, "score_breakdown": {}, "_required_years": 5}
        skill_analysis = {"matched_skills": ["python"], "missing_skills": [], "required_count": 1}
        result = _build_fallback_narrative(python_result, skill_analysis)
        assert "72" in result["recommendation_rationale"]

    def test_fallback_has_ai_enhanced_false(self):
        """Fallback narrative should have ai_enhanced=False to distinguish from LLM."""
        python_result = {"fit_score": 65, "score_breakdown": {}, "_required_years": 5}
        skill_analysis = {"matched_skills": ["python"], "missing_skills": [], "required_count": 1}
        result = _build_fallback_narrative(python_result, skill_analysis)
        assert result.get("ai_enhanced") is False


class TestMergeLlmIntoResult:
    """Tests for _merge_llm_into_result function."""

    def test_merge_includes_ai_enhanced_from_llm_result(self):
        """Merged result should include ai_enhanced field from LLM result."""
        python_result = {"fit_score": 75, "score_breakdown": {}, "skill_analysis": {}}
        llm_result = {
            "ai_enhanced": True,
            "fit_summary": "Great candidate",
            "strengths": ["Strong skills"],
            "concerns": [],
            "weaknesses": [],
        }
        merged = _merge_llm_into_result(python_result, llm_result)
        assert merged.get("ai_enhanced") is True

    def test_merge_includes_ai_enhanced_false_for_fallback(self):
        """Merged result should include ai_enhanced=False for fallback."""
        python_result = {"fit_score": 75, "score_breakdown": {}, "skill_analysis": {}}
        fallback_result = {
            "ai_enhanced": False,
            "fit_summary": "Fallback summary",
            "strengths": ["Some strengths"],
            "concerns": ["Some concerns"],
            "weaknesses": ["Some concerns"],
        }
        merged = _merge_llm_into_result(python_result, fallback_result)
        assert merged.get("ai_enhanced") is False



# ═══════════════════════════════════════════════════════════════════════════════
# Normalization helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestNormalizeSkill:

    def test_lowercase(self):
        assert _normalize_skill("Python") == "python"

    def test_dot_replaced(self):
        assert _normalize_skill("Node.js") == "node js"

    def test_dash_replaced(self):
        assert _normalize_skill("ci-cd") == "ci cd"

    def test_csharp_preserved(self):
        assert _normalize_skill("C#") == "c#"

    def test_cpp_preserved(self):
        assert _normalize_skill("C++") == "c++"

    def test_multiple_spaces_collapsed(self):
        # _normalize_skill strips surrounding whitespace and collapses internal
        # runs of spaces to a single space
        assert _normalize_skill("  react   native  ") == "react native"


class TestExpandSkill:

    def test_js_expands_to_javascript(self):
        expanded = _expand_skill("javascript")
        assert "js" in expanded

    def test_postgres_in_postgresql_aliases(self):
        expanded = _expand_skill("postgresql")
        assert "postgres" in expanded

    def test_no_duplicates(self):
        expanded = _expand_skill("python")
        assert len(expanded) == len(set(expanded))


# ═══════════════════════════════════════════════════════════════════════════════
# Component 8: explain_with_llm (mocked)
# ═══════════════════════════════════════════════════════════════════════════════

class TestExplainWithLlm:

    @pytest.mark.asyncio
    async def test_llm_result_parsed(self):
        from app.backend.services.hybrid_pipeline import explain_with_llm

        mock_response_json = json.dumps({
            "strengths": ["Strong Python skills", "Good architecture background"],
            "weaknesses": ["Limited Kubernetes experience"],
            "recommendation_rationale": "Good fit for the role.",
            "explainability": {
                "skill_rationale": "Matches core skills.",
                "experience_rationale": "7 years is above the required 5.",
                "overall_rationale": "Solid candidate.",
            },
            "interview_questions": {
                "technical_questions":   ["Describe your Python async experience."],
                "behavioral_questions":  ["Tell me about a project you led."],
                "culture_fit_questions": ["What motivates you?"],
            },
        })

        mock_llm_response = MagicMock()
        mock_llm_response.content = mock_response_json

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)

        with patch("app.backend.services.hybrid_pipeline._get_llm", return_value=mock_llm):
            context = {
                "jd_analysis": {"role_title": "Python Engineer", "domain": "backend",
                                  "seniority": "senior"},
                "candidate_profile": {"name": "Jane Doe", "total_effective_years": 7,
                                       "current_role": "Engineer", "current_company": "Tech",
                                       "career_summary": "Engineer at Tech — 7y"},
                "skill_analysis": {"matched_skills": ["python"], "missing_skills": ["kubernetes"]},
                "scores": {"skill_score": 80, "exp_score": 85, "edu_score": 70,
                           "timeline_score": 85, "fit_score": 79, "final_recommendation": "Shortlist"},
            }
            result = await explain_with_llm(context)

        assert "strengths" in result
        assert len(result["strengths"]) == 2
        assert "weaknesses" in result
        assert "interview_questions" in result
        assert len(result["interview_questions"]["technical_questions"]) == 1

    @pytest.mark.asyncio
    async def test_llm_unavailable_raises(self):
        from app.backend.services.hybrid_pipeline import explain_with_llm

        with patch("app.backend.services.hybrid_pipeline._get_llm", return_value=None):
            with pytest.raises(RuntimeError, match="LLM not available"):
                await explain_with_llm({})


import json


# ═══════════════════════════════════════════════════════════════════════════════
# End-to-end: run_hybrid_pipeline (mocked LLM)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunHybridPipeline:

    def _parsed_data(self):
        return {
            "raw_text": (
                "John Doe | john@example.com | +1-555-0100\n"
                "Senior Python Developer with 7 years experience.\n"
                "Skills: Python, FastAPI, PostgreSQL, Docker, Kubernetes\n"
                "Education: BSc Computer Science, MIT, 2014\n"
                "Experience:\n"
                "  Senior Engineer, TechCorp, Jan 2019 – Present\n"
                "  Software Developer, StartupInc, Jun 2016 – Dec 2018\n"
            ),
            "work_experience": [
                {"title": "Senior Engineer", "company": "TechCorp",
                 "start_date": "Jan 2019", "end_date": "present"},
                {"title": "Software Developer", "company": "StartupInc",
                 "start_date": "Jun 2016", "end_date": "Dec 2018"},
            ],
            "skills": ["python", "fastapi", "postgresql", "docker", "kubernetes"],
            "education": [{"degree": "BSc Computer Science", "field": "computer science",
                           "university": "MIT", "year": "2014"}],
            "contact_info": {"name": "John Doe", "email": "john@example.com"},
        }

    def _gap_analysis(self):
        return {
            "employment_timeline": [],
            "employment_gaps": [],
            "overlapping_jobs": [],
            "short_stints": [],
            "total_years": 7.0,
        }

    def _jd_text(self):
        return (
            "Senior Python Backend Engineer\n"
            "We are looking for a Senior Python Engineer with 5+ years experience.\n"
            "Required: Python, FastAPI, PostgreSQL, Docker, Kubernetes, REST API.\n"
            "Nice to have: Redis, Elasticsearch, Terraform.\n"
            "You will design and build scalable microservices and mentor junior engineers.\n"
            "Responsibilities include system design, code reviews, and technical leadership.\n"
            "Strong understanding of distributed systems and high availability is required.\n"
        )

    @pytest.mark.asyncio
    async def test_full_pipeline_returns_fit_score(self):
        mock_llm_json = json.dumps({
            "strengths": ["Strong Python"],
            "weaknesses": ["Limited Redis"],
            "recommendation_rationale": "Good match.",
            "explainability": {"skill_rationale": "", "experience_rationale": "", "overall_rationale": ""},
            "interview_questions": {
                "technical_questions": ["Question 1"],
                "behavioral_questions": ["Behavioral 1"],
                "culture_fit_questions": ["Culture 1"],
            },
        })
        mock_resp = MagicMock()
        mock_resp.content = mock_llm_json

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_resp)

        with patch("app.backend.services.hybrid_pipeline._get_llm", return_value=mock_llm):
            result = await run_hybrid_pipeline(
                resume_text=self._parsed_data()["raw_text"],
                job_description=self._jd_text(),
                parsed_data=self._parsed_data(),
                gap_analysis=self._gap_analysis(),
            )

        assert isinstance(result["fit_score"], int)
        assert 0 <= result["fit_score"] <= 100
        assert result["final_recommendation"] in ("Shortlist", "Consider", "Reject")
        assert isinstance(result["matched_skills"], list)
        assert isinstance(result["missing_skills"], list)
        assert result["analysis_quality"] in ("high", "medium", "low")
        assert result["interview_questions"] is not None

    @pytest.mark.asyncio
    async def test_pipeline_fallback_on_llm_timeout(self):
        """Pipeline must return a valid result even when LLM times out."""
        async def _slow_explain(*_args, **_kwargs):
            await asyncio.sleep(100)

        with patch("app.backend.services.hybrid_pipeline.explain_with_llm",
                   side_effect=asyncio.TimeoutError()):
            result = await run_hybrid_pipeline(
                resume_text=self._parsed_data()["raw_text"],
                job_description=self._jd_text(),
                parsed_data=self._parsed_data(),
                gap_analysis=self._gap_analysis(),
            )

        # Must always return scores — never raise
        assert isinstance(result["fit_score"], int)
        assert result["narrative_pending"] is True
        assert result["final_recommendation"] in ("Shortlist", "Consider", "Reject")

    @pytest.mark.asyncio
    async def test_precomputed_jd_analysis_skips_parse(self):
        """If jd_analysis is pre-provided, parse_jd_rules should not be called."""
        mock_resp = MagicMock()
        mock_resp.content = json.dumps({
            "strengths": [], "weaknesses": [], "recommendation_rationale": "",
            "explainability": {"skill_rationale": "", "experience_rationale": "", "overall_rationale": ""},
            "interview_questions": {"technical_questions": [], "behavioral_questions": [], "culture_fit_questions": []},
        })
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_resp)

        prebuilt_jd = {
            "role_title": "Pre-built", "domain": "backend", "seniority": "senior",
            "required_skills": ["python"], "required_years": 5,
            "nice_to_have_skills": [], "key_responsibilities": [],
        }

        with patch("app.backend.services.hybrid_pipeline._get_llm", return_value=mock_llm):
            with patch("app.backend.services.hybrid_pipeline.parse_jd_rules") as mock_parse:
                result = await run_hybrid_pipeline(
                    resume_text="python developer 5 years experience",
                    job_description="this text should not be parsed",
                    parsed_data=self._parsed_data(),
                    gap_analysis=self._gap_analysis(),
                    jd_analysis=prebuilt_jd,
                )
                mock_parse.assert_not_called()

        assert result["job_role"] == "Pre-built"
