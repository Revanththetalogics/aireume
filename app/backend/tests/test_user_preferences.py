"""Tests for user preferences API."""
import pytest


class TestUserPreferences:
    def test_get_preferences_requires_auth(self, client):
        response = client.get("/api/users/me/preferences")
        assert response.status_code in (401, 403)

    def test_get_default_preferences(self, auth_client):
        response = auth_client.get("/api/users/me/preferences")
        assert response.status_code == 200
        prefs = response.json()["preferences"]
        assert prefs["notifications"]["emailOnComplete"] is True
        assert prefs["notifications"]["marketing"] is False
        assert prefs["seen_modals"] == {}

    def test_patch_notification_preferences(self, auth_client):
        response = auth_client.patch("/api/users/me/preferences", json={
            "notifications": {"marketing": True, "emailOnComplete": False},
        })
        assert response.status_code == 200
        prefs = response.json()["preferences"]
        assert prefs["notifications"]["marketing"] is True
        assert prefs["notifications"]["emailOnComplete"] is False
        assert prefs["notifications"]["emailOnBatchComplete"] is True

    def test_mark_modal_seen(self, auth_client):
        response = auth_client.post("/api/users/me/preferences/seen-modal", json={
            "modal_id": "analyze",
        })
        assert response.status_code == 200
        assert response.json()["preferences"]["seen_modals"]["analyze"] is True

        get_resp = auth_client.get("/api/users/me/preferences")
        assert get_resp.json()["preferences"]["seen_modals"]["analyze"] is True
