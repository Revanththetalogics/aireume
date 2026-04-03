"""
JD URL extraction endpoint — paste a job URL and get the JD text back.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import User
from app.backend.models.schemas import JdUrlRequest, JdUrlResponse
from app.backend.services.jd_scraper import scrape_jd

router = APIRouter(prefix="/api/jd", tags=["jd"])


@router.post("/extract-url", response_model=JdUrlResponse)
async def extract_jd_from_url(
    body: JdUrlRequest,
    current_user: User = Depends(get_current_user),
):
    if not body.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL — must start with http:// or https://")

    try:
        jd_text = await scrape_jd(body.url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to extract JD: {str(e)}")

    return JdUrlResponse(jd_text=jd_text, source_url=body.url)
