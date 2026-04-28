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
            text_scanned_skills=["railway"],
        )
        assert "railway" not in result["matched_skills"], (
            f"'railway' should NOT be matched for a data engineer with no cloud context. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_railway_accepted_with_cloud_context(self):
        """A cloud engineer with deployment-platforms context SHOULD get 'railway' matched."""
        result = match_skills(
            candidate_skills=["docker", "kubernetes", "vercel", "heroku", "aws"],
            jd_skills=["railway", "docker"],
            text_scanned_skills=["railway"],
        )
        assert "railway" in result["matched_skills"], (
            f"'railway' SHOULD be matched for a cloud engineer with deployment context. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_rtos_rejected_without_embedded_context(self):
        """A software dev without embedded skills should NOT get 'rtos' matched from text."""
        result = match_skills(
            candidate_skills=["python", "django", "react"],
            jd_skills=["rtos"],
            text_scanned_skills=["rtos"],
        )
        assert "rtos" not in result["matched_skills"], (
            f"'rtos' should NOT be matched for a web dev without embedded context. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_rtos_accepted_with_embedded_context(self):
        """An embedded engineer SHOULD get 'rtos' matched from text."""
        result = match_skills(
            candidate_skills=["freertos", "zephyr", "arm", "firmware"],
            jd_skills=["rtos"],
            text_scanned_skills=["rtos"],
        )
        assert "rtos" in result["matched_skills"], (
            f"'rtos' SHOULD be matched for an embedded engineer with embedded context. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_non_collision_skill_accepted_with_domain_context(self):
        """A non-collision skill like 'docker' should be accepted from text scanning with same-domain context."""
        result = match_skills(
            candidate_skills=["kubernetes"],
            jd_skills=["docker"],
            text_scanned_skills=["docker"],
        )
        assert "docker" in result["matched_skills"], (
            f"'docker' (non-collision) should be accepted from text with domain context. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_structured_skills_always_accepted(self):
        """Even high-collision skills in the structured candidate_skills list should be accepted."""
        # "railway" is in HIGH_COLLISION_SKILLS, but when it's in the structured
        # candidate_skills list (from a Skills section), it should always be accepted
        result = match_skills(
            candidate_skills=["railway", "docker", "python"],
            jd_skills=["railway"],
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
            text_scanned_skills=["railway"],
        )
        assert "railway" not in result["matched_skills"], (
            f"'railway' should NOT be matched for a big-data engineer. "
            f"matched_skills={result['matched_skills']}"
        )
        # But python and sql should still match
        assert "python" in result["matched_skills"], "'python' should still match"
        assert "sql" in result["matched_skills"], "'sql' should still match"


# ═══════════════════════════════════════════════════════════════════════════════
# Regression tests for domain boundary enforcement
# ═══════════════════════════════════════════════════════════════════════════════


class TestDomainBoundaryRegressions:
    """Regression tests ensuring domain boundaries prevent false-positive skill matches."""

    def test_data_warehouse_resume_vs_embedded_jd(self):
        """Data Warehouse/ETL candidate must NOT match embedded JD's railway or rtos."""
        result = match_skills(
            candidate_skills=["teradata", "informatica", "hadoop", "hive", "sql", "data_modeling", "etl"],
            jd_skills=["railway", "rtos", "embedded", "communication", "c", "linux"],
            text_scanned_skills=["railway", "rtos"],
        )
        assert "railway" not in result["matched_skills"], (
            f"'railway' should NOT match for a data-warehouse candidate. "
            f"matched_skills={result['matched_skills']}"
        )
        assert "rtos" not in result["matched_skills"], (
            f"'rtos' should NOT match for a data-warehouse candidate. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_embedded_resume_vs_embedded_jd(self):
        """Embedded Systems candidate SHOULD match embedded JD's railway and rtos."""
        result = match_skills(
            candidate_skills=["rtos", "railway", "embedded", "c", "linux", "can_bus", "arm"],
            jd_skills=["railway", "rtos", "embedded", "communication", "c", "linux"],
        )
        assert "railway" in result["matched_skills"], (
            f"'railway' SHOULD match for an embedded candidate with railway skill. "
            f"matched_skills={result['matched_skills']}"
        )
        assert "rtos" in result["matched_skills"], (
            f"'rtos' SHOULD match for an embedded candidate with rtos skill. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_substring_matching_respects_domain_boundaries(self):
        """Substring matching for high-collision skills requires subcategory overlap."""
        # Positive: react_native shares subcategory with react → should match
        result_pos = match_skills(
            candidate_skills=["react native"],
            jd_skills=["react"],
        )
        assert "react" in result_pos["matched_skills"], (
            f"'react' SHOULD match via substring with 'react native' (same subcategory). "
            f"matched_skills={result_pos['matched_skills']}"
        )

        # Negative: data_warehouse does not share subcategory with railway → no substring match
        result_neg = match_skills(
            candidate_skills=["data_warehouse"],
            jd_skills=["railway"],
        )
        assert "railway" not in result_neg["matched_skills"], (
            f"'railway' should NOT match via substring with 'data_warehouse' (different domains). "
            f"matched_skills={result_neg['matched_skills']}"
        )

    def test_short_skills_skip_substring_matching(self):
        """Skills with ≤3 characters should not match via substring."""
        result = match_skills(
            candidate_skills=["redux"],
            jd_skills=["r"],
        )
        assert "r" not in result["matched_skills"], (
            f"'r' should NOT match 'redux' via substring (≤3 chars skip substring matching). "
            f"matched_skills={result['matched_skills']}"
        )

    def test_structured_skills_context_only(self):
        """When structured_skills provided, two-pass validation uses ONLY those for context."""
        result = match_skills(
            candidate_skills=["teradata", "sql", "hadoop"],
            jd_skills=["railway", "rtos", "sql"],
            text_scanned_skills=["railway", "rtos"],
            structured_skills=["teradata", "sql", "hadoop"],
        )
        assert "railway" not in result["matched_skills"], (
            f"'railway' should NOT match — no embedded/cloud context in structured skills. "
            f"matched_skills={result['matched_skills']}"
        )
        assert "rtos" not in result["matched_skills"], (
            f"'rtos' should NOT match — no embedded context in structured skills. "
            f"matched_skills={result['matched_skills']}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Regression tests for text_scanned_skills architecture
# ═══════════════════════════════════════════════════════════════════════════════


class TestTextScannedSkillRegression:
    """Regression tests for the text_scanned_skills promotion architecture.

    These tests validate the new three-tier skill matching:
      - Tier 0: structured_skills / candidate_skills (trusted, always accepted)
      - Tier 2: text_scanned_skills (low confidence, require domain validation)
    """

    def test_text_scanned_rejected_without_context(self):
        """text_scanned_skills with no candidate context must not be promoted (no circular fallback)."""
        result = match_skills(
            candidate_skills=[],
            jd_skills=["railway", "rtos"],
            text_scanned_skills=["railway", "rtos"],
        )
        assert "railway" not in result["matched_skills"], (
            f"'railway' should NOT be matched with empty candidate skills (no circular fallback). "
            f"matched_skills={result['matched_skills']}"
        )
        assert "rtos" not in result["matched_skills"], (
            f"'rtos' should NOT be matched with empty candidate skills (no circular fallback). "
            f"matched_skills={result['matched_skills']}"
        )

    def test_text_scanned_accepted_with_cloud_context(self):
        """text_scanned 'railway' is promoted when structured skills provide deployment_platforms context."""
        result = match_skills(
            candidate_skills=["vercel", "heroku", "aws"],
            jd_skills=["railway", "aws"],
            text_scanned_skills=["railway"],
            structured_skills=["vercel", "heroku", "aws"],
        )
        assert "railway" in result["matched_skills"], (
            f"'railway' SHOULD be matched — vercel and heroku provide deployment_platforms context. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_text_scanned_rejected_wrong_domain(self):
        """text_scanned 'railway' is rejected when context is data engineering, not cloud platforms."""
        result = match_skills(
            candidate_skills=["teradata", "hadoop", "sql"],
            jd_skills=["railway"],
            text_scanned_skills=["railway"],
            structured_skills=["teradata", "hadoop", "sql"],
        )
        assert "railway" not in result["matched_skills"], (
            f"'railway' should NOT be matched — data engineering doesn't validate cloud platform skills. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_structured_skills_always_match(self):
        """Structured candidate_skills always match regardless of domain context."""
        result = match_skills(
            candidate_skills=["python", "aws"],
            jd_skills=["python", "aws"],
        )
        assert "python" in result["matched_skills"], (
            f"'python' should always match from structured skills. "
            f"matched_skills={result['matched_skills']}"
        )
        assert "aws" in result["matched_skills"], (
            f"'aws' should always match from structured skills. "
            f"matched_skills={result['matched_skills']}"
        )

    def test_fuzzy_skipped_for_collision_skills(self):
        """HIGH_COLLISION_SKILLS must not match via fuzzy matching."""
        result = match_skills(
            candidate_skills=["redux"],
            jd_skills=["rtos"],
        )
        assert "rtos" not in result["matched_skills"], (
            f"'rtos' should NOT match 'redux' via fuzzy (collision skill). "
            f"matched_skills={result['matched_skills']}"
        )

    def test_text_scanned_non_collision_accepted_same_domain(self):
        """Non-collision text_scanned skill is promoted when same-domain context exists."""
        result = match_skills(
            candidate_skills=["aws", "docker"],
            jd_skills=["terraform"],
            text_scanned_skills=["terraform"],
            structured_skills=["aws", "docker"],
        )
        assert "terraform" in result["matched_skills"], (
            f"'terraform' SHOULD be matched — shares devops_infrastructure domain with docker. "
            f"matched_skills={result['matched_skills']}"
        )
