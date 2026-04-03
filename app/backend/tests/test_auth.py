"""
Tests for /api/auth/* endpoints: register, login, refresh, /me.
"""
import pytest


REGISTER_PAYLOAD = {
    "company_name": "Acme Corp",
    "email": "hr@acme.com",
    "password": "HRPass123!",
    "full_name": "HR Manager",
}


class TestRegister:
    def test_register_creates_tenant_and_user(self, client):
        resp = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "access_token" in data
        assert "tenant" in data
        assert data["tenant"]["name"] == "Acme Corp"

    def test_register_duplicate_email_returns_4xx(self, client):
        client.post("/api/auth/register", json=REGISTER_PAYLOAD)
        resp = client.post("/api/auth/register", json=REGISTER_PAYLOAD)
        assert resp.status_code in (400, 409)  # Either is valid for duplicate

    def test_register_missing_fields_returns_422(self, client):
        resp = client.post("/api/auth/register", json={"email": "x@y.com"})
        assert resp.status_code == 422

    def test_register_missing_required_field_returns_422(self, client):
        # Missing company_name should fail validation
        resp = client.post("/api/auth/register", json={"email": "x@y.com", "password": "Pass123!"})
        assert resp.status_code == 422


class TestLogin:
    def setup_method(self, _):
        """Each test calls register fresh via the `client` fixture."""
        pass

    def test_login_success_returns_tokens(self, client):
        client.post("/api/auth/register", json=REGISTER_PAYLOAD)
        resp = client.post("/api/auth/login", json={
            "email": REGISTER_PAYLOAD["email"],
            "password": REGISTER_PAYLOAD["password"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, client):
        client.post("/api/auth/register", json=REGISTER_PAYLOAD)
        resp = client.post("/api/auth/login", json={
            "email": REGISTER_PAYLOAD["email"],
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_unknown_email_returns_401(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "nobody@nowhere.com",
            "password": "whatever",
        })
        assert resp.status_code == 401

    def test_login_missing_password_returns_422(self, client):
        resp = client.post("/api/auth/login", json={"email": "x@y.com"})
        assert resp.status_code == 422


class TestMe:
    def test_me_returns_user_data(self, auth_client):
        resp = auth_client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        # Response is {"user": {...}, "tenant": {...}}
        user = data.get("user") or data
        assert "email" in user
        assert "role" in user
        assert user["role"] == "admin"

    def test_me_without_token_returns_401(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token_returns_401(self, client):
        client.headers.update({"Authorization": "Bearer totally.invalid.token"})
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401


class TestRefresh:
    def test_refresh_returns_new_access_token(self, client):
        client.post("/api/auth/register", json=REGISTER_PAYLOAD)
        login = client.post("/api/auth/login", json={
            "email": REGISTER_PAYLOAD["email"],
            "password": REGISTER_PAYLOAD["password"],
        }).json()
        refresh_token = login["refresh_token"]

        resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_refresh_with_invalid_token_returns_401(self, client):
        resp = client.post("/api/auth/refresh", json={"refresh_token": "bad.token.here"})
        assert resp.status_code == 401
