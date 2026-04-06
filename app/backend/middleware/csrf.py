"""
CSRF protection middleware using double-submit cookie pattern.

For browser clients using cookie-based auth, this middleware validates that
the CSRF token in the cookie matches the X-CSRF-Token header.
API clients using Authorization header bypass CSRF checks.
"""
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
    """
    
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    EXEMPT_PATHS = {
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
        "/api/auth/logout",
        "/health",
        "/api/health",
        "/api/llm-status",
    }

    async def dispatch(self, request: Request, call_next):
        # Skip CSRF check for safe methods
        if request.method in self.SAFE_METHODS:
            return await call_next(request)
        
        # Skip for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Skip CSRF if using Authorization header (API clients, not browser)
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return await call_next(request)
        
        # For cookie-based auth, require CSRF token
        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("x-csrf-token")
        
        if not cookie_token or not header_token or cookie_token != header_token:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing or invalid"}
            )
        
        return await call_next(request)
