"""
Tests for the domain-clustered skill taxonomy and two-pass skill validation
in skill_matcher.py (Task 14 additions).
"""

import pytest

from app.backend.services.skill_matcher import (
    MASTER_SKILLS,
    SKILL_TAXONOMY,
    HIGH_COLLISION_SKILLS,
    _normalize_skill,
    _get_skill_domains,
    _get_skill_subcategory_keys,
    _flatten_taxonomy,
    match_skills,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Taxonomy structure tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTaxonomyStructure:
    """Validate SKILL_TAXONOMY structural integrity."""

    def test_all_master_skills_in_taxonomy(self):
        """All HIGH_COLLISION_SKILLS must appear in SKILL_TAXONOMY.

        This is critical: the two-pass validation relies on _get_skill_subcategory_keys()
        returning results for every high-collision skill.  If a high-collision skill
        is missing from the taxonomy, the validation would silently skip it.
        """
        flat = _flatten_taxonomy()
        missing = []
        for skill in HIGH_COLLISION_SKILLS:
            if _normalize_skill(skill) not in flat:
                missing.append(skill)
        assert not missing, (
            f"HIGH_COLLISION_SKILLS missing from SKILL_TAXONOMY: {missing}"
        )

    def test_taxonomy_structure_valid(self):
        """Every domain has subcategories, every subcategory is a non-empty list."""
        for domain_name, subcategories in SKILL_TAXONOMY.items():
            assert isinstance(subcategories, dict), (
                f"Domain '{domain_name}' should map to a dict of subcategories"
            )
            assert len(subcategories) > 0, (
                f"Domain '{domain_name}' has no subcategories"
            )
            for subcat_name, skill_list in subcategories.items():
                assert isinstance(skill_list, list), (
                    f"Subcategory '{domain_name}.{subcat_name}' should be a list"
                )
                assert len(skill_list) > 0, (
                    f"Subcategory '{domain_name}.{subcat_name}' is empty"
                )
                for skill in skill_list:
                    assert isinstance(skill, str) and skill.strip(), (
                        f"Invalid skill entry in '{domain_name}.{subcat_name}': {skill!r}"
                    )

    def test_get_skill_domains_known(self):
        """'python' should be in programming_languages; 'railway' should be in cloud_platforms."""
        python_domains = _get_skill_domains("python")
        assert "programming_languages" in python_domains, (
            f"'python' expected in programming_languages, got domains: {python_domains}"
        )

        railway_domains = _get_skill_domains("railway")
        assert "cloud_platforms" in railway_domains, (
            f"'railway' expected in cloud_platforms, got domains: {railway_domains}"
        )

    def test_get_skill_domains_unknown(self):
        """An unknown skill should return an empty set of domains."""
        domains = _get_skill_domains("xyzzy_nonexistent_skill")
        assert domains == set(), (
            f"Unknown skill should return empty set, got: {domains}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Two-pass validation tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTwoPassValidation:
    """Validate that high-collision skills require domain co-occurrence from text scanning."""

    def test_railway_rejected_without_cloud_context(self):
        """A data engineer without cloud skills should NOT get 'railway' matched from text."""
        result = match_skills(
            candidate_skills=["python", "sql", "hadoop", "spark", "etl"],
            jd_skills=["railway", "docker", "kubernetes"],
            jd_text="Worked on railway modernization project for Indian Railways",
        )
        assert "railway" not in result["matched_skills"], (
            f"'railway' should NOT be matched for a data engineer with no cloud context. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_railway_accepted_with_cloud_context(self):
        """A cloud engineer with cloud skills SHOULD get 'railway' matched from text."""
        result = match_skills(
            candidate_skills=["docker", "kubernetes", "vercel", "aws"],
            jd_skills=["railway", "docker"],
            jd_text="Deployed app on railway platform",
        )
        assert "railway" in result["matched_skills"], (
            f"'railway' SHOULD be matched for a cloud engineer with cloud context. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_rtos_rejected_without_embedded_context(self):
        """A software dev without embedded skills should NOT get 'rtos' matched from text."""
        result = match_skills(
            candidate_skills=["python", "django", "react"],
            jd_skills=["rtos"],
            jd_text="Experience with rtos scheduling and real-time systems",
        )
        assert "rtos" not in result["matched_skills"], (
            f"'rtos' should NOT be matched for a web dev without embedded context. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_rtos_accepted_with_embedded_context(self):
        """An embedded engineer SHOULD get 'rtos' matched from text."""
        result = match_skills(
            candidate_skills=["freertos", "arm", "firmware"],
            jd_skills=["rtos"],
            jd_text="Experience with rtos scheduling and real-time systems",
        )
        assert "rtos" in result["matched_skills"], (
            f"'rtos' SHOULD be matched for an embedded engineer with embedded context. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_non_collision_skill_always_accepted(self):
        """A non-collision skill like 'docker' should always be accepted from text scanning."""
        result = match_skills(
            candidate_skills=["python"],
            jd_skills=["docker"],
            jd_text="Containerized applications using docker and kubernetes",
        )
        assert "docker" in result["matched_skills"], (
            f"'docker' (non-collision) should always be accepted from text. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_structured_skills_always_accepted(self):
        """Even high-collision skills in the structured candidate_skills list should be accepted."""
        # "railway" is in HIGH_COLLISION_SKILLS, but when it's in the structured
        # candidate_skills list (from a Skills section), it should always be accepted
        result = match_skills(
            candidate_skills=["railway", "docker", "python"],
            jd_skills=["railway"],
            jd_text="",  # No text scanning needed — structured skills bypass validation
        )
        assert "railway" in result["matched_skills"], (
            f"'railway' from structured skills should always be accepted. "
            f"matched_skills={result['matched_skills']}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# The actual false positive case from the user's bug report
# ═══════════════════════════════════════════════════════════════════════════════


class TestBigDataRailwayFalsePositive:
    """Reproduce the actual bug: big-data resume getting 'railway' as a matched skill."""

    def test_big_data_resume_railway_false_positive(self):
        """A big-data engineer's resume should NOT match 'railway' from business context."""
        result = match_skills(
            candidate_skills=[
                "python", "sql", "hadoop", "spark", "informatica",
                "teradata", "bigquery", "etl", "data warehousing",
                "snowflake", "azure", "aws",
            ],
            jd_skills=["railway", "python", "sql"],
            jd_text="Railway domain client project experience preferred",
        )
        assert "railway" not in result["matched_skills"], (
            f"'railway' should NOT be matched for a big-data engineer. "
            f"matched_skills={result['matched_skills']}"
        )
        # But python and sql should still match
        assert "python" in result["matched_skills"], "'python' should still match"
        assert "sql" in result["matched_skills"], "'sql' should still match"
