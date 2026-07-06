"""
Tests for the CSRF middleware's double-submit enforcement, focused on the
fix that closed the silent-bypass hole: a cookie-authenticated request
(access_token cookie present) MUST carry a matching csrf_token, otherwise 403.

Bearer (API) clients remain exempt; genuine non-cookie clients fall through to
normal auth (401).
"""
import pytest

NON_EXEMPT_POST_PATH = "/api/analyze"


class TestCSRFEnforcement:
    def test_cookie_auth_without_csrf_cookie_is_rejected(self, client):
        """access_token cookie present but no csrf_token cookie → 403."""
        client.cookies.set("access_token", "some.jwt.value")
        resp = client.post(NON_EXEMPT_POST_PATH, json={})
        client.cookies.clear()
        assert resp.status_code == 403
        assert "csrf" in resp.json()["detail"].lower()

    def test_cookie_auth_with_mismatched_csrf_is_rejected(self, client):
        """csrf cookie present but header missing/mismatched → 403."""
        client.cookies.set("access_token", "some.jwt.value")
        client.cookies.set("csrf_token", "cookie-token")
        resp = client.post(
            NON_EXEMPT_POST_PATH,
            json={},
            headers={"X-CSRF-Token": "different-header-token"},
        )
        client.cookies.clear()
        assert resp.status_code == 403

    def test_bearer_client_bypasses_csrf(self, auth_client):
        """Bearer-authenticated API clients are exempt from CSRF (no 403)."""
        resp = auth_client.post(NON_EXEMPT_POST_PATH, json={})
        # Not blocked by CSRF; downstream may 422/400 for the empty body.
        assert resp.status_code != 403

    def test_non_cookie_client_falls_through_to_auth(self, client):
        """No access cookie and no Bearer → CSRF passes, auth returns 401."""
        resp = client.post(NON_EXEMPT_POST_PATH, json={})
        assert resp.status_code == 401

    def test_safe_methods_are_exempt(self, client):
        """GET is never CSRF-checked even with an access cookie."""
        client.cookies.set("access_token", "some.jwt.value")
        resp = client.get("/api/health")
        client.cookies.clear()
        assert resp.status_code != 403
