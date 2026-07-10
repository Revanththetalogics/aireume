"""Tests for targeted interview kit generation."""

from app.backend.services.interview_kit_generator import (
    generate_targeted_interview_kit,
    refresh_interview_questions_in_analysis,
    count_kit_questions,
)


class TestGenerateTargetedInterviewKit:

    def _kit(self, **kwargs):
        defaults = {
            "profile": {
                "name": "Kalpana P",
                "current_role": "SAP MM Consultant",
                "current_company": "Acme Corp",
                "total_effective_years": 12.7,
                "work_experience": [
                    {"company": "Acme Corp", "title": "SAP MM Consultant", "description": "SAP MM P2P IDOC"},
                ],
            },
            "jd_analysis": {
                "role_title": "SAP MM Consultant",
                "domain": "SAP ERP",
                "required_skills": ["SAP MM", "P2P", "SAP S/4HANA", "IDOC"],
                "key_responsibilities": ["Lead SAP MM implementation and support"],
            },
            "skill_analysis": {
                "matched_required": ["SAP MM", "P2P"],
                "missing_required": ["SAP S/4HANA", "IDOC"],
            },
        }
        defaults.update(kwargs)
        return generate_targeted_interview_kit(**defaults)

    def test_gap_probe_for_missing_skills(self):
        kit = self._kit()
        tech_texts = [q["text"] for q in kit["technical_questions"]]
        assert not any("isn't on your resume" in t for t in tech_texts)
        assert any("IDOC" in t or "S/4HANA" in t for t in tech_texts)
        assert any("role calls for" in t.lower() or "experience with" in t.lower() for t in tech_texts)

    def test_resume_personalization_for_matched_skills(self):
        kit = self._kit()
        tech_texts = " ".join(q["text"] for q in kit["technical_questions"])
        assert "Acme Corp" in tech_texts or "SAP MM" in tech_texts

    def test_no_culture_fit_questions(self):
        kit = self._kit()
        assert kit["culture_fit_questions"] == []

    def test_questions_are_short(self):
        kit = self._kit()
        all_q = (
            kit["technical_questions"]
            + kit["behavioral_questions"]
            + kit["experience_deep_dive_questions"]
        )
        assert 5 <= len(all_q) <= 10
        for q in all_q:
            assert len(q["text"]) <= 160

    def test_no_duplicate_question_stems(self):
        kit = self._kit()
        texts = [
            q["text"].lower()[:60]
            for q in kit["technical_questions"] + kit["experience_deep_dive_questions"]
        ]
        assert len(texts) == len(set(texts))

    def test_experience_anchored_to_work_history(self):
        kit = self._kit()
        exp_texts = [q["text"] for q in kit["experience_deep_dive_questions"]]
        assert any("Acme Corp" in t for t in exp_texts)

    def test_corrupted_profile_fields_are_cleaned(self):
        kit = self._kit(
            profile={
                "name": "Kalpana {",
                "current_role": "Recruiter {",
                "current_company": "ValueLabs {",
                "total_effective_years": 8,
                "work_experience": [{"title": "ValueLabs {", "company": ""}],
            },
            jd_analysis={
                "role_title": "Talent Acquisition",
                "domain": "HR",
                "required_skills": ["Stakeholder Management"],
                "key_responsibilities": [
                    "job description: talent acquisition specialist / lead talent",
                    "Manage stakeholder expectations during offer negotiations",
                ],
            },
            skill_analysis={
                "matched_required": [],
                "missing_required": ["Stakeholder Management", "5-12 years IT recruitment experience"],
            },
        )
        exp_texts = " ".join(q["text"] for q in kit["experience_deep_dive_questions"])
        assert "{" not in exp_texts
        assert "ValueLabs" in exp_texts or "your last role" in exp_texts
        behavioral = " ".join(q["text"] for q in kit["behavioral_questions"])
        assert "job description:" not in behavioral.lower()

    def test_ta_role_filters_irrelevant_gap_probes(self):
        kit = self._kit(
            jd_analysis={
                "role_title": "Talent Acquisition Specialist",
                "domain": "HR",
                "required_skills": ["Talent Acquisition", "Stakeholder Management"],
                "key_responsibilities": ["Manage stakeholder expectations during offer negotiations"],
            },
            skill_analysis={
                "matched_required": ["Talent Acquisition"],
                "missing_required": ["Machine Learning", "Stakeholder Management"],
            },
        )
        tech_texts = " ".join(q["text"] for q in kit["technical_questions"]).lower()
        assert "machine learning" not in tech_texts

    def test_refresh_preserves_ready_llm_kit(self):
        existing_kit = {
            "technical_questions": [{"text": "LLM-crafted question about stakeholder management"}],
            "behavioral_questions": [{"text": "Tell me about a tough hire you closed."}],
            "culture_fit_questions": [],
            "experience_deep_dive_questions": [],
        }
        analysis = {
            "candidate_profile": {"name": "Test", "current_role": "Dev"},
            "jd_analysis": {"required_skills": ["Python"], "role_title": "Backend Dev"},
            "skill_analysis": {"matched_skills": [], "missing_skills": ["Python"]},
            "interview_questions": existing_kit,
        }
        kit = refresh_interview_questions_in_analysis(analysis, kit_status="ready")
        assert kit["technical_questions"][0]["text"] == "LLM-crafted question about stakeholder management"

    def test_refresh_on_existing_analysis(self):
        analysis = {
            "candidate_profile": {"name": "Test", "current_role": "Dev"},
            "jd_analysis": {"required_skills": ["Python"], "role_title": "Backend Dev"},
            "skill_analysis": {"matched_skills": [], "missing_skills": ["Python"]},
            "matched_skills": [],
            "missing_skills": ["Python"],
            "interview_questions": {
                "technical_questions": [{"text": "Old generic question about a project"}],
                "culture_fit_questions": [{"text": "What motivates you?"}],
            },
        }
        refresh_interview_questions_in_analysis(analysis, force=True)
        iq = analysis["interview_questions"]
        assert iq["culture_fit_questions"] == []
        assert "isn't on your resume" not in iq["technical_questions"][0]["text"]

    def test_count_kit_questions(self):
        assert count_kit_questions(None) == 0
        assert count_kit_questions({"technical_questions": [], "behavioral_questions": []}) == 0
        assert count_kit_questions({"technical_questions": [{"text": "Q1"}, {"text": "Q2"}]}) == 2
