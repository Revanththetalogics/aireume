from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import httpx

from app.backend.db.database import engine, Base, SessionLocal
from app.backend.middleware.csrf import CSRFMiddleware
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
from app.backend.routes import subscription

log = logging.getLogger("aria.startup")

VERSION = "2.0.0"
W = 54  # banner width (inner)


def _banner_line(text: str = "", fill: str = " ") -> str:
    return f"║ {text:{fill}<{W}} ║"


def _check(ok: bool) -> str:
    return "OK  " if ok else "FAIL"


def _print_startup_banner(checks: dict) -> None:
    """Print a one-glance startup status table to stdout (captured by docker logs)."""
    if not checks:
        print("\n[ARIA startup] No dependency checks ran.\n", flush=True)
        return

    overall_ok = all(v["ok"] for v in checks.values())
    status_label = "READY" if overall_ok else "DEGRADED — check items marked FAIL"

    lines = [
        f"╔{'═' * (W + 2)}╗",
        _banner_line(f"  ARIA — Resume Intelligence v{VERSION}  ·  ThetaLogics"),
        f"╠{'═' * (W + 2)}╣",
    ]
    for name, info in checks.items():
        icon  = "✓" if info["ok"] else "✗"
        label = info["label"]
        # Keep row within W so box-drawing does not overflow terminals
        note  = (info.get("note", "") or "")[:28]
        row   = f"{icon}  {label:<18} {note}"
        lines.append(_banner_line(row))

    lines += [
        f"╠{'═' * (W + 2)}╣",
        _banner_line(f"  Status : {status_label}"),
        f"╚{'═' * (W + 2)}╝",
    ]
    # Use print so it always appears in docker logs regardless of log level
    print("\n" + "\n".join(lines) + "\n", flush=True)


async def _startup_checks() -> dict:
    """Run all dependency checks and return structured results."""
    from sqlalchemy import text

    results = {}

    # ── 1. Database ───────────────────────────────────────────────────────────
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_name = os.getenv("DATABASE_URL", "").split("/")[-1] or "connected"
            results["database"] = {"ok": True, "label": "Database",
                                   "note": f"connected  ({db_name})"}
        finally:
            db.close()
    except Exception as e:
        results["database"] = {"ok": False, "label": "Database",
                               "note": str(e)[:30]}

    # ── 2. Skills registry ────────────────────────────────────────────────────
    try:
        from app.backend.services.hybrid_pipeline import skills_registry
        db = SessionLocal()
        try:
            skills_registry.seed_if_empty(db)
            skills_registry.load(db)
        finally:
            db.close()
        count = len(skills_registry._skills)
        results["skills"] = {"ok": count > 0, "label": "Skills registry",
                             "note": f"{count} skills loaded"}
    except Exception as e:
        results["skills"] = {"ok": False, "label": "Skills registry",
                             "note": str(e)[:30]}

    # ── 3. Ollama reachability ────────────────────────────────────────────────
    ollama_url    = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    narrative_model = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
    pulled_models = []
    hot_models    = []
    ollama_ok     = False

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            r = await client.get(f"{ollama_url}/api/tags")
            r.raise_for_status()
            ollama_ok = True
            pulled_models = [m["name"] for m in r.json().get("models", [])]
            try:
                ps = await client.get(f"{ollama_url}/api/ps")
                if ps.status_code == 200:
                    hot_models = [m["name"] for m in ps.json().get("models", [])]
            except Exception:
                pass
        results["ollama"] = {"ok": True, "label": "Ollama",
                             "note": f"reachable  ({ollama_url})"}
    except Exception as e:
        results["ollama"] = {"ok": False, "label": "Ollama",
                             "note": str(e)[:35]}

    # ── 4. Narrative model pulled ─────────────────────────────────────────────
    model_pulled = ollama_ok and any(narrative_model in m for m in pulled_models)
    results["model_pulled"] = {
        "ok":    model_pulled,
        "label": "Model (pulled)",
        "note":  f"{narrative_model}" if model_pulled else f"{narrative_model}  NOT FOUND",
    }

    # ── 5. Narrative model hot in RAM ─────────────────────────────────────────
    model_hot = ollama_ok and any(narrative_model in m for m in hot_models)
    results["model_hot"] = {
        "ok":    model_hot,
        "label": "Model (hot/RAM)",
        "note":  "loaded" if model_hot else "cold — will load on first request",
    }

    # ── 6. Environment ────────────────────────────────────────────────────────
    env = os.getenv("ENVIRONMENT", "development")
    results["environment"] = {"ok": True, "label": "Environment", "note": env}

    return results


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables, run dependency checks, print banner.

    Never raises: if startup checks crash, we still bind the server so nginx
    does not return 502 Bad Gateway (upstream connection refused).
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        log.exception("create_all failed: %s", e)

    try:
        checks = await _startup_checks()
        _print_startup_banner(checks)
    except Exception as e:
        log.exception("Startup checks failed — API will still start: %s", e)
        print(f"\n[ARIA startup ERROR] {type(e).__name__}: {e}\n", flush=True)

    yield


app = FastAPI(
    title="ARIA — AI Resume Intelligence by ThetaLogics",
    description="Multi-tenant AI resume screening platform",
    version=VERSION,
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

# Load CORS origins from environment variable (comma-separated)
# Default includes common dev ports and production domain
cors_origins_str = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,https://airesume-staging.thetalogics.com"
)
origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── CSRF Protection ─────────────────────────────────────────────────────────

app.add_middleware(CSRFMiddleware)

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
app.include_router(subscription.router)


# ─── Root endpoints ───────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "message": "ARIA API — AI Resume Intelligence",
        "version": VERSION,
        "docs":    "/docs",
    }


@app.get("/health")
async def health_check():
    """
    Active health check — verifies DB and Ollama connectivity.
    Returns 200 with status 'ok' or 'degraded' (never 5xx) so upstream
    load balancers keep routing while operators are alerted.
    """
    from sqlalchemy import text

    checks: dict = {"status": "ok", "db": "ok", "ollama": "ok"}

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception as e:
        checks["db"] = f"error: {str(e)[:80]}"
        checks["status"] = "degraded"

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


@app.get("/api/llm-status")
async def llm_status():
    """
    Diagnostic endpoint — shows pulled models, hot models, and a plain-English
    diagnosis of why the LLM narrative may be falling back to Python.

    Usage from the VPS:
      curl http://localhost:8080/api/llm-status
    """
    ollama_url     = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    target_model   = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
    fast_model     = os.getenv("OLLAMA_FAST_MODEL", "qwen3.5:4b")

    result: dict = {
        "ollama_url":            ollama_url,
        "narrative_model":       target_model,
        "fast_model":            fast_model,
        "ollama_reachable":      False,
        "pulled_models":         [],
        "narrative_model_ready": False,
        "fast_model_ready":      False,
        "running_models":        [],
        "diagnosis":             "",
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            tags_resp = await client.get(f"{ollama_url}/api/tags")
            tags_resp.raise_for_status()
            result["ollama_reachable"] = True
            result["pulled_models"] = [m["name"] for m in tags_resp.json().get("models", [])]
            result["narrative_model_ready"] = any(
                target_model in m for m in result["pulled_models"]
            )
            result["fast_model_ready"] = any(
                fast_model in m for m in result["pulled_models"]
            )
            try:
                ps = await client.get(f"{ollama_url}/api/ps")
                if ps.status_code == 200:
                    result["running_models"] = [
                        m["name"] for m in ps.json().get("models", [])
                    ]
            except Exception:
                pass
    except Exception as e:
        result["diagnosis"] = f"Ollama unreachable: {str(e)[:120]}"
        return result

    narrative_hot = any(target_model in m for m in result["running_models"])

    if not result["narrative_model_ready"]:
        result["diagnosis"] = (
            f"'{target_model}' not pulled. "
            f"Run: docker exec resume-screener-ollama ollama pull {target_model}"
        )
    elif not narrative_hot:
        result["diagnosis"] = (
            f"'{target_model}' pulled but NOT in RAM (cold). "
            f"Pre-warm: docker exec resume-screener-ollama ollama run {target_model} 'Hi'"
        )
    else:
        result["diagnosis"] = f"'{target_model}' is HOT in RAM — LLM narrative is active."

    return result
