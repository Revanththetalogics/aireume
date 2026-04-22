"""
Tests for per-tenant rate limiting middleware.
"""
import pytest
from app.backend.middleware.rate_limit import RateLimitMiddleware


@pytest.fixture(autouse=True)
def _clear_rate_limit_buckets():
    """Clear buckets and config cache before each test to avoid interference."""
    middleware = RateLimitMiddleware._instance
    if middleware is not None:
        middleware.buckets.clear()
        middleware.config_cache.clear()


def test_whitelisted_paths_not_rate_limited(client):
    """Health, auth login/register, docs, root, metrics never get 429."""
    paths = [
        "/",
        "/health",
        "/metrics",
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
        "/api/auth/logout",
        "/docs",
        "/openapi.json",
    ]
    for path in paths:
        if path in ("/api/auth/login", "/api/auth/register", "/api/auth/refresh", "/api/auth/logout"):
            resp = client.post(path, json={})
        else:
            resp = client.get(path)
        assert resp.status_code != 429, f"{path} should not be rate limited"


def test_normal_requests_under_limit(auth_client):
    """A few authenticated requests should not trigger rate limiting."""
    for _ in range(5):
        resp = auth_client.get("/api/candidates")
        assert resp.status_code != 429


def test_rate_limit_exceeded(auth_client):
    """Exhausting the token bucket should return 429."""
    middleware = RateLimitMiddleware._instance
    assert middleware is not None, "RateLimitMiddleware instance should exist"

    # Make one request to establish the bucket for this tenant
    resp = auth_client.get("/api/candidates")
    assert resp.status_code != 429

    # Directly exhaust the bucket by setting tokens to 0
    for bucket in middleware.buckets.values():
        bucket["tokens"] = 0.0

    # Next request should be blocked
    resp = auth_client.get("/api/candidates")
    assert resp.status_code == 429
    assert resp.json()["detail"] == "Rate limit exceeded. Try again later."


def test_429_has_retry_after_header(auth_client):
    """A 429 response must include a Retry-After header."""
    middleware = RateLimitMiddleware._instance
    assert middleware is not None, "RateLimitMiddleware instance should exist"

    # Establish bucket then exhaust it
    auth_client.get("/api/candidates")
    for bucket in middleware.buckets.values():
        bucket["tokens"] = 0.0

    resp = auth_client.get("/api/candidates")
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
    assert int(resp.headers["Retry-After"]) > 0


def test_unauthenticated_requests_not_rate_limited(client):
    """Requests without auth token are passed through (auth middleware handles them)."""
    for _ in range(5):
        resp = client.get("/api/candidates")
        assert resp.status_code != 429  # expect 401 from auth middleware
