The project employs a containerized, multi-service architecture managed via **Docker Compose** for local development and production deployment, with **GitHub Actions** handling Continuous Integration (CI) and Continuous Deployment (CD).

### Build System & Tools
- **Containerization**: All services (Backend, Frontend, Nginx, Voice Agent, Speech Service, LiveKit) are containerized using Docker. Each service has its own `Dockerfile` optimized for size and security (e.g., multi-stage builds for frontend, non-root users).
- **Orchestration**: 
  - `docker-compose.yml`: Used for local development.
  - `docker-compose.prod.yml`: Production stack with resource limits, healthchecks, and Watchtower for auto-updates.
  - `docker-compose.staging.yml`: Isolated staging environment with separate volumes/networks.
- **CI/CD**: GitHub Actions workflows (`ci.yml`, `cd.yml`) automate testing, building, and pushing Docker images to Docker Hub.

### Key Files
- `.github/workflows/ci.yml`: Runs backend (pytest) and frontend (npm test) tests on PRs and pushes.
- `.github/workflows/cd.yml`: Builds and pushes Docker images to Docker Hub tagged as `staging` or `latest` based on the branch (`main` vs `production`).
- `docker-compose*.yml`: Define service topology, resource constraints, and environment-specific configurations.
- `app/*/Dockerfile`: Service-specific build instructions.
- `app/backend/scripts/docker-entrypoint.sh`: Handles database migrations (Alembic) and Ollama warmup before starting the backend.

### Architecture & Conventions
- **Environment Separation**: Strict separation between `staging` and `production` via distinct compose files and image tags. Staging uses `aria-staging` project name to avoid volume collisions.
- **Automated Deployments**: Production uses **Watchtower** to poll Docker Hub every 60 seconds for new images, enabling zero-touch deployments after a successful CD pipeline run.
- **Resource Management**: Production compose files explicitly define CPU and memory limits for each service to optimize VPS usage (e.g., Ollama limited to 8 CPUs/8GB RAM).
- **Health Checks**: Services include health checks to ensure dependencies (Postgres, Ollama, LiveKit) are ready before dependent services start.

### Developer Rules
- **Branching Strategy**: 
  - Pushes to `main` trigger `staging` builds.
  - Pushes to `production` trigger `latest` (production) builds.
- **Testing**: All PRs and pushes to protected branches must pass backend and frontend tests in CI.
- **Local Development**: Use `docker-compose up` for local setup. Ensure `.env` files are configured for local secrets.
- **Migrations**: Database migrations are automatically applied via the backend entrypoint script when using PostgreSQL.
- **Image Tagging**: Never manually tag production images; rely on the CD workflow to assign `staging` or `latest` tags.