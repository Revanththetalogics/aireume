"""
Video interview analysis endpoints.
  POST /api/analyze/video       — file upload
  POST /api/analyze/video-url   — public recording URL (Zoom, Teams, Drive, Loom…)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, HttpUrl

from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import User
from app.backend.services.video_service import analyze_video_file, analyze_video_from_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analyze", tags=["video"])

ALLOWED_EXTENSIONS = (".mp4", ".webm", ".avi", ".mov", ".mkv", ".m4v")
MAX_UPLOAD_BYTES   = 200 * 1024 * 1024  # 200 MB


# ─── File upload ──────────────────────────────────────────────────────────────

@router.post("/video")
async def analyze_video(
    video:        UploadFile = File(...),
    candidate_id: int        = Form(None),
    current_user: User       = Depends(get_current_user),
):
    if not video.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await video.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Video too large. Maximum upload size is 200 MB.")

    try:
        result = await analyze_video_file(content, video.filename)
    except Exception as e:
        logger.warning("Video analysis failed for %s: %s", video.filename, e)
        raise HTTPException(status_code=422, detail=f"Video analysis failed: {str(e)}")

    return {"candidate_id": candidate_id, "filename": video.filename, **result}


# ─── Public URL ───────────────────────────────────────────────────────────────

class VideoUrlRequest(BaseModel):
    url:          str
    candidate_id: int | None = None


@router.post("/video-url")
async def analyze_video_url(
    body:         VideoUrlRequest,
    current_user: User = Depends(get_current_user),
):
    if not body.url or not body.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="A valid HTTP/HTTPS URL is required.")

    try:
        result = await analyze_video_from_url(body.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.warning("Video URL analysis failed for %s: %s", body.url, e)
        raise HTTPException(status_code=422, detail=f"Video analysis failed: {str(e)}")

    return {"candidate_id": body.candidate_id, **result}
