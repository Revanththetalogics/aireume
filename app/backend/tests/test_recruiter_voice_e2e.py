"""Golden-path tests for recruiter voice personalization pipeline."""

import pytest


@pytest.mark.asyncio
async def test_pipeline_ci_kit_personalize_lint_strategy(monkeypatch):
    from app.backend.services.candidate_intelligence_service import build_candidate_intelligence
    from app.backend.services.interview_kit_generator import generate_targeted_interview_kit, is_playbook_kit
    from app.backend.services.interview_kit_quality import lint_interview_kit, get_spoken_line
    from app.backend.services.kit_strategy import strategy_from_kit

    async def fake_personalize(kit, context):
        out = dict(kit)
        for thread in out.get("threads") or []:
            for step in thread.get("steps") or []:
                company = (context.get("resume_anchors") or {}).get("current_company") or "Acme"
                step["spoken_text"] = f"At {company}, what did you personally own on the MM rollout?"
                step["intent"] = "Verify SAP MM ownership with specifics"
                step["follow_up_intents"] = ["If they say 'we', ask what they did personally"]
        return out

    monkeypatch.setattr(
        "app.backend.services.recruiter_voice_personalizer.personalize_kit",
        fake_personalize,
    )

    python_result = {
        "candidate_profile": {
            "name": "Kalpana P",
            "current_role": "SAP MM Consultant",
            "current_company": "Acme Corp",
            "work_experience": [{"company": "Acme Corp", "title": "SAP MM Consultant"}],
        },
        "jd_analysis": {
            "role_title": "SAP MM Consultant",
            "domain": "SAP ERP",
            "required_skills": ["SAP MM", "IDOC"],
        },
        "skill_analysis": {
            "matched_required": ["SAP MM"],
            "missing_required": ["IDOC"],
        },
        "fit_score": 68,
    }

    ci = build_candidate_intelligence(
        analysis_result=python_result,
        probe_areas=[{
            "category": "skill_validation",
            "skill": "IDOC",
            "priority": "high",
            "reasoning": "IDOC required but not matched on resume",
        }],
    )

    kit = generate_targeted_interview_kit(
        profile=python_result["candidate_profile"],
        jd_analysis=python_result["jd_analysis"],
        skill_analysis=python_result["skill_analysis"],
        candidate_intelligence=ci,
    )
    assert kit["kit_version"] == 3
    assert is_playbook_kit(kit)

    from app.backend.services.recruiter_voice_personalizer import personalize_kit
    from app.backend.services.candidate_intelligence_service import merge_ci_into_kit_context

    ctx = merge_ci_into_kit_context(python_result, ci)
    personalized = await personalize_kit(kit, ctx)
    lint = lint_interview_kit(personalized)
    assert lint["ok"] is True

    spoken_lines = [
        get_spoken_line(s)
        for t in personalized["threads"]
        for s in t.get("steps") or []
    ]
    assert any("Acme" in line for line in spoken_lines)

    strategy = strategy_from_kit(
        personalized,
        candidate_name="Kalpana",
        role_title="SAP MM Consultant",
        candidate_intelligence=ci,
    )
    assert strategy["source"] == "interview_kit"
    assert strategy["planned_questions"]
    assert strategy["planned_questions"][0].get("intent")
