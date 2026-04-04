from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

from app.backend.db.database import engine, Base, SessionLocal
from app.backend.routes import analyze
from app.backend.routes import auth
from app.backend.routes import compare
from app.backend.routes import export
from app.backend.routes import templates
from app.backend.routes import candidates
from app.backend.routes import email_gen
from app.backend.routes import jd_url
from app.backend.routes import team
from app.backend.routes import training
from app.backend.routes import video
from app.backend.routes import transcript

log = logging.getLogger("aria.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables (idempotent — no-op if they already exist)
    Base.metadata.create_all(bind=engine)

    # Seed skills registry from DB (or hardcoded list if DB is empty)
    try:
        from app.backend.services.hybrid_pipeline import skills_registry
        db = SessionLocal()
        try:
            skills_registry.seed_if_empty(db)
            skills_registry.load(db)
        finally:
            db.close()
    except Exception as e:
        log.warning("Skills registry startup failed (non-fatal): %s", e)

    yield


app = FastAPI(
    title="ARIA — AI Resume Intelligence by ThetaLogics",
    description="Multi-tenant AI resume screening platform with 4-agent pipeline",
    version="2.0.0",
    lifespan=lifespan
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://airesume-staging.thetalogics.com",
]

if os.getenv("ENVIRONMENT", "development") == "development":
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(analyze.router)
app.include_router(compare.router)
app.include_router(export.router)
app.include_router(templates.router)
app.include_router(candidates.router)
app.include_router(email_gen.router)
app.include_router(jd_url.router)
app.include_router(team.router)
app.include_router(training.router)
app.include_router(video.router)
app.include_router(transcript.router)


# ─── Root endpoints ───────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "message": "ARIA API — AI Resume Intelligence",
        "version": "2.0.0",
        "docs":    "/docs",
    }


@app.get("/health")
async def health_check():
    """
    Active health check — verifies DB connectivity and Ollama reachability.
    Returns "degraded" (not "error") so upstream load balancers keep routing
    but operators are alerted via monitoring dashboards.
    """
    import httpx
    from sqlalchemy import text

    checks: dict = {"status": "ok", "db": "ok", "ollama": "ok"}

    # DB check
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception as e:
        checks["db"] = f"error: {str(e)[:80]}"
        checks["status"] = "degraded"

    # Ollama check
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}")
    except Exception as e:
        checks["ollama"] = f"error: {str(e)[:80]}"
        checks["status"] = "degraded"

    return checks
