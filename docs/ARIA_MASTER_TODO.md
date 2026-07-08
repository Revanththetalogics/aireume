# ARIA v2.0.0 — Master Remediation Todo List
**Source:** Full-stack audit (Backend + Security + Architecture + UI/UX)  
**Generated:** July 6, 2026  
**Total Items:** 113 actionable tasks across 4 priority tiers

---

## HOW TO USE THIS LIST

| Tier | SLA | Definition |
|------|-----|------------|
| 🔴 P0 — Critical | Fix before any enterprise demo or production traffic | Functional bugs, active security vulnerabilities, data leakage |
| 🟠 P1 — High | Complete within Sprint 1–2 (Week 1–4) | Serious UX breaks, compliance gaps, scalability blockers |
| 🟡 P2 — Medium | Complete within Sprint 3–6 (Week 5–12) | Quality gaps, missing features, performance, maintainability |
| 🟢 P3 — Low | Backlog / nice-to-have (Week 13+) | Polish, minor a11y, developer experience |

Each item includes:
- **ID** — unique reference (use in PR titles and commit messages)
- **Area** — domain it belongs to
- **Task** — what to do
- **Files** — which files to change
- **Effort** — S (< 2h), M (2–8h), L (1–3d), XL (3d+)

---

## 🔴 P0 — CRITICAL (Fix Before Production)

### Security

- [ ] **P0-SEC-01** · Secrets in `.env.example`
  - **Task:** Rotate all committed credentials. Replace JWT secret, Ollama API key, and SIP phone number with placeholder strings (`REPLACE_WITH_...`). Run `gitleaks` against full git history.
  - **Files:** `.env.example`
  - **Effort:** S

- [ ] **P0-SEC-02** · Unauthenticated internal API endpoints
  - **Task:** Add shared `INTERNAL_SERVICE_SECRET` header validation to all `/api/voice/internal/*`, `/api/recruiter/internal/*`, and `/api/interviews/internal/*` endpoints.
  - **Files:** `app/backend/routes/voice.py`, `app/backend/routes/recruiter.py`, `app/backend/routes/interviews.py`
  - **Effort:** M

- [ ] **P0-SEC-03** · `PATCH /sessions/{id}` has no authentication
  - **Task:** Add JWT auth dependency and a typed Pydantic schema (replacing `body: dict`) to the voice session update endpoint.
  - **Files:** `app/backend/routes/voice.py` (line 550)
  - **Effort:** S

- [ ] **P0-SEC-04** · CSRF middleware silent bypass
  - **Task:** Replace the silent bypass (lines 84–87 in `csrf.py`) with a 403 rejection when `access_token` cookie is present but `csrf_token` cookie is absent.
  - **Files:** `app/backend/middleware/csrf.py`
  - **Effort:** S

- [ ] **P0-SEC-05** · No access token revocation on logout
  - **Task:** Add JTI claim to access tokens at issuance. Store JTI in `RevokedToken` on logout. Check JTI in `get_current_user` on every request.
  - **Files:** `app/backend/routes/auth.py`, `app/backend/middleware/auth.py`, `app/backend/models/db_models.py`
  - **Effort:** M

- [ ] **P0-SEC-06** · `console.log` debug leak in production (`ReportPage`)
  - **Task:** Remove `console.log('[ReportPage] Using complete result from state')` at line ~470. Add `vite-plugin-remove-console` to `vite.config.js` for production builds.
  - **Files:** `app/frontend/src/pages/ReportPage.jsx`, `app/frontend/vite.config.js`, `app/frontend/package.json`
  - **Effort:** S

### Functional Bugs

- [ ] **P0-BUG-01** · Login `tenantSlug` never sent to API
  - **Task:** Update `AuthContext.login()` to accept and forward `tenant_slug`. Update `LoginPage.jsx` to pass the collected value to the context call.
  - **Files:** `app/frontend/src/contexts/AuthContext.jsx`, `app/frontend/src/pages/LoginPage.jsx`
  - **Effort:** S

- [ ] **P0-BUG-02** · Score threshold inconsistency (Dashboard vs constants)
  - **Task:** Remove the inline threshold from `DashboardNew.jsx` `ScoreRing`. Import and use `getScoreColor()` from `constants.js` everywhere a score color is computed.
  - **Files:** `app/frontend/src/pages/DashboardNew.jsx`, `app/frontend/src/lib/constants.js`
  - **Effort:** S

- [ ] **P0-BUG-03** · Duplicate Alembic revision `036` breaks clean deploys
  - **Task:** Run `alembic history` to identify the true revision IDs. Rename and renumber the conflicting migration file. Verify no other duplicate revision IDs exist.
  - **Files:** `alembic/036_fix_audit_tenant_id.py` or `alembic/036_queue_lease_locking.py`
  - **Effort:** M

- [ ] **P0-BUG-04** · `create_all()` runs alongside Alembic (schema drift risk)
  - **Task:** Remove `Base.metadata.create_all(bind=engine)` from the FastAPI lifespan in `main.py`. Rely exclusively on `alembic upgrade head` via `docker-entrypoint.sh`.
  - **Files:** `app/backend/main.py`
  - **Effort:** S

### UX Critical

- [ ] **P0-UX-01** · No route-level error boundaries
  - **Task:** Wrap every lazy-loaded route in `App.jsx` with an `<ErrorBoundary>` component so a page crash does not unmount the NavBar or lose in-progress work.
  - **Files:** `app/frontend/src/App.jsx`
  - **Effort:** S

- [ ] **P0-UX-02** · `SecurityEventsPage` silently swallows fetch errors
  - **Task:** Add `error` state. On fetch failure call `setError(...)`. Render an error banner with a Retry button above the table.
  - **Files:** `app/frontend/src/pages/admin/SecurityEventsPage.jsx`
  - **Effort:** S

- [ ] **P0-UX-03** · `FeatureFlagsPage` is a misleading re-export
  - **Task:** Either (a) build a real global feature flag toggle page that calls `toggleFeatureFlag()`, or (b) fix the navigation label to "Plan Features" to match the actual `PlanFeaturesPage` content. Fix the route in `AdminLayout`.
  - **Files:** `app/frontend/src/pages/admin/FeatureFlagsPage.jsx`, `app/frontend/src/layouts/AdminLayout.jsx`
  - **Effort:** M

---

## 🟠 P1 — HIGH (Sprint 1–2, Weeks 1–4)

### Security — High

- [ ] **P1-SEC-01** · Rate limiting not Redis-backed (6-worker bypass)
  - **Task:** Replace in-memory token bucket in `rate_limit.py` with Redis-backed atomic counter using `fastapi-limiter` or `redis-py` Lua scripts. Add `REDIS_URL` to env config.
  - **Files:** `app/backend/middleware/rate_limit.py`, `docker-compose.yml`, `docker-compose.prod.yml`, `requirements.txt`
  - **Effort:** L

- [ ] **P1-SEC-02** · Prometheus `/metrics` endpoint publicly accessible
  - **Task:** Add nginx `allow` rules restricting `/metrics` to internal monitoring IPs, or add HTTP basic auth to the Prometheus scrape endpoint.
  - **Files:** `nginx/nginx.prod.conf`, `app/backend/main.py`
  - **Effort:** S

- [ ] **P1-SEC-03** · OpenAPI docs exposed in production
  - **Task:** Set `docs_url=None, redoc_url=None, openapi_url=None` when `ENVIRONMENT=production`.
  - **Files:** `app/backend/main.py`
  - **Effort:** S

- [ ] **P1-SEC-04** · Temporary password returned in admin user creation response
  - **Task:** Remove `temporary_password` from the API response. Send a password reset email link instead.
  - **Files:** `app/backend/routes/admin.py`, `app/backend/services/admin_service.py`
  - **Effort:** S

- [ ] **P1-SEC-05** · SSRF risk in JD URL scraping
  - **Task:** Before fetching, validate URL scheme (allow only `http://`, `https://`), resolve hostname, reject private IP ranges (10.x, 172.16–31.x, 192.168.x, 127.x, 169.254.x). Consider domain allowlist.
  - **Files:** `app/backend/routes/jd_url.py`, `app/backend/services/jd_extractor_service.py`
  - **Effort:** M

- [ ] **P1-SEC-06** · SSRF risk in video URL processing
  - **Task:** Validate URL scheme and reject private IP ranges before passing to yt-dlp. Run yt-dlp in subprocess with restricted network access.
  - **Files:** `app/backend/routes/video.py`, `app/backend/services/video_service.py`
  - **Effort:** M

- [ ] **P1-SEC-07** · CORS OPTIONS wildcard in nginx
  - **Task:** Remove the OPTIONS handler that sets `Access-Control-Allow-Origin: *`. Let FastAPI's CORS middleware handle both preflight and actual requests.
  - **Files:** `nginx/nginx.prod.conf`
  - **Effort:** S

- [ ] **P1-SEC-08** · No malware scanning on file upload
  - **Task:** Add ClamAV as a Docker sidecar. Scan all uploaded files before parsing. Reject files that fail with HTTP 422.
  - **Files:** `app/backend/routes/upload.py`, `app/backend/services/parser_service.py`, `docker-compose.yml`
  - **Effort:** L

- [ ] **P1-SEC-09** · Prompt injection not sanitized before LLM embedding
  - **Task:** Before embedding resume/JD text into prompts, strip known injection patterns. Wrap candidate content in XML role-demarcated sections. Log detection events.
  - **Files:** `app/backend/services/hybrid_pipeline.py`, `app/backend/services/guardrail_service.py`
  - **Effort:** M

- [ ] **P1-SEC-10** · Add security scanning to CI pipeline
  - **Task:** Add `gitleaks` (secret scan), `pip-audit` (Python CVEs), `npm audit` (JS CVEs), and Trivy (container image scan) to CI/CD workflows.
  - **Files:** `.github/workflows/ci.yml`, `.github/workflows/cd.yml`
  - **Effort:** M

### Compliance — High

- [ ] **P1-COMP-01** · No candidate consent records
  - **Task:** Create `CandidateConsent` table with `candidate_id`, `consent_type`, `consented_at`, `consent_version`, `consent_ip`, `withdrawal_at`. Write migration. Gate AI processing behind consent check.
  - **Files:** `app/backend/models/db_models.py`, `alembic/` (new migration), `app/backend/routes/candidates.py`
  - **Effort:** L

- [ ] **P1-COMP-02** · No AI decision audit trail
  - **Task:** Create `AIDecisionLog` table with model name, prompt version, prompt hash, raw LLM output, guardrails triggered, fallback used, final score. Populate on every `ScreeningResult` write.
  - **Files:** `app/backend/models/db_models.py`, `alembic/` (new migration), `app/backend/services/hybrid_pipeline.py`
  - **Effort:** L

### DevOps — High

- [ ] **P1-OPS-01** · No database migration step in CD pipeline
  - **Task:** Add `alembic upgrade head` as an explicit step in `cd.yml` before Watchtower promotion. Add failure alerting and rollback documentation.
  - **Files:** `.github/workflows/cd.yml`
  - **Effort:** M

- [ ] **P1-OPS-02** · `AnalysisJob` ORM model not in `db_models.py`
  - **Task:** Move `AnalysisJob`, `AnalysisArtifact`, `WorkerHeartbeat` from `queue_manager.py` into `db_models.py`. Verify Alembic imports all models. Run `alembic check`.
  - **Files:** `app/backend/services/queue_manager.py`, `app/backend/models/db_models.py`, `alembic/env.py`
  - **Effort:** M

- [ ] **P1-OPS-03** · No E2E tests in CI pipeline
  - **Task:** Add Playwright E2E test stage to `ci.yml` using Docker Compose test environment with health-check gate.
  - **Files:** `.github/workflows/ci.yml`, `e2e/`
  - **Effort:** L

- [ ] **P1-OPS-04** · Watchtower polling every 60s — no approval gate
  - **Task:** Add a manual approval step in the CD workflow (`environment: production` with required reviewer). Change Watchtower interval to 300s minimum.
  - **Files:** `.github/workflows/cd.yml`, `docker-compose.prod.yml`
  - **Effort:** M

### Database — High

- [ ] **P1-DB-01** · Add performance indexes for candidate queries
  - **Task:** Create via Alembic: composite index on `(tenant_id, status)` for candidates, GIN index on `skills` JSONB, composite index on `(tenant_id, created_at DESC)` for `screening_results`.
  - **Files:** `alembic/` (new migration)
  - **Effort:** M

- [ ] **P1-DB-02** · Add score range check constraint
  - **Task:** Add `CHECK (fit_score >= 0 AND fit_score <= 100)` on all score columns in `ScreeningResult`.
  - **Files:** `alembic/` (new migration), `app/backend/models/db_models.py`
  - **Effort:** S

- [ ] **P1-DB-03** · Subscription quota race condition (check-and-increment)
  - **Task:** Replace read-then-write quota check with atomic `SELECT ... FOR UPDATE` or Redis `INCR` with limit comparison.
  - **Files:** `app/backend/services/quota_service.py`, `app/backend/routes/analyze.py`
  - **Effort:** M

### Backend — High

- [ ] **P1-BE-01** · Database connection pool not reading env var
  - **Task:** Read `DATABASE_POOL_SIZE` from env var in `database.py`. Set per-worker default to 5 to prevent exhausting PostgreSQL `max_connections` at 6 workers.
  - **Files:** `app/backend/db/database.py`
  - **Effort:** S

- [ ] **P1-BE-02** · Stripe webhook replay attack risk
  - **Task:** Check processed Stripe event IDs against the `WebhookDelivery` table on every webhook receipt. Return 200 without re-processing if already handled.
  - **Files:** `app/backend/routes/billing.py`, `app/backend/services/billing_service.py`
  - **Effort:** M

- [ ] **P1-BE-03** · LLM JSON output not fully validated (unhandled 500 risk)
  - **Task:** Wrap all LLM JSON parsing in Pydantic model validation. On parse failure, use deterministic fallback and log the raw output to `AIDecisionLog`. Never surface raw LLM errors to frontend.
  - **Files:** `app/backend/services/hybrid_pipeline.py`, `app/backend/services/guardrail_service.py`
  - **Effort:** M

### UX — High

- [ ] **P1-UX-01** · Modal dialogs have no focus trap or ARIA semantics
  - **Task:** Add `focus-trap-react` package. Update `ModalOverlay.jsx` with `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, Escape key handler, and `<FocusTrap>` wrapper. Apply to all modal components.
  - **Files:** `app/frontend/src/components/motion/ModalOverlay.jsx`, all modal components
  - **Effort:** L

- [ ] **P1-UX-02** · Icon-only buttons have no `aria-label`
  - **Task:** Create `IconButton` wrapper component with required `aria-label` prop. Replace all icon-only `<button>` elements throughout the app.
  - **Files:** `app/frontend/src/components/ui/IconButton.jsx` (new), all pages with icon buttons
  - **Effort:** L

- [ ] **P1-UX-03** · Password visibility toggles not accessible
  - **Task:** Add `aria-label={showPw ? "Hide password" : "Show password"}` and `aria-pressed={showPw}` to eye-toggle buttons on all auth pages.
  - **Files:** `app/frontend/src/pages/LoginPage.jsx`, `RegisterPage.jsx`, `ResetPasswordPage.jsx`
  - **Effort:** S

- [ ] **P1-UX-04** · No skip-to-content link (keyboard navigation broken)
  - **Task:** Add a visually hidden skip link as the first element in `AppShell.jsx`. Add `id="main-content"` to the `<main>` element.
  - **Files:** `app/frontend/src/components/AppShell.jsx`, `app/frontend/src/layouts/AdminLayout.jsx`
  - **Effort:** S

- [ ] **P1-UX-05** · Empty states applied inconsistently (only 3 of 20+ pages)
  - **Task:** Apply `<EmptyState>` component to: `ComparePage`, `TranscriptPage`, `VideoPage`, `TeamPage`, `AnalyticsPage`, `InterviewPage`, `VoiceScreeningPage`, `RecruiterInterviewPage`. Each empty state must have a meaningful CTA.
  - **Files:** All listed page components
  - **Effort:** M

- [ ] **P1-UX-06** · Admin tables overflow on mobile (no horizontal scroll)
  - **Task:** Wrap all admin `<table>` elements in `<div className="overflow-x-auto w-full">`.
  - **Files:** `app/frontend/src/pages/admin/TenantsPage.jsx`, `UsersPage.jsx`, `AuditLogPage.jsx`, `PlanManagementPage.jsx`, and all other admin tables
  - **Effort:** S

- [ ] **P1-UX-07** · SSE stream has no reconnection or failure UX
  - **Task:** Add `onerror` reconnect logic with exponential backoff to the SSE client. Show "Connection lost — reconnecting…" toast. After 3 failures, show persistent error with link to results page.
  - **Files:** `app/frontend/src/lib/api.js`, `app/frontend/src/pages/AnalyzePage.jsx`
  - **Effort:** M

- [ ] **P1-UX-08** · `SessionTimeoutModal` not accessible to screen readers
  - **Task:** Add `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to modal title, and `aria-live="assertive"` on the countdown element.
  - **Files:** `app/frontend/src/components/SessionTimeoutModal.jsx`
  - **Effort:** S

- [ ] **P1-UX-09** · Three overlapping interview UX flows
  - **Task:** Consolidate to `InterviewPage.jsx` as the single entry point. Add redirects from `/voice-screening` and `/recruiter-interviews` to `/ai-interviews`. Remove legacy routes from NavBar.
  - **Files:** `app/frontend/src/App.jsx`, `app/frontend/src/components/NavBar.jsx`
  - **Effort:** M

- [ ] **P1-UX-10** · Data tables have no semantic headers
  - **Task:** Add `scope="col"` to all `<th>` header cells. Add `scope="row"` to row identifier cells. Add `<caption className="sr-only">` with descriptive names to all `<table>` elements.
  - **Files:** All page components with `<table>` elements
  - **Effort:** M

- [ ] **P1-UX-11** · i18n infrastructure is dead code
  - **Task:** Either install `i18next` + `react-i18next`, import `src/i18n/index.js` from `main.jsx`, and migrate high-priority strings — or delete `src/i18n/index.js` to remove the broken dead code.
  - **Files:** `app/frontend/src/i18n/index.js`, `app/frontend/src/main.jsx`, `app/frontend/package.json`
  - **Effort:** M (remove) / XL (implement)

- [ ] **P1-UX-12** · `@future-use` admin APIs never wired to UI
  - **Task:** Wire `addUserToTenant` and `removeUserFromTenant` to `TenantDetailPage` users tab. Wire `getTenantRateLimit` to `RateLimitsPage`.
  - **Files:** `app/frontend/src/pages/admin/TenantDetailPage.jsx`, `app/frontend/src/pages/admin/RateLimitsPage.jsx`
  - **Effort:** M

- [ ] **P1-UX-13** · Notification system is non-functional
  - **Task:** Wire `setNotifications` in `NotificationContext` to analysis completion, invite receipt, and subscription limit events. Add notification bell to NavBar with count badge and dropdown.
  - **Files:** `app/frontend/src/contexts/NotificationContext.jsx`, `app/frontend/src/components/NavBar.jsx`
  - **Effort:** L

- [ ] **P1-UX-14** · Keyboard shortcuts undiscoverable
  - **Task:** Add `?` shortcut to open a `KeyboardShortcutsModal`. Show `⌘K` hint next to search icon in NavBar. Show `J↓ K↑` hints in candidate list footer.
  - **Files:** `app/frontend/src/components/NavBar.jsx`, new `KeyboardShortcutsModal.jsx`
  - **Effort:** M

- [ ] **P1-UX-15** · `NavBar` missing `aria-current="page"` on active route
  - **Task:** Add `aria-current={isActive ? "page" : undefined}` to all active navigation links.
  - **Files:** `app/frontend/src/components/NavBar.jsx`
  - **Effort:** S

---

## 🟡 P2 — MEDIUM (Sprint 3–6, Weeks 5–12)

### Security — Medium

- [ ] **P2-SEC-01** · Missing `Content-Security-Policy` header
  - **Task:** Add CSP header in nginx: `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://ollama.com`.
  - **Files:** `nginx/nginx.prod.conf`
  - **Effort:** M

- [ ] **P2-SEC-02** · Missing security headers (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`)
  - **Task:** Add the missing HTTP security headers in nginx config.
  - **Files:** `nginx/nginx.prod.conf`
  - **Effort:** S

- [ ] **P2-SEC-03** · Candidate ID enumeration via sequential integers
  - **Task:** Migrate candidate IDs to UUIDs. Update all FK references. Write and test the migration. Update all route parameters.
  - **Files:** `app/backend/models/db_models.py`, `alembic/` (new migration), all route files referencing candidate IDs
  - **Effort:** XL

- [ ] **P2-SEC-04** · Brute force protection bypassed in multi-worker setup
  - **Task:** Move per-IP auth rate limiting (login/register/forgot-password) to Redis-backed counter so limits are shared across all 6 uvicorn workers.
  - **Files:** `app/backend/routes/auth.py`, `app/backend/middleware/rate_limit.py`
  - **Effort:** M

- [ ] **P2-SEC-05** · Admin impersonation audit trail may lose admin identity
  - **Task:** Ensure all `AuditLog` entries written during impersonation sessions include both `impersonated_by: admin_user_id` and `user_id: impersonated_user_id`.
  - **Files:** `app/backend/routes/admin.py`, `app/backend/services/audit_service.py`
  - **Effort:** M

- [ ] **P2-SEC-06** · No `robots.txt` blocking admin routes
  - **Task:** Add `robots.txt` disallowing `/admin`, `/api`, `/docs`, `/metrics`.
  - **Files:** `nginx/nginx.prod.conf`, add static `robots.txt`
  - **Effort:** S

- [ ] **P2-SEC-07** · Production debug scripts in repository root
  - **Task:** Move or delete all `debug_*.py`, `test_*.py`, `verify_*.py` files from the repository root. Any useful logic should be in `scripts/` or `tests/`.
  - **Files:** Root-level debug/test scripts
  - **Effort:** S

### Compliance — Medium

- [ ] **P2-COMP-01** · No data retention policy engine
  - **Task:** Create `DataRetentionPolicy` table per tenant. Add APScheduler job that runs nightly and marks expired records. Provide UI for tenants to configure retention windows.
  - **Files:** `app/backend/models/db_models.py`, `alembic/`, `app/backend/services/`, admin UI
  - **Effort:** XL

- [ ] **P2-COMP-02** · No GDPR Right-to-Access report for candidates
  - **Task:** Build a structured JSON export endpoint for all data held about a specific candidate (`GET /api/candidates/{id}/data-export`).
  - **Files:** `app/backend/routes/candidates.py`, `app/backend/services/gdpr_service.py`
  - **Effort:** L

- [ ] **P2-COMP-03** · No AI decision explanation for candidates
  - **Task:** Build an explanation endpoint that returns a human-readable explanation of why a score was assigned (`GET /api/results/{id}/explanation`), drawing from `AIDecisionLog`.
  - **Files:** `app/backend/routes/analyze.py`, `app/backend/services/hybrid_pipeline.py`
  - **Effort:** L

- [ ] **P2-COMP-04** · No HITL gate before automated hire/reject recommendation
  - **Task:** Require recruiter confirmation before AI recommendation changes candidate pipeline status to "Reject." Log the confirmation with timestamp and user ID.
  - **Files:** `app/backend/routes/candidates.py`, `app/frontend/src/pages/CandidatesPage.jsx`
  - **Effort:** L

- [ ] **P2-COMP-05** · No breach log table
  - **Task:** Create `BreachLog` table. Build admin UI for logging and tracking data breach incidents including authority notification and subject notification timestamps.
  - **Files:** `app/backend/models/db_models.py`, `alembic/`, `app/backend/routes/admin.py`
  - **Effort:** L

- [x] **P2-COMP-06** · LLM processing sends candidate PII to Ollama Cloud without explicit disclosure
  - **Done:** Onboarding acknowledgment checkbox + Settings → Security → AI & data processing section (`uxLabels.TRUST`, `OnboardingWizard`, `SettingsPage`).

### DevOps — Medium

- [ ] **P2-OPS-01** · Docker Hub images use `latest` tag
  - **Task:** Replace `latest` image tags in `docker-compose.prod.yml` with immutable SHA digest tags or versioned tags (e.g., `v2.0.1-abc1234`).
  - **Files:** `docker-compose.prod.yml`, `.github/workflows/cd.yml`
  - **Effort:** M

- [ ] **P2-OPS-02** · ollama-warmup hardcodes model name
  - **Task:** Replace hardcoded `gemma4:31b` in the ollama-warmup sidecar command with `${OLLAMA_MODEL}` variable.
  - **Files:** `docker-compose.prod.yml`
  - **Effort:** S

- [ ] **P2-OPS-03** · No automated PostgreSQL backup
  - **Task:** Add a scheduled `pg_dump` job (daily full, weekly encrypted upload to S3). Document restore procedure. Add backup status to admin monitoring dashboard.
  - **Files:** `docker-compose.prod.yml`, new backup script
  - **Effort:** L

- [ ] **P2-OPS-04** · No Grafana + Alertmanager configuration
  - **Task:** Add Grafana and Alertmanager to `docker-compose.prod.yml`. Create a pre-built dashboard for LLM latency, fallback rate, queue depth, error rate, DB connections. Add alerts for critical thresholds.
  - **Files:** `docker-compose.prod.yml`, new `grafana/` and `alertmanager/` config directories
  - **Effort:** XL

- [ ] **P2-OPS-05** · Add PgBouncer connection pooler
  - **Task:** Add PgBouncer as a service in `docker-compose.prod.yml`. Update `DATABASE_URL` to point to PgBouncer. Set per-worker SQLAlchemy `pool_size` to 3.
  - **Files:** `docker-compose.prod.yml`, `app/backend/db/database.py`
  - **Effort:** M

- [ ] **P2-OPS-06** · Add Redis to infrastructure
  - **Task:** Add Redis to `docker-compose.yml` and `docker-compose.prod.yml`. Provides shared state for rate limiting (P1-SEC-01), session management, and LLM concurrency coordination.
  - **Files:** `docker-compose.yml`, `docker-compose.prod.yml`
  - **Effort:** M

- [ ] **P2-OPS-07** · No OpenTelemetry distributed tracing
  - **Task:** Add `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `opentelemetry-instrumentation-fastapi`. Create spans in `hybrid_pipeline.py` phases. Export to Grafana Tempo or Jaeger.
  - **Files:** `requirements.txt`, `app/backend/main.py`, `app/backend/services/hybrid_pipeline.py`
  - **Effort:** L

### Backend — Medium

- [ ] **P2-BE-01** · Dead letter queue for failed analysis jobs
  - **Task:** Add max retry count (3). After max retries, set status to `dead_letter`. Emit a Prometheus alert. Add admin visibility to dead-letter jobs.
  - **Files:** `app/backend/services/queue_manager.py`, `app/backend/routes/queue_api.py`
  - **Effort:** M

- [ ] **P2-BE-02** · Access token expiry default mismatch (5 min vs 60 min)
  - **Task:** Align code default for `ACCESS_TOKEN_EXPIRE_MINUTES` to 15 minutes. Update `.env.example` to 15 minutes. Document the security trade-off.
  - **Files:** `app/backend/routes/auth.py`, `.env.example`
  - **Effort:** S

- [ ] **P2-BE-03** · No API versioning prefix
  - **Task:** Add `/api/v2/` prefix to all routes. Maintain current paths as deprecated aliases for 6 months with `Deprecation` and `Sunset` headers.
  - **Files:** All 28 route modules, `app/backend/main.py`
  - **Effort:** XL

- [ ] **P2-BE-04** · SSE connection not cleaned up on client disconnect
  - **Task:** Implement `asyncio.CancelledError` handling in the SSE generator. Cancel the underlying LLM call on client disconnect. Track active SSE connections per tenant.
  - **Files:** `app/backend/routes/analyze.py`
  - **Effort:** M

- [ ] **P2-BE-05** · No idempotency keys on analysis endpoints
  - **Task:** Accept optional `Idempotency-Key` header on `POST /api/analyze` and `POST /api/analyze/batch`. Store processed keys in an `IdempotencyKey` table with TTL. Return cached result for duplicates.
  - **Files:** `app/backend/routes/analyze.py`, `app/backend/models/db_models.py`, `alembic/`
  - **Effort:** L

- [ ] **P2-BE-06** · LLM prompt token budget not enforced
  - **Task:** Add `MAX_RESUME_TOKENS` limit before LLM prompt construction. Truncate/chunk resume text to fit within the budget. Log when truncation occurs.
  - **Files:** `app/backend/services/hybrid_pipeline.py`
  - **Effort:** M

- [ ] **P2-BE-07** · Resume BYTEA storage still active (DB bloat)
  - **Task:** Deprecate the BYTEA path in `Candidate` model. Require S3/MinIO for all deployments. Add MinIO to `docker-compose.yml` as default object storage. Provide a migration script to move existing BLOBs.
  - **Files:** `app/backend/models/db_models.py`, `alembic/`, `docker-compose.yml`
  - **Effort:** XL

- [ ] **P2-BE-08** · SP-initiated SAML logout (SLO) missing
  - **Task:** Implement SAML SLO: `LogoutRequest` generation, `LogoutResponse` processing, and session binding in the SSO service.
  - **Files:** `app/backend/routes/sso.py`, `app/backend/services/sso_service.py`
  - **Effort:** L

- [ ] **P2-BE-09** · Training endpoint accessible in production (WIP feature)
  - **Task:** Gate `/api/training/train` with a `FeatureFlag` that is disabled by default in production. Add UI messaging that fine-tuning is in beta.
  - **Files:** `app/backend/routes/training.py`, `app/frontend/src/pages/TeamPage.jsx`
  - **Effort:** S

- [ ] **P2-BE-10** · Webhook retry without exponential backoff
  - **Task:** Implement exponential backoff retry (1s, 5s, 30s, 5m, 30m) for failed webhook deliveries. After max retries, alert tenant admin and disable the endpoint.
  - **Files:** `app/backend/services/webhook_service.py`
  - **Effort:** M

- [ ] **P2-BE-11** · Password policy enforcement not confirmed
  - **Task:** Enforce minimum 12 characters, complexity requirements. Optionally check HaveIBeenPwned API with k-anonymity.
  - **Files:** `app/backend/routes/auth.py`
  - **Effort:** M

### Database — Medium

- [ ] **P2-DB-01** · No `BreachLog` table
  - **Task:** See P2-COMP-05 — create the table via migration.
  - **Files:** `app/backend/models/db_models.py`, `alembic/`
  - **Effort:** M

- [ ] **P2-DB-02** · No `IdempotencyKey` table
  - **Task:** See P2-BE-05 — create the table via migration.
  - **Files:** `app/backend/models/db_models.py`, `alembic/`
  - **Effort:** S

- [ ] **P2-DB-03** · No `DataRetentionPolicy` table
  - **Task:** See P2-COMP-01 — create the table via migration.
  - **Files:** `app/backend/models/db_models.py`, `alembic/`
  - **Effort:** M

- [ ] **P2-DB-04** · Add PostgreSQL row-level security (RLS) as defense-in-depth
  - **Task:** Enable RLS on the `candidates`, `screening_results`, and `voice_screening_sessions` tables. Create policies enforcing `tenant_id` match. Use a `SET app.current_tenant_id` session variable from the SQLAlchemy event.
  - **Files:** `alembic/` (new migration), `app/backend/db/database.py`
  - **Effort:** XL

### UX — Medium

- [ ] **P2-UX-01** · Dark mode incomplete (majority of pages)
  - **Task:** Systematically add `dark:` Tailwind variants to all page containers, card backgrounds, table rows, form inputs, modals, and text. Priority: `AnalyzePage`, `ReportPage`, `CandidateProfilePage`, `DashboardNew`, all admin pages.
  - **Files:** All page and component JSX files
  - **Effort:** XL

- [ ] **P2-UX-02** · `AnalyticsPage` charts render with no empty state
  - **Task:** Add conditional rendering: show `EmptyState` with CTA if chart data is empty after loading completes.
  - **Files:** `app/frontend/src/pages/AnalyticsPage.jsx`
  - **Effort:** S

- [ ] **P2-UX-03** · `RevenuePage` silently swallows fetch errors
  - **Task:** Add error state and user-visible error banner with Retry (same pattern as P0-UX-02).
  - **Files:** `app/frontend/src/pages/admin/RevenuePage.jsx`
  - **Effort:** S

- [ ] **P2-UX-04** · `ReportPage` uses `html2pdf.js` fallback (inconsistent PDF output)
  - **Task:** Remove `html2pdf.js` client-side fallback. Show user-friendly error if server PDF fails. Ensure visual consistency between both PDF paths.
  - **Files:** `app/frontend/src/pages/ReportPage.jsx`, `app/frontend/package.json`
  - **Effort:** M

- [ ] **P2-UX-05** · `AnalyzePage` has no progress persistence on page refresh
  - **Task:** On analysis start, persist `jobId` to `sessionStorage`. On page load, detect pending job and restore progress view by polling queue status endpoint.
  - **Files:** `app/frontend/src/pages/AnalyzePage.jsx`
  - **Effort:** M

- [ ] **P2-UX-06** · No page `<title>` updates per route
  - **Task:** Install `react-helmet-async`. Set descriptive, unique `<title>` on every page component.
  - **Files:** `app/frontend/package.json`, `app/frontend/src/App.jsx` (provider), all page components
  - **Effort:** M

- [ ] **P2-UX-07** · Color-only status differentiation (WCAG SC 1.4.1)
  - **Task:** Add text labels or symbols alongside color in all status badges. Ensure status is never communicated by color alone.
  - **Files:** `app/frontend/src/components/Badges.jsx`, `app/frontend/src/lib/constants.js`
  - **Effort:** M

- [ ] **P2-UX-08** · `TenantsPage` is a 1000+ line monolith
  - **Task:** Extract `CreateTenantModal`, `SuspendTenantModal`, `ChangePlanModal`, `EditTenantModal` into separate component files.
  - **Files:** `app/frontend/src/pages/admin/TenantsPage.jsx`
  - **Effort:** M

- [ ] **P2-UX-09** · `StreamingText` causes screen reader chaos
  - **Task:** Wrap streaming content in `<span aria-live="polite">` that updates only at sentence/paragraph boundaries, not per character.
  - **Files:** `app/frontend/src/components/StreamingText.jsx`
  - **Effort:** S

- [ ] **P2-UX-10** · `SettingsPage` exposes admin debug functions in recruiter context
  - **Task:** Audit `adminResetUsage()` and `adminChangePlan()` visibility in `SettingsPage`. Move to admin panel if shown to non-admin roles.
  - **Files:** `app/frontend/src/pages/SettingsPage.jsx`
  - **Effort:** S

- [ ] **P2-UX-11** · `Button` component missing `aria-busy` for loading state
  - **Task:** Add `aria-disabled={loading || disabled}` and `aria-busy={loading}` to the `Button` component.
  - **Files:** `app/frontend/src/components/ui/Button.jsx`
  - **Effort:** S

- [ ] **P2-UX-12** · No `prefers-reduced-motion` respect in animations
  - **Task:** Add `useReducedMotion()` hook from Framer Motion. Disable or minimize all animations when the OS preference is set. Apply to `PageTransition`, `AnimatedScore`, `AnimatedShimmer`, `StaggerContainer`.
  - **Files:** `app/frontend/src/components/motion/PageTransition.jsx`, `AnimatedScore.jsx`, all animation components
  - **Effort:** M

- [ ] **P2-UX-13** · `CandidateProfilePage` no virtual scrolling for large histories
  - **Task:** Add `react-virtual` for the history list and notes list sections on the candidate profile page.
  - **Files:** `app/frontend/src/pages/CandidateProfilePage.jsx`, `app/frontend/package.json`
  - **Effort:** M

- [ ] **P2-UX-14** · Hardcoded industry/company size lists in onboarding
  - **Task:** Move `INDUSTRIES` and `COMPANY_SIZES` arrays from the component to a config file or API endpoint.
  - **Files:** `app/frontend/src/components/OnboardingWizard.jsx`
  - **Effort:** S

- [ ] **P2-UX-15** · Duplicate test setup file
  - **Task:** Delete `src/test/setup.js` (dead code). Keep `src/__tests__/setup.js` as the single test setup file.
  - **Files:** `app/frontend/src/test/setup.js`
  - **Effort:** S

---

## 🟢 P3 — LOW (Backlog / Polish)

### Security — Low

- [ ] **P3-SEC-01** · Add `SECURITY.md` with responsible disclosure policy
  - **Files:** Root `SECURITY.md`  ·  **Effort:** S

- [ ] **P3-SEC-02** · Add `CORS_ORIGINS` wildcard validation on production startup
  - **Files:** `app/backend/main.py`  ·  **Effort:** S

- [ ] **P3-SEC-03** · LiveKit dev credentials (`devkey`/`devsecret`) as default if env unset
  - **Task:** Add startup check similar to JWT secret that prevents launch with default LiveKit keys in production.
  - **Files:** `app/backend/main.py`  ·  **Effort:** S

### DevOps — Low

- [ ] **P3-OPS-01** · Add uptime monitoring for production health endpoints
  - **Task:** Configure Uptime Robot or Better Uptime to monitor `/health` and `/api/health/deep`. Alert on downtime.
  - **Effort:** S

- [ ] **P3-OPS-02** · Add PostgreSQL slow query logging
  - **Task:** Set `log_min_duration_statement = 1000` in PostgreSQL config.
  - **Files:** `docker-compose.prod.yml` (postgres environment)  ·  **Effort:** S

- [ ] **P3-OPS-03** · Add `alembic check` to CI to detect migration inconsistencies
  - **Files:** `.github/workflows/ci.yml`  ·  **Effort:** S

- [ ] **P3-OPS-04** · Add `VACUUM ANALYZE` schedule for PostgreSQL maintenance
  - **Files:** `docker-compose.prod.yml` or cron job  ·  **Effort:** S

### Backend — Low

- [ ] **P3-BE-01** · Structured logging in all environments (not just production)
  - **Task:** Use `structlog` or `python-json-logger` in all environments. Use human-readable format in dev while maintaining structured fields (`tenant_id`, `user_id`, `request_id`).
  - **Files:** `app/backend/main.py`, all services  ·  **Effort:** M

- [ ] **P3-BE-02** · Add global request timeout at ASGI level
  - **Task:** Enforce a maximum 240-second request timeout at the ASGI middleware level using `asgi-timeout-middleware` or equivalent.
  - **Files:** `app/backend/main.py`  ·  **Effort:** S

- [ ] **P3-BE-03** · Graceful shutdown for in-flight requests
  - **Task:** Implement signal handlers that drain in-flight requests before shutdown. Add `--graceful-timeout` to uvicorn config.
  - **Files:** `app/backend/scripts/docker-entrypoint.sh`, `docker-compose.prod.yml`  ·  **Effort:** M

- [ ] **P3-BE-04** · Tenant self-service feature flag toggle
  - **Task:** Allow tenant admins to toggle features gated behind `TenantFeatureOverride` without requiring a platform admin.
  - **Files:** `app/backend/routes/subscription.py`, admin UI  ·  **Effort:** M

- [ ] **P3-BE-05** · Tenant full data export package for offboarding
  - **Task:** Build a tenant-scoped bulk export endpoint that packages all candidates, results, billing history, and team data into a ZIP archive.
  - **Files:** `app/backend/routes/export.py`  ·  **Effort:** L

### UX — Low

- [ ] **P3-UX-01** · Hardcoded marketing copy in auth pages
  - **Task:** Move "ARIA", "ThetaLogics", and marketing taglines to a `src/lib/branding.js` config file or environment variable.
  - **Files:** `app/frontend/src/pages/LoginPage.jsx`, `RegisterPage.jsx`  ·  **Effort:** S

- [ ] **P3-UX-02** · Add `rel="noopener noreferrer"` to all external links
  - **Files:** All page components with `<a target="_blank">`  ·  **Effort:** S

- [ ] **P3-UX-03** · Idle timeout should be tenant-configurable
  - **Task:** Read idle timeout from tenant subscription settings rather than hardcoding 30 minutes.
  - **Files:** `app/frontend/src/hooks/useIdleTimeout.js`  ·  **Effort:** M

- [ ] **P3-UX-04** · Add timezone to all date/time displays
  - **Task:** Update `formatDate()` in `utils.js` to include timezone abbreviation. Apply to analysis history, voice schedules, audit logs.
  - **Files:** `app/frontend/src/lib/utils.js`  ·  **Effort:** S

- [ ] **P3-UX-05** · Add toast duration configuration (errors should persist longer)
  - **Task:** In `toast.jsx`, set error toasts to `duration: 6000`. Success toasts: `duration: 3000`. Loading toasts: `duration: Infinity` until dismissed.
  - **Files:** `app/frontend/src/lib/toast.jsx`  ·  **Effort:** S

- [ ] **P3-UX-06** · `ScoreGauge` needs text alternative
  - **Task:** Render the numeric score as accessible text inside the SVG or via `aria-label` on the container.
  - **Files:** `app/frontend/src/components/ScoreGauge.jsx`  ·  **Effort:** S

- [ ] **P3-UX-07** · `RecruiterTranscript` has no empty state
  - **Task:** Show "No transcript available for this session." if transcript is empty.
  - **Files:** `app/frontend/src/components/RecruiterTranscript.jsx`  ·  **Effort:** S

- [ ] **P3-UX-08** · `VoiceAssessmentPanel` has no error state for malformed data
  - **Task:** Show "Assessment data unavailable" when assessment JSON is malformed or missing fields.
  - **Files:** `app/frontend/src/components/VoiceAssessmentPanel.jsx`  ·  **Effort:** S

- [ ] **P3-UX-09** · `VersionHistory` needs explainer tooltip
  - **Task:** Add a `?` help tooltip explaining what "versions" means (re-analysis history) to reduce recruiter confusion.
  - **Files:** `app/frontend/src/components/VersionHistory.jsx`  ·  **Effort:** S

- [ ] **P3-UX-10** · Add `@media print` styles for report and profile pages
  - **Task:** Add print stylesheets to `ReportPage` and `CandidateProfilePage` for clean browser printing.
  - **Files:** `app/frontend/src/pages/ReportPage.jsx`, `CandidateProfilePage.jsx`  ·  **Effort:** M

- [ ] **P3-UX-11** · All `console.error` in catch blocks should show user feedback
  - **Task:** Replace remaining `console.error(...)` used as the only error handler in admin and feature component catch blocks with toast error messages.
  - **Files:** `src/pages/admin/RevenuePage.jsx`, `PhoneScreenKit.jsx`, `usePrefetch.js`, all pages with console-only error handling  ·  **Effort:** M

---

## SUMMARY BY PRIORITY

| Tier | Count | Primary Domain |
|------|-------|----------------|
| 🔴 P0 Critical | **13 items** | Security, auth bugs, functional breaks |
| 🟠 P1 High | **33 items** | Security hardening, accessibility, compliance foundations |
| 🟡 P2 Medium | **42 items** | Dark mode, DevOps, DB design, UX completeness |
| 🟢 P3 Low | **25 items** | Polish, developer experience, minor a11y |
| **Total** | **113 items** | |

---

## SUGGESTED SPRINT STRUCTURE

| Sprint | Weeks | Focus | Items |
|--------|-------|-------|-------|
| Sprint 0 (Hotfix) | 1–2 days | Stop active security bleeding | P0-SEC-01 through P0-SEC-05 + P0-BUG-01 |
| Sprint 1 | Week 1 | Remaining P0s + critical UX | P0-BUG-02 through P0-UX-03 |
| Sprint 2 | Week 2–3 | High security + accessibility | P1-SEC-01 to P1-SEC-10, P1-UX-01 to P1-UX-05 |
| Sprint 3 | Week 3–4 | Compliance + DevOps + UX | P1-COMP-01, P1-COMP-02, P1-OPS-01 to P1-OPS-04, P1-UX-06 to P1-UX-15 |
| Sprint 4 | Week 5–6 | DB design + Backend quality | P1-DB-*, P1-BE-*, P2-DB-* |
| Sprint 5 | Week 7–8 | Dark mode + Empty states | P2-UX-01 to P2-UX-08 |
| Sprint 6 | Week 9–10 | DevOps + Observability | P2-OPS-01 to P2-OPS-07 |
| Sprint 7 | Week 11–12 | Compliance + Advanced features | P2-COMP-01 to P2-COMP-06 |
| Sprints 8+ | Week 13+ | P3 backlog, i18n, performance | P3-* |

---

*Last updated: July 6, 2026 — based on ARIA v2.0.0 full-stack audit (backend + security + architecture + UI/UX)*
