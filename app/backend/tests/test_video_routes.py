"""
Tests for video analysis routes:
  POST /api/analyze/video      — file upload
  POST /api/analyze/video-url  — public URL analysis
"""
import io
import json
import pytest
from unittest.mock import patch, AsyncMock


MOCK_ANALYSIS_RESULT = {
    "source": "test_video.mp4",
    "transcript": "Hello, I have five years of experience in Python development.",
    "language": "en",
    "duration_s": 30.0,
    "segments": [],
    "communication_score": 78,
    "confidence_level": "high",
    "clarity_score": 82,
    "articulation_score": 75,
    "key_phrases": ["five years", "Python development"],
    "strengths": ["Clear articulation"],
    "red_flags": [],
    "summary": "Good communicator.",
    "words_per_minute": 120,
    "malpractice": {
        "malpractice_score": 10,
        "malpractice_risk": "low",
        "reliability_rating": "trustworthy",
        "flags": [],
        "positive_signals": ["Natural speech"],
        "overall_assessment": "No malpractice detected.",
        "follow_up_questions": [],
        "pause_count": 0,
        "pauses": [],
    },
}


# ─── File upload endpoint ─────────────────────────────────────────────────────

class TestVideoFileUpload:
    def test_upload_requires_auth(self, client):
        resp = client.post(
            "/api/analyze/video",
            files={"video": ("test.mp4", io.BytesIO(b"\x00" * 100), "video/mp4")},
        )
        assert resp.status_code == 401

    def test_invalid_file_extension_returns_400(self, auth_client):
        resp = auth_client.post(
            "/api/analyze/video",
            files={"video": ("resume.pdf", io.BytesIO(b"not a video"), "application/pdf")},
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json().get("detail", "") or "supported" in resp.json().get("detail", "").lower()

    def test_file_too_large_returns_400(self, auth_client):
        # Create content larger than 200 MB
        large_content = b"\x00" * (201 * 1024 * 1024)
        resp = auth_client.post(
            "/api/analyze/video",
            files={"video": ("big.mp4", io.BytesIO(large_content), "video/mp4")},
        )
        assert resp.status_code == 400
        assert "200 MB" in resp.json().get("detail", "") or "large" in resp.json().get("detail", "").lower()

    def test_successful_video_upload(self, auth_client):
        with patch(
            "app.backend.routes.video.analyze_video_file",
            new_callable=AsyncMock,
            return_value=MOCK_ANALYSIS_RESULT.copy(),
        ) as mock_analyze:
            resp = auth_client.post(
                "/api/analyze/video",
                files={"video": ("test.mp4", io.BytesIO(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 100), "video/mp4")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "communication_score" in data
        assert "malpractice" in data
        assert data["malpractice"]["malpractice_risk"] == "low"
        assert data["filename"] == "test.mp4"

    def test_video_upload_with_candidate_id(self, auth_client):
        with patch(
            "app.backend.routes.video.analyze_video_file",
            new_callable=AsyncMock,
            return_value=MOCK_ANALYSIS_RESULT.copy(),
        ):
            resp = auth_client.post(
                "/api/analyze/video",
                data={"candidate_id": "42"},
                files={"video": ("interview.mp4", io.BytesIO(b"\x00" * 100), "video/mp4")},
            )

        assert resp.status_code == 200
        assert resp.json()["candidate_id"] == 42

    def test_accepted_video_extensions(self, auth_client):
        allowed = [".mp4", ".webm", ".avi", ".mov", ".mkv"]
        for ext in allowed:
            with patch(
                "app.backend.routes.video.analyze_video_file",
                new_callable=AsyncMock,
                return_value=MOCK_ANALYSIS_RESULT.copy(),
            ):
                resp = auth_client.post(
                    "/api/analyze/video",
                    files={"video": (f"interview{ext}", io.BytesIO(b"\x00" * 100), "video/mp4")},
                )
            assert resp.status_code == 200, f"Extension {ext} should be accepted"

    def test_service_exception_returns_422(self, auth_client):
        with patch(
            "app.backend.routes.video.analyze_video_file",
            new_callable=AsyncMock,
            side_effect=Exception("Whisper crashed"),
        ):
            resp = auth_client.post(
                "/api/analyze/video",
                files={"video": ("test.mp4", io.BytesIO(b"\x00" * 100), "video/mp4")},
            )
        assert resp.status_code == 422


# ─── URL endpoint ─────────────────────────────────────────────────────────────

class TestVideoUrlAnalysis:
    def test_url_endpoint_requires_auth(self, client):
        resp = client.post("/api/analyze/video-url", json={"url": "https://zoom.us/rec/share/abc"})
        assert resp.status_code == 401

    def test_missing_url_returns_422(self, auth_client):
        resp = auth_client.post("/api/analyze/video-url", json={})
        assert resp.status_code == 422

    def test_invalid_url_scheme_returns_400(self, auth_client):
        resp = auth_client.post("/api/analyze/video-url", json={"url": "not-a-url"})
        assert resp.status_code == 400

    def test_successful_url_analysis_zoom(self, auth_client):
        url_result = {**MOCK_ANALYSIS_RESULT, "source_url": "https://zoom.us/rec/share/abc", "platform": "Zoom", "filename": "zoom_recording.mp4"}
        with patch(
            "app.backend.routes.video.analyze_video_from_url",
            new_callable=AsyncMock,
            return_value=url_result,
        ):
            resp = auth_client.post(
                "/api/analyze/video-url",
                json={"url": "https://zoom.us/rec/share/abc123"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "communication_score" in data
        assert "malpractice" in data
        assert data.get("platform") == "Zoom"

    def test_url_analysis_with_candidate_id(self, auth_client):
        url_result = {**MOCK_ANALYSIS_RESULT, "source_url": "https://loom.com/share/abc", "platform": "Loom", "filename": "loom_recording.mp4"}
        with patch(
            "app.backend.routes.video.analyze_video_from_url",
            new_callable=AsyncMock,
            return_value=url_result,
        ):
            resp = auth_client.post(
                "/api/analyze/video-url",
                json={"url": "https://www.loom.com/share/abc123", "candidate_id": 7},
            )

        assert resp.status_code == 200
        assert resp.json()["candidate_id"] == 7

    def test_download_failure_returns_422(self, auth_client):
        with patch(
            "app.backend.routes.video.analyze_video_from_url",
            new_callable=AsyncMock,
            side_effect=ValueError("Access denied. Make sure the recording is shared publicly."),
        ):
            resp = auth_client.post(
                "/api/analyze/video-url",
                json={"url": "https://zoom.us/rec/share/private"},
            )

        assert resp.status_code == 422
        assert "Access denied" in resp.json()["detail"]

    def test_url_analysis_google_drive(self, auth_client):
        url_result = {**MOCK_ANALYSIS_RESULT, "platform": "Google Drive", "filename": "drive_recording.mp4", "source_url": "https://drive.google.com/file/d/ABC/view"}
        with patch(
            "app.backend.routes.video.analyze_video_from_url",
            new_callable=AsyncMock,
            return_value=url_result,
        ):
            resp = auth_client.post(
                "/api/analyze/video-url",
                json={"url": "https://drive.google.com/file/d/FILEID/view"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["platform"] == "Google Drive"

    def test_url_analysis_teams(self, auth_client):
        url_result = {**MOCK_ANALYSIS_RESULT, "platform": "Microsoft Teams", "filename": "teams_recording.mp4"}
        with patch(
            "app.backend.routes.video.analyze_video_from_url",
            new_callable=AsyncMock,
            return_value=url_result,
        ):
            resp = auth_client.post(
                "/api/analyze/video-url",
                json={"url": "https://company.sharepoint.com/:v:/g/abc123"},
            )

        assert resp.status_code == 200
