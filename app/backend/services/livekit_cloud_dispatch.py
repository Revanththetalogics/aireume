"""
Dispatch voice screening calls via LiveKit Cloud (no self-hosted voice-agent).

Enabled when LIVEKIT_CLOUD_VOICE=1 on the backend.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

from app.voice_agent.livekit_dispatch import dispatch_cloud_screening_call

logger = logging.getLogger(__name__)

ARIA_BACKEND_URL = os.getenv("ARIA_BACKEND_URL", "http://backend:8000")
# When running inside the backend container, use the internal URL for self-callbacks.
BACKEND_INTERNAL_URL = os.getenv("BACKEND_INTERNAL_URL", ARIA_BACKEND_URL)
INTERNAL_SERVICE_SECRET = os.getenv("INTERNAL_SERVICE_SECRET", "dev-internal-service-secret")
INTERNAL_HEADERS = {"X-Internal-Secret": INTERNAL_SERVICE_SECRET}


def is_cloud_voice_enabled() -> bool:
    return os.getenv("LIVEKIT_CLOUD_VOICE", "").strip().lower() in ("1", "true", "yes")


async def _fetch_tenant_config(tenant_id: int) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{BACKEND_INTERNAL_URL}/api/voice/internal/config/{tenant_id}",
            headers=INTERNAL_HEADERS,
        )
        if resp.status_code == 200:
            return resp.json()
    return {}


async def _fetch_candidate_context(tenant_id: int, candidate_id: int) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{BACKEND_INTERNAL_URL}/api/voice/internal/candidate/{tenant_id}/{candidate_id}",
            headers=INTERNAL_HEADERS,
        )
        if resp.status_code == 200:
            return resp.json()
    return {}


async def dispatch_screening_call_async(payload: dict[str, Any]) -> dict[str, Any]:
    """Enrich payload with tenant/candidate context and dispatch to LiveKit Cloud."""
    tenant_id = payload.get("tenant_id")
    candidate_id = payload.get("candidate_id")
    if tenant_id is not None:
        payload["tenant_config"] = await _fetch_tenant_config(int(tenant_id))
    if tenant_id is not None and candidate_id is not None:
        payload["candidate_context"] = await _fetch_candidate_context(
            int(tenant_id), int(candidate_id)
        )
    return await dispatch_cloud_screening_call(payload)


def dispatch_screening_call(payload: dict[str, Any]) -> dict[str, Any]:
    """Sync wrapper for APScheduler and other sync callers."""
    return asyncio.run(dispatch_screening_call_async(payload))
