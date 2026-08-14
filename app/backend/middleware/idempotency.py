"""Honor X-Idempotency-Key on mutating requests."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
_TTL_HOURS = 24


def _tenant_from_request(request: Request) -> str:
    """Bind idempotency to the authenticated tenant, never to spoofable headers."""
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        token = request.cookies.get("access_token")
    if not token:
        return "0"
    try:
        from app.backend.middleware.auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        tenant_id = payload.get("tenant_id")
        if tenant_id is not None:
            return str(tenant_id)
    except Exception:
        pass
    return "0"


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method not in _MUTATING:
            return await call_next(request)
        if "stream" in request.url.path:
            return await call_next(request)
        key = request.headers.get("X-Idempotency-Key", "").strip()
        if not key:
            return await call_next(request)
        if os.getenv("TESTING", "").lower() in ("1", "true") and not key:
            return await call_next(request)

        tenant_id = _tenant_from_request(request)
        endpoint = f"{request.method}:{request.url.path}"
        stored = _lookup(key, tenant_id, endpoint)
        if stored is not None:
            status, body = stored
            return JSONResponse(content=body, status_code=status, headers={"X-Idempotent-Replay": "true"})

        response = await call_next(request)
        if 200 <= response.status_code < 300:
            body_bytes = getattr(response, "body", b"")
            if not body_bytes and hasattr(response, "body_iterator"):
                chunks = []
                async for chunk in response.body_iterator:
                    chunks.append(chunk)
                body_bytes = b"".join(chunks)
                response = Response(
                    content=body_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            try:
                payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            except Exception:
                payload = {"raw": hashlib.sha256(body_bytes).hexdigest()}
            _store(key, tenant_id, endpoint, response.status_code, payload)
        return response


def _lookup(key: str, tenant_id: str, endpoint: str):
    try:
        from app.backend.db.database import SessionLocal
        from app.backend.models.db_models import IdempotencyKey

        db = SessionLocal()
        try:
            row = (
                db.query(IdempotencyKey)
                .filter(
                    IdempotencyKey.key == key[:128],
                    IdempotencyKey.endpoint == endpoint[:200],
                    IdempotencyKey.tenant_id == (int(tenant_id) if str(tenant_id).isdigit() else 0),
                )
                .first()
            )
            if not row:
                return None
            if row.expires_at and row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                return None
            return row.response_status, row.response_body or {}
        finally:
            db.close()
    except Exception:
        return None


def _store(key: str, tenant_id: str, endpoint: str, status: int, body) -> None:
    try:
        from app.backend.db.database import SessionLocal
        from app.backend.models.db_models import IdempotencyKey

        db = SessionLocal()
        try:
            db.merge(
                IdempotencyKey(
                    key=key[:128],
                    tenant_id=int(tenant_id) if str(tenant_id).isdigit() else 0,
                    endpoint=endpoint[:200],
                    response_status=status,
                    response_body=body if isinstance(body, (dict, list)) else {"ok": True},
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=_TTL_HOURS),
                )
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        pass
