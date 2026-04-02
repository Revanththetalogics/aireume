from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.backend.db.database import engine, Base
from app.backend.routes import analyze


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup on shutdown (if needed)


app = FastAPI(
    title="AI Resume Screener by ThetaLogics",
    description="Local-first AI resume screening using Ollama",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://airesume-staging.thetalogics.com"
]

# Allow all in dev mode
if os.getenv("ENVIRONMENT", "development") == "development":
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analyze.router)


@app.get("/")
def root():
    return {
        "message": "AI Resume Screener API",
        "docs": "/docs",
        "endpoints": {
            "analyze": "POST /api/analyze",
            "history": "GET /api/history"
        }
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
