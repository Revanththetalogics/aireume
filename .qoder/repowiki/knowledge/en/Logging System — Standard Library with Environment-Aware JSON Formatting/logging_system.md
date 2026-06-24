The application uses Python's built-in `logging` module for all backend logging, with a custom environment-aware configuration in the FastAPI entry point (`app/backend/main.py`).

### 1. Framework and Approach
- **Core Framework**: Python standard library `logging`.
- **Configuration**: Centralized in `app/backend/main.py` via `logging.basicConfig`.
- **Environment Switching**:
  - **Development/Default**: Uses a human-readable text format: `%(asctime)s %(levelname)s [%(name)s] [%(funcName)s] %(message)s`.
  - **Production**: When `ENVIRONMENT=production`, the root logger handlers are replaced with a custom `JsonFormatter` that outputs structured JSON logs to `stdout`. This JSON includes `timestamp`, `level`, `logger`, `message`, `function`, and optional `exception` fields.

### 2. Logger Naming Convention
- **Root Logger**: `aria` (used in `main.py`).
- **Module-Specific Loggers**: Developers are expected to use `logging.getLogger(__name__)` or named loggers following the `aria.<module>` pattern (e.g., `aria.analysis`, `aria.startup`, `aria.compare`).
- **Examples**:
  - `log = logging.getLogger("aria.analysis")` in `routes/analyze.py`
  - `logger = logging.getLogger("aria.startup")` in `main.py`
  - `logger = logging.getLogger(__name__)` in most services and routes.

### 3. Key Files
- **`app/backend/main.py`**: Contains the core logging configuration, including the `JsonFormatter` class and the environment-based switch.
- **`app/backend/services/queue_manager.py`**: Heavy usage of `logger.info`, `logger.warning`, and `logger.error` for job lifecycle tracking.
- **`app/backend/routes/analyze.py`**: Uses `log` for analysis pipeline events and validation warnings.
- **`app/backend/services/llm_service.py`**: Logs LLM health sentinel status and API interactions.

### 4. Observability Integrations
- **Correlation IDs**: A `RequestIdMiddleware` injects an `X-Request-ID` header into every request and stores it in a `contextvars.ContextVar`. While not automatically injected into log records by the current configuration, this mechanism is in place for future structured log enrichment.
- **Metrics**: The application uses `prometheus_fastapi_instrumentator` for HTTP metrics and custom Prometheus counters/histograms in `app/backend/services/metrics.py` for LLM calls, guardrails, and parsing durations. These complement logs but are not part of the log output itself.
- **Audit Logging**: Business-critical actions are recorded in the database via `app/backend/services/audit_service.py` using `AuditLog` and `FieldAuditLog` models, separate from the application log stream.

### 5. Developer Rules
- **Use Named Loggers**: Always use `logging.getLogger(__name__)` or a specific `aria.` prefix to enable filtering.
- **Structured Data in Production**: In production, logs are JSON. Avoid multi-line raw strings for complex data; prefer passing context via extra fields if the formatter is extended, or ensure messages are concise.
- **Exception Logging**: Use `logger.exception("message", exc_info=True)` or `log.exception("message")` to capture stack traces in the `exception` field of the JSON output.
- **Non-Critical Warnings**: Prefix non-blocking errors with "Non-critical:" in the log message (e.g., `log.warning("Non-critical: Failed to parse cached JD JSON...")`) to aid in operational triage.