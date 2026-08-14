"""Client-side error reports from ErrorBoundary / window.onerror."""
from fastapi import APIRouter, Request
from pydantic import BaseModel
import logging

from app.backend.services.observability import capture_exception, capture_message

logger = logging.getLogger("aria.client")
router = APIRouter(prefix="/api", tags=["client"])


class ClientErrorBody(BaseModel):
    message: str = ""
    stack: str = ""
    source: str = ""


@router.post("/client-error")
async def client_error(body: ClientErrorBody, request: Request):
    logger.warning("browser_error message=%s source=%s", body.message[:500], body.source[:200])
    if body.stack:
        capture_exception(RuntimeError(f"browser_error:{body.message[:200]}"))
    else:
        capture_message(f"browser_error:{body.message[:200]}")
    return {"ok": True}
