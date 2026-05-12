from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import json
import httpx
import uuid
import contextvars
import time
import threading
import shutil
import asyncio
from datetime import datetime, timezone, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] [%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("aria")

# Production JSON logging
if os.getenv("ENVIRONMENT") == "production":
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_obj = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "function": record.funcName,
            }
            if record.exc_info:
                log_obj["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_obj)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.root.handlers = [handler]

# Request correlation ID context variable
request_id_var = contextvars.ContextVar('request_id', default='-')


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware that generates/propagates a correlation ID per request."""
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        request_id_var.set(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

from app.backend.db.database import engine, Base, SessionLocal
from app.backend.middleware.csrf import CSRFMiddleware
from app.backend.middleware.rate_limit import RateLimitMiddleware
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
from app.backend.routes import queue_api
from app.backend.routes import admin
from app.backend.routes import upload
from app.backend.routes import billing
from app.backend.routes import interview_kit
from app.backend.routes import dashboard
from app.backend.routes import onboarding
from app.backend.services import llm_service

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
        from app.backend.services.skill_matcher import skills_registry
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


async def _cleanup_revoked_tokens():
    """Background task to delete expired revoked tokens every 24 hours."""
    while True:
        await asyncio.sleep(86400)  # 24 hours
        try:
            db = SessionLocal()
            from app.backend.models.db_models import RevokedToken
            deleted = db.query(RevokedToken).filter(
                RevokedToken.expires_at < datetime.now(timezone.utc)
            ).delete()
            db.commit()
            db.close()
            if deleted > 0:
                log.info("Cleaned up %d expired revoked tokens", deleted)
        except Exception as e:
            log.exception("Failed to clean up revoked tokens: %s", e)


async def _cleanup_jd_cache():
    """Delete JdCache entries older than 30 days."""
    while True:
        await asyncio.sleep(86400)  # 24 hours
        try:
            db = SessionLocal()
            from app.backend.models.db_models import JdCache
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            deleted = db.query(JdCache).filter(JdCache.created_at < cutoff).delete()
            db.commit()
            db.close()
            if deleted > 0:
                log.info("Cleaned up %d expired JD cache entries", deleted)
        except Exception as e:
            log.exception("Failed to clean up JD cache: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables, run dependency checks, print banner, start sentinel.

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

    # Start Ollama health sentinel after startup checks
    try:
        llm_service._sentinel = llm_service.OllamaHealthSentinel()
        await llm_service._sentinel.start()
    except Exception as e:
        log.exception("Failed to start Ollama health sentinel: %s", e)

    # Start revoked tokens cleanup task
    cleanup_task = asyncio.create_task(_cleanup_revoked_tokens())

    # Start JD cache cleanup task
    jd_cache_cleanup_task = asyncio.create_task(_cleanup_jd_cache())

    # Start queue worker
    queue_worker_task = None
    try:
        from app.backend.services.queue_manager import start_queue_worker
        await start_queue_worker()
        log.info("Queue worker started successfully")
    except Exception as e:
        log.exception("Failed to start queue worker: %s", e)

    # Start O*NET background sync (daemon thread — non-blocking, graceful on failure)
    try:
        def _onet_bg_sync():
            try:
                from app.backend.services.onet.onet_sync import sync_if_stale
                sync_if_stale(max_age_days=30)
            except Exception as exc:
                log.warning("O*NET startup sync skipped: %s", exc)

        onet_thread = threading.Thread(
            target=_onet_bg_sync, daemon=True, name="onet-sync"
        )
        onet_thread.start()
    except Exception as e:
        log.exception("Failed to start O*NET background sync thread: %s", e)

    yield

    # Shutdown: stop the sentinel gracefully
    try:
        if llm_service._sentinel:
            await llm_service._sentinel.stop()
    except Exception as e:
        log.exception("Error stopping Ollama health sentinel: %s", e)

    # Stop queue worker
    try:
        from app.backend.services.queue_manager import stop_queue_worker
        await stop_queue_worker()
        log.info("Queue worker stopped")
    except Exception as e:
        log.exception("Error stopping queue worker: %s", e)

    # Cancel the cleanup tasks
    cleanup_task.cancel()
    jd_cache_cleanup_task.cancel()


app = FastAPI(
    title="ARIA — AI Resume Intelligence by ThetaLogics",
    description="Multi-tenant AI resume screening platform",
    version=VERSION,
    lifespan=lifespan,
)

# ─── Prometheus Metrics ───────────────────────────────────────────────────────

instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    excluded_handlers=["/health", "/metrics"],
)
instrumentator.instrument(app).expose(app, endpoint="/metrics")

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

# ─── Rate Limiting ────────────────────────────────────────────────────────────

app.add_middleware(RateLimitMiddleware)

# ─── Request Correlation ID ───────────────────────────────────────────────────

app.add_middleware(RequestIdMiddleware)

# ─── CSRF Protection ─────────────────────────────────────────────────────────

app.add_middleware(CSRFMiddleware)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(analyze.router)
app.include_router(compare.router)
app.include_router(export.router)
app.include_router(templates.router)
app.include_router(candidates.router)
app.include_router(candidates.jd_router)
app.include_router(email_gen.router)
app.include_router(jd_url.router)
app.include_router(team.router)
app.include_router(training.router)
app.include_router(video.router)
app.include_router(transcript.router)
app.include_router(subscription.router)
app.include_router(queue_api.router)
app.include_router(admin.router)
app.include_router(upload.router)
app.include_router(billing.router)
app.include_router(interview_kit.router)
app.include_router(dashboard.router)
app.include_router(onboarding.router)


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
    Shallow health check — FAST (<10ms), just confirms the process is alive.
    Used by Docker/nginx for container health checks. No DB queries or external calls.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/health/deep")
async def deep_health_check():
    """
    Deep health check — comprehensive check of all dependencies.
    Checks DB connectivity, Ollama sentinel state, and disk space.
    Returns 'healthy', 'degraded', or 'unhealthy' status.
    """
    from sqlalchemy import text
    from app.backend.services.llm_service import get_sentinel

    start_time = time.monotonic()
    checks = {}
    overall_status = "healthy"

    # ── 1. Database check ─────────────────────────────────────────────────────
    db_start = time.monotonic()
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = {
                "status": "ok",
                "latency_ms": round((time.monotonic() - db_start) * 1000, 1),
            }
        finally:
            db.close()
    except Exception as e:
        checks["database"] = {
            "status": f"error: {str(e)[:50]}",
            "latency_ms": round((time.monotonic() - db_start) * 1000, 1),
        }
        overall_status = "unhealthy"  # DB failure = unhealthy

    # ── 2. Ollama check via sentinel ────────────────────────────────────────────
    ollama_start = time.monotonic()
    sentinel = get_sentinel()
    model_name = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")

    if sentinel is None:
        checks["ollama"] = {
            "status": "unknown",
            "latency_ms": round((time.monotonic() - ollama_start) * 1000, 1),
            "model": model_name,
            "message": "Sentinel not initialized",
        }
        overall_status = "degraded"
    else:
        sentinel_status = sentinel.get_status()
        ollama_state = sentinel_status.get("state", "unknown")
        is_healthy = sentinel_status.get("healthy", False)

        checks["ollama"] = {
            "status": ollama_state,
            "latency_ms": round((time.monotonic() - ollama_start) * 1000, 1),
            "model": sentinel_status.get("model", model_name),
            "last_probe_latency_ms": sentinel_status.get("last_latency_ms"),
        }

        if not is_healthy:
            # If Ollama is not HOT, mark as degraded
            if overall_status == "healthy":
                overall_status = "degraded"

    # ── 3. Disk space check (optional) ─────────────────────────────────────────
    try:
        disk_usage = shutil.disk_usage("/")
        free_gb = round(disk_usage.free / (1024 ** 3), 1)
        total_gb = round(disk_usage.total / (1024 ** 3), 1)
        used_percent = round((disk_usage.used / disk_usage.total) * 100, 1)

        disk_status = "ok"
        if used_percent > 90:
            disk_status = "warning"
            if overall_status == "healthy":
                overall_status = "degraded"

        checks["disk"] = {
            "status": disk_status,
            "free_gb": free_gb,
            "total_gb": total_gb,
            "used_percent": used_percent,
        }
    except Exception as e:
        checks["disk"] = {
            "status": f"error: {str(e)[:30]}",
        }

    response_time_ms = round((time.monotonic() - start_time) * 1000, 1)

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response_time_ms": response_time_ms,
        "checks": checks,
    }


@app.get("/api/llm-status")
async def llm_status():
    """
    Diagnostic endpoint — shows sentinel state, pulled models, hot models,
    and a plain-English diagnosis of why the LLM narrative may be falling back to Python.

    Usage from the VPS:
      curl http://localhost:8080/api/llm-status
    """
    from app.backend.services.llm_service import get_sentinel, is_ollama_cloud, get_ollama_headers

    sentinel = get_sentinel()
    if sentinel is None:
        return {"state": "unknown", "healthy": False, "message": "Sentinel not initialized"}

    ollama_url     = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    target_model   = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
    fast_model     = os.getenv("OLLAMA_FAST_MODEL", "qwen3.5:4b")
    is_cloud       = is_ollama_cloud(ollama_url)

    result: dict = {
        "ollama_url":            ollama_url,
        "narrative_model":       target_model,
        "fast_model":            fast_model,
        "mode":                  "cloud" if is_cloud else "local",
        "ollama_reachable":      False,
        "pulled_models":         [],
        "narrative_model_ready": False,
        "fast_model_ready":      False,
        "running_models":        [],
        "diagnosis":             "",
    }

    # Add sentinel status
    sentinel_status = sentinel.get_status()
    result["sentinel"] = sentinel_status

    # For Ollama Cloud, return early with cloud-specific status
    if is_cloud:
        result["ollama_reachable"] = True
        result["narrative_model_ready"] = True
        result["fast_model_ready"] = True
        result["diagnosis"] = f"Using Ollama Cloud with model: {target_model}"
        if sentinel_status.get("healthy"):
            result["diagnosis"] += " — Cloud connection is healthy."
        else:
            result["diagnosis"] += " — Cloud connection status unknown."
        return result

    # Local Ollama checks
    headers = get_ollama_headers(ollama_url)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            tags_resp = await client.get(f"{ollama_url}/api/tags", headers=headers)
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
                ps = await client.get(f"{ollama_url}/api/ps", headers=headers)
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
