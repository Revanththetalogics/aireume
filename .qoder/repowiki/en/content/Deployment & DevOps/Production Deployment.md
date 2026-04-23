# Production Deployment

<cite>
**Referenced Files in This Document**
- [docker-compose.prod.yml](file://docker-compose.prod.yml)
- [nginx.prod.conf](file://nginx/nginx.prod.conf)
- [Dockerfile (backend)](file://app/backend/Dockerfile)
- [Dockerfile (frontend)](file://app/frontend/Dockerfile)
- [Dockerfile (nginx)](file://nginx/Dockerfile)
- [docker-entrypoint.sh](file://app/backend/scripts/docker-entrypoint.sh)
- [wait_for_ollama.py](file://app/backend/scripts/wait_for_owlama.py)
- [main.py](file://app/backend/main.py)
- [database.py](file://app/backend/db/database.py)
- [auth.py](file://app/backend/middleware/auth.py)
- [env.py](file://alembic/env.py)
- [alembic.ini](file://alembic.ini)
- [README.md](file://README.md)
- [ci.yml](file://.github/workflows/ci.yml)
- [cd.yml](file://.github/workflows/cd.yml)
- [requirements.txt](file://requirements.txt)
- [llm_service.py](file://app/backend/services/llm_service.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [012_admin_foundation.py](file://alembic/versions/012_admin_foundation.py)
- [013_webhooks_and_notifications.py](file://alembic/versions/013_webhooks_and_notifications.py)
- [014_billing_system.py](file://alembic/versions/014_billing_system.py)
- [db_models.py](file://app/backend/models/db_models.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced PostgreSQL migration system with improved compatibility for feature flag seeding and webhook delivery tables
- Added comprehensive database schema support for webhooks, webhook deliveries, and billing configurations
- Implemented idempotent migration patterns ensuring consistent behavior across database systems
- Expanded feature flag infrastructure with tenant-specific override capabilities
- Introduced billing system configuration tables for payment provider settings

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document provides comprehensive production deployment guidance for Resume AI by ThetaLogics. It covers server preparation, container orchestration with Docker Compose, Nginx reverse proxy configuration, environment variable management, secrets handling, database migrations and backups, monitoring and alerting, scaling and auto-scaling, performance tuning, deployment checklists, rollback procedures, and security hardening.

## Project Structure
The repository organizes the stack into four primary services:
- Backend: FastAPI application with Uvicorn, Alembic migrations, and Ollama integration
- Frontend: Static React SPA served by Nginx on port 8080
- Nginx: Reverse proxy and static asset server with production configuration baked into the image
- **Updated**: Ollama-warmup: Dedicated service for model warmup with persistent loading

```mermaid
graph TB
subgraph "Production Stack"
NGINX["Nginx (reverse proxy)"]
FRONT["React Frontend (static on port 8080)"]
BACK["FastAPI Backend (6 workers)"]
DB["PostgreSQL"]
OLL["Ollama (8GB RAM)"]
WARM["Ollama-Warmup (single-run)"]
end
CLIENT["Browser"] --> NGINX
NGINX --> FRONT
NGINX --> BACK
BACK --> DB
BACK --> OLL
OLL --> WARM
```

**Diagram sources**
- [docker-compose.prod.yml:126-145](file://docker-compose.prod.yml#L126-L145)
- [docker-compose.prod.yml:156-188](file://docker-compose.prod.yml#L156-L188)
- [nginx.prod.conf:19-87](file://nginx/nginx.prod.conf#L19-L87)
- [Dockerfile (backend):1-39](file://app/backend/Dockerfile#L1-L39)
- [Dockerfile (frontend):1-26](file://app/frontend/Dockerfile#L1-L26)

**Section sources**
- [docker-compose.prod.yml:7-227](file://docker-compose.prod.yml#L7-L227)
- [nginx.prod.conf:1-89](file://nginx/nginx.prod.conf#L1-L89)
- [Dockerfile (backend):1-39](file://app/backend/Dockerfile#L1-L39)
- [Dockerfile (frontend):1-26](file://app/frontend/Dockerfile#L1-L26)
- [Dockerfile (nginx):1-13](file://nginx/Dockerfile#L1-L13)

## Core Components
- Backend service
  - **Updated**: Uvicorn with 6 workers for enhanced I/O-bound concurrency
  - Alembic migrations executed at startup for PostgreSQL
  - Startup gating for Ollama readiness and model warm-up
  - Health endpoint validating database and LLM connectivity
  - **Critical**: JWT_SECRET_KEY must be set in production environment
- Frontend service
  - Nginx static hosting of built React assets on port 8080
- Nginx service
  - Production configuration with reverse proxy, streaming, and SPA fallback
  - Health check endpoint proxied to backend
- **Updated**: Ollama-warmup service
  - Dedicated single-run container that loads the model into RAM
  - Uses OLLAMA_KEEP_ALIVE=-1 to persist model in memory
  - Exits after successful warmup, leaving the model loaded in Ollama
- Supporting services
  - PostgreSQL for persistence with optimized resource allocation
  - **Updated**: Ollama for local LLM inference with increased memory allocation (8GB)
  - Watchtower for automated image updates
  - Certbot for Let's Encrypt certificate renewal

Key production configuration highlights:
- **Updated**: Resource limits and health checks for enhanced resilience with 4CPUs/6GB backend allocation
- Dynamic DNS resolution for Docker embedded DNS to avoid stale IPs
- Streaming and CORS handling for SSE and cross-origin requests
- **Enhanced**: Dedicated warmup job with persistent model loading using OLLAMA_KEEP_ALIVE=-1
- **Updated**: Increased LLM_NARRATIVE_TIMEOUT from 120s to 180s for better concurrent request handling
- **Enhanced**: Mandatory JWT_SECRET_KEY environment variable for production security
- **Updated**: Ollama memory allocation increased from 6GB to 8GB for improved stability

**Section sources**
- [docker-compose.prod.yml:75-112](file://docker-compose.prod.yml#L75-L112)
- [docker-compose.prod.yml:126-145](file://docker-compose.prod.yml#L126-L145)
- [docker-compose.prod.yml:41-71](file://docker-compose.prod.yml#L41-L71)
- [docker-compose.prod.yml:22-39](file://docker-compose.prod.yml#L22-L39)
- [docker-compose.prod.yml:156-188](file://docker-compose.prod.yml#L156-L188)
- [docker-compose.prod.yml:192-211](file://docker-compose.prod.yml#L192-L211)
- [docker-compose.prod.yml:213-221](file://docker-compose.prod.yml#L213-L221)
- [nginx.prod.conf:19-87](file://nginx/nginx.prod.conf#L19-L87)
- [docker-entrypoint.sh:4-14](file://app/backend/scripts/docker-entrypoint.sh#L4-L14)
- [wait_for_ollama.py:34-91](file://app/backend/scripts/wait_for_ollama.py#L34-L91)
- [main.py:228-259](file://app/backend/main.py#L228-L259)
- [auth.py:13-21](file://app/backend/middleware/auth.py#L13-L21)

## Architecture Overview
The production architecture uses Docker Compose to orchestrate services behind Nginx. Nginx terminates HTTP/HTTPS traffic, proxies API and streaming endpoints to the backend, and serves the frontend SPA on port 8080. The backend connects to PostgreSQL and interacts with Ollama for AI analysis. A dedicated warmup service ensures the model is loaded into RAM before serving requests.

```mermaid
graph TB
subgraph "External"
U["User Agent"]
end
subgraph "Load Balancer / Edge"
LB["Optional external LB"]
end
subgraph "Reverse Proxy Layer"
NX["Nginx (nginx.prod.conf)"]
end
subgraph "Application Layer"
FE["Frontend (Nginx static on port 8080)"]
BE["Backend (FastAPI/Uvicorn with 6 workers)"]
end
subgraph "Data Layer"
PG["PostgreSQL (2CPUs/6GB)"]
OL["Ollama (8GB RAM)"]
WU["Ollama-Warmup (single-run)"]
end
U --> NX
NX --> FE
NX --> BE
BE --> PG
BE --> OL
OL --> WU
```

**Diagram sources**
- [nginx.prod.conf:19-87](file://nginx/nginx.prod.conf#L19-L87)
- [docker-compose.prod.yml:126-145](file://docker-compose.prod.yml#L126-L145)
- [docker-compose.prod.yml:156-188](file://docker-compose.prod.yml#L156-L188)
- [Dockerfile (backend):36-38](file://app/backend/Dockerfile#L36-L38)
- [Dockerfile (frontend):15-25](file://app/frontend/Dockerfile#L15-L25)

## Detailed Component Analysis

### Nginx Reverse Proxy and SSL Termination
Nginx is configured with:
- Production configuration baked into the image
- Resolver with short TTL to refresh backend/frontend IPs
- Health endpoint proxying to backend
- Streaming endpoint for SSE with appropriate timeouts and buffer settings
- **Updated**: SPA fallback now proxies to frontend service on port 8080
- Logging and performance tuning (keepalive, gzip)

Operational notes:
- The configuration listens on port 80 internally but is mapped to port 8080 externally via Docker port mapping
- The resolver directive ensures dynamic upstream resolution to avoid stale container IPs after recreation
- Frontend service is now exposed on port 8080 internally, requiring the frontend proxy to target `frontend:8080`

**Section sources**
- [nginx.prod.conf:19-87](file://nginx/nginx.prod.conf#L19-L87)
- [Dockerfile (nginx):1-13](file://nginx/Dockerfile#L1-L13)
- [docker-compose.prod.yml:126-145](file://docker-compose.prod.yml#L126-L145)

### Backend Service: Startup, Migrations, and Health
- Startup flow
  - Alembic migrations run on PostgreSQL URLs at container start
  - Optional Ollama readiness gate with warm-up
  - Startup banner prints dependency checks
- **Critical Security Enhancement**: JWT_SECRET_KEY validation
  - Backend enforces JWT_SECRET_KEY environment variable in production
  - Raises RuntimeError if JWT_SECRET_KEY is not set in production environment
  - Uses development fallback only in non-production environments
- **Updated**: Enhanced concurrency with 6 Uvicorn workers for improved I/O-bound performance
- Health endpoint
  - Validates database connectivity and Ollama availability
  - Returns degraded status without raising errors to prevent upstream failures
- Database configuration
  - Supports both SQLite and PostgreSQL with normalization and connection pooling

```mermaid
sequenceDiagram
participant Entrypoint as "Entrypoint Script"
participant JWTCheck as "JWT Secret Validation"
participant Alembic as "Alembic"
participant Wait as "Wait for Ollama"
participant Uvicorn as "Uvicorn (6 workers)"
Entrypoint->>JWTCheck : "Validate JWT_SECRET_KEY"
JWTCheck-->>Entrypoint : "Valid or raise error"
Entrypoint->>Alembic : "Upgrade to head (PostgreSQL)"
Entrypoint->>Wait : "Check Ollama readiness and warm model"
Wait-->>Entrypoint : "Ready"
Entrypoint->>Uvicorn : "Start server with 6 workers"
```

**Diagram sources**
- [docker-entrypoint.sh:4-14](file://app/backend/scripts/docker-entrypoint.sh#L4-L14)
- [auth.py:13-21](file://app/backend/middleware/auth.py#L13-L21)
- [wait_for_ollama.py:34-91](file://app/backend/scripts/wait_for_ollama.py#L34-L91)
- [Dockerfile (backend):36-38](file://app/backend/Dockerfile#L36-L38)

**Section sources**
- [docker-entrypoint.sh:4-14](file://app/backend/scripts/docker-entrypoint.sh#L4-L14)
- [auth.py:13-21](file://app/backend/middleware/auth.py#L13-L21)
- [wait_for_ollama.py:34-91](file://app/backend/scripts/wait_for_ollama.py#L34-L91)
- [main.py:68-149](file://app/backend/main.py#L68-L149)
- [main.py:228-259](file://app/backend/main.py#L228-L259)
- [database.py:1-33](file://app/backend/db/database.py#L1-L33)

### Frontend Service: Static Hosting
- Built assets served by Nginx from the frontend build output
- **Updated**: Production image exposes port 8080 internally for Nginx proxying
- Non-root user execution for security

**Section sources**
- [Dockerfile (frontend):1-26](file://app/frontend/Dockerfile#L1-L26)

### Database: PostgreSQL Tuning and Migration
- PostgreSQL tuned for 6 GB RAM allocation with shared buffers, work_mem, and max connections
- Alembic migrations executed at startup for PostgreSQL deployments
- Environment variables for credentials and database name

**Updated**: Enhanced PostgreSQL migration system with improved compatibility for feature flag seeding and webhook delivery tables

The migration system now includes comprehensive database schema support through recent additions:

#### Feature Flag Infrastructure
- **Admin Foundation Migration (012)**: Establishes core feature flag tables including `feature_flags`, `tenant_feature_overrides`, and audit logging
- **Webhook System Migration (013)**: Adds `webhooks` and `webhook_deliveries` tables with proper foreign key relationships and indexing
- **Billing System Migration (014)**: Introduces `platform_configs` table for payment provider settings

#### PostgreSQL Compatibility Improvements
- **Idempotent Operations**: All migrations use `_table_exists()` and `_index_names()` checks to ensure safe repeated execution
- **Consistent Indexing**: Standardized index creation patterns across all migration scripts
- **Foreign Key Constraints**: Proper CASCADE deletion handling for dependent records
- **Timezone Support**: Consistent use of `DateTime(timezone=True)` for temporal data
- **JSON Data Handling**: Appropriate TEXT column types for JSON payload storage

```mermaid
flowchart TD
Start(["Container Start"]) --> CheckURL["Check DATABASE_URL scheme"]
CheckURL --> |PostgreSQL| RunMigrations["Run Alembic upgrade head"]
CheckURL --> |Other| SkipMigrations["Skip migrations"]
RunMigrations --> CheckSchema["Verify feature flag tables"]
CheckSchema --> |Missing| CreateTables["Create webhooks, feature flags, billing tables"]
CheckSchema --> |Present| ValidateIndexes["Validate indexes exist"]
CreateTables --> Ready(["Services start normally"])
ValidateIndexes --> Ready
SkipMigrations --> Ready
```

**Diagram sources**
- [docker-entrypoint.sh:4-14](file://app/backend/scripts/docker-entrypoint.sh#L4-L14)
- [env.py:14-20](file://alembic/env.py#L14-L20)
- [alembic.ini:84-87](file://alembic.ini#L84-L87)

**Section sources**
- [docker-compose.prod.yml:22-39](file://docker-compose.prod.yml#L22-L39)
- [docker-entrypoint.sh:4-14](file://app/backend/scripts/docker-entrypoint.sh#L4-L14)
- [env.py:14-20](file://alembic/env.py#L14-L20)
- [alembic.ini:84-87](file://alembic.ini#L84-L87)
- [012_admin_foundation.py:90-109](file://alembic/versions/012_admin_foundation.py#L90-L109)
- [013_webhooks_and_notifications.py:36-114](file://alembic/versions/013_webhooks_and_notifications.py#L36-L114)
- [014_billing_system.py:33-56](file://alembic/versions/014_billing_system.py#L33-L56)

### Enhanced Ollama and Model Warm-Up
- **Updated**: Ollama configured with thread and parallelism settings for throughput
- **Enhanced**: Dedicated warmup service with single-run approach using OLLAMA_KEEP_ALIVE=-1
- **Updated**: Increased memory allocation from 6GB to 8GB for improved stability under load
- **Enhanced**: Persistent model loading eliminates need for continuous keep-alive loops
- **Updated**: LLM_NARRATIVE_TIMEOUT increased from 120s to 180s for better concurrent request handling
- Backend startup can gate on Ollama readiness and warm model presence
- Memory calculation: qwen3.5:4b actual: 3.6 GiB weights + 1.3 GiB KV-cache + 394 MiB compute = 5.3 GiB with 8GB headroom for OS overhead and concurrent requests

**Section sources**
- [docker-compose.prod.yml:41-71](file://docker-compose.prod.yml#L41-L71)
- [docker-compose.prod.yml:156-188](file://docker-compose.prod.yml#L156-L188)
- [docker-compose.prod.yml:96-97](file://docker-compose.prod.yml#L96-L97)
- [wait_for_ollama.py:34-91](file://app/backend/scripts/wait_for_ollama.py#L34-L91)
- [main.py:262-326](file://app/backend/main.py#L262-L326)
- [llm_service.py:138-175](file://app/backend/services/llm_service.py#L138-L175)
- [hybrid_pipeline.py:107-130](file://app/backend/services/hybrid_pipeline.py#L107-L130)

### Watchtower and Certbot
- Watchtower monitors ARIA containers and auto-restarts when images change
- Certbot runs as a long-lived container to renew certificates

**Section sources**
- [docker-compose.prod.yml:192-211](file://docker-compose.prod.yml#L192-L211)
- [docker-compose.prod.yml:213-221](file://docker-compose.prod.yml#L213-L221)

## Dependency Analysis
Inter-service dependencies and health checks:
- Backend depends on PostgreSQL and Ollama being healthy
- **Updated**: Nginx depends on frontend (on port 8080) and backend
- **Enhanced**: Warmup service depends on Ollama health and exits after completion
- **Updated**: Ollama service maintains persistent model loading with OLLAMA_KEEP_ALIVE=-1

```mermaid
graph LR
PG["PostgreSQL (2CPUs/6GB)"] -- "healthy" --> BE["Backend (6 workers, 4CPUs/6GB)"]
OL["Ollama (8GB RAM, KEEP_ALIVE=-1)"] -- "persistent" --> BE
FE["Frontend (port 8080)"] -- "available" --> NX["Nginx"]
BE -- "available" --> NX
WU["Ollama-Warmup (single-run)"] -- "completes" --> OL
NX -- "healthy" --> CL["Client"]
```

**Diagram sources**
- [docker-compose.prod.yml:96-100](file://docker-compose.prod.yml#L96-L100)
- [docker-compose.prod.yml:131-133](file://docker-compose.prod.yml#L131-L133)
- [docker-compose.prod.yml:140-144](file://docker-compose.prod.yml#L140-L144)
- [docker-compose.prod.yml:156-188](file://docker-compose.prod.yml#L156-L188)

**Section sources**
- [docker-compose.prod.yml:96-100](file://docker-compose.prod.yml#L96-L100)
- [docker-compose.prod.yml:131-133](file://docker-compose.prod.yml#L131-L133)
- [docker-compose.prod.yml:140-144](file://docker-compose.prod.yml#L140-L144)
- [docker-compose.prod.yml:156-188](file://docker-compose.prod.yml#L156-L188)

## Performance Considerations
- **Updated**: Backend workers: increased from 4 to 6 workers for enhanced I/O-bound concurrency; adjust based on CPU and memory headroom
- **Updated**: Backend resource allocation: 4CPUs/6GB provides optimal balance for 6 workers with sufficient headroom
- PostgreSQL tuning: shared_buffers, work_mem, and max_connections optimized for 6 GB RAM allocation
- **Updated**: Ollama settings: thread count, parallel requests, and KV cache quantization to maximize throughput and reduce memory pressure with increased 8GB allocation
- **Enhanced**: Persistent model loading eliminates warmup overhead for subsequent requests
- **Updated**: LLM_NARRATIVE_TIMEOUT increased to 180s provides better handling of concurrent requests and model loading
- Nginx: keepalive, gzip, and streaming timeouts tuned for SSE and SPA behavior
- **Updated**: Frontend proxy port optimization for better separation of concerns
- Volume placement: persistent volumes for PostgreSQL and Ollama data for durability and performance
- **Memory headroom**: 8GB Ollama allocation provides sufficient headroom for OS overhead and concurrent requests beyond the 5.3GB model footprint

## Troubleshooting Guide
Common operational issues and remedies:
- **JWT_SECRET_KEY errors in production**
  - Error: "JWT_SECRET_KEY environment variable must be set in production"
  - Solution: Set JWT_SECRET_KEY environment variable with a strong random value
  - Check: `docker-compose.prod.yml` line 86 requires JWT_SECRET_KEY
- **Ollama memory overflow under load**
  - **Updated**: Error: Ollama running out of memory during concurrent requests
  - Solution: Verify Ollama memory allocation is set to 8GB in `docker-compose.prod.yml` line 66
  - Check: Monitor Ollama container memory usage and consider adjusting OLLAMA_NUM_PARALLEL setting
- **Model not warming up properly**
  - **Updated**: Verify Ollama-warmup service completes successfully
  - Check: OLLAMA_KEEP_ALIVE=-1 persists model in memory
  - Verify: LLM_NARRATIVE_TIMEOUT=180 allows sufficient time for concurrent requests
- **Backend performance issues**
  - **Updated**: Verify backend has sufficient resources with 4CPUs/6GB allocation
  - Check: Uvicorn workers count is set to 6 in `docker-compose.prod.yml` line 82
  - Monitor: Backend CPU utilization and worker thread saturation
- **Database migration failures**
  - **Updated**: Verify PostgreSQL migration compatibility with recent changes
  - Check: Feature flag tables (`feature_flags`, `tenant_feature_overrides`) exist and are indexed
  - Verify: Webhook tables (`webhooks`, `webhook_deliveries`) have proper foreign key constraints
  - Monitor: Alembic migration logs for idempotent operation errors
- Ollama not responding
  - Inspect container logs and ensure the model is pulled and warmed
- Database locked errors
  - SQLite does not support concurrent writes; restart backend if encountering locks
- SSL certificate issues
  - Renew certificates and restart Nginx
- **Frontend not loading**
  - Verify port 8080 mapping in `docker-compose.prod.yml` line 132
  - Check frontend service health and port configuration

**Section sources**
- [README.md:339-355](file://README.md#L339-L355)
- [auth.py:13-21](file://app/backend/middleware/auth.py#L13-L21)
- [docker-compose.prod.yml:86](file://docker-compose.prod.yml#L86)
- [docker-compose.prod.yml:66](file://docker-compose.prod.yml#L66)
- [docker-compose.prod.yml:132](file://docker-compose.prod.yml#L132)
- [docker-compose.prod.yml:96-97](file://docker-compose.prod.yml#L96-L97)

## Conclusion
This production deployment leverages Docker Compose to orchestrate a resilient stack with Nginx as the reverse proxy, Alembic-managed PostgreSQL migrations, and Ollama for AI inference. The configuration emphasizes health checks, dynamic DNS resolution, streaming support, and automated image updates via Watchtower. **Critical security enhancements** include mandatory JWT_SECRET_KEY enforcement in production environments. **Enhanced**: The Ollama model warmup mechanism now uses a dedicated single-run container with persistent loading via OLLAMA_KEEP_ALIVE=-1, eliminating continuous keep-alive loops. **Updated**: LLM_NARRATIVE_TIMEOUT has been increased to 180s to better handle concurrent requests and improve system stability under load conditions. **Updated**: Backend service now operates with 6 Uvicorn workers and 4CPUs/6GB resource allocation for optimal performance. **Enhanced**: The PostgreSQL migration system now includes comprehensive compatibility improvements for feature flag seeding, webhook delivery tables, and billing configurations, ensuring consistent behavior across database systems. For production hardening, integrate external load balancing, SSL termination, and centralized monitoring/alerting.

## Appendices

### A. Server Preparation Checklist
- Install Docker Engine and add the deployment user to the docker group
- Create application directory and set ownership
- Install Certbot and obtain a certificate for the domain
- Configure DNS A record to point to the VPS

**Section sources**
- [README.md:113-138](file://README.md#L113-L138)

### B. Environment Variables and Secrets Management
- **Updated**: Required secrets and variables for deployment
  - Docker Hub credentials for image pulls
  - VPS host, username, and SSH key for automated deployment
  - **Critical**: JWT_SECRET_KEY must be set in production environment
  - **Updated**: Ollama memory allocation set to 8GB for production stability
  - **Enhanced**: LLM_NARRATIVE_TIMEOUT=180 for improved concurrent request handling
- Runtime environment variables
  - JWT secret key (required), database URL, Ollama base URL, model names, and timeouts
- Storage
  - Use Docker named volumes for PostgreSQL and Ollama data

**Section sources**
- [README.md:147-178](file://README.md#L147-L178)
- [docker-compose.prod.yml:81-95](file://docker-compose.prod.yml#L81-L95)
- [docker-compose.prod.yml:222-226](file://docker-compose.prod.yml#L222-L226)
- [auth.py:13-21](file://app/backend/middleware/auth.py#L13-L21)

### C. CI/CD and Automated Deployment
- CI workflow validates backend and frontend tests
- CD workflow builds and pushes images to Docker Hub
- Manual deployment step pulls latest images and restarts services

**Section sources**
- [ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

### D. Monitoring, Metrics, and Alerting
- Health endpoints
  - Backend health endpoint returns status and degraded indicators
  - Nginx health endpoint proxies to backend
- Recommendations
  - Integrate Prometheus and Grafana for metrics collection
  - Configure alerts for backend health, database connectivity, Ollama status, JWT_SECRET_KEY validation, Ollama memory usage, and model warmup completion

**Section sources**
- [main.py:228-259](file://app/backend/main.py#L228-L259)
- [nginx.prod.conf:29-34](file://nginx/nginx.prod.conf#L29-L34)
- [docker-compose.prod.yml:140-144](file://docker-compose.prod.yml#L140-L144)

### E. Scaling and Auto-Scaling
- Horizontal scaling
  - **Updated**: Backend service already configured with 6 Uvicorn workers for optimal CPU-bound tasks
  - Use an external load balancer to distribute traffic across replicas
- Auto-scaling
  - Scale backend pods based on CPU utilization and response latency
  - Ensure stateless backend and shared PostgreSQL/Ollama configuration
  - **Consider**: JWT_SECRET_KEY must be synchronized across scaled instances
  - **Updated**: Consider Ollama memory constraints when scaling multiple instances
  - **Enhanced**: Persistent model loading reduces scaling complexity as models remain loaded
  - **Updated**: Backend resource allocation (4CPUs/6GB) provides headroom for horizontal scaling

**Section sources**
- [docker-compose.prod.yml:101-112](file://docker-compose.prod.yml#L101-L112)
- [docker-compose.prod.yml:129-133](file://docker-compose.prod.yml#L129-L133)

### F. Database Migration Strategies
- Automated migrations
  - Alembic upgrades run at container start for PostgreSQL
- Version control
  - Migration scripts under alembic/versions
- Safe rollouts
  - Prefer zero-downtime migrations and maintain backups before updates
- **Updated**: PostgreSQL compatibility improvements
  - Idempotent operations ensure safe repeated execution
  - Consistent indexing patterns across all migration scripts
  - Foreign key constraints with proper CASCADE handling
  - Timezone-aware datetime columns for temporal data consistency

**Section sources**
- [docker-entrypoint.sh:4-14](file://app/backend/scripts/docker-entrypoint.sh#L4-L14)
- [env.py:14-20](file://alembic/env.py#L14-L20)
- [alembic.ini:84-87](file://alembic.ini#L84-L87)
- [012_admin_foundation.py:24-34](file://alembic/versions/012_admin_foundation.py#L24-L34)
- [013_webhooks_and_notifications.py:24-34](file://alembic/versions/013_webhooks_and_notifications.py#L24-L34)
- [014_billing_system.py:21-31](file://alembic/versions/014_billing_system.py#L21-L31)

### G. Backup and Disaster Recovery
- Backups
  - Snapshot PostgreSQL volume and Ollama data volume regularly
- Recovery
  - Restore volumes to a new stack and redeploy; verify health endpoints and model warm-up
  - **Include**: Verify JWT_SECRET_KEY consistency during recovery
  - **Updated**: Ensure Ollama memory allocation is properly restored during recovery
  - **Enhanced**: Verify persistent model loading continues to work after recovery
  - **Updated**: Validate PostgreSQL migration compatibility with restored database schema

**Section sources**
- [docker-compose.prod.yml:26-27](file://docker-compose.prod.yml#L26-L27)
- [docker-compose.prod.yml:56-57](file://docker-compose.prod.yml#L56-L57)

### H. Security Hardening and Access Control
- **Updated**: Network security
  - Restrict inbound ports; allow only necessary ports (e.g., 8080 for Nginx)
  - JWT_SECRET_KEY enforcement prevents unauthorized authentication
- **Enhanced**: Secrets management
  - Store JWT_SECRET_KEY in repository secrets and pass via environment variables
  - Use strong, randomly generated JWT_SECRET_KEY values
- TLS
  - Use external SSL termination or Certbot within the stack
- Access control
  - Limit SSH access to trusted keys and restrict administrative users

**Section sources**
- [README.md:147-178](file://README.md#L147-L178)
- [docker-compose.prod.yml:213-221](file://docker-compose.prod.yml#L213-L221)
- [auth.py:13-21](file://app/backend/middleware/auth.py#L13-L21)

### I. Deployment Checklists
- Pre-deploy
  - Verify environment variables and secrets including JWT_SECRET_KEY
  - Confirm model is pulled and warmed
  - **Verify**: JWT_SECRET_KEY is set in production environment
  - **Verify**: Ollama memory allocation is set to 8GB
  - **Verify**: LLM_NARRATIVE_TIMEOUT=180 for concurrent request handling
  - **Verify**: Backend has 6 Uvicorn workers configured
  - **Verify**: Backend resource allocation is 4CPUs/6GB
  - **Updated**: Verify PostgreSQL migration compatibility with feature flag and webhook tables
- Deploy
  - Pull latest images and restart services
- Post-deploy
  - Validate health endpoints and streaming
  - Monitor logs and metrics
  - **Test**: Authentication endpoints with JWT_SECRET_KEY
  - **Monitor**: Ollama memory usage under load conditions
  - **Verify**: Ollama-warmup service completes successfully and model remains loaded
  - **Updated**: Test database connectivity with new migration tables

**Section sources**
- [cd.yml:97-101](file://.github/workflows/cd.yml#L97-L101)
- [main.py:228-259](file://app/backend/main.py#L228-L259)
- [nginx.prod.conf:29-34](file://nginx/nginx.prod.conf#L29-L34)
- [auth.py:13-21](file://app/backend/middleware/auth.py#L13-L21)

### J. Rollback Procedures
- Rollback images
  - Use Watchtower or redeploy previous image tags
- Database rollback
  - Use Alembic downgrade to the prior migration if reversible
  - **Updated**: Consider rolling back to migration 012 if webhook functionality is problematic
- **Include**: JWT_SECRET_KEY rollback considerations for authentication continuity
- **Updated**: Consider reverting Ollama memory allocation if stability issues arise
- **Enhanced**: If persistent model loading fails, revert to continuous warmup approach
- **Updated**: Consider reducing backend workers from 6 back to 4 if performance issues occur

**Section sources**
- [docker-compose.prod.yml:192-211](file://docker-compose.prod.yml#L192-L211)
- [docker-entrypoint.sh:4-14](file://app/backend/scripts/docker-entrypoint.sh#L4-L14)

### K. Maintenance Schedule
- Weekly
  - Renew certificates
  - Review logs and metrics
  - **Monitor**: Ollama memory usage patterns
  - **Verify**: Persistent model loading continues to work correctly
  - **Monitor**: Backend worker utilization and performance
  - **Updated**: Validate PostgreSQL migration compatibility after updates
- Monthly
  - Rotate JWT_SECRET_KEY and update repository secrets
  - Validate database and Ollama volume snapshots
- **Quarterly**
  - **Review**: JWT_SECRET_KEY security audit and rotation policy compliance
  - **Review**: Ollama memory allocation effectiveness under production load
  - **Review**: LLM_NARRATIVE_TIMEOUT effectiveness for concurrent request handling
  - **Review**: Backend worker configuration effectiveness and resource utilization
  - **Updated**: Review PostgreSQL migration system performance and compatibility

**Section sources**
- [docker-compose.prod.yml:213-221](file://docker-compose.prod.yml#L213-L221)
- [README.md:147-178](file://README.md#L147-L178)