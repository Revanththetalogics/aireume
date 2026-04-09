# Production Stability Overhaul — 20 Solutions

## Context
- Phase 1 security is complete (483 backend + 91 frontend tests passing)
- 3 recurring production issues persist: LLM timeout, name extraction, Ollama memory
- Full audit found 50 issues across 10 areas (6 CRITICAL, 13 HIGH, 25 MEDIUM, 10 LOW)
- VPS: 8-core CPU, no GPU, 14 GiB RAM, Docker Compose with Portainer

---

## P0 — Eliminate Recurring Issues (Solutions 1-4)

### Task 1: Decouple LLM from Request Lifecycle (Background Worker)

**File**: `app/backend/services/hybrid_pipeline.py`, `app/backend/routes/analyze.py`

Change the streaming pipeline so LLM runs as a fire-and-forget background task:
- `astream_hybrid_pipeline()` yields Python results immediately, then spawns `asyncio.create_task()` for LLM
- LLM task writes narrative to DB (`ScreeningResult.narrative_json` column) when done — no timeout pressure
- Add new endpoint `GET /api/analysis/{id}/narrative` for frontend polling
- Remove `asyncio.wait_for()` timeout wrapper — LLM takes however long it needs
- Keep `_build_fallback_narrative()` as the immediate response; LLM upgrades it asynchronously
- Add Alembic migration for `narrative_json` column on `ScreeningResult` if needed

**Frontend** (`app/frontend/src/components/ResultCard.jsx`, `app/frontend/src/pages/ReportPage.jsx`):
- After receiving Python results, poll `/api/analysis/{id}/narrative` every 10s
- When narrative arrives, merge into displayed result with smooth animation
- Show subtle "AI analysis enhancing report..." indicator while polling

### Task 2: spaCy NER Name Extraction (Replace Regex Heuristics)

**File**: `app/backend/services/parser_service.py`, `requirements.txt`

- Add `spacy` and `en_core_web_sm` to requirements.txt
- Add new Tier 0 function `_extract_name_ner(raw_text)`:
  - Load `en_core_web_sm` model (singleton, ~12MB)
  - Run NER on first 50 lines of resume
  - Extract first PERSON entity with confidence > 0.7
  - Return name string or None
- Update `enrich_parsed_resume()` call order: Tier 0 (NER) -> Tier 1 (header) -> Tier 2 (email) -> Tier 3 (relaxed)
- Add spaCy model download to `Dockerfile`: `RUN python -m spacy download en_core_web_sm`
- Add tests for name extraction with various resume formats

### Task 3: Active Ollama Health Sentinel (Backend-Side Probing)

**File**: `app/backend/main.py`, `app/backend/services/llm_service.py`

- Add background task in FastAPI lifespan that runs every 60s:
  - `POST /api/generate` with `num_predict=1` to Ollama
  - Track state enum: `COLD | WARMING | HOT | ERROR`
  - If `COLD` detected, auto-trigger warmup
  - Expose state via existing `/api/llm-status` endpoint
- Update health check to use sentinel state (not just `ollama list`)
- Remove dependency on sidecar warmup container (ollama-warmup service in docker-compose.prod.yml)
- Add `stop_grace_period: 60s` to backend service in docker-compose.prod.yml

### Task 4: Progressive Enhancement UI (Remove "LLM Offline" Stigma)

**File**: `app/frontend/src/components/ResultCard.jsx`

- Remove amber "Python scores only — LLM narrative unavailable" banner
- Replace with subtle "AI narrative loading..." indicator (only while polling from Task 1)
- If LLM never completes, show nothing — the Python report IS the report
- Python-generated `fit_summary`, `score_rationales`, `risk_flags` are the primary content
- LLM narrative sections (prose strengths/concerns) appear as "AI Enhanced" addon when available
- Remove `narrative_pending` flag from UI logic; replace with polling state

---

## P1 — Prevent Production Crashes Under Load (Solutions 11-14)

### Task 5: Database Connection Pooling and Transaction Safety

**File**: `app/backend/db/database.py`, `app/backend/routes/analyze.py`

- Add pool configuration to `create_engine()`:
  ```python
  pool_size=10, max_overflow=20, pool_recycle=3600, pool_pre_ping=True
  ```
- Wrap analysis pipeline DB operations in context managers with explicit rollback
- Fix usage check race condition: use `SELECT ... FOR UPDATE` or `db.execute(update(...).where(...))` atomic increment
- Fix usage increment order: validate files BEFORE incrementing quota

### Task 6: Batch Processing Concurrency Limiter

**File**: `app/backend/routes/analyze.py`

- Add `_BATCH_SEMAPHORE = asyncio.Semaphore(5)` module-level
- Wrap each `_process_single_resume()` call with semaphore acquire
- Check usage limits BEFORE reading files into memory (move `_check_and_increment_usage` before file loop)
- Track per-file success/failure; return `{"results": [...], "failed": [{"filename": "x.pdf", "error": "corrupt PDF"}]}`
- Add max batch size constant: `MAX_BATCH_SIZE = 50`

### Task 7: SSE Streaming Hardening

**File**: `app/backend/routes/analyze.py`

- Add client disconnect detection: wrap generator with `request.is_disconnected()` check
- Save result to DB early (after Python phase), update with LLM results later
- Always yield `data: [DONE]\n\n` in exception handlers
- Add `finally` block to clean up resources on disconnect
- Add max JD size validation: reject JDs > 50KB (currently unbounded)

### Task 8: Comprehensive Error Logging

**File**: `app/backend/services/parser_service.py`, `app/backend/routes/analyze.py`, all route files

- Replace ALL bare `except Exception: pass` with `logging.exception("context")` — 15+ locations in parser_service.py, 8+ in analyze.py
- Add structured log format with request correlation ID
- Add `logging.warning()` for non-fatal degradations (cache miss, fallback triggered)
- Keep `except` blocks that are intentionally swallowing errors, but add log line

---

## P2 — UX Resilience and Zero-Downtime Deploys (Solutions 15-17)

### Task 9: React Error Boundaries + API Retry Logic

**File**: `app/frontend/src/App.jsx`, `app/frontend/src/lib/api.js`, new `app/frontend/src/components/ErrorBoundary.jsx`

- Create `ErrorBoundary` component that catches render errors, shows friendly "Something went wrong" UI with retry button
- Wrap all `<Routes>` in App.jsx with ErrorBoundary
- Add axios retry interceptor for 5xx and network errors: 3 retries, exponential backoff (1s, 2s, 4s)
- Map backend error codes to user-friendly messages (e.g., "CSRF token missing" -> "Session expired, please refresh")
- Add `window.onerror` and `unhandledrejection` handlers for uncaught errors

### Task 10: Graceful Deployment with Zero-Downtime

**File**: `docker-compose.prod.yml`

- Add `stop_grace_period: 60s` to backend service
- Add `stop_grace_period: 30s` to nginx service
- Configure Watchtower with `--rolling-restart` flag if available, or sequential restart order
- Add uvicorn `--timeout-graceful-shutdown 30` to CMD
- Ensure nginx upstream uses `least_conn` for load balancing across workers

### Task 11: Health Check Enhancement

**File**: `app/backend/main.py`, `docker-compose.prod.yml`

- Split health into two endpoints:
  - `GET /health` (shallow) — process alive, used by nginx/Docker
  - `GET /api/health/deep` — checks DB query, Ollama model loaded, disk space
- Update Docker health check to use shallow endpoint (fast, reliable)
- Update `/api/llm-status` to return sentinel state from Task 3
- Add response time tracking to deep health check

---

## P3 — Security Hardening and Scalability (Solutions 18-20)

### Task 12: Token Revocation + CSRF Rotation

**File**: `app/backend/routes/auth.py`, `app/backend/middleware/auth.py`, `app/backend/models/db_models.py`

- Add `RevokedToken` table (id, jti, revoked_at, expires_at)
- On logout: insert refresh token JTI into revocation table
- On refresh: check revocation table before issuing new access token
- Add periodic cleanup task: delete expired revoked tokens (older than refresh TTL)
- Rotate CSRF token on each authenticated POST/PUT/DELETE request
- Add Alembic migration for RevokedToken table

### Task 13: Pagination and Query Optimization

**File**: `app/backend/routes/candidates.py`, `app/backend/routes/templates.py`, `app/backend/models/db_models.py`

- Add `limit` and `offset` query params to all list endpoints (default limit=50, max=200)
- Fix N+1 in candidates: use `joinedload(Candidate.screening_results)` or `subqueryload()`
- Add database indexes:
  - `Candidate.tenant_id` (if missing)
  - `ScreeningResult.candidate_id`
  - `ScreeningResult.created_at` (for sorting)
  - `JdCache.hash` (unique index)
- Add `created_at` column to JdCache for TTL-based eviction

### Task 14: JD Cache Eviction + Request Size Limits

**File**: `app/backend/routes/analyze.py`, `app/backend/main.py`

- Add `created_at` timestamp to JdCache model
- Add periodic cleanup: delete JdCache entries older than 30 days (background task every 24h)
- Add request size validation:
  - JD text: max 50KB (~10,000 words)
  - `scoring_weights` form param: max 4KB
  - Already has file size limit (10MB) — keep as-is
- Add Alembic migration for JdCache.created_at column

### Task 15: Observability Foundation (Structured Logging + Metrics)

**File**: `app/backend/main.py`, `requirements.txt`

- Add `prometheus-fastapi-instrumentator` to requirements
- Add `/metrics` endpoint with auto-instrumented request latency, status codes, in-flight requests
- Add custom metrics:
  - `aria_llm_call_duration_seconds` (histogram)
  - `aria_llm_fallback_total` (counter)
  - `aria_resume_parse_duration_seconds` (histogram)
  - `aria_batch_size` (histogram)
- Configure structured JSON logging format for production (replace print statements)
- Add request ID middleware that injects correlation ID into all log messages

---

## Execution Order and Dependencies

```
P0 (parallel where possible):
  Task 1 (background LLM)     -- foundation, changes streaming architecture
  Task 2 (spaCy names)        -- independent, parser only
  Task 3 (Ollama sentinel)    -- independent, main.py only
  Task 4 (progressive UI)     -- depends on Task 1 (polling endpoint)

P1 (after P0 complete):
  Task 5 (DB pooling)         -- independent
  Task 6 (batch limiter)      -- independent
  Task 7 (SSE hardening)      -- depends on Task 1 (streaming changes)
  Task 8 (error logging)      -- independent

P2 (after P1):
  Task 9 (error boundaries)   -- independent frontend
  Task 10 (graceful deploy)   -- independent Docker config
  Task 11 (health check)      -- depends on Task 3 (sentinel state)

P3 (after P2):
  Task 12 (token revocation)  -- independent auth
  Task 13 (pagination)        -- independent DB
  Task 14 (cache eviction)    -- independent
  Task 15 (observability)     -- independent, last to avoid noise during other changes
```

## Testing Strategy
- Each task runs full backend test suite (483+) and frontend suite (91+)
- Tasks adding new functionality include new test cases
- P0 tasks require production validation on VPS after deploy
- Final integration test after each priority tier is complete

## Risk Notes
- Task 1 (background LLM) is the largest architectural change — needs careful testing
- Task 2 (spaCy) adds ~50MB to Docker image size — acceptable tradeoff
- Task 12 (token revocation) requires Alembic migration — coordinate with deploy
- Task 15 (observability) adds Prometheus dependency — optional if VPS resources are tight
