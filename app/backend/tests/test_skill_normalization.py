"""Tests for the Skill Normalization Engine (SKILL_SYNONYMS, SKILL_HIERARCHY)."""

import pytest

from app.backend.services.skill_matcher import (
    normalize_skill,
    get_implied_skills,
    match_skills,
)
from app.backend.services.constants import SKILL_SYNONYMS, SKILL_HIERARCHY


# ---------------------------------------------------------------------------
# normalize_skill — synonym lookup
# ---------------------------------------------------------------------------

class TestNormalizeSkill:
    """Tests for the normalize_skill() synonym-normalization function."""

    def test_language_abbreviations(self):
        assert normalize_skill("JS") == "javascript"
        assert normalize_skill("TS") == "typescript"
        assert normalize_skill("PY") == "python"
        assert normalize_skill("RB") == "ruby"

    def test_cloud_devops(self):
        assert normalize_skill("K8s") == "kubernetes"
        assert normalize_skill("Kube") == "kubernetes"
        assert normalize_skill("AWS") == "aws"
        assert normalize_skill("Amazon Web Services") == "aws"

    def test_framework_variants(self):
        assert normalize_skill("React.js") == "react"
        assert normalize_skill("ReactJS") == "react"
        assert normalize_skill("Vue.js") == "vue"
        assert normalize_skill("Node.js") == "nodejs"
        assert normalize_skill("Express.js") == "express"

    def test_database_variants(self):
        assert normalize_skill("Postgres") == "postgresql"
        assert normalize_skill("PG") == "postgresql"
        assert normalize_skill("Mongo") == "mongodb"
        assert normalize_skill("SQL Server") == "mssql"

    def test_data_ml(self):
        assert normalize_skill("ML") == "machine learning"
        assert normalize_skill("DL") == "deep learning"
        assert normalize_skill("NLP") == "natural language processing"
        assert normalize_skill("sklearn") == "scikit-learn"
        assert normalize_skill("Torch") == "pytorch"

    def test_messaging_api(self):
        assert normalize_skill("REST") == "rest api"
        assert normalize_skill("RESTful") == "rest api"
        assert normalize_skill("WS") == "websockets"

    def test_methodologies(self):
        assert normalize_skill("TDD") == "test driven development"
        assert normalize_skill("BDD") == "behavior driven development"
        assert normalize_skill("OOP") == "object oriented programming"

    def test_frontend(self):
        assert normalize_skill("HTML5") == "html"
        assert normalize_skill("CSS3") == "css"
        assert normalize_skill("SCSS") == "sass"
        assert normalize_skill("MUI") == "material-ui"
        assert normalize_skill("Tailwind CSS") == "tailwindcss"

    def test_others(self):
        assert normalize_skill("VS Code") == "visual studio code"
        assert normalize_skill("PS") == "powershell"

    def test_empty_string(self):
        assert normalize_skill("") == ""

    def test_none_like(self):
        assert normalize_skill("  ") == ""  # strip leads to empty

    def test_unknown_skill_passthrough(self):
        assert normalize_skill("foobar") == "foobar"

    def test_case_insensitive(self):
        assert normalize_skill("javascript") == "javascript"
        assert normalize_skill("JAVASCRIPT") == "javascript"

    def test_idempotent(self):
        """Normalizing a canonical form should return the same canonical form."""
        for _key, canonical in SKILL_SYNONYMS.items():
            assert normalize_skill(canonical) == canonical, (
                f"normalize_skill({canonical!r}) should be idempotent"
            )


# ---------------------------------------------------------------------------
# get_implied_skills — hierarchy traversal
# ---------------------------------------------------------------------------

class TestGetImpliedSkills:
    """Tests for the get_implied_skills() hierarchy function."""

    def test_react_implies_javascript(self):
        implied = get_implied_skills("react")
        assert any(i["skill"] == "javascript" for i in implied)
        assert implied[0]["skill"] == "javascript"
        assert implied[0]["confidence"] == 0.7

    def test_nextjs_implies_react_then_javascript(self):
        implied = get_implied_skills("nextjs")
        skills = [i["skill"] for i in implied]
        assert "react" in skills
        assert "javascript" in skills
        # react is at depth 0 (conf 0.7), javascript at depth 1 (conf 0.55)
        react_entry = next(i for i in implied if i["skill"] == "react")
        js_entry = next(i for i in implied if i["skill"] == "javascript")
        assert react_entry["confidence"] == 0.7
        assert js_entry["confidence"] == 0.55

    def test_django_implies_python(self):
        implied = get_implied_skills("django")
        assert any(i["skill"] == "python" for i in implied)

    def test_kubernetes_implies_docker(self):
        implied = get_implied_skills("kubernetes")
        assert any(i["skill"] == "docker" for i in implied)

    def test_helm_implies_kubernetes_then_docker(self):
        implied = get_implied_skills("helm")
        skills = [i["skill"] for i in implied]
        assert "kubernetes" in skills
        assert "docker" in skills

    def test_depth_limit_three(self):
        """Hierarchy traversal should stop at depth 3."""
        # helm -> kubernetes -> docker -> (would stop, docker has no parent in hierarchy)
        implied = get_implied_skills("helm")
        assert len(implied) <= 3

    def test_confidence_minimum(self):
        """Confidence should never drop below 0.4."""
        implied = get_implied_skills("helm")
        for entry in implied:
            assert entry["confidence"] >= 0.4

    def test_leaf_skill_no_implied(self):
        """A skill not in SKILL_HIERARCHY should return empty list."""
        implied = get_implied_skills("python")
        assert implied == []

    def test_source_preserved(self):
        implied = get_implied_skills("react")
        for entry in implied:
            assert entry["source"] == "react"

    def test_empty_skill(self):
        assert get_implied_skills("") == []


# ---------------------------------------------------------------------------
# match_skills — integration with normalization engine
# ---------------------------------------------------------------------------

class TestMatchSkillsWithNormalization:
    """Tests for match_skills() enhanced with normalization and hierarchy."""

    def test_synonym_match_js_to_javascript(self):
        """'JS' in resume should match 'JavaScript' in JD."""
        result = match_skills(["JS"], ["JavaScript"])
        assert "JavaScript" in result["matched_skills"]
        # matched_skills_detailed should have confidence metadata
        detailed = result["matched_skills_detailed"]
        js_match = [d for d in detailed if d["skill"] == "JavaScript"]
        assert len(js_match) >= 1
        assert js_match[0]["confidence"] > 0
        assert js_match[0]["match_type"] in ("exact", "alias", "hierarchy_inferred", "substring")

    def test_exact_match_type(self):
        """Directly matching skill should be tagged as 'exact'."""
        result = match_skills(["Python"], ["Python"])
        detailed = result["matched_skills_detailed"]
        python_match = [d for d in detailed if d["skill"] == "Python"]
        assert len(python_match) == 1
        assert python_match[0]["match_type"] == "exact"
        assert python_match[0]["confidence"] == 1.0

    def test_alias_match_type(self):
        """Skill matched through alias expansion should be tagged as 'alias'."""
        # "JS" is an alias for "javascript" — when JD says "JavaScript",
        # and candidate has "JS", the match is via alias.
        result = match_skills(["JS"], ["JavaScript"])
        detailed = result["matched_skills_detailed"]
        js_match = [d for d in detailed if d["skill"] == "JavaScript"]
        assert len(js_match) >= 1
        assert js_match[0]["match_type"] == "alias"

    def test_hierarchy_inferred_in_detailed_only(self):
        """Hierarchy-inferred skills should appear in matched_skills_detailed but NOT in matched_skills."""
        # Candidate has React, JD requires JavaScript (implied by React)
        result = match_skills(["React"], ["JavaScript"])
        detailed = result["matched_skills_detailed"]
        hierarchy_matches = [d for d in detailed if d["match_type"] == "hierarchy_inferred"]
        assert len(hierarchy_matches) >= 1
        assert any(d["skill"] == "JavaScript" for d in hierarchy_matches)
        # Flat matched_skills should NOT include hierarchy-inferred matches
        assert "JavaScript" not in result["matched_skills"]

    def test_hierarchy_inferred_confidence(self):
        """Hierarchy-inferred match should carry confidence from get_implied_skills."""
        result = match_skills(["React"], ["JavaScript"])
        detailed = result["matched_skills_detailed"]
        hierarchy_matches = [d for d in detailed if d["match_type"] == "hierarchy_inferred"]
        assert len(hierarchy_matches) >= 1
        js_match = next(d for d in hierarchy_matches if d["skill"] == "JavaScript")
        assert js_match["confidence"] == 0.7
        assert js_match["source"] == "React"

    def test_backward_compat_matched_skills(self):
        """The flat matched_skills list must remain backward compatible."""
        result = match_skills(
            ["Python", "Docker", "React"],
            ["Python", "Docker", "React"],
        )
        assert "Python" in result["matched_skills"]
        assert "Docker" in result["matched_skills"]
        assert "React" in result["matched_skills"]
        assert "matched_skills_detailed" in result

    def test_matched_skills_detailed_always_present(self):
        """matched_skills_detailed should always be in result, even when empty."""
        result = match_skills([], [])
        assert "matched_skills_detailed" in result
        assert isinstance(result["matched_skills_detailed"], list)

    def test_missing_skills_unaffected(self):
        """Missing skills should not include hierarchy-inferred entries in the flat list."""
        result = match_skills(["React"], ["JavaScript", "Docker"])
        # JavaScript is missing from flat matched_skills (only hierarchy-inferred)
        # but should be in missing_skills
        assert "JavaScript" in result["missing_skills"]
        assert "Docker" in result["missing_skills"]

    def test_deep_hierarchy_inference(self):
        """Next.js → React → JavaScript chain should produce multi-level inference."""
        result = match_skills(["Next.js"], ["JavaScript"])
        detailed = result["matched_skills_detailed"]
        hierarchy_matches = [d for d in detailed if d["match_type"] == "hierarchy_inferred"]
        assert len(hierarchy_matches) >= 1
        js_match = next(
            (d for d in hierarchy_matches if d["skill"] == "JavaScript"), None
        )
        assert js_match is not None
        # Next.js → React (depth 0) → JavaScript (depth 1), confidence = 0.55
        assert js_match["confidence"] == 0.55

    def test_k8s_matches_kubernetes(self):
        """'K8s' in resume should match 'Kubernetes' in JD."""
        result = match_skills(["K8s"], ["Kubernetes"])
        assert "Kubernetes" in result["matched_skills"]

    def test_postgres_matches_postgresql(self):
        """'Postgres' in resume should match 'PostgreSQL' in JD."""
        result = match_skills(["Postgres"], ["PostgreSQL"])
        assert "PostgreSQL" in result["matched_skills"]

    def test_no_false_hierarchy_for_unrelated_skills(self):
        """Skills with no hierarchy relationship should not produce hierarchy_inferred matches."""
        result = match_skills(["Python"], ["Java"])
        detailed = result["matched_skills_detailed"]
        hierarchy_matches = [d for d in detailed if d["match_type"] == "hierarchy_inferred"]
        assert len(hierarchy_matches) == 0
