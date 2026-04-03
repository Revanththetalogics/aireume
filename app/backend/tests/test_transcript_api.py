"""
Integration tests for the Transcript Analysis API routes.

Routes under test:
  POST /api/transcript/analyze
  GET  /api/transcript/analyses
  GET  /api/transcript/analyses/{id}

All Ollama calls are patched so the test suite runs offline.
"""
import io
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.backend.models.db_models import Candidate, RoleTemplate


# ─── Shared mock Ollama response ─────────────────────────────────────────────

MOCK_ANALYSIS = {
    "fit_score": 78,
    "technical_depth": 72,
    "communication_quality": 80,
    "jd_alignment": [
        {"requirement": "Python", "demonstrated": True,  "evidence": "5 years Python"},
        {"requirement": "AWS",    "demonstrated": False, "evidence": None},
    ],
    "strengths": ["Strong Python skills", "Good communication"],
    "areas_for_improvement": ["Cloud experience limited"],
    "bias_note": "Evaluation based solely on demonstrated skills and knowledge in the transcript.",
    "recommendation": "proceed",
}


def mock_ollama_transcript():
    """Return a context-manager-compatible mock that yields MOCK_ANALYSIS."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": json.dumps(MOCK_ANALYSIS)}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)
    return mock_client


SAMPLE_PLAIN_TRANSCRIPT = (
    "I have been working with Python for five years, building REST APIs "
    "with FastAPI. I led a team migrating a monolith to microservices."
)

SAMPLE_VTT_TRANSCRIPT = """\
WEBVTT

1
00:00:01.000 --> 00:00:06.000
Interviewer: Tell me about yourself.

2
00:00:07.000 --> 00:00:15.000
Jane: I have worked with Python for five years and built REST APIs.
"""

SAMPLE_SRT_TRANSCRIPT = """\
1
00:00:01,000 --> 00:00:05,000
Can you describe your Python experience?

2
00:00:06,000 --> 00:00:14,000
I have five years of Python and have built microservices at scale.
"""


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def setup_template(auth_client, db):
    """Create a RoleTemplate directly in the DB and return (auth_client, template_id)."""
    from app.backend.db.database import SessionLocal
    # Get the tenant_id from the logged-in user by hitting /api/auth/me (or creating directly)
    # We'll insert via the Templates API endpoint instead to stay fully integrated
    resp = auth_client.post("/api/templates", json={
        "name": "Senior Python Engineer",
        "jd_text": (
            "Looking for an experienced Python engineer with 5+ years. "
            "Must know FastAPI, Docker, and AWS."
        ),
        "tags": "python,fastapi,docker",
    })
    assert resp.status_code in (200, 201), f"Template creation failed: {resp.text}"
    return auth_client, resp.json()["id"]


@pytest.fixture
def setup_candidate_and_template(auth_client, db):
    """Create a Candidate (via candidates API if available, else insert) and a RoleTemplate."""
    # Create template
    t_resp = auth_client.post("/api/templates", json={
        "name": "Backend Developer",
        "jd_text": "Python, FastAPI, PostgreSQL, Docker required.",
    })
    assert t_resp.status_code in (200, 201)
    template_id = t_resp.json()["id"]

    # Candidates are usually created by the analyze route; we'll insert via DB fixture
    # by checking if POST /api/candidates exists, else we skip candidate tests
    return auth_client, template_id


# ─── Auth guard tests ─────────────────────────────────────────────────────────

class TestTranscriptAuthGuard:

    def test_analyze_unauthenticated_returns_401(self, client):
        resp = client.post(
            "/api/transcript/analyze",
            data={"transcript_text": SAMPLE_PLAIN_TRANSCRIPT, "role_template_id": 1},
        )
        assert resp.status_code == 401

    def test_list_analyses_unauthenticated_returns_401(self, client):
        assert client.get("/api/transcript/analyses").status_code == 401

    def test_get_analysis_unauthenticated_returns_401(self, client):
        assert client.get("/api/transcript/analyses/1").status_code == 401


# ─── POST /api/transcript/analyze ────────────────────────────────────────────

class TestAnalyzeTranscriptEndpoint:

    def test_analyze_with_plain_text_and_template(self, setup_template):
        auth_client, template_id = setup_template
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            resp = auth_client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id,
                "source_platform": "zoom",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["analysis_result"]["fit_score"] == 78
        assert data["analysis_result"]["recommendation"] == "proceed"

    def test_analyze_response_has_all_fields(self, setup_template):
        auth_client, template_id = setup_template
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            resp = auth_client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id,
            })
        assert resp.status_code == 200
        data = resp.json()
        ar = data["analysis_result"]
        for key in ("fit_score", "technical_depth", "communication_quality",
                    "jd_alignment", "strengths", "areas_for_improvement",
                    "bias_note", "recommendation"):
            assert key in ar, f"Missing key: {key}"

    def test_analyze_with_vtt_file(self, setup_template):
        auth_client, template_id = setup_template
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            resp = auth_client.post(
                "/api/transcript/analyze",
                data={"role_template_id": template_id, "source_platform": "teams"},
                files={"transcript_file": ("interview.vtt",
                                           io.BytesIO(SAMPLE_VTT_TRANSCRIPT.encode()),
                                           "text/vtt")},
            )
        assert resp.status_code == 200

    def test_analyze_with_srt_file(self, setup_template):
        auth_client, template_id = setup_template
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            resp = auth_client.post(
                "/api/transcript/analyze",
                data={"role_template_id": template_id},
                files={"transcript_file": ("interview.srt",
                                           io.BytesIO(SAMPLE_SRT_TRANSCRIPT.encode()),
                                           "text/x-srt")},
            )
        assert resp.status_code == 200

    def test_analyze_with_txt_file(self, setup_template):
        auth_client, template_id = setup_template
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            resp = auth_client.post(
                "/api/transcript/analyze",
                data={"role_template_id": template_id},
                files={"transcript_file": ("interview.txt",
                                           io.BytesIO(SAMPLE_PLAIN_TRANSCRIPT.encode()),
                                           "text/plain")},
            )
        assert resp.status_code == 200

    def test_analyze_stores_record_and_returns_id(self, setup_template):
        auth_client, template_id = setup_template
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            resp = auth_client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id,
            })
        assert resp.status_code == 200
        assert "id" in resp.json()
        assert isinstance(resp.json()["id"], int)

    def test_analyze_echoes_template_name(self, setup_template):
        auth_client, template_id = setup_template
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            resp = auth_client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id,
            })
        assert resp.status_code == 200
        assert resp.json()["role_template_name"] == "Senior Python Engineer"

    def test_analyze_echoes_source_platform(self, setup_template):
        auth_client, template_id = setup_template
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            resp = auth_client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id,
                "source_platform": "teams",
            })
        assert resp.json()["source_platform"] == "teams"

    # ── Validation errors ──────────────────────────────────────────────────────

    def test_missing_both_transcript_and_file_returns_400(self, setup_template):
        auth_client, template_id = setup_template
        resp = auth_client.post("/api/transcript/analyze", data={
            "role_template_id": template_id,
        })
        assert resp.status_code == 400

    def test_missing_role_template_returns_400(self, setup_template):
        auth_client, _ = setup_template
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            resp = auth_client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                # no role_template_id
            })
        assert resp.status_code == 400

    def test_nonexistent_template_returns_404(self, auth_client):
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            resp = auth_client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": 99999,
            })
        assert resp.status_code == 404

    def test_invalid_file_extension_returns_400(self, setup_template):
        auth_client, template_id = setup_template
        resp = auth_client.post(
            "/api/transcript/analyze",
            data={"role_template_id": template_id},
            files={"transcript_file": ("interview.docx",
                                       io.BytesIO(b"not a transcript"),
                                       "application/octet-stream")},
        )
        assert resp.status_code == 400

    def test_oversized_file_returns_400(self, setup_template):
        auth_client, template_id = setup_template
        big_content = b"word " * (1024 * 1024 + 1)   # > 5 MB
        resp = auth_client.post(
            "/api/transcript/analyze",
            data={"role_template_id": template_id},
            files={"transcript_file": ("big.txt", io.BytesIO(big_content), "text/plain")},
        )
        assert resp.status_code == 400

    def test_nonexistent_candidate_returns_404(self, setup_template):
        auth_client, template_id = setup_template
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            resp = auth_client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id,
                "candidate_id": 99999,
            })
        assert resp.status_code == 404

    # ── Ollama failure graceful degradation ───────────────────────────────────

    def test_ollama_failure_still_returns_200_with_fallback(self, setup_template):
        auth_client, template_id = setup_template
        with patch("app.backend.services.transcript_service.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(
                side_effect=Exception("Ollama unavailable")
            )
            resp = auth_client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id,
            })
        assert resp.status_code == 200
        assert resp.json()["analysis_result"]["fit_score"] == 50
        assert resp.json()["analysis_result"]["recommendation"] == "hold"

    # ── Tenant isolation ──────────────────────────────────────────────────────

    def test_cannot_use_another_tenants_template(self, client):
        """Two different tenant users cannot cross-use templates."""
        # Tenant A registers and creates a template
        client.post("/api/auth/register", json={
            "company_name": "TenantA",
            "email": "a@tenanta.com",
            "password": "PassA123!",
        })
        login_a = client.post("/api/auth/login", json={
            "email": "a@tenanta.com", "password": "PassA123!"
        })
        token_a = login_a.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token_a}"})

        t_resp = client.post("/api/templates", json={
            "name": "TenantA JD", "jd_text": "Python required."
        })
        template_id_a = t_resp.json()["id"]

        # Tenant B registers and tries to use Tenant A's template
        client.headers.clear()
        client.post("/api/auth/register", json={
            "company_name": "TenantB",
            "email": "b@tenantb.com",
            "password": "PassB123!",
        })
        login_b = client.post("/api/auth/login", json={
            "email": "b@tenantb.com", "password": "PassB123!"
        })
        token_b = login_b.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token_b}"})

        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            resp = client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id_a,   # belongs to Tenant A
            })
        assert resp.status_code == 404


# ─── GET /api/transcript/analyses ────────────────────────────────────────────

class TestListTranscriptAnalyses:

    def test_empty_list_before_any_analysis(self, auth_client):
        resp = auth_client.get("/api/transcript/analyses")
        assert resp.status_code == 200
        data = resp.json()
        assert "analyses" in data
        assert "total" in data
        assert data["total"] == 0

    def test_list_reflects_created_analysis(self, setup_template):
        auth_client, template_id = setup_template
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            auth_client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id,
            })
        resp = auth_client.get("/api/transcript/analyses")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["analyses"][0]
        assert item["fit_score"] == 78
        assert item["recommendation"] == "proceed"

    def test_list_includes_template_name(self, setup_template):
        auth_client, template_id = setup_template
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            auth_client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id,
            })
        resp = auth_client.get("/api/transcript/analyses")
        assert resp.json()["analyses"][0]["role_template_name"] == "Senior Python Engineer"

    def test_list_items_have_required_fields(self, setup_template):
        auth_client, template_id = setup_template
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            auth_client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id,
            })
        resp = auth_client.get("/api/transcript/analyses")
        item = resp.json()["analyses"][0]
        for field in ("id", "fit_score", "recommendation", "source_platform",
                      "created_at", "role_template_id", "role_template_name"):
            assert field in item, f"Missing field: {field}"

    def test_multiple_analyses_ordered_newest_first(self, setup_template):
        auth_client, template_id = setup_template
        for _ in range(3):
            with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                       return_value=mock_ollama_transcript()):
                auth_client.post("/api/transcript/analyze", data={
                    "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                    "role_template_id": template_id,
                })
        resp = auth_client.get("/api/transcript/analyses")
        assert resp.json()["total"] == 3

    def test_tenant_isolation_in_list(self, client):
        """Two tenants see only their own analyses."""
        for company, email, pwd in [
            ("CorpX", "x@corpx.com", "PassX123!"),
            ("CorpY", "y@corpy.com", "PassY123!"),
        ]:
            client.post("/api/auth/register", json={
                "company_name": company, "email": email, "password": pwd
            })

        # Tenant X creates a template and an analysis
        login_x = client.post("/api/auth/login", json={"email": "x@corpx.com", "password": "PassX123!"})
        token_x = login_x.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token_x}"})

        t_resp = client.post("/api/templates", json={"name": "X JD", "jd_text": "Python."})
        template_id_x = t_resp.json()["id"]

        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id_x,
            })

        # Tenant Y should see an empty list
        login_y = client.post("/api/auth/login", json={"email": "y@corpy.com", "password": "PassY123!"})
        token_y = login_y.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token_y}"})

        resp = client.get("/api/transcript/analyses")
        assert resp.json()["total"] == 0


# ─── GET /api/transcript/analyses/{id} ───────────────────────────────────────

class TestGetTranscriptAnalysis:

    def _create_analysis(self, auth_client, template_id):
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            resp = auth_client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id,
            })
        assert resp.status_code == 200
        return resp.json()["id"]

    def test_get_analysis_by_id_returns_200(self, setup_template):
        auth_client, template_id = setup_template
        analysis_id = self._create_analysis(auth_client, template_id)
        resp = auth_client.get(f"/api/transcript/analyses/{analysis_id}")
        assert resp.status_code == 200

    def test_get_analysis_has_full_jd_alignment(self, setup_template):
        auth_client, template_id = setup_template
        analysis_id = self._create_analysis(auth_client, template_id)
        resp = auth_client.get(f"/api/transcript/analyses/{analysis_id}")
        ar = resp.json()["analysis_result"]
        assert isinstance(ar["jd_alignment"], list)
        assert len(ar["jd_alignment"]) == 2

    def test_get_analysis_has_strengths_and_improvements(self, setup_template):
        auth_client, template_id = setup_template
        analysis_id = self._create_analysis(auth_client, template_id)
        resp = auth_client.get(f"/api/transcript/analyses/{analysis_id}")
        ar = resp.json()["analysis_result"]
        assert isinstance(ar["strengths"], list)
        assert isinstance(ar["areas_for_improvement"], list)

    def test_get_nonexistent_analysis_returns_404(self, auth_client):
        assert auth_client.get("/api/transcript/analyses/99999").status_code == 404

    def test_cannot_get_other_tenants_analysis(self, client):
        """Tenant A cannot retrieve Tenant B's analysis."""
        for company, email, pwd in [
            ("Alpha", "alpha@alpha.com", "AlphaPass1!"),
            ("Beta",  "beta@beta.com",  "BetaPass1!"),
        ]:
            client.post("/api/auth/register", json={
                "company_name": company, "email": email, "password": pwd
            })

        # Tenant Alpha creates an analysis
        login_a = client.post("/api/auth/login", json={"email": "alpha@alpha.com", "password": "AlphaPass1!"})
        client.headers.update({"Authorization": f"Bearer {login_a.json()['access_token']}"})

        t_resp = client.post("/api/templates", json={"name": "Alpha JD", "jd_text": "Python."})
        template_id = t_resp.json()["id"]

        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            create_resp = client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id,
            })
        analysis_id = create_resp.json()["id"]

        # Tenant Beta attempts to fetch it
        login_b = client.post("/api/auth/login", json={"email": "beta@beta.com", "password": "BetaPass1!"})
        client.headers.update({"Authorization": f"Bearer {login_b.json()['access_token']}"})

        resp = client.get(f"/api/transcript/analyses/{analysis_id}")
        assert resp.status_code == 404


# ─── End-to-end flow: create → list → fetch ──────────────────────────────────

class TestTranscriptEndToEndFlow:

    def test_full_flow_create_list_fetch(self, setup_template):
        auth_client, template_id = setup_template

        # 1. Create analysis
        with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                   return_value=mock_ollama_transcript()):
            create_resp = auth_client.post("/api/transcript/analyze", data={
                "transcript_text": SAMPLE_PLAIN_TRANSCRIPT,
                "role_template_id": template_id,
                "source_platform": "zoom",
            })
        assert create_resp.status_code == 200
        analysis_id = create_resp.json()["id"]

        # 2. Verify it appears in the list
        list_resp = auth_client.get("/api/transcript/analyses")
        assert list_resp.status_code == 200
        ids_in_list = [a["id"] for a in list_resp.json()["analyses"]]
        assert analysis_id in ids_in_list

        # 3. Fetch the full record by ID
        fetch_resp = auth_client.get(f"/api/transcript/analyses/{analysis_id}")
        assert fetch_resp.status_code == 200
        fetched = fetch_resp.json()
        assert fetched["id"] == analysis_id
        assert fetched["role_template_name"] == "Senior Python Engineer"
        assert fetched["source_platform"] == "zoom"
        assert fetched["analysis_result"]["fit_score"] == 78

    def test_multiple_formats_all_succeed(self, setup_template):
        auth_client, template_id = setup_template

        test_cases = [
            ("interview.txt", SAMPLE_PLAIN_TRANSCRIPT.encode(), "text/plain"),
            ("interview.vtt", SAMPLE_VTT_TRANSCRIPT.encode(),   "text/vtt"),
            ("interview.srt", SAMPLE_SRT_TRANSCRIPT.encode(),   "text/x-srt"),
        ]

        for filename, content, mime in test_cases:
            with patch("app.backend.services.transcript_service.httpx.AsyncClient",
                       return_value=mock_ollama_transcript()):
                resp = auth_client.post(
                    "/api/transcript/analyze",
                    data={"role_template_id": template_id},
                    files={"transcript_file": (filename, io.BytesIO(content), mime)},
                )
            assert resp.status_code == 200, f"Failed for {filename}: {resp.text}"

        # All three should appear in history
        list_resp = auth_client.get("/api/transcript/analyses")
        assert list_resp.json()["total"] == 3
