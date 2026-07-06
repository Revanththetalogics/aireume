"""
Tests that logout revokes the ACCESS token's JTI (not just the refresh token),
so a stolen/leaked access token cannot be reused before its natural expiry.
"""
import pytest
from jose import jwt

from app.backend.middleware.auth import SECRET_KEY, ALGORITHM
from app.backend.tests.test_helpers import _verify_user_via_api

REGISTER = {
    "company_name": "RevokeCorp",
    "email": "revoke@corp.com",
    "password": "RevokePass123!",
    "full_name": "Revoke User",
}


def _login(client):
    client.post("/api/auth/register", json=REGISTER)
    _verify_user_via_api(REGISTER["email"])
    resp = client.post("/api/auth/login", json={
        "email": REGISTER["email"], "password": REGISTER["password"],
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


class TestAccessTokenRevocation:
    def test_access_token_works_before_logout(self, client):
        token = _login(client)
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_access_token_rejected_after_logout(self, client):
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Sanity: works pre-logout
        assert client.get("/api/auth/me", headers=headers).status_code == 200

        # Logout with the access token in the Authorization header
        logout = client.post("/api/auth/logout", headers=headers)
        assert logout.status_code == 200

        # The same access token must now be rejected
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401
        assert "revoked" in resp.json()["detail"].lower()

    def test_revoked_jti_is_stored(self, client, db):
        from app.backend.models.db_models import RevokedToken
        token = _login(client)
        jti = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("jti")
        assert jti is not None

        client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

        revoked = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
        assert revoked is not None
