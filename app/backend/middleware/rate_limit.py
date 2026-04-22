"""
Per-tenant rate limiting middleware using an in-memory token bucket.
"""
import time
import threading
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from jose import JWTError, jwt

from app.backend.middleware.auth import SECRET_KEY, ALGORITHM
from app.backend.db import database
from app.backend.models.db_models import RateLimitConfig


class RateLimitMiddleware(BaseHTTPMiddleware):
    WHITELIST_PREFIXES = [
        "/health",
        "/metrics",
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
        "/api/auth/logout",
        "/docs",
        "/openapi.json",
    ]
    DEFAULT_RPM = 60
    CONFIG_TTL = 60  # seconds
    _instance = None  # set on init for test access

    def __init__(self, app):
        super().__init__(app)
        RateLimitMiddleware._instance = self
        self.buckets = {}  # {tenant_id: {"tokens": float, "last_refill": float}}
        self.lock = threading.Lock()
        self.config_cache = {}  # {tenant_id: {"rpm": int, "cached_at": float}}

    def _is_whitelisted(self, path: str) -> bool:
        if path == "/":
            return True
        for prefix in self.WHITELIST_PREFIXES:
            if path.startswith(prefix):
                return True
        return False

    def _extract_tenant_id(self, request: Request) -> int | None:
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = request.cookies.get("access_token")

        if not token:
            return None

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                return None
        except JWTError:
            return None

        # Look up tenant_id from DB via user record
        db = database.SessionLocal()
        try:
            from app.backend.models.db_models import User
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                return user.tenant_id
        except Exception:
            pass
        finally:
            db.close()
        return None

    def _get_rate_limit(self, tenant_id: int) -> int:
        now = time.time()
        cached = self.config_cache.get(tenant_id)
        if cached and (now - cached["cached_at"]) < self.CONFIG_TTL:
            return cached["rpm"]

        rpm = self.DEFAULT_RPM
        db = database.SessionLocal()
        try:
            config = db.query(RateLimitConfig).filter(
                RateLimitConfig.tenant_id == tenant_id
            ).first()
            if config:
                rpm = config.requests_per_minute
        except Exception:
            pass
        finally:
            db.close()

        self.config_cache[tenant_id] = {"rpm": rpm, "cached_at": now}
        return rpm

    def _consume_token(self, tenant_id: int, rpm: int) -> tuple[bool, float]:
        now = time.time()
        with self.lock:
            bucket = self.buckets.get(tenant_id)
            if bucket is None:
                bucket = {"tokens": float(rpm), "last_refill": now}
                self.buckets[tenant_id] = bucket

            # Refill tokens based on elapsed time
            elapsed = now - bucket["last_refill"]
            refill_rate = rpm / 60.0  # tokens per second
            bucket["tokens"] = min(rpm, bucket["tokens"] + elapsed * refill_rate)
            bucket["last_refill"] = now

            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return True, 0.0

            # Calculate seconds until next token is available
            deficit = 1 - bucket["tokens"]
            retry_after = deficit / refill_rate if refill_rate > 0 else 60.0
            return False, retry_after

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if self._is_whitelisted(path):
            return await call_next(request)

        tenant_id = self._extract_tenant_id(request)
        if tenant_id is None:
            return await call_next(request)

        rpm = self._get_rate_limit(tenant_id)
        allowed, retry_after = self._consume_token(tenant_id, rpm)

        if allowed:
            return await call_next(request)

        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
            headers={"Retry-After": str(int(retry_after) + 1)},
        )
