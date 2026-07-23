"""Tests for recruiter screen playbook generation."""

from app.backend.services.interview_kit_generator import (
    generate_targeted_interview_kit,
    refresh_interview_questions_in_analysis,
    count_kit_questions,
    is_playbook_kit,
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

    def test_playbook_v3_structure(self):
        kit = self._kit()
        assert kit["kit_version"] == 3
        assert is_playbook_kit(kit)
        assert kit["screen_objective"]
        assert len(kit["hypotheses"]) >= 3
        assert len(kit["threads"]) >= 2
        assert kit["open"]["recruiter_owned"] is True
        assert kit["open"]["script"] == ""
        assert kit["close"]["script"]
        assert kit["hm_debrief_template"]["must_haves"]

    def test_risk_thread_for_missing_skills(self):
        kit = self._kit()
        risk_threads = [t for t in kit["threads"] if t["kind"] == "risk"]
        assert len(risk_threads) == 1
        risk_text = " ".join(s["text"] for s in risk_threads[0]["steps"])
        assert "IDOC" in risk_text or "S/4HANA" in risk_text
        assert "isn't on your resume" not in risk_text.lower()

    def test_ownership_thread_domain_specific(self):
        kit = self._kit()
        ownership = next(t for t in kit["threads"] if t["kind"] == "ownership")
        text = " ".join(s["text"] for s in ownership["steps"])
        assert "MM" in text or "ERP" in text or "engagement" in text.lower()

    def test_no_culture_fit_questions(self):
        kit = self._kit()
        assert kit["culture_fit_questions"] == []

    def test_steps_are_spoken_length(self):
        kit = self._kit()
        all_steps = []
        for thread in kit["threads"]:
            all_steps.extend(thread["steps"])
        assert 4 <= len(all_steps) <= 12
        for step in all_steps:
            assert len(step["text"]) <= 200
            assert step.get("intent")
            assert step.get("spoken_text") or step.get("text")

    def test_no_duplicate_question_stems(self):
        kit = self._kit()
        texts = [s["text"].lower()[:50] for t in kit["threads"] for s in t["steps"]]
        assert len(texts) == len(set(texts))

    def test_legacy_categories_populated(self):
        kit = self._kit()
        legacy_total = (
            len(kit["technical_questions"])
            + len(kit["behavioral_questions"])
            + len(kit["experience_deep_dive_questions"])
        )
        assert legacy_total >= count_kit_questions(kit) - 1

    def test_corrupted_profile_fields_are_cleaned(self):
        kit = self._kit(
            profile={
                "name": "Kalpana {",
                "current_role": "Recruiter {",
                "current_company": "ValueLabs {",
                "total_effective_years": 8,
                "work_experience": [{"title": "Duration", "company": ""}],
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
        all_text = " ".join(
            s["text"] for t in kit["threads"] for s in t["steps"]
        )
        assert "{" not in all_text
        assert "job description:" not in all_text.lower()
        assert "Duration" not in all_text

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
        all_text = " ".join(
            s["text"] for t in kit["threads"] for s in t["steps"]
        ).lower()
        assert "machine learning" not in all_text

    def test_engineering_domain_playbook(self):
        kit = self._kit(
            profile={
                "name": "Alex",
                "current_role": "Backend Engineer",
                "total_effective_years": 6,
                "work_experience": [{"company": "TechCo", "title": "Senior Engineer"}],
            },
            jd_analysis={
                "role_title": "Backend Software Engineer",
                "domain": "Engineering",
                "required_skills": ["Python", "PostgreSQL", "Kubernetes"],
            },
            skill_analysis={
                "matched_required": ["Python", "PostgreSQL"],
                "missing_required": ["Kubernetes"],
            },
        )
        assert is_playbook_kit(kit)
        assert any(t["kind"] == "risk" for t in kit["threads"])

    def test_refresh_preserves_ready_llm_kit(self):
        existing_kit = {
            "kit_version": 2,
            "threads": [{"id": "t1", "steps": [{"text": "LLM thread question"}]}],
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
        assert iq["kit_version"] == 3
        assert iq["culture_fit_questions"] == []
        assert "isn't on your resume" not in iq["technical_questions"][0]["text"]

    def test_count_kit_questions(self):
        assert count_kit_questions(None) == 0
        playbook = {
            "threads": [
                {"steps": [{"text": "Q1"}, {"text": "Q2"}]},
                {"steps": [{"text": "Q3"}]},
            ],
        }
        assert count_kit_questions(playbook) == 3
        assert count_kit_questions({"technical_questions": [{"text": "Q1"}, {"text": "Q2"}]}) == 2
