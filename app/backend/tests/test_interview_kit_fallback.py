"""Tests for interview kit refresh preservation and briefing."""

from app.backend.services.interview_kit_generator import (
    generate_targeted_interview_kit,
    refresh_interview_questions_in_analysis,
    count_kit_questions,
)


class TestRefreshPreservesFallbackKit:
    def test_preserves_fallback_when_questions_exist(self):
        kit = {
            "kit_version": 2,
            "threads": [{"id": "t1", "steps": [{"text": "Stored question?"}]}],
        }
        analysis = {"interview_questions": kit}
        out = refresh_interview_questions_in_analysis(
            analysis, kit_status="fallback",
        )
        assert out["threads"][0]["steps"][0]["text"] == "Stored question?"

    def test_regenerates_when_fallback_empty(self):
        analysis = {"interview_questions": {"threads": []}}
        out = refresh_interview_questions_in_analysis(
            analysis,
            kit_status="fallback",
            parsed_data={},
        )
        assert count_kit_questions(out) > 0


class TestHmFocusKit:
    def test_hm_topics_create_thread(self):
        kit = generate_targeted_interview_kit(
            profile={"name": "Alex", "current_role": "Analyst", "total_effective_years": 5},
            jd_analysis={"role_title": "FP&A Analyst", "required_skills": ["Excel"]},
            skill_analysis={"matched_required": ["Excel"], "missing_required": []},
            kit_inputs={
                "hm_screen_topics": [
                    {"question": "How do you build annual budgets?", "category": "hm_focus"},
                ],
            },
        )
        thread_ids = [t["id"] for t in kit.get("threads", [])]
        assert "thread_hm_focus" in thread_ids
        assert kit["open"]["script"] == ""
        probes = kit["candidate_briefing"]["areas_to_probe"]
        assert any("HM focus" in p for p in probes)
        assert not any("JD needs" in p for p in probes)
