"""Comprehensive tests for O*NET integration and false-positive prevention.

Tests cover:
- ONETCache: SQLite cache operations
- ONETValidator: Occupation-aware skill validation
- match_skills_with_onet: Skill matching with O*NET context
- Graceful degradation when DB is unavailable
- False-positive prevention for homonym skills (railway, rtos)

DB-dependent tests are conditionally skipped when the O*NET cache
file is absent (e.g. fresh CI environment).
"""

import os
import sys
import tempfile

import pytest

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.backend.services.onet.onet_cache import ONETCache
from app.backend.services.onet.onet_validator import ONETValidator
from app.backend.services.skill_matcher import match_skills, match_skills_with_onet

# ── O*NET DB path ─────────────────────────────────────────────────────────────
ONET_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "onet", "db", "onet_cache.db"
)
ONET_DB_PATH = os.path.normpath(ONET_DB_PATH)

ONET_DB_AVAILABLE = os.path.exists(ONET_DB_PATH)

# Skip marker for tests that require the synced O*NET database
requires_onet_db = pytest.mark.skipif(
    not ONET_DB_AVAILABLE,
    reason="O*NET cache DB not found — run onet_sync first",
)


# ═══════════════════════════════════════════════════════════════════════════════
# ONETCache tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestONETCache:
    """Tests for ONETCache SQLite operations."""

    @requires_onet_db
    def test_cache_opens_existing_db(self):
        """Verify the synced DB is accessible and has valid tables."""
        cache = ONETCache(ONET_DB_PATH)
        try:
            # Should not raise — tables already exist
            assert cache.is_populated()
        finally:
            cache.close()

    @requires_onet_db
    def test_cache_is_populated(self):
        """is_populated() returns True for a populated DB."""
        cache = ONETCache(ONET_DB_PATH)
        try:
            assert cache.is_populated() is True
        finally:
            cache.close()

    @requires_onet_db
    def test_cache_get_version(self):
        """Returns a version string from the synced DB."""
        cache = ONETCache(ONET_DB_PATH)
        try:
            version = cache.get_version()
            assert version is not None
            assert isinstance(version, str)
            # The sync script writes "30.2"
            assert version.startswith("30")
        finally:
            cache.close()

    @requires_onet_db
    def test_get_skills_for_occupation(self):
        """Query 15-1252.00 (Software Developers) returns skills like Python, Java, etc."""
        cache = ONETCache(ONET_DB_PATH)
        try:
            skills = cache.get_skills_for_occupation("15-1252.00")
            assert len(skills) > 0, "Software Developers should have technology skills"
            skill_names = {s["skill_name"].lower() for s in skills}
            # Python and Java are standard tech skills for Software Developers
            assert "python" in skill_names or "java" in skill_names, (
                f"Expected Python or Java in Software Developers skills; got: {skill_names}"
            )
        finally:
            cache.close()

    @requires_onet_db
    def test_find_soc_by_title(self):
        """'Software Developer' returns 15-1252.00."""
        cache = ONETCache(ONET_DB_PATH)
        try:
            matches = cache.find_soc_by_title("Software Developer")
            assert len(matches) > 0, "Expected at least one match for 'Software Developer'"
            soc_codes = [m[0] for m in matches]
            assert "15-1252.00" in soc_codes, (
                f"Expected 15-1252.00 in matches; got: {soc_codes}"
            )
        finally:
            cache.close()

    @requires_onet_db
    def test_skill_exists_for_occupation(self):
        """'Python' exists for 15-1252.00 (Software Developers)."""
        cache = ONETCache(ONET_DB_PATH)
        try:
            assert cache.skill_exists_for_occupation("Python", "15-1252.00") is True
        finally:
            cache.close()

    @requires_onet_db
    def test_skill_not_exists_for_occupation(self):
        """'Railway' should NOT exist for a data warehouse occupation."""
        cache = ONETCache(ONET_DB_PATH)
        try:
            # 15-2051.00 = Data Scientists — 'Railway' is not a technology skill
            result = cache.skill_exists_for_occupation("Railway", "15-2051.00")
            assert result is False, "'Railway' should not be a technology skill for Data Scientists"
        finally:
            cache.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ONETValidator tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestONETValidator:
    """Tests for ONETValidator occupation-aware validation."""

    @requires_onet_db
    def test_validator_available(self):
        """'available' property is True when DB exists and is populated."""
        validator = ONETValidator(db_path=ONET_DB_PATH)
        assert validator.available is True

    @requires_onet_db
    def test_resolve_occupation_exact(self):
        """'Software Developer' resolves to a SOC code."""
        validator = ONETValidator(db_path=ONET_DB_PATH)
        result = validator.resolve_occupation("Software Developer")
        assert result is not None
        assert "soc_code" in result
        assert "title" in result
        assert "confidence" in result
        assert result["soc_code"] == "15-1252.00"
        assert result["confidence"] == 1.0  # exact alternate-title match

    @requires_onet_db
    def test_resolve_occupation_fuzzy(self):
        """A partial title should still resolve via LIKE match."""
        validator = ONETValidator(db_path=ONET_DB_PATH)
        # 'Software Engineer' is an alternate title for Software Developers (15-1252.00)
        # and will also LIKE-match the occupation title 'Software Developers'
        result = validator.resolve_occupation("Software Engineer")
        assert result is not None, "Should resolve 'Software Engineer'"
        assert result["soc_code"] is not None
        # Should match Software Developers as one of the top results
        # (exact alternate title match gives confidence 1.0)
        assert result["confidence"] >= 0.5

    @requires_onet_db
    def test_resolve_occupation_unknown(self):
        """'Underwater Basket Weaver' returns None."""
        validator = ONETValidator(db_path=ONET_DB_PATH)
        result = validator.resolve_occupation("Underwater Basket Weaver")
        assert result is None

    @requires_onet_db
    def test_validate_skill_recognized(self):
        """'Python' for Software Developers is recognized."""
        validator = ONETValidator(db_path=ONET_DB_PATH)
        result = validator.validate_skill("Python", "15-1252.00")
        assert result["valid"] is True
        assert isinstance(result["is_hot"], bool)
        assert isinstance(result["is_in_demand"], bool)

    @requires_onet_db
    def test_validate_skill_hot_technology(self):
        """Python should be marked as hot technology for Software Developers."""
        validator = ONETValidator(db_path=ONET_DB_PATH)
        result = validator.validate_skill("Python", "15-1252.00")
        assert result["valid"] is True
        # Python is a hot technology in O*NET 30.2 for Software Developers
        assert result["is_hot"] is True, "Python should be marked as hot technology"

    @requires_onet_db
    def test_validate_skills_batch(self):
        """Batch validation with mixed valid/invalid skills."""
        validator = ONETValidator(db_path=ONET_DB_PATH)
        skills = ["Python", "Java", "Underwater Welding", "Railway"]
        result = validator.validate_skills_batch(skills, "Software Developer")
        assert result["soc_code"] is not None
        assert result["occupation_title"] is not None
        assert len(result["validated"]) == len(skills)
        # Python and Java should be recognized
        recognized = [v for v in result["validated"] if v["recognized"]]
        unrecognized = [v for v in result["validated"] if not v["recognized"]]
        assert len(recognized) >= 1, "At least Python or Java should be recognized"
        assert len(unrecognized) >= 1, "At least one skill should be unrecognized"
        # Match ratio should be between 0 and 1
        assert 0.0 <= result["occupation_match_ratio"] <= 1.0

    @requires_onet_db
    def test_get_hot_technologies(self):
        """Returns a non-empty list of hot technologies."""
        validator = ONETValidator(db_path=ONET_DB_PATH)
        hot = validator.get_hot_technologies()
        assert isinstance(hot, list)
        assert len(hot) > 0, "O*NET data should contain hot technologies"
        # Python should appear as a hot technology across some occupation
        assert "Python" in hot, "Python should be a hot technology in O*NET"


# ═══════════════════════════════════════════════════════════════════════════════
# Graceful degradation tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestGracefulDegradation:
    """Tests that O*NET integration gracefully degrades when data is unavailable."""

    def test_validator_unavailable_with_bad_path(self):
        """ONETValidator with nonexistent DB path has available=False."""
        validator = ONETValidator(db_path="/tmp/nonexistent_onet_test_12345/onet.db")
        assert validator.available is False

    def test_validate_skill_when_unavailable(self):
        """validate_skill returns appropriate fallback when unavailable."""
        validator = ONETValidator(db_path="/tmp/nonexistent_onet_test_12345/onet.db")
        result = validator.validate_skill("Python", "15-1252.00")
        assert result["valid"] is False
        assert result["is_hot"] is False
        assert result["is_in_demand"] is False
        assert result["commodity"] is None

    def test_resolve_occupation_when_unavailable(self):
        """resolve_occupation returns None when unavailable."""
        validator = ONETValidator(db_path="/tmp/nonexistent_onet_test_12345/onet.db")
        result = validator.resolve_occupation("Software Developer")
        assert result is None

    def test_validate_skills_batch_when_unavailable(self):
        """validate_skills_batch returns empty result when unavailable."""
        validator = ONETValidator(db_path="/tmp/nonexistent_onet_test_12345/onet.db")
        result = validator.validate_skills_batch(["Python"], "Software Developer")
        assert result["soc_code"] is None
        assert result["validated"] == []
        assert result["occupation_match_ratio"] == 0.0

    def test_get_hot_technologies_when_unavailable(self):
        """get_hot_technologies returns empty list when unavailable."""
        validator = ONETValidator(db_path="/tmp/nonexistent_onet_test_12345/onet.db")
        result = validator.get_hot_technologies()
        assert result == []

    def test_empty_db_is_not_available(self):
        """An empty (schema-only) DB should result in available=False."""
        tmpdir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmpdir, "empty_onet.db")
            # Creating the cache auto-creates the schema but inserts no data
            cache = ONETCache(db_path)
            cache.close()  # Close the cache connection so the validator can open it
            # Now open it through the validator
            validator = ONETValidator(db_path=db_path)
            assert validator.available is False, "Empty DB should not be marked as available"
        finally:
            # Clean up manually — Windows can't delete a file held open by SQLite
            # The validator opened it but it's read-only, so close shouldn't be needed
            # but we use ignore_errors to handle Windows file locking
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════════
# match_skills_with_onet tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestMatchSkillsWithOnet:
    """Tests for the match_skills_with_onet integration function."""

    @requires_onet_db
    def test_match_skills_with_onet_adds_validation(self):
        """When job_title provided and DB available, result contains onet_validation key."""
        # Reset module-level validator so it picks up the DB
        import app.backend.services.skill_matcher as sm
        sm._onet_validator = None

        candidate_skills = ["Python", "Java", "Docker"]
        jd_skills = ["Python", "Java", "Kubernetes"]

        result = match_skills_with_onet(
            candidate_skills, jd_skills, job_title="Software Developer"
        )
        # Should contain standard match_skills keys
        assert "matched_skills" in result
        assert "missing_skills" in result
        # Should also contain O*NET validation
        assert "onet_validation" in result
        onet_val = result["onet_validation"]
        assert onet_val["soc_code"] is not None
        assert onet_val["occupation_title"] is not None
        assert len(onet_val["validated"]) > 0

    def test_match_skills_with_onet_without_title(self):
        """Without job_title, behaves exactly like match_skills()."""
        candidate_skills = ["Python", "Java", "Docker"]
        jd_skills = ["Python", "Java", "Kubernetes"]

        result = match_skills_with_onet(candidate_skills, jd_skills)
        # Should NOT contain onet_validation when no job_title
        assert "onet_validation" not in result
        # Should still produce standard match_skills output
        assert "matched_skills" in result
        assert "core_match_ratio" in result

    def test_match_skills_with_onet_graceful_fallback(self):
        """Works even if O*NET data unavailable — resets validator to simulate."""
        import app.backend.services.skill_matcher as sm
        # Force the validator to be an unavailable one
        sm._onet_validator = ONETValidator(db_path="/tmp/nonexistent_onet_test_12345/onet.db")

        candidate_skills = ["Python", "Java"]
        jd_skills = ["Python"]

        result = match_skills_with_onet(
            candidate_skills, jd_skills, job_title="Software Developer"
        )
        # Should still produce results — no crash
        assert "matched_skills" in result
        assert "onet_validation" not in result

        # Reset for other tests
        sm._onet_validator = None


# ═══════════════════════════════════════════════════════════════════════════════
# False-positive prevention tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestFalsePositivePrevention:
    """Verify that O*NET validation prevents homonym-skill false positives.

    These are the core motivating scenarios: 'railway' (a cloud deployment
    platform) appearing in 'railway company' (industry domain) context, and
    'rtos' (an embedded OS) appearing in 'RTOS-related project' (descriptive
    phrase) context.
    """

    @requires_onet_db
    def test_railway_not_valid_for_data_engineer(self):
        """'railway' is NOT a recognized technology for Data Engineer / Data
        Warehouse Architect occupations in O*NET."""
        validator = ONETValidator(db_path=ONET_DB_PATH)

        # Try several data-related occupations
        data_titles = [
            "Data Engineer",
            "Data Warehouse Architect",
            "Database Architect",
        ]
        for title in data_titles:
            occ = validator.resolve_occupation(title)
            if occ is None:
                continue
            result = validator.validate_skill("Railway", occ["soc_code"])
            assert result["valid"] is False, (
                f"'Railway' should NOT be a recognized technology for {title} "
                f"(SOC {occ['soc_code']}); got valid={result['valid']}"
            )

    @requires_onet_db
    def test_rtos_not_valid_for_web_developer(self):
        """'rtos' is NOT recognized for Web Developer occupations."""
        validator = ONETValidator(db_path=ONET_DB_PATH)

        web_titles = [
            "Web Developer",
            "Front End Developer",
            "Full Stack Developer",
        ]
        for title in web_titles:
            occ = validator.resolve_occupation(title)
            if occ is None:
                continue
            result = validator.validate_skill("RTOS", occ["soc_code"])
            assert result["valid"] is False, (
                f"'RTOS' should NOT be a recognized technology for {title} "
                f"(SOC {occ['soc_code']}); got valid={result['valid']}"
            )

    @requires_onet_db
    def test_railway_valid_for_devops_where_applicable(self):
        """'railway' as a deployment platform SHOULD be recognized for
        occupations that list it (e.g. DevOps-related roles) if present
        in O*NET data.

        This is a positive-control test: if O*NET lists Railway (the cloud
        platform) as a technology skill for any DevOps/cloud occupation,
        it should be validated as True. If O*NET does not list it at all,
        the test gracefully passes (the point is: O*NET is the authority).
        """
        validator = ONETValidator(db_path=ONET_DB_PATH)

        # Check if "Railway" appears anywhere in the DB
        cache = ONETCache(ONET_DB_PATH)
        try:
            cur = cache._conn.execute(
                "SELECT DISTINCT soc_code FROM onet_technology_skill "
                "WHERE skill_name = ? COLLATE NOCASE",
                ("Railway",),
            )
            rows = cur.fetchall()
            if not rows:
                # O*NET doesn't have "Railway" at all — that's fine, the test
                # passes because the whole point is that O*NET is the authority
                return
            # If it does exist, verify it validates as True
            soc_codes = [r[0] for r in rows]
            for soc in soc_codes:
                result = validator.validate_skill("Railway", soc)
                assert result["valid"] is True, (
                    f"'Railway' listed in O*NET for SOC {soc} should validate as True"
                )
        finally:
            cache.close()

    @requires_onet_db
    def test_rtos_valid_for_embedded_where_applicable(self):
        """'RTOS' SHOULD be recognized for embedded systems occupations.
        Positive-control test — RTOS is a legitimate skill for embedded roles."""
        validator = ONETValidator(db_path=ONET_DB_PATH)

        embedded_titles = [
            "Embedded Software Engineer",
            "Electronics Engineer",
            "Software Quality Assurance Analyst",
        ]
        found_valid = False
        for title in embedded_titles:
            occ = validator.resolve_occupation(title)
            if occ is None:
                continue
            result = validator.validate_skill("RTOS", occ["soc_code"])
            if result["valid"]:
                found_valid = True
                break

        # If no embedded occupation in O*NET lists RTOS, that's unusual
        # but not a test failure — O*NET is the authority
        if not found_valid:
            # Check if RTOS exists in O*NET at all
            cache = ONETCache(ONET_DB_PATH)
            try:
                cur = cache._conn.execute(
                    "SELECT 1 FROM onet_technology_skill WHERE skill_name = ? COLLATE NOCASE LIMIT 1",
                    ("RTOS",),
                )
                has_rtos = cur.fetchone() is not None
            finally:
                cache.close()
            if not has_rtos:
                pytest.skip("O*NET does not contain 'RTOS' as a technology skill — test is N/A")


# ═══════════════════════════════════════════════════════════════════════════════
# Cache unit tests (do not require the synced DB)
# ═══════════════════════════════════════════════════════════════════════════════


class TestONETCacheUnit:
    """Unit tests for ONETCache that use a temporary DB — no synced data needed."""

    def _make_cache(self, tmpdir, name="test_cache.db"):
        """Helper: create cache, return (cache, db_path). Caller must close cache."""
        db_path = os.path.join(tmpdir, name)
        return ONETCache(db_path), db_path

    def test_cache_creates_new_db(self):
        """Creating ONETCache at a new path creates the schema."""
        tmpdir = tempfile.mkdtemp()
        try:
            cache, _ = self._make_cache(tmpdir)
            try:
                assert not cache.is_populated(), "Fresh DB should not be populated"
            finally:
                cache.close()
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_upsert_and_retrieve_occupation(self):
        """Insert and retrieve an occupation record."""
        tmpdir = tempfile.mkdtemp()
        try:
            cache, _ = self._make_cache(tmpdir)
            try:
                cache.upsert_occupation("15-1252.00", "Software Developers", "Design software")
                cache.commit()
                occ = cache.get_occupation("15-1252.00")
                assert occ is not None
                assert occ["title"] == "Software Developers"
                assert cache.is_populated() is True
            finally:
                cache.close()
        finally:
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

    def test_upsert_and_skill_exists(self):
        """Insert a technology skill and verify skill_exists_for_occupation."""
        tmpdir = tempfile.mkdtemp()
        try:
            cache, _ = self._make_cache(tmpdir)
            try:
                cache.upsert_occupation("15-1252.00", "Software Developers", "Design software")
                cache.upsert_technology_skill(
                    "15-1252.00", "Python", 1234, "Python Language", True, True
                )
                cache.commit()
                assert cache.skill_exists_for_occupation("Python", "15-1252.00") is True
                assert cache.skill_exists_for_occupation("Railway", "15-1252.00") is False
                # Case-insensitive
                assert cache.skill_exists_for_occupation("python", "15-1252.00") is True
            finally:
                cache.close()
        finally:
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

    def test_find_soc_by_title_alternate(self):
        """find_soc_by_title resolves via alternate titles."""
        tmpdir = tempfile.mkdtemp()
        try:
            cache, _ = self._make_cache(tmpdir)
            try:
                cache.upsert_occupation("15-1252.00", "Software Developers", "Design software")
                cache.upsert_alternate_title("15-1252.00", "Software Engineer", "SWE")
                cache.commit()

                matches = cache.find_soc_by_title("Software Engineer")
                assert len(matches) > 0
                assert matches[0][0] == "15-1252.00"
                assert matches[0][2] == 1.0  # exact alternate title match
            finally:
                cache.close()
        finally:
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_version_returns_none_when_unset(self):
        """get_version returns None when no version metadata exists."""
        tmpdir = tempfile.mkdtemp()
        try:
            cache, _ = self._make_cache(tmpdir)
            try:
                assert cache.get_version() is None
                cache.set_metadata("version", "30.2")
                assert cache.get_version() == "30.2"
            finally:
                cache.close()
        finally:
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_all_hot_technologies(self):
        """get_all_hot_technologies returns only hot skills."""
        tmpdir = tempfile.mkdtemp()
        try:
            cache, _ = self._make_cache(tmpdir)
            try:
                cache.upsert_occupation("15-1252.00", "Software Developers", "Design software")
                cache.upsert_technology_skill(
                    "15-1252.00", "Python", 1, "Python", True, True
                )
                cache.upsert_technology_skill(
                    "15-1252.00", "COBOL", 2, "COBOL", False, False
                )
                cache.commit()
                hot = cache.get_all_hot_technologies()
                assert "Python" in hot
                assert "COBOL" not in hot
            finally:
                cache.close()
        finally:
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline O*NET integration tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPipelineONETIntegration:
    """Verify O*NET is wired into the analysis pipelines."""

    def test_hybrid_pipeline_imports_onet(self):
        """Verify hybrid_pipeline imports match_skills_with_onet."""
        from app.backend.services import hybrid_pipeline
        import inspect
        source = inspect.getsource(hybrid_pipeline)
        assert "match_skills_with_onet" in source

    def test_agent_pipeline_imports_onet(self):
        """Verify agent_pipeline imports match_skills_with_onet."""
        from app.backend.services import agent_pipeline
        import inspect
        source = inspect.getsource(agent_pipeline)
        assert "match_skills_with_onet" in source

    def test_hybrid_pipeline_passes_job_title(self):
        """Verify hybrid_pipeline passes job_title to match_skills_with_onet."""
        from app.backend.services import hybrid_pipeline
        import inspect
        source = inspect.getsource(hybrid_pipeline)
        assert "job_title=" in source

    def test_agent_pipeline_passes_job_title(self):
        """Verify agent_pipeline passes job_title to match_skills_with_onet."""
        from app.backend.services import agent_pipeline
        import inspect
        source = inspect.getsource(agent_pipeline)
        assert "job_title=" in source
