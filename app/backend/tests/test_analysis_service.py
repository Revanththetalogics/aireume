import pytest
from unittest.mock import AsyncMock, patch
from app.backend.services.analysis_service import AnalysisService, analyze_resume


class TestAnalysisService:
    @pytest.mark.asyncio
    async def test_calculate_skill_match(self):
        service = AnalysisService()
        candidate_skills = ["Python", "JavaScript", "React"]
        job_description = "We need Python and React developers with AWS experience"

        match_percent = service._calculate_skill_match(candidate_skills, job_description)

        assert 0 <= match_percent <= 100
        # Python and React should match
        assert match_percent > 0

    def test_extract_skills_from_jd(self):
        service = AnalysisService()
        jd = "Looking for Python, AWS, Docker, and Kubernetes experts"

        skills = service._extract_skills_from_jd(jd)

        assert "python" in skills
        assert "aws" in skills
        assert "docker" in skills
        assert "kubernetes" in skills

    def test_prepare_risk_signals(self):
        service = AnalysisService()
        gap_analysis = {
            "overlapping_jobs": [
                {"job1": "Job A", "job2": "Job B"}
            ],
            "short_stints": [
                {"company": "StartupX", "duration_months": 3}
            ]
        }

        risks = service._prepare_risk_signals(gap_analysis)

        assert len(risks) == 2
        assert any(r["type"] == "overlapping_employment" for r in risks)
        assert any(r["type"] == "job_hopper" for r in risks)

    @pytest.mark.asyncio
    async def test_analyze_full_flow(self, sample_resume_text, sample_job_description):
        parsed_data = {
            "raw_text": sample_resume_text,
            "skills": ["Python", "JavaScript", "React", "Node.js"],
            "work_experience": [
                {"company": "TechCorp", "title": "Senior Dev", "start_date": "2020-01", "end_date": "present"},
                {"company": "Startup", "title": "Dev", "start_date": "2017-06", "end_date": "2019-12"}
            ],
            "education": [{"degree": "BS", "field": "CS"}]
        }

        gap_analysis = {
            "employment_gaps": [],
            "overlapping_jobs": [],
            "short_stints": [],
            "total_years": 6.5
        }

        mock_llm_response = {
            "fit_score": 85,
            "strengths": ["Strong Python skills", "Leadership experience"],
            "weaknesses": ["Limited cloud experience"],
            "education_analysis": "Relevant degree",
            "risk_signals": [],
            "final_recommendation": "Shortlist"
        }

        with patch('app.backend.services.analysis_service.analyze_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response

            result = await analyze_resume(
                resume_text=sample_resume_text,
                job_description=sample_job_description,
                parsed_data=parsed_data,
                gap_analysis=gap_analysis
            )

            assert "fit_score" in result
            assert "strengths" in result
            assert "weaknesses" in result
            assert "final_recommendation" in result
            assert result["fit_score"] == 85
