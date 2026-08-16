"""Regression: JD skill enrichment must resolve proficiency without NameError."""

from app.backend.routes.analyze_helpers import _enrich_skills_with_confidence


def test_enrich_skills_with_confidence_includes_proficiency():
    result = _enrich_skills_with_confidence(
        ["Python"],
        "We require expert in Python for this senior backend role.",
        is_nice_to_have=False,
        seniority="senior",
    )
    assert len(result) == 1
    assert result[0]["skill"] == "Python"
    assert result[0]["proficiency_expected"] in {"basic", "intermediate", "advanced", "expert"}
    assert result[0]["confidence"] in {"high", "medium", "low"}
