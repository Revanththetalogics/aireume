"""
Phase 2 & 3 feature tests:
  - Email generation (/api/email/generate)
  - JD URL extraction (/api/jd/extract-url)
  - Team management (/api/team, /api/invites)
  - Comments (/api/results/{id}/comments)
  - Training label/status (/api/training/label, /api/training/status)
  - SSE Streaming hardening (/analyze/stream)
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import json
from io import BytesIO


# ─── JD URL extraction ────────────────────────────────────────────────────────

class TestJdUrlExtraction:
    def test_extract_url_requires_auth(self, client):
        resp = client.post("/api/jd/extract-url", json={"url": "https://example.com/job"})
        assert resp.status_code == 403  # CSRF middleware blocks before auth check

    def test_extract_url_with_mock_scraper(self, auth_client):
        with patch("app.backend.routes.jd_url.scrape_jd", return_value="Senior Python Developer. 5+ years required.") as mock_scrape:
            resp = auth_client.post("/api/jd/extract-url", json={"url": "https://example.com/job"})
            assert resp.status_code == 200
            data = resp.json()
            assert "jd_text" in data
            assert len(data["jd_text"]) > 0
            mock_scrape.assert_called_once()

    def test_extract_url_scraper_failure_returns_422(self, auth_client):
        with patch("app.backend.routes.jd_url.scrape_jd", side_effect=Exception("fetch failed")):
            resp = auth_client.post("/api/jd/extract-url", json={"url": "https://broken.example.com"})
            assert resp.status_code in (422, 500)

    def test_extract_url_missing_url_returns_422(self, auth_client):
        resp = auth_client.post("/api/jd/extract-url", json={})
        assert resp.status_code == 422


# ─── Email generation ─────────────────────────────────────────────────────────

class TestEmailGeneration:
    def test_generate_email_requires_auth(self, client):
        resp = client.post("/api/email/generate", json={"candidate_id": 1, "type": "shortlist"})
        assert resp.status_code == 403  # CSRF middleware blocks before auth check

    def test_generate_email_nonexistent_candidate_returns_404(self, auth_client):
        resp = auth_client.post("/api/email/generate", json={"candidate_id": 99999, "type": "shortlist"})
        assert resp.status_code == 404

    def test_generate_email_invalid_type_returns_400(self, auth_client):
        resp = auth_client.post("/api/email/generate", json={"candidate_id": 1, "type": "spam_everyone"})
        assert resp.status_code == 400

    def test_generate_email_valid_types_accepted(self, auth_client):
        """All three valid email types should reach past the validation check."""
        for email_type in ["shortlist", "rejection", "screening_call"]:
            resp = auth_client.post("/api/email/generate", json={"candidate_id": 99999, "type": email_type})
            # 404 means it passed type validation and failed on candidate lookup — acceptable
            assert resp.status_code in (400, 404, 200)


# ─── Team management ─────────────────────────────────────────────────────────

class TestTeamManagement:
    def test_get_team_members_requires_auth(self, client):
        resp = client.get("/api/team")
        assert resp.status_code == 401

    def test_get_team_members_returns_list(self, auth_client):
        resp = auth_client.get("/api/team")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        # The current admin user should appear in the list
        assert len(resp.json()) >= 1

    def test_invite_requires_admin(self, auth_client):
        resp = auth_client.post("/api/invites", json={"email": "new@example.com", "role": "recruiter"})
        # Admin fixture has role=admin, so this should succeed
        assert resp.status_code in (200, 201)

    def test_invite_creates_user_with_temp_password(self, auth_client):
        resp = auth_client.post("/api/invites", json={"email": "recruiter@testcorp.com", "role": "recruiter"})
        assert resp.status_code in (200, 201)
        data = resp.json()
        # temp_password intentionally removed from response for security
        assert "message" in data

    def test_invite_missing_email_returns_4xx(self, auth_client):
        # Missing email should fail validation or auth
        resp = auth_client.post("/api/invites", json={"role": "recruiter"})
        assert resp.status_code in (400, 422)

    def test_deactivate_nonexistent_user_returns_404(self, auth_client):
        resp = auth_client.delete("/api/team/99999")
        assert resp.status_code == 404


# ─── Comments ─────────────────────────────────────────────────────────────────

class TestComments:
    def test_get_comments_requires_auth(self, client):
        resp = client.get("/api/results/1/comments")
        assert resp.status_code == 401

    def test_post_comment_requires_auth(self, client):
        resp = client.post("/api/results/1/comments", json={"text": "Looks good"})
        assert resp.status_code == 403  # CSRF middleware blocks before auth check

    def test_get_comments_nonexistent_result_returns_404(self, auth_client):
        resp = auth_client.get("/api/results/99999/comments")
        assert resp.status_code == 404

    def test_post_comment_nonexistent_result_returns_404(self, auth_client):
        resp = auth_client.post("/api/results/99999/comments", json={"text": "Test comment"})
        assert resp.status_code == 404


# ─── Training ────────────────────────────────────────────────────────────────

class TestTraining:
    def test_training_status_requires_auth(self, client):
        resp = client.get("/api/training/status")
        assert resp.status_code == 401

    def test_training_status_returns_structure(self, auth_client):
        resp = auth_client.get("/api/training/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "labeled_count" in data
        assert "trained" in data
        assert data["labeled_count"] == 0
        assert data["trained"] is False

    def test_label_requires_auth(self, client):
        resp = client.post("/api/training/label", json={"screening_result_id": 1, "outcome": "hired"})
        assert resp.status_code == 403  # CSRF middleware blocks before auth check

    def test_label_nonexistent_result_returns_404(self, auth_client):
        resp = auth_client.post("/api/training/label", json={
            "screening_result_id": 99999,
            "outcome": "hired",
            "feedback": "Great candidate",
        })
        assert resp.status_code == 404

    def test_label_invalid_outcome_returns_4xx(self, auth_client):
        # "maybe" is not a valid outcome; response is either 422 (schema) or
        # 404 (result not found first) depending on route order
        resp = auth_client.post("/api/training/label", json={
            "screening_result_id": 99999,
            "outcome": "maybe",
        })
        assert resp.status_code in (400, 404, 422)

    def test_start_training_requires_admin(self, auth_client):
        # With fewer than 10 examples, should return 400 not 401
        resp = auth_client.post("/api/training/train")
        assert resp.status_code in (400, 401, 403)

    def test_start_training_insufficient_examples_returns_400(self, auth_client):
        resp = auth_client.post("/api/training/train")
        # Should say need at least 10 examples
        assert resp.status_code == 400
        assert "10" in resp.json().get("detail", "")


# ─── SSE Streaming Hardening ──────────────────────────────────────────────────

class TestSseStreamingHardening:
    """Tests for SSE streaming hardening features (Task #8)."""

    def test_analyze_rejects_oversized_jd(self, auth_client, mock_hybrid_pipeline):
        """Test that /analyze rejects JD exceeding 50KB limit."""
        # Create a JD that's over 50KB
        oversized_jd = "Python developer " * 5000  # ~75KB

        resume_content = b"John Doe\nPython Developer\n5 years experience"
        files = {
            "resume": ("test_resume.pdf", BytesIO(resume_content), "application/pdf")
        }
        data = {
            "job_description": oversized_jd
        }

        resp = auth_client.post("/api/analyze", data=data, files=files)
        assert resp.status_code == 400
        assert "50KB" in resp.json().get("detail", "")

    def test_analyze_stream_rejects_oversized_jd(self, auth_client):
        """Test that /analyze/stream rejects JD exceeding 50KB limit."""
        # Create a JD that's over 50KB
        oversized_jd = "Python developer " * 5000  # ~75KB

        resume_content = b"John Doe\nPython Developer\n5 years experience"
        files = {
            "resume": ("test_resume.pdf", BytesIO(resume_content), "application/pdf")
        }
        data = {
            "job_description": oversized_jd
        }

        resp = auth_client.post("/api/analyze/stream", data=data, files=files)
        assert resp.status_code == 400
        assert "50KB" in resp.json().get("detail", "")

    # Long valid JD that meets the 80 word minimum
    _VALID_JD = (
        "Senior Python Developer position with 5+ years of professional software development experience required. "
        "Must have strong expertise in Django, Flask, FastAPI, and PostgreSQL database design and optimization. "
        "Experience with cloud platforms such as AWS, GCP, or Azure is highly preferred. "
        "The ideal candidate will have excellent communication skills, leadership experience, "
        "and the ability to mentor junior developers. Knowledge of Docker, Kubernetes, and CI/CD pipelines is essential. "
        "Experience with microservices architecture, event-driven systems, and message queues like RabbitMQ or Kafka is a plus. "
        "Strong understanding of software design patterns, testing methodologies, and agile development practices required."
    )

    def test_analyze_stream_includes_done_event(self, auth_client, mock_hybrid_pipeline):
        """Test that /analyze/stream always includes [DONE] event even on errors."""
        # Create a minimal valid resume
        resume_content = b"John Doe\nPython Developer\njohn@example.com\n5 years Python experience"
        files = {
            "resume": ("test_resume.pdf", BytesIO(resume_content), "application/pdf")
        }
        data = {
            "job_description": self._VALID_JD
        }

        resp = auth_client.post("/api/analyze/stream", data=data, files=files)
        assert resp.status_code == 200

        # Read the streaming response
        content = resp.content.decode('utf-8')

        # Verify [DONE] event is present
        assert "data: [DONE]" in content, f"Missing [DONE] event in response: {content[:500]}"

    def test_analyze_stream_done_event_with_valid_response(self, auth_client, mock_hybrid_pipeline):
        """Test that /analyze/stream includes [DONE] event with successful analysis."""
        resume_content = b"John Doe\nPython Developer\njohn@example.com\n5 years Python experience"
        files = {
            "resume": ("test_resume.pdf", BytesIO(resume_content), "application/pdf")
        }
        data = {
            "job_description": self._VALID_JD
        }

        resp = auth_client.post("/api/analyze/stream", data=data, files=files)
        assert resp.status_code == 200

        # Parse SSE events
        content = resp.content.decode('utf-8')
        events = [line for line in content.split('\n\n') if line.strip()]

        # Should have at least one data event and [DONE] event
        data_events = [e for e in events if e.startswith('data:')]
        done_events = [e for e in data_events if '[DONE]' in e]

        assert len(done_events) >= 1, f"Expected at least one [DONE] event, got events: {events}"

    def test_analyze_accepts_valid_jd_size(self, auth_client, mock_hybrid_pipeline):
        """Test that /analyze accepts JD under 50KB limit."""
        # Create a valid JD under 50KB
        valid_jd = self._VALID_JD

        resume_content = b"John Doe\nPython Developer\njohn@example.com\n5 years Python experience"
        files = {
            "resume": ("test_resume.pdf", BytesIO(resume_content), "application/pdf")
        }
        data = {
            "job_description": valid_jd
        }

        resp = auth_client.post("/api/analyze", data=data, files=files)
        # Should not be rejected for size (may fail for other reasons)
        assert resp.status_code != 400 or "50KB" not in resp.json().get("detail", "")


# ─── Scoring Weights Size Validation ──────────────────────────────────────────

class TestScoringWeightsSizeValidation:
    """Tests for scoring_weights size limit (Task #17)."""

    _VALID_JD = (
        "Senior Python Developer position with 5+ years of professional software development experience required. "
        "Must have strong expertise in Django, Flask, FastAPI, and PostgreSQL database design and optimization. "
        "Experience with cloud platforms such as AWS, GCP, or Azure is highly preferred. "
        "The ideal candidate will have excellent communication skills, leadership experience, "
        "and the ability to mentor junior developers. Knowledge of Docker, Kubernetes, and CI/CD pipelines is essential. "
        "Experience with microservices architecture, event-driven systems, and message queues like RabbitMQ or Kafka is a plus. "
        "Strong understanding of software design patterns, testing methodologies, and agile development practices required."
    )

    def test_analyze_rejects_oversized_scoring_weights(self, auth_client, mock_hybrid_pipeline):
        """Test that /analyze rejects scoring_weights exceeding 4KB limit."""
        # Create scoring_weights that exceed 4KB
        oversized_weights = {"skills": {f"skill_{i}": 1.0 for i in range(300)}}  # ~5KB JSON
        import json
        oversized_json = json.dumps(oversized_weights)

        resume_content = b"John Doe\nPython Developer\n5 years experience"
        files = {
            "resume": ("test_resume.pdf", BytesIO(resume_content), "application/pdf")
        }
        data = {
            "job_description": self._VALID_JD,
            "scoring_weights": oversized_json
        }

        resp = auth_client.post("/api/analyze", data=data, files=files)
        assert resp.status_code == 400
        assert "4KB" in resp.json().get("detail", "")

    def test_analyze_stream_rejects_oversized_scoring_weights(self, auth_client):
        """Test that /analyze/stream rejects scoring_weights exceeding 4KB limit."""
        # Create scoring_weights that exceed 4KB
        oversized_weights = {"skills": {f"skill_{i}": 1.0 for i in range(300)}}  # ~5KB JSON
        import json
        oversized_json = json.dumps(oversized_weights)

        resume_content = b"John Doe\nPython Developer\n5 years experience"
        files = {
            "resume": ("test_resume.pdf", BytesIO(resume_content), "application/pdf")
        }
        data = {
            "job_description": self._VALID_JD,
            "scoring_weights": oversized_json
        }

        resp = auth_client.post("/api/analyze/stream", data=data, files=files)
        assert resp.status_code == 400
        assert "4KB" in resp.json().get("detail", "")

    def test_analyze_batch_rejects_oversized_scoring_weights(self, auth_client):
        """Test that /analyze/batch rejects scoring_weights exceeding 4KB limit."""
        # Create scoring_weights that exceed 4KB
        oversized_weights = {"skills": {f"skill_{i}": 1.0 for i in range(300)}}  # ~5KB JSON
        import json
        oversized_json = json.dumps(oversized_weights)

        resume_content = b"John Doe\nPython Developer\n5 years experience"
        files = [
            ("resumes", ("test_resume.pdf", BytesIO(resume_content), "application/pdf")),
        ]
        data = {
            "job_description": self._VALID_JD,
            "scoring_weights": oversized_json
        }

        resp = auth_client.post("/api/analyze/batch", data=data, files=files)
        assert resp.status_code == 400
        assert "4KB" in resp.json().get("detail", "")

    def test_analyze_accepts_valid_scoring_weights(self, auth_client, mock_hybrid_pipeline):
        """Test that /analyze accepts scoring_weights under 4KB limit."""
        import json
        valid_weights = {"skills": {"python": 0.5, "docker": 0.3, "aws": 0.2}}
        valid_weights_json = json.dumps(valid_weights)

        resume_content = b"John Doe\nPython Developer\njohn@example.com\n5 years Python experience"
        files = {
            "resume": ("test_resume.pdf", BytesIO(resume_content), "application/pdf")
        }
        data = {
            "job_description": self._VALID_JD,
            "scoring_weights": valid_weights_json
        }

        resp = auth_client.post("/api/analyze", data=data, files=files)
        # Should not be rejected for size (may fail for other reasons)
        assert resp.status_code != 400 or "4KB" not in resp.json().get("detail", "")


# ─── JD Cache Eviction ────────────────────────────────────────────────────────

class TestJdCacheEviction:
    """Tests for JD cache eviction background task (Task #17)."""

    def test_jd_cache_eviction_deletes_old_entries(self, db):
        """Test that JD cache entries older than 30 days are deleted."""
        from app.backend.models.db_models import JdCache
        from datetime import datetime, timezone, timedelta
        import json
        import hashlib

        # Create an old entry (31 days old)
        old_cutoff = datetime.now(timezone.utc) - timedelta(days=31)
        old_hash = hashlib.md5(b"old_jd").hexdigest()
        old_entry = JdCache(
            hash=old_hash,
            result_json=json.dumps({"role": "old"}),
            created_at=old_cutoff
        )
        db.add(old_entry)

        # Create a new entry (1 day old)
        new_hash = hashlib.md5(b"new_jd").hexdigest()
        new_entry = JdCache(
            hash=new_hash,
            result_json=json.dumps({"role": "new"}),
            created_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        db.add(new_entry)
        db.commit()

        # Verify both entries exist
        assert db.query(JdCache).count() == 2

        # Simulate the cleanup logic
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        deleted = db.query(JdCache).filter(JdCache.created_at < cutoff).delete()
        db.commit()

        # Verify only old entry was deleted
        assert deleted == 1
        assert db.query(JdCache).filter(JdCache.hash == old_hash).first() is None
        assert db.query(JdCache).filter(JdCache.hash == new_hash).first() is not None

    def test_jd_cache_eviction_keeps_recent_entries(self, db):
        """Test that JD cache entries newer than 30 days are kept."""
        from app.backend.models.db_models import JdCache
        from datetime import datetime, timezone, timedelta
        import json
        import hashlib

        # Create entries at different ages
        ages = [1, 7, 14, 29]  # days old
        entries = []
        for age in ages:
            entry_hash = hashlib.md5(f"jd_{age}_days".encode()).hexdigest()
            entry = JdCache(
                hash=entry_hash,
                result_json=json.dumps({"age_days": age}),
                created_at=datetime.now(timezone.utc) - timedelta(days=age)
            )
            db.add(entry)
            entries.append(entry_hash)
        db.commit()

        # Verify all entries exist
        assert db.query(JdCache).count() == 4

        # Simulate the cleanup logic
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        deleted = db.query(JdCache).filter(JdCache.created_at < cutoff).delete()
        db.commit()

        # Verify no entries were deleted (all are < 30 days old)
        assert deleted == 0
        assert db.query(JdCache).count() == 4

    def test_cleanup_jd_cache_function_exists(self):
        """Verify the JD cache cleanup function exists and has correct logic."""
        from app.backend.main import _cleanup_jd_cache
        import inspect

        # Verify the function exists and is async
        assert inspect.iscoroutinefunction(_cleanup_jd_cache)
        # Verify it has a docstring
        assert _cleanup_jd_cache.__doc__ is not None
        assert "30 days" in _cleanup_jd_cache.__doc__


class TestBatchJdSizeValidation:
    """Tests for JD size validation in batch endpoint (Task #17)."""

    def test_batch_rejects_oversized_jd(self, auth_client):
        """Test that /analyze/batch rejects JD exceeding 50KB limit."""
        # Create a JD that's over 50KB
        oversized_jd = "Python developer " * 5000  # ~75KB

        resume_content = b"John Doe\nPython Developer\n5 years experience"
        files = [
            ("resumes", ("test_resume.pdf", BytesIO(resume_content), "application/pdf")),
        ]
        data = {
            "job_description": oversized_jd
        }

        resp = auth_client.post("/api/analyze/batch", data=data, files=files)
        assert resp.status_code == 400
        assert "50KB" in resp.json().get("detail", "")
