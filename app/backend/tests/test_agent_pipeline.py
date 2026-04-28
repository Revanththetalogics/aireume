"""
Tests for app/backend/services/agent_pipeline.py

Strategy:
  - Unit tests for pure helper functions (_parse_json, _normalize_weights, etc.)
  - Node tests: each async agent node is called with a fixed PipelineState;
    ChatOllama.ainvoke is mocked — no real Ollama needed.
  - Fallback tests: verify that each node returns typed-null fallback when
    Ollama raises an exception (no crash, just graceful degradation).
  - Integration: run_agent_pipeline end-to-end with all nodes mocked.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.backend.services.agent_pipeline import (
    _parse_json,
    _normalize_weights,
    _compute_fallback_scores,
    build_initial_state,
    assemble_result,
    run_agent_pipeline,
    jd_parser_node,
    resume_analyser_node,
    scorer_node,
    pipeline,
    DEFAULT_WEIGHTS,
    STREAMABLE_NODES,
)


# ─── Sample fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def base_state():
    return {
        "raw_jd_text":           "Senior Python Engineer with FastAPI and PostgreSQL",
        "raw_resume_text":       "Jane Doe. Python 7y. FastAPI. PostgreSQL. AWS.",
        "employment_timeline":   [],
        "scoring_weights":       DEFAULT_WEIGHTS,
        "jd_analysis":           {},
        "candidate_profile":     {},
        "skill_analysis":        {},
        "edu_timeline_analysis": {},
        "final_scores":          {},
        "interview_questions":   {},
        "errors":                [],
    }


@pytest.fixture
def state_with_jd(base_state):
    """State after jd_parser has run (Step 1)."""
    return {
        **base_state,
        "jd_analysis": {
            "role_title": "Senior Python Engineer",
            "domain": "backend",
            "seniority": "senior",
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "required_years": 5,
            "nice_to_have_skills": ["AWS"],
            "key_responsibilities": ["Build APIs", "Optimize DB"],
        },
    }


@pytest.fixture
def state_with_analysis(state_with_jd):
    """State after resume_analyser has run (Step 2)."""
    return {
        **state_with_jd,
        "candidate_profile": {
            "name": "Jane Doe",
            "skills_identified": ["Python", "FastAPI", "PostgreSQL", "AWS"],
            "education": {
                "degree": "Bachelor of Science",
                "field": "Computer Science",
                "institution": "MIT",
                "gpa_or_distinction": "3.8",
            },
            "career_summary": "Experienced backend engineer.",
            "total_effective_years": 7.0,
            "current_role": "Senior Engineer",
            "current_company": "TechCorp",
        },
        "skill_analysis": {
            "matched_skills":    ["Python", "FastAPI", "PostgreSQL"],
            "missing_skills":    [],
            "adjacent_skills":   ["AWS"],
            "skill_score":       95,
            "domain_fit_score":  90,
            "architecture_score": 80,
            "domain_fit_comment":  "Strong backend alignment.",
            "architecture_comment": "Microservices experience evident.",
        },
        "edu_timeline_analysis": {
            "education_score":    85,
            "education_analysis": "Relevant CS degree from a top institution.",
            "field_alignment":    "aligned",
            "timeline_score":     88,
            "timeline_analysis":  "Stable career progression.",
            "gap_interpretation": "No significant gaps.",
        },
    }


def _make_llm_mock(response_dict: dict) -> AsyncMock:
    """Helper: return an AsyncMock ChatOllama whose ainvoke returns a JSON string."""
    llm = AsyncMock()
    msg = MagicMock()
    msg.content = json.dumps(response_dict)
    llm.ainvoke.return_value = msg
    return llm


# ─── Helper function unit tests ───────────────────────────────────────────────

class TestParseJson:
    def test_valid_json(self):
        result = _parse_json('{"key": "value"}', {})
        assert result == {"key": "value"}

    def test_fallback_on_invalid(self):
        result = _parse_json("not json at all", {"default": True})
        assert result == {"default": True}

    def test_extracts_json_from_markdown_code_block(self):
        raw = 'Sure, here is the result:\n```\n{"score": 80}\n```'
        result = _parse_json(raw, {})
        assert result.get("score") == 80

    def test_fallback_on_none(self):
        result = _parse_json(None, {"fallback": 1})
        assert result == {"fallback": 1}


class TestNormalizeWeights:
    def test_already_sums_to_one(self):
        w = {"skills": 0.5, "experience": 0.5}
        normalized = _normalize_weights(w)
        total = sum(normalized.values())
        assert abs(total - 1.0) < 0.01

    def test_missing_keys_filled_from_defaults(self):
        w = {"skills": 1.0}
        normalized = _normalize_weights(w)
        for key in DEFAULT_WEIGHTS:
            assert key in normalized

    def test_proportions_preserved(self):
        w = {"skills": 2.0, "experience": 2.0,
             "architecture": 0.0, "education": 0.0,
             "timeline": 0.0, "domain": 0.0, "risk": 0.0}
        normalized = _normalize_weights(w)
        assert normalized["skills"] == pytest.approx(normalized["experience"], abs=0.01)


class TestComputeFallbackScores:
    def test_returns_all_required_keys(self):
        sa  = {"skill_score": 70, "domain_fit_score": 60, "architecture_score": 55}
        eta = {"education_score": 80, "timeline_score": 75}
        cp  = {"total_effective_years": 5.0}
        jd  = {"required_years": 4}
        result = _compute_fallback_scores(sa, eta, cp, jd, DEFAULT_WEIGHTS)
        for key in ("fit_score", "score_breakdown", "risk_signals", "strengths",
                    "weaknesses", "explainability", "final_recommendation", "risk_level"):
            assert key in result

    def test_fit_score_clamped_0_to_100(self):
        sa  = {"skill_score": 200, "domain_fit_score": 200, "architecture_score": 200}
        eta = {"education_score": 200, "timeline_score": 200}
        cp  = {"total_effective_years": 50.0}
        jd  = {"required_years": 1}
        result = _compute_fallback_scores(sa, eta, cp, jd, DEFAULT_WEIGHTS)
        assert 0 <= result["fit_score"] <= 100

    def test_shortlist_recommendation_at_high_score(self):
        sa  = {"skill_score": 100, "domain_fit_score": 100, "architecture_score": 100}
        eta = {"education_score": 100, "timeline_score": 100}
        cp  = {"total_effective_years": 10.0}
        jd  = {"required_years": 5}
        result = _compute_fallback_scores(sa, eta, cp, jd, DEFAULT_WEIGHTS)
        assert result["final_recommendation"] == "Shortlist"

    def test_reject_recommendation_at_zero_scores(self):
        sa  = {"skill_score": 0, "domain_fit_score": 0, "architecture_score": 0}
        eta = {"education_score": 0, "timeline_score": 0}
        cp  = {"total_effective_years": 0.0}
        jd  = {"required_years": 10}
        result = _compute_fallback_scores(sa, eta, cp, jd, DEFAULT_WEIGHTS)
        assert result["final_recommendation"] == "Reject"


class TestBuildInitialState:
    def test_required_keys_present(self):
        state = build_initial_state("resume", "jd", {}, None)
        for key in ("raw_jd_text", "raw_resume_text", "employment_timeline",
                    "scoring_weights", "jd_analysis", "candidate_profile",
                    "skill_analysis", "edu_timeline_analysis", "final_scores",
                    "interview_questions", "errors"):
            assert key in state

    def test_defaults_to_default_weights(self):
        state = build_initial_state("r", "jd", {}, None)
        assert state["scoring_weights"] == DEFAULT_WEIGHTS

    def test_custom_weights_passed_through(self):
        w = {"skills": 1.0}
        state = build_initial_state("r", "jd", {}, w)
        assert state["scoring_weights"] == w

    def test_employment_timeline_from_gap_analysis(self):
        gap = {"employment_timeline": [{"role": "Dev", "company": "A"}]}
        state = build_initial_state("r", "jd", gap, None)
        assert len(state["employment_timeline"]) == 1


class TestAssembleResult:
    def test_backward_compat_fields_present(self, state_with_analysis):
        """All fields that the existing frontend expects must be present."""
        state_with_analysis["final_scores"] = {
            "fit_score": 82,
            "risk_level": "Low",
            "risk_signals": [],
            "strengths": ["Strong Python"],
            "weaknesses": [],
            "score_breakdown": {"skill_match": 95, "experience_match": 88},
            "final_recommendation": "Shortlist",
            "recommendation_rationale": "Score 82/100 — Shortlist.",
            "explainability": {"overall_rationale": "Strong backend match."},
        }
        state_with_analysis["interview_questions"] = {
            "technical_questions": ["Q1"],
            "behavioral_questions": ["Q2"],
            "culture_fit_questions": ["Q3"],
        }
        parsed_data = {
            "raw_text": "...", "work_experience": [], "contact_info": {"name": "Jane"}
        }
        gap_analysis = {"employment_gaps": [], "employment_timeline": []}

        result = assemble_result(state_with_analysis, parsed_data, gap_analysis)

        for key in ("fit_score", "strengths", "weaknesses", "employment_gaps",
                    "education_analysis", "risk_signals", "final_recommendation",
                    "score_breakdown", "matched_skills", "missing_skills",
                    "risk_level", "interview_questions", "work_experience"):
            assert key in result, f"Missing key: {key}"

    def test_new_fields_present(self, state_with_analysis):
        state_with_analysis["final_scores"] = {
            "fit_score": 75, "risk_level": "Medium", "risk_signals": [],
            "strengths": [], "weaknesses": [], "score_breakdown": {},
            "final_recommendation": "Consider", "explainability": {},
        }
        result = assemble_result(state_with_analysis, {}, {})
        for key in ("jd_analysis", "candidate_profile", "skill_analysis",
                    "edu_timeline_analysis", "explainability", "adjacent_skills",
                    "pipeline_errors"):
            assert key in result

    def test_score_breakdown_stability_backward_compat(self, state_with_analysis):
        """score_breakdown.stability must be present for the existing ScoreBar."""
        state_with_analysis["final_scores"] = {
            "fit_score": 70, "risk_level": "Medium", "risk_signals": [],
            "strengths": [], "weaknesses": [], "final_recommendation": "Consider",
            "score_breakdown": {"timeline": 75},
            "explainability": {},
        }
        result = assemble_result(state_with_analysis, {}, {})
        assert "stability" in result["score_breakdown"]

    def test_job_role_populated_from_jd_analysis(self, state_with_analysis):
        """assemble_result must expose job_role for backward compat with ReportPage."""
        state_with_analysis["final_scores"] = {
            "fit_score": 80, "risk_level": "Low", "risk_signals": [],
            "strengths": [], "weaknesses": [], "final_recommendation": "Shortlist",
            "score_breakdown": {}, "explainability": {},
        }
        result = assemble_result(state_with_analysis, {}, {})
        assert result.get("job_role") == "Senior Python Engineer"

    def test_job_role_empty_string_when_no_jd(self):
        """When jd_analysis is empty, job_role should default to empty string."""
        state = {
            "raw_jd_text": "", "raw_resume_text": "",
            "employment_timeline": [], "scoring_weights": DEFAULT_WEIGHTS,
            "jd_analysis": {}, "candidate_profile": {},
            "skill_analysis": {}, "edu_timeline_analysis": {},
            "final_scores": {
                "fit_score": 50, "risk_level": "Medium", "risk_signals": [],
                "strengths": [], "weaknesses": [], "final_recommendation": "Consider",
                "score_breakdown": {}, "explainability": {},
            },
            "interview_questions": {}, "errors": [],
        }
        result = assemble_result(state, {}, {})
        assert result.get("job_role") == ""


# ─── Pipeline node tests ──────────────────────────────────────────────────────

class TestJdParserNode:
    @pytest.fixture(autouse=True)
    def clear_jd_cache(self):
        """Reset the module-level JD cache before every test so cache hits don't mask fallbacks."""
        import app.backend.services.agent_pipeline as _ap
        _ap._jd_cache.clear()
        yield
        _ap._jd_cache.clear()

    @pytest.mark.asyncio
    async def test_returns_jd_analysis_on_success(self, base_state):
        jd_output = {
            "role_title": "Senior Python Engineer", "domain": "backend",
            "seniority": "senior", "required_skills": ["Python", "FastAPI"],
            "required_years": 5, "nice_to_have_skills": [], "key_responsibilities": [],
        }
        with patch("app.backend.services.agent_pipeline.get_fast_llm",
                   return_value=_make_llm_mock(jd_output)):
            result = await jd_parser_node(base_state)

        assert "jd_analysis" in result
        assert result["jd_analysis"]["role_title"] == "Senior Python Engineer"
        assert "errors" not in result or result.get("errors") == []

    @pytest.mark.asyncio
    async def test_fallback_on_llm_exception(self, base_state):
        llm = AsyncMock()
        llm.ainvoke.side_effect = Exception("Ollama timeout")
        with patch("app.backend.services.agent_pipeline.get_fast_llm", return_value=llm):
            result = await jd_parser_node(base_state)

        assert "jd_analysis" in result
        assert result["jd_analysis"]["domain"] == "other"
        assert "errors" in result
        assert "jd_parser" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_caches_result_on_second_call(self, base_state):
        """Second call with same JD text must be served from cache (LLM not called)."""
        jd_output = {
            "role_title": "Cached Role", "domain": "backend", "seniority": "mid",
            "required_skills": [], "required_years": 0,
            "nice_to_have_skills": [], "key_responsibilities": [],
        }
        llm = _make_llm_mock(jd_output)
        with patch("app.backend.services.agent_pipeline.get_fast_llm", return_value=llm):
            await jd_parser_node(base_state)
            await jd_parser_node(base_state)

        assert llm.ainvoke.call_count == 1


class TestResumeAnalyserNode:
    """Tests for the combined resume parsing + skill matching + education/timeline node."""

    @pytest.mark.asyncio
    async def test_returns_all_three_state_keys(self, state_with_jd):
        combined_output = {
            "name": "Jane Doe", "skills_identified": ["Python", "FastAPI"],
            "education": {"degree": "BSc", "field": "CS", "institution": "MIT",
                          "gpa_or_distinction": None},
            "career_summary": "Backend engineer.", "total_effective_years": 7.0,
            "current_role": "Senior Engineer", "current_company": "TechCorp",
            "matched_skills": ["Python", "FastAPI"],
            "missing_skills": ["PostgreSQL"],
            "adjacent_skills": ["AWS"],
            "skill_score": 80, "domain_fit_score": 85, "architecture_score": 70,
            "domain_fit_comment": "Strong backend.", "architecture_comment": "Some arch.",
            "education_score": 85, "education_analysis": "Relevant CS degree.",
            "field_alignment": "aligned", "timeline_score": 88,
            "timeline_analysis": "Stable career.", "gap_interpretation": "No gaps.",
        }
        with patch("app.backend.services.agent_pipeline.get_fast_llm",
                   return_value=_make_llm_mock(combined_output)):
            result = await resume_analyser_node(state_with_jd)

        assert "candidate_profile" in result
        assert "skill_analysis" in result
        assert "edu_timeline_analysis" in result
        assert result["candidate_profile"]["name"] == "Jane Doe"
        assert result["skill_analysis"]["skill_score"] == 80
        assert result["edu_timeline_analysis"]["field_alignment"] == "aligned"

    @pytest.mark.asyncio
    async def test_candidate_profile_fields_correct(self, state_with_jd):
        combined_output = {
            "name": "Alice Smith", "skills_identified": ["Django", "Python"],
            "total_effective_years": 4.0, "current_role": "Dev",
            "current_company": "Co", "career_summary": "Summary.",
            "education": {"degree": "MSc", "field": "SE", "institution": "UCL",
                          "gpa_or_distinction": None},
            "matched_skills": ["Python"], "missing_skills": ["FastAPI", "PostgreSQL"],
            "adjacent_skills": [], "skill_score": 40,
            "domain_fit_score": 60, "architecture_score": 50,
            "domain_fit_comment": "", "architecture_comment": "",
            "education_score": 80, "education_analysis": "Masters in SE.",
            "field_alignment": "partially_aligned", "timeline_score": 70,
            "timeline_analysis": "2 short stints.", "gap_interpretation": "1 gap.",
        }
        with patch("app.backend.services.agent_pipeline.get_fast_llm",
                   return_value=_make_llm_mock(combined_output)):
            result = await resume_analyser_node(state_with_jd)

        cp = result["candidate_profile"]
        assert cp["name"] == "Alice Smith"
        assert cp["total_effective_years"] == 4.0
        assert "Django" in cp["skills_identified"]

    @pytest.mark.asyncio
    async def test_fallback_on_llm_exception(self, state_with_jd):
        llm = AsyncMock()
        llm.ainvoke.side_effect = RuntimeError("Connection refused")
        with patch("app.backend.services.agent_pipeline.get_fast_llm", return_value=llm):
            result = await resume_analyser_node(state_with_jd)

        assert result["candidate_profile"]["name"] is None
        assert result["skill_analysis"]["skill_score"] == 0
        assert result["edu_timeline_analysis"]["education_score"] == 60  # fallback default
        assert "resume_analyser" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_missing_skills_default_to_required(self, state_with_jd):
        """When skill_score/missing_skills are absent from LLM output, missing_skills
        should fall back to the JD's required_skills."""
        partial_output = {
            "name": "Bob", "skills_identified": [],
            "total_effective_years": 2.0,
        }
        with patch("app.backend.services.agent_pipeline.get_fast_llm",
                   return_value=_make_llm_mock(partial_output)):
            result = await resume_analyser_node(state_with_jd)

        sa = result["skill_analysis"]
        # required_skills from state_with_jd fixture = ["Python", "FastAPI", "PostgreSQL"]
        assert set(sa["missing_skills"]).issubset(
            {"Python", "FastAPI", "PostgreSQL"} | set(sa["missing_skills"])
        )


class TestScorerNode:
    """Tests for the combined scorer + interview questions node."""

    @pytest.mark.asyncio
    async def test_returns_final_scores_and_interview_questions(self, state_with_analysis):
        scorer_output = {
            "experience_score": 88,
            "risk_penalty": 0,
            "score_breakdown": {
                "skill_match": 95, "experience_match": 88, "architecture": 80,
                "education": 85, "timeline": 88, "domain_fit": 90, "risk_penalty": 0,
            },
            "fit_score": 88,
            "risk_level": "Low",
            "risk_signals": [],
            "strengths": ["Deep Python expertise"],
            "weaknesses": [],
            "explainability": {
                "skill_rationale": "All required skills present.",
                "overall_rationale": "Strong all-round match.",
            },
            "final_recommendation": "Shortlist",
            "recommendation_rationale": "Score 88/100.",
            "interview_questions": {
                "technical_questions": ["Explain async Python."],
                "behavioral_questions": ["Tell me about a hard deadline."],
                "culture_fit_questions": ["What motivates you?"],
            },
        }
        with patch("app.backend.services.agent_pipeline.get_reasoning_llm",
                   return_value=_make_llm_mock(scorer_output)):
            result = await scorer_node(state_with_analysis)

        assert "final_scores" in result
        assert "interview_questions" in result
        assert result["final_scores"]["final_recommendation"] == "Shortlist"
        assert result["final_scores"]["fit_score"] == 88
        iq = result["interview_questions"]
        assert len(iq["technical_questions"]) >= 1
        assert len(iq["behavioral_questions"]) >= 1

    @pytest.mark.asyncio
    async def test_fit_score_clamped(self, state_with_analysis):
        scorer_output = {
            "fit_score": 150, "final_recommendation": "Shortlist",
            "risk_level": "Low", "risk_signals": [],
            "strengths": [], "weaknesses": [],
            "score_breakdown": {}, "explainability": {},
            "interview_questions": {"technical_questions": [], "behavioral_questions": [], "culture_fit_questions": []},
        }
        with patch("app.backend.services.agent_pipeline.get_reasoning_llm",
                   return_value=_make_llm_mock(scorer_output)):
            result = await scorer_node(state_with_analysis)

        assert result["final_scores"]["fit_score"] <= 100

    @pytest.mark.asyncio
    async def test_invalid_recommendation_corrected(self, state_with_analysis):
        scorer_output = {
            "fit_score": 80, "final_recommendation": "UNKNOWN_VALUE",
            "risk_level": "Low", "risk_signals": [],
            "strengths": [], "weaknesses": [],
            "score_breakdown": {}, "explainability": {},
            "interview_questions": {"technical_questions": [], "behavioral_questions": [], "culture_fit_questions": []},
        }
        with patch("app.backend.services.agent_pipeline.get_reasoning_llm",
                   return_value=_make_llm_mock(scorer_output)):
            result = await scorer_node(state_with_analysis)

        assert result["final_scores"]["final_recommendation"] in ("Shortlist", "Consider", "Reject")

    @pytest.mark.asyncio
    async def test_score_breakdown_overridden_with_agent_scores(self, state_with_analysis):
        """score_breakdown.skill_match must come from skill_analysis.skill_score, not LLM."""
        scorer_output = {
            "fit_score": 75, "final_recommendation": "Consider",
            "risk_level": "Medium", "risk_signals": [],
            "strengths": [], "weaknesses": [],
            "score_breakdown": {"skill_match": 0},  # LLM returned 0 (template literal)
            "explainability": {},
            "interview_questions": {"technical_questions": [], "behavioral_questions": [], "culture_fit_questions": []},
        }
        with patch("app.backend.services.agent_pipeline.get_reasoning_llm",
                   return_value=_make_llm_mock(scorer_output)):
            result = await scorer_node(state_with_analysis)

        # state_with_analysis has skill_score=95 — override must apply
        assert result["final_scores"]["score_breakdown"]["skill_match"] == 95

    @pytest.mark.asyncio
    async def test_fallback_on_llm_exception(self, state_with_analysis):
        llm = AsyncMock()
        llm.ainvoke.side_effect = Exception("model not found")
        with patch("app.backend.services.agent_pipeline.get_reasoning_llm", return_value=llm):
            result = await scorer_node(state_with_analysis)

        assert "final_scores" in result
        assert "interview_questions" in result
        fs = result["final_scores"]
        assert fs["fit_score"] >= 0
        assert fs["final_recommendation"] in ("Shortlist", "Consider", "Reject")
        assert "scorer" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_fallback_interview_questions_non_empty(self, state_with_analysis):
        """Even on failure, interview_questions must contain non-empty question lists."""
        llm = AsyncMock()
        llm.ainvoke.side_effect = Exception("Ollama down")
        with patch("app.backend.services.agent_pipeline.get_reasoning_llm", return_value=llm):
            result = await scorer_node(state_with_analysis)

        iq = result["interview_questions"]
        assert len(iq["behavioral_questions"]) >= 1
        assert len(iq["culture_fit_questions"]) >= 1


# ─── Pipeline compilation ─────────────────────────────────────────────────────

class TestPipelineCompilation:
    def test_pipeline_is_compiled(self):
        """The LangGraph pipeline must compile without errors at module load."""
        assert pipeline is not None

    def test_streamable_nodes_three_sequential(self):
        """3-step sequential pipeline: jd_parser → resume_analyser → scorer."""
        expected = {"jd_parser", "resume_analyser", "scorer"}
        assert STREAMABLE_NODES == expected


# ─── run_agent_pipeline end-to-end ───────────────────────────────────────────

class TestRunAgentPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_with_mocked_nodes(self):
        """
        Run run_agent_pipeline with all 3 LLM calls mocked.
        Verifies the final assembled result has all expected keys.
        """
        import app.backend.services.agent_pipeline as _ap
        _ap._jd_cache.clear()

        jd_out = {
            "role_title": "Backend Engineer", "domain": "backend", "seniority": "mid",
            "required_skills": ["Python", "Django"], "required_years": 3,
            "nice_to_have_skills": [], "key_responsibilities": ["Build APIs"],
        }
        # Combined resume analyser output (all fields in one dict)
        analyser_out = {
            "name": "Alice", "skills_identified": ["Python", "Django", "React"],
            "education": {"degree": "BSc", "field": "CS", "institution": "UCL",
                          "gpa_or_distinction": None},
            "career_summary": "Mid-level backend dev.",
            "total_effective_years": 4.0,
            "current_role": "Developer", "current_company": "Agency",
            "matched_skills": ["Python", "Django"], "missing_skills": [],
            "adjacent_skills": ["React"], "skill_score": 90,
            "domain_fit_score": 85, "architecture_score": 70,
            "domain_fit_comment": "Good match.", "architecture_comment": "Some patterns.",
            "education_score": 80, "education_analysis": "Relevant CS degree.",
            "field_alignment": "aligned", "timeline_score": 85,
            "timeline_analysis": "Steady progression.", "gap_interpretation": "No gaps.",
        }
        # Combined scorer output (scores + interview questions in one dict)
        scorer_out = {
            "experience_score": 82, "risk_penalty": 0,
            "score_breakdown": {
                "skill_match": 90, "experience_match": 82, "architecture": 70,
                "education": 80, "timeline": 85, "domain_fit": 85, "risk_penalty": 0,
            },
            "fit_score": 79, "risk_level": "Low", "risk_signals": [],
            "strengths": ["Strong Python"], "weaknesses": ["Limited architecture evidence"],
            "explainability": {"overall_rationale": "Good backend match."},
            "final_recommendation": "Shortlist",
            "recommendation_rationale": "Score 79/100.",
            "interview_questions": {
                "technical_questions": ["Describe Django ORM."],
                "behavioral_questions": ["Tell me about a difficult bug."],
                "culture_fit_questions": ["How do you learn new things?"],
            },
        }

        fast_call = 0

        async def fast_side_effect(prompt):
            nonlocal fast_call
            msg = MagicMock()
            # Call 0 = jd_parser, Call 1 = resume_analyser
            msg.content = json.dumps(jd_out if fast_call == 0 else analyser_out)
            fast_call += 1
            return msg

        async def reasoning_side_effect(prompt):
            msg = MagicMock()
            msg.content = json.dumps(scorer_out)
            return msg

        fast_llm = AsyncMock()
        reasoning = AsyncMock()
        fast_llm.ainvoke.side_effect   = fast_side_effect
        reasoning.ainvoke.side_effect  = reasoning_side_effect

        with patch("app.backend.services.agent_pipeline.get_fast_llm",
                   return_value=fast_llm), \
             patch("app.backend.services.agent_pipeline.get_reasoning_llm",
                   return_value=reasoning):
            result = await run_agent_pipeline(
                resume_text="Alice resume...",
                job_description="Backend engineer needed",
                parsed_data={"raw_text": "Alice", "work_experience": [],
                             "contact_info": {"name": "Alice"}},
                gap_analysis={"employment_timeline": [], "employment_gaps": [],
                              "overlapping_jobs": [], "short_stints": [], "total_years": 4.0},
            )

        for key in ("fit_score", "strengths", "weaknesses", "employment_gaps",
                    "education_analysis", "risk_signals", "final_recommendation",
                    "score_breakdown", "matched_skills", "missing_skills",
                    "risk_level", "interview_questions"):
            assert key in result, f"Missing key: {key}"

        for key in ("jd_analysis", "candidate_profile", "skill_analysis",
                    "edu_timeline_analysis", "explainability"):
            assert key in result, f"Missing new key: {key}"

        assert result["fit_score"] >= 0
        assert result["final_recommendation"] in ("Shortlist", "Consider", "Reject")

    @pytest.mark.asyncio
    async def test_pipeline_returns_fallback_when_all_llm_calls_fail(self):
        """If every Ollama call fails, the pipeline must still return a valid result
        (no crash, typed-null defaults, graceful degradation)."""
        import app.backend.services.agent_pipeline as _ap
        _ap._jd_cache.clear()

        llm = AsyncMock()
        llm.ainvoke.side_effect = Exception("Ollama unavailable")

        with patch("app.backend.services.agent_pipeline.get_fast_llm", return_value=llm), \
             patch("app.backend.services.agent_pipeline.get_reasoning_llm", return_value=llm):
            result = await run_agent_pipeline(
                resume_text="Some resume",
                job_description="Some JD",
                parsed_data={"raw_text": "r", "work_experience": [], "contact_info": {}},
                gap_analysis={"employment_timeline": [], "employment_gaps": [],
                              "overlapping_jobs": [], "short_stints": [], "total_years": 0},
            )

        assert "fit_score" in result
        assert "final_recommendation" in result
        assert isinstance(result.get("pipeline_errors"), list)
        assert len(result["pipeline_errors"]) > 0


# ─── Schema-level tests (Pydantic validators + model config) ──────────────────

class TestInterviewQuestionsSchema:
    """Tests for the field_validator that coerces LLM output to List[InterviewQuestion]."""

    def test_plain_string_list_backward_compatible(self):
        """Old string lists are converted to InterviewQuestion objects."""
        from app.backend.models.schemas import InterviewQuestions, InterviewQuestion
        iq = InterviewQuestions(
            technical_questions=["Explain async/await."],
            behavioral_questions=["Tell me about a deadline."],
            culture_fit_questions=["What motivates you?"],
        )
        assert isinstance(iq.technical_questions[0], InterviewQuestion)
        assert iq.technical_questions[0].text == "Explain async/await."

    def test_dict_items_with_text_key_parsed(self):
        """Dict items with 'text' key become structured InterviewQuestions."""
        from app.backend.models.schemas import InterviewQuestions, InterviewQuestion
        iq = InterviewQuestions(
            technical_questions=[{"text": "Explain REST?", "what_to_listen_for": ["async knowledge"]}],
            behavioral_questions=[{"text": "How do you handle pressure?"}],
            culture_fit_questions=[],
        )
        assert isinstance(iq.technical_questions[0], InterviewQuestion)
        assert iq.technical_questions[0].text == "Explain REST?"
        assert iq.technical_questions[0].what_to_listen_for == ["async knowledge"]
        assert isinstance(iq.behavioral_questions[0], InterviewQuestion)

    def test_dict_items_without_text_key_salvaged(self):
        """Dict items without 'text' key are salvaged as string representation."""
        from app.backend.models.schemas import InterviewQuestions, InterviewQuestion
        iq = InterviewQuestions(
            technical_questions=[{"question": "Explain REST?"}],
        )
        assert isinstance(iq.technical_questions[0], InterviewQuestion)
        assert "question" in iq.technical_questions[0].text

    def test_integer_items_coerced_to_questions(self):
        from app.backend.models.schemas import InterviewQuestions, InterviewQuestion
        iq = InterviewQuestions(technical_questions=[1, 2, 3])
        assert all(isinstance(q, InterviewQuestion) for q in iq.technical_questions)
        assert iq.technical_questions[0].text == "1"

    def test_non_list_field_becomes_empty_list(self):
        """If LLM returns a string instead of a list, field should be []."""
        from app.backend.models.schemas import InterviewQuestions
        iq = InterviewQuestions(technical_questions="just a string")  # type: ignore
        assert iq.technical_questions == []

    def test_none_field_becomes_empty_list(self):
        from app.backend.models.schemas import InterviewQuestions
        iq = InterviewQuestions(technical_questions=None)  # type: ignore
        assert iq.technical_questions == []

    def test_empty_lists_valid(self):
        from app.backend.models.schemas import InterviewQuestions
        iq = InterviewQuestions()
        assert iq.technical_questions == []
        assert iq.behavioral_questions == []
        assert iq.culture_fit_questions == []

    def test_structured_format_works(self):
        """New structured InterviewQuestion format works end-to-end."""
        from app.backend.models.schemas import InterviewQuestions, InterviewQuestion, CandidateBriefing
        iq = InterviewQuestions(
            technical_questions=[
                InterviewQuestion(text="Q1", what_to_listen_for=["x"], follow_ups=["y"])
            ],
            candidate_briefing=CandidateBriefing(
                profile_snapshot="Senior dev",
                strengths_to_confirm=["Python"],
            ),
        )
        assert iq.technical_questions[0].what_to_listen_for == ["x"]
        assert iq.candidate_briefing.profile_snapshot == "Senior dev"

    def test_mixed_format_backward_compatible(self):
        """Mixed plain strings and dicts both work."""
        from app.backend.models.schemas import InterviewQuestions, InterviewQuestion
        iq = InterviewQuestions(
            technical_questions=["plain string", {"text": "structured", "what_to_listen_for": ["x"]}]
        )
        assert iq.technical_questions[0].text == "plain string"
        assert iq.technical_questions[1].what_to_listen_for == ["x"]


class TestAnalysisResponseSchema:
    """Tests for AnalysisResponse extra='ignore' config and null fit_score."""

    def test_extra_fields_silently_ignored(self):
        """Extra LLM-produced keys must not raise a ValidationError."""
        from app.backend.models.schemas import AnalysisResponse
        result = AnalysisResponse(
            fit_score=72,
            final_recommendation="Shortlist",
            unexpected_llm_key="some value",      # should be silently dropped
            another_extra_field={"nested": True},  # type: ignore
        )
        assert result.fit_score == 72
        assert not hasattr(result, "unexpected_llm_key")

    def test_null_fit_score_valid(self):
        """fit_score=None must be accepted (represents the Pending / fallback state)."""
        from app.backend.models.schemas import AnalysisResponse
        result = AnalysisResponse(fit_score=None, final_recommendation="Pending")
        assert result.fit_score is None
        assert result.final_recommendation == "Pending"

    def test_pending_recommendation_valid(self):
        from app.backend.models.schemas import AnalysisResponse
        result = AnalysisResponse(final_recommendation="Pending")
        assert result.final_recommendation == "Pending"

    def test_job_role_field_present(self):
        """job_role must be an accepted field in AnalysisResponse."""
        from app.backend.models.schemas import AnalysisResponse
        result = AnalysisResponse(job_role="Senior Python Engineer")
        assert result.job_role == "Senior Python Engineer"

    def test_job_role_defaults_to_none(self):
        from app.backend.models.schemas import AnalysisResponse
        result = AnalysisResponse()
        assert result.job_role is None

    def test_interview_questions_with_dict_items_coerced(self):
        """End-to-end: AnalysisResponse wrapping InterviewQuestions with dict items."""
        from app.backend.models.schemas import AnalysisResponse, InterviewQuestion
        result = AnalysisResponse(
            fit_score=65,
            interview_questions={
                "technical_questions": [{"question": "Explain REST."}],
                "behavioral_questions": ["How do you handle conflict?"],
                "culture_fit_questions": [],
            },
        )
        assert isinstance(result.interview_questions.technical_questions[0], InterviewQuestion)
        assert result.interview_questions.behavioral_questions[0].text == "How do you handle conflict?"
