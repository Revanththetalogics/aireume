from app.backend.services.candidate_intelligence_service import build_candidate_intelligence


def test_build_includes_claims_to_validate():
    ci = build_candidate_intelligence(
        screening_result_id=1,
        analysis_result={
            "skill_analysis": {"missing_required": ["Kubernetes"], "matched_required": ["Python"]},
            "risk_signals": [],
            "candidate_profile": {
                "name": "Jane Doe",
                "current_company": "Acme Corp",
                "current_role": "Engineer",
            },
        },
        parsed_data={"work_experience": [{"company": "Acme Corp", "title": "Engineer"}]},
        gap_analysis={"employment_gaps": []},
        probe_areas=[{
            "category": "skill_validation",
            "skill": "Kubernetes",
            "priority": "high",
            "reasoning": "Kubernetes required but not matched",
        }],
        fit_score=65,
    )
    assert ci["version"] == 1
    assert len(ci["claims_to_validate"]) >= 1
    assert ci["resume_anchors"]["current_company"] == "Acme Corp"
    assert ci["hiring_confidence_pre_interview"] == 0.65
