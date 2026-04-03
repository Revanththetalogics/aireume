from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.backend.db.database import engine, Base
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
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
def health_check():
    return {"status": "ok"}
