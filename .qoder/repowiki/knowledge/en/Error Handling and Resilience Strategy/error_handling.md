The codebase employs a multi-layered error handling strategy combining FastAPI's built-in exception mechanisms, custom middleware for operational resilience (rate limiting, CSRF), and robust service-level fallbacks for external dependencies (LLM, Database). The system prioritizes availability through graceful degradation, particularly in AI-driven pipelines where LLM failures trigger deterministic Python-based scoring fallbacks.

### 1. Backend Error Propagation (FastAPI)
- **HTTPExceptions**: The primary mechanism for API-level errors is `fastapi.HTTPException`. It is used extensively in routes (`app/backend/routes/*.py`) and dependencies (`app/backend/middleware/auth.py`) to return structured JSON errors with appropriate HTTP status codes (400, 401, 403, 429, 500).
- **Structured Details**: Error responses often include machine-readable `error_code` fields (e.g., `SUBSCRIPTION_SUSPENDED`, `SSO_ENFORCED`) alongside human-readable `detail` messages to facilitate frontend handling.
- **Validation Errors**: Input validation (file signatures, JD length, password complexity) raises 400 errors with specific guidance, preventing downstream processing of invalid data.

### 2. Middleware and Operational Resilience
- **Rate Limiting**: A custom `RateLimitMiddleware` (`app/backend/middleware/rate_limit.py`) implements a token-bucket algorithm per tenant. It returns `429 Too Many Requests` with `Retry-After` headers when limits are exceeded, protecting the system from abuse and resource exhaustion.
- **Authentication & Authorization**: The `auth.py` middleware intercepts requests to validate JWTs. It raises 401/403 errors for invalid tokens, revoked sessions, or insufficient permissions (RBAC), ensuring secure access control before route logic executes.
- **CSRF Protection**: A dedicated middleware validates CSRF tokens for state-changing requests from browser clients, returning 403 errors if validation fails.

### 3. Service-Level Fallbacks and Degradation
- **LLM Resilience**: The `llm_service.py` implements a "Health Sentinel" that monitors Ollama connectivity. If the LLM is unreachable or times out, the system gracefully degrades to a Python-based deterministic scoring model, ensuring the core functionality remains available even if AI features are temporarily impaired.
- **Queue-Based Reliability**: Long-running analysis jobs are managed by a `QueueManager` (`app/backend/services/queue_manager.py`). It features:
    - **Automatic Retries**: Failed jobs are retried with exponential backoff.
    - **Stale Job Recovery**: A background process detects and re-queues jobs abandoned by crashed workers.
    - **Lease Locking**: Prevents multiple workers from processing the same job simultaneously.
- **Database Transaction Safety**: Services use `SessionLocal` with explicit `commit()` and `rollback()` blocks. Critical operations (like candidate deduplication) handle `IntegrityError` exceptions to manage concurrent writes safely.

### 4. Frontend Error Boundaries and Recovery
- **React Error Boundary**: A class-based `ErrorBoundary` component (`app/frontend/src/components/ErrorBoundary.jsx`) catches unhandled JavaScript errors in the UI tree, preventing full-page crashes and offering users a "Try Again" or "Refresh" option.
- **API Interceptors**: The Axios client (`app/frontend/src/lib/api.js`) uses interceptors to:
    - **Auto-Refresh Tokens**: Automatically retries failed 401 requests by refreshing the access token via httpOnly cookies.
    - **Retry Transient Errors**: Implements exponential backoff for 5xx server errors and network failures.
    - **CSRF Token Management**: Automatically attaches CSRF tokens to state-mutating requests.

### 5. Logging and Observability
- **Structured Logging**: The backend uses structured JSON logging in production environments, capturing timestamps, levels, and exception traces for easier parsing by observability tools.
- **Correlation IDs**: A `RequestIdMiddleware` injects unique `X-Request-ID` headers into every request and response, enabling end-to-end tracing of errors across the distributed system.
- **Health Checks**: Dedicated `/health` and `/api/health/deep` endpoints provide real-time status on database connectivity, LLM availability, and disk space, allowing orchestration layers (Docker/Kubernetes) to detect and restart unhealthy instances.