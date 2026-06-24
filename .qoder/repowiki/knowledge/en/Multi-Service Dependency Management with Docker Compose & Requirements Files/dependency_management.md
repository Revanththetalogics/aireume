This repository employs a polyglot dependency management strategy across four distinct service boundaries: a Python FastAPI backend, a React/Vite frontend, and two specialized Python microservices (Speech Service and Voice Agent). Dependencies are managed using standard ecosystem tools (`pip`/`requirements.txt` for Python, `npm`/`package-lock.json` for Node.js) with strict version pinning in production services to ensure deterministic builds.

### 1. Backend Services (Python)
The core application logic resides in `app/backend`, `app/speech_service`, and `app/voice_agent`. Each service maintains its own `requirements.txt` file.

- **Versioning Strategy**: The primary backend (`app/backend/requirements.txt`) uses exact version pinning (e.g., `fastapi==0.115.5`, `sqlalchemy==2.0.36`) for critical infrastructure libraries to prevent breaking changes. Some NLP and utility libraries use minimum version constraints (e.g., `spacy>=3.7`, `langgraph>=0.2.0`) to allow for minor updates while ensuring compatibility.
- **System Dependencies**: The `Dockerfile` for the backend explicitly installs system-level dependencies required by Python libraries, such as `libreoffice` for document conversion and `libpango`/`libcairo` for PDF generation (`weasyprint`). This ensures that Python package dependencies on native libraries are resolved during the container build.
- **Microservice Isolation**: 
    - `app/speech_service/requirements.txt` isolates heavy ML dependencies like `torch` and `transformers`, preventing them from bloating the main backend image.
    - `app/voice_agent/requirements.txt` manages LiveKit SDK dependencies separately, reflecting its role as a real-time communication orchestrator.

### 2. Frontend Application (Node.js)
The frontend (`app/frontend`) uses `npm` for dependency management.

- **Lockfile Strategy**: A `package-lock.json` is committed to the repository, ensuring that all developers and CI environments install the exact same dependency tree. The CI workflow explicitly caches dependencies based on this lockfile (`cache-dependency-path: app/frontend/package-lock.json`).
- **Build Tooling**: The project uses `Vite` for building and `Vitest` for testing. Dependencies are split into `dependencies` (runtime: `react`, `axios`, `framer-motion`) and `devDependencies` (build/test: `vite`, `eslint`, `vitest`).
- **Root-Level E2E Testing**: A root-level `package.json` exists solely to manage End-to-End (E2E) testing dependencies (`@playwright/test`). This separates E2E tooling from the application's runtime dependencies.

### 3. Containerization & Orchestration
Docker Compose (`docker-compose.yml`) serves as the primary mechanism for resolving service-to-service dependencies at runtime.

- **Image Pinning**: Infrastructure services use specific, stable base images (e.g., `postgres:16-alpine`, `nginx:alpine`, `node:20-alpine` in Dockerfiles).
- **Build Contexts**: The `docker-compose.yml` defines build contexts for custom services, ensuring that dependency installation (`pip install`, `npm ci`) happens within isolated container layers. This avoids "it works on my machine" issues related to local Python/Node versions.
- **Health Checks**: Dependencies between services are managed via `depends_on` with health check conditions (e.g., `backend` waits for `postgres` and `ollama` to be healthy), ensuring that application dependencies are available before startup.

### 4. CI/CD Integration
GitHub Actions workflows (`.github/workflows/ci.yml`) enforce dependency integrity:

- **Python**: Uses `pip install -r requirements.txt` followed by explicit installation of test tools (`pytest`, `respx`).
- **Node.js**: Uses `npm ci` instead of `npm install` in CI, which strictly adheres to `package-lock.json` and fails if the lockfile is out of sync with `package.json`.

### Developer Guidelines
1. **Pin Critical Dependencies**: When adding new Python packages to `app/backend/requirements.txt`, prefer exact versions (`==`) for core frameworks (FastAPI, SQLAlchemy, Pydantic) to maintain stability.
2. **Update Lockfiles**: After modifying `app/frontend/package.json`, always run `npm install` to update `package-lock.json` and commit both files.
3. **System Dependencies**: If a new Python library requires native system libraries (e.g., for image processing or PDF generation), update the `apt-get install` step in the corresponding `Dockerfile`.
4. **Microservice Boundaries**: Do not add heavy ML dependencies (like `torch`) to the main backend `requirements.txt`. Keep them isolated in `app/speech_service` or `app/voice_agent` to keep the main API image lightweight.