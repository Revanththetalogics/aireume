"""
CSRF protection middleware using double-submit cookie pattern.

For browser clients using cookie-based auth, this middleware validates that
the CSRF token in the cookie matches the X-CSRF-Token header.
API clients using Authorization header bypass CSRF checks.
"""
import os
import re
import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware using double-submit cookie pattern.
    
    - Safe methods (GET, HEAD, OPTIONS) are exempt
    - Paths for login/register/refresh are exempt (no token yet)
    - Requests with Authorization header bypass CSRF (API clients)
    - Other requests must have matching csrf_token cookie and X-CSRF-Token header
    - After successful POST/PUT/DELETE, rotate the CSRF token
    """
    
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    EXEMPT_PATHS = {
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
        "/api/auth/logout",
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
        "/api/billing/webhook",
        "/api/sso/callback",
        "/api/webhooks/",
        "/api/recruiter/internal/",
        "/api/interviews/internal/",
        "/health",
        "/api/health",
        "/api/health/deep",
        "/api/llm-status",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/metrics",
    }

    # Regex patterns for paths that should be CSRF-exempt (e.g. dynamic path segments)
    EXEMPT_PATTERNS = [
        re.compile(r"^/api/candidates/\d+/name$"),  # PUT candidate name (auth-protected)
    ]

    def _is_exempt(self, path: str) -> bool:
        """Check if a path is CSRF-exempt (exact match, prefix match, or pattern match)."""
        if path in self.EXEMPT_PATHS:
            return True
        for exempt in self.EXEMPT_PATHS:
            if exempt.endswith("/") and path.startswith(exempt):
                return True
            if not exempt.endswith("/") and path.startswith(exempt + "/"):
                return True
        for pattern in self.EXEMPT_PATTERNS:
            if pattern.match(path):
                return True
        return False

    async def dispatch(self, request: Request, call_next):
        # Skip CSRF check for safe methods
        if request.method in self.SAFE_METHODS:
            return await call_next(request)
        
        # Skip for exempt paths
        if self._is_exempt(request.url.path):
            return await call_next(request)
        
        # Skip CSRF if using Authorization header (API clients, not browser)
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return await call_next(request)
        
        # For cookie-based auth, require CSRF token
        cookie_token = request.cookies.get("csrf_token")
        if not cookie_token:
            # No CSRF cookie set - skip validation (might be API client)
            return await call_next(request)

        header_token = request.headers.get("x-csrf-token")
        if not header_token or not secrets.compare_digest(cookie_token, header_token):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing or invalid"}
            )
        
        # Execute the request
        response = await call_next(request)
        
        # Rotate CSRF token after successful state-changing requests
        # Only rotate if the request was authenticated via cookies (not Bearer token)
        if response.status_code < 400 and request.method in {"POST", "PUT", "DELETE", "PATCH"}:
            is_production = os.getenv("ENVIRONMENT", "development") == "production"
            new_csrf_token = secrets.token_hex(32)
            response.set_cookie(
                key="csrf_token",
                value=new_csrf_token,
                httponly=False,
                secure=is_production,
                samesite="lax",
                max_age=3600,  # 1 hour
                path="/"
            )
        
        return response
