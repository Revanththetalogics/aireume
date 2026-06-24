The application employs a layered, environment-driven configuration system primarily based on **environment variables** and **Docker Compose** service definitions. It supports distinct runtime profiles (development, staging, production) through dedicated `.env` files and conditional logic in the backend entrypoint.

### 1. Configuration Sources & Layering
*   **Environment Variables (`.env`)**: The primary source for secrets, service endpoints, and feature toggles. The repo provides `.env.example` as a template, with environment-specific overrides (`.env.production`, `.env.staging`).
*   **Docker Compose**: Orchestrates service-level configuration, injecting environment variables into containers (`backend`, `voice-agent`, `livekit`, etc.) and managing volume mounts for persistent data (PostgreSQL, Ollama).
*   **Database-Backed Config**: Runtime configurations such as **Feature Flags**, **Tenant Overrides**, **Subscription Plans**, and **SMTP Settings** are stored in the PostgreSQL database, allowing dynamic updates without restarts. These are cached in-memory with TTL-based invalidation.
*   **Static YAML/INI**: Used for infrastructure components like **LiveKit** (`livekit.yaml`) and **Alembic** (`alembic.ini`).

### 2. Key Configuration Categories
*   **LLM/Ollama**: Configured via `OLLAMA_BASE_URL`, `OLLAMA_API_KEY`, and `OLLAMA_MODEL`. The system supports both local self-hosted Ollama instances and the Ollama Cloud API, with startup health checks to ensure model availability.
*   **Database**: `DATABASE_URL` determines the connection string. The backend defaults to SQLite for local development but requires PostgreSQL in production. Connection pooling is configured dynamically based on the detected database engine.
*   **Security & Auth**: `JWT_SECRET_KEY`, `ENCRYPTION_KEY` (for tenant SMTP passwords), and `CORS_ORIGINS` are strictly enforced in production mode. CSRF tokens and rate limits are middleware-configured.
*   **Voice Screening**: LiveKit and Twilio SIP integration relies on `LIVEKIT_API_KEY/SECRET`, `SIP_TRUNK_ID`, and `SIP_OUTBOUND_NUMBER`.

### 3. Architecture & Conventions
*   **Startup Validation**: The FastAPI lifespan event (`app/backend/main.py`) performs rigorous dependency checks (DB connectivity, Ollama reachability, model warmth) and prints a status banner. This ensures the application fails fast if critical configuration is missing or invalid.
*   **Environment Mode**: The `ENVIRONMENT` variable (development/production) toggles strictness levels for CORS, JWT validation, and logging formats (JSON in production).
*   **Frontend Proxying**: The React frontend uses Vite's `proxy` configuration in `vite.config.js` for local development to bypass CORS issues, while production builds rely on Nginx reverse proxy rules defined in `nginx.prod.conf`.

### 4. Developer Rules
*   **Secrets Management**: Never commit real secrets. Use `.env.example` as the source of truth for required variables. In production, inject secrets via Docker secrets or secure environment injection.
*   **Database URL**: Ensure `DATABASE_URL` matches the target environment. Local dev can use SQLite (`./resume_screener.db`), but production must use PostgreSQL.
*   **Feature Flags**: New features should be gated via the `feature_flag_service` to allow gradual rollouts and tenant-specific enablement.
*   **CORS**: In production, explicitly set `CORS_ORIGINS` to trusted frontend domains. The default includes localhost for dev convenience but triggers a warning if used in production.