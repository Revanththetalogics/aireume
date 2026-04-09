# Deployment & DevOps

<cite>
**Referenced Files in This Document**
- [docker-compose.yml](file://docker-compose.yml)
- [docker-compose.prod.yml](file://docker-compose.prod.yml)
- [app/backend/Dockerfile](file://app/backend/Dockerfile)
- [app/frontend/Dockerfile](file://app/frontend/Dockerfile)
- [nginx/Dockerfile](file://nginx/Dockerfile)
- [app/nginx/nginx.conf](file://app/nginx/nginx.conf)
- [app/nginx/nginx.prod.conf](file://app/nginx/nginx.prod.conf)
- [.github/workflows/ci.yml](file://.github/workflows/ci.yml)
- [.github/workflows/cd.yml](file://.github/workflows/cd.yml)
- [app/backend/scripts/docker-entrypoint.sh](file://app/backend/scripts/docker-entrypoint.sh)
- [app/backend/scripts/wait_for_ollama.py](file://app/backend/scripts/wait_for_ollama.py)
- [app/backend/main.py](file://app/backend/main.py)
- [requirements.txt](file://requirements.txt)
- [README.md](file://README.md)
</cite>

## Update Summary
**Changes Made**
- Enhanced Docker configuration with zero-downtime rolling restarts using Watchtower's --rolling-restart flag
- Improved health checking with shallow/fast `/health` endpoint and comprehensive `/api/health/deep` endpoint
- Optimized worker processes with graceful shutdown handling using --workers 4 and --timeout-graceful-shutdown 30
- Added comprehensive background task management with proper shutdown handling
- Enhanced production deployment with optimized resource allocation and health checks

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
This document provides comprehensive deployment and DevOps guidance for Resume AI by ThetaLogics. It covers Docker configuration for development and production, multi-container orchestration, CI/CD with GitHub Actions, production deployment to a VPS, Nginx reverse proxy and SSL, environment variables and secrets, monitoring and logging, health checks, maintenance, troubleshooting, rollback procedures, scaling, security hardening, backups, and disaster recovery.

## Project Structure
The repository organizes the stack into three primary services plus supporting configurations:
- Backend service (FastAPI) with Dockerfile and entrypoint scripts
- Frontend service (React) built into Nginx static assets
- Nginx reverse proxy with distinct development and production configurations
- Orchestration via Docker Compose for local development and production
- CI/CD workflows for automated testing and image publishing

```mermaid
graph TB
subgraph "Local Dev"
DCDev["docker-compose.yml"]
DCDev --> PostgresDev["PostgreSQL"]
DCDev --> OllamaDev["Ollama"]
DCDev --> BackendDev["Backend (FastAPI)"]
DCDev --> FrontendDev["Frontend (Nginx static)"]
DCDev --> NginxDev["Nginx (dev config)"]
end
subgraph "Production"
DCP["docker-compose.prod.yml"]
DCP --> PostgresProd["PostgreSQL"]
DCP --> OllamaProd["Ollama"]
DCP --> BackendProd["Backend (FastAPI)"]
DCP --> FrontendProd["Frontend (Nginx static)"]
DCP --> NginxProd["Nginx (prod config)"]
DCP --> Watchtower["Watchtower (Rolling Restart)"]
DCP --> Certbot["Certbot"]
end
```

**Diagram sources**
- [docker-compose.yml:1-102](file://docker-compose.yml#L1-L102)
- [docker-compose.prod.yml:1-236](file://docker-compose.prod.yml#L1-L236)
- [app/nginx/nginx.conf:1-37](file://app/nginx/nginx.conf#L1-L37)
- [app/nginx/nginx.prod.conf:1-110](file://app/nginx/nginx.prod.conf#L1-L110)

**Section sources**
- [README.md:231-251](file://README.md#L231-L251)
- [docker-compose.yml:1-102](file://docker-compose.yml#L1-L102)
- [docker-compose.prod.yml:1-236](file://docker-compose.prod.yml#L1-L236)

## Core Components
- Backend service
  - FastAPI application with enhanced health checks and diagnostic endpoints
  - Entrypoint applies database migrations and waits for Ollama readiness
  - Exposes both shallow `/health` (fast) and comprehensive `/api/health/deep` endpoints
  - Optimized with 4 workers and graceful shutdown handling
- Frontend service
  - React app built into static assets served by Nginx
  - Multi-stage Dockerfile for efficient production images
- Nginx reverse proxy
  - Development configuration proxies to local dev servers
  - Production configuration handles SSL termination, rate limiting, and streaming
  - Health check passthrough to backend
- Orchestration
  - Local compose for development
  - Production compose with resource limits, healthchecks, and Watchtower auto-updates with rolling restarts

**Section sources**
- [app/backend/main.py:354-460](file://app/backend/main.py#L354-L460)
- [app/backend/scripts/docker-entrypoint.sh:1-20](file://app/backend/scripts/docker-entrypoint.sh#L1-L20)
- [app/backend/scripts/wait_for_ollama.py:1-96](file://app/backend/scripts/wait_for_ollama.py#L1-L96)
- [app/frontend/Dockerfile:1-26](file://app/frontend/Dockerfile#L1-L26)
- [nginx/Dockerfile:1-13](file://nginx/Dockerfile#L1-L13)
- [app/nginx/nginx.conf:1-37](file://app/nginx/nginx.conf#L1-L37)
- [app/nginx/nginx.prod.conf:1-110](file://app/nginx/nginx.prod.conf#L1-L110)

## Architecture Overview
The system uses a reverse proxy (Nginx) to route traffic to the React frontend and FastAPI backend. PostgreSQL stores application data, and Ollama provides local LLM inference. In production, Watchtower monitors images and auto-updates containers with zero-downtime rolling restarts, while Certbot manages SSL certificates.

```mermaid
graph TB
Client["Browser"] --> Nginx["Nginx (Reverse Proxy)"]
Nginx --> FE["Frontend (React Static)"]
Nginx --> BE["Backend (FastAPI)"]
BE --> DB["PostgreSQL"]
BE --> Ollama["Ollama (LLM)"]
subgraph "Production Orchestration"
Watchtower["Watchtower (Rolling Restart)"]
Certbot["Certbot"]
end
Watchtower -.-> Containers["Containers"]
Certbot -.-> Nginx
```

**Diagram sources**
- [app/nginx/nginx.prod.conf:1-110](file://app/nginx/nginx.prod.conf#L1-L110)
- [docker-compose.prod.yml:1-236](file://docker-compose.prod.yml#L1-L236)

## Detailed Component Analysis

### Backend Service
- Responsibilities
  - Application lifecycle: database initialization, dependency checks, startup banner
  - Enhanced health checks: shallow `/health` for container health and comprehensive `/api/health/deep` for full dependency validation
  - Streaming and non-streaming API routes with graceful shutdown support
- Startup flow
  - Entrypoint runs migrations for PostgreSQL and waits for Ollama readiness before launching Uvicorn
  - Shallow health endpoint validates process is alive (fast <10ms)
  - Deep health endpoint reports database connectivity, Ollama sentinel state, and disk space
  - Background tasks for cleanup with proper shutdown handling
- Containerization
  - Python slim image with system dependencies
  - Copies application code, Alembic migrations, and entrypoint scripts
  - Exposes port 8000; CMD overridden in production to use 4 workers with graceful shutdown

```mermaid
sequenceDiagram
participant Entrypoint as "Entrypoint Script"
participant Alembic as "Alembic"
participant Wait as "Wait for Ollama"
participant Uvicorn as "Uvicorn (4 workers)"
Entrypoint->>Alembic : "Upgrade database to head"
Alembic-->>Entrypoint : "Complete"
Entrypoint->>Wait : "Poll /api/tags and warm model"
Wait-->>Entrypoint : "Ready"
Entrypoint->>Uvicorn : "Start server with graceful shutdown"
```

**Diagram sources**
- [app/backend/scripts/docker-entrypoint.sh:1-20](file://app/backend/scripts/docker-entrypoint.sh#L1-L20)
- [app/backend/scripts/wait_for_ollama.py:1-96](file://app/backend/scripts/wait_for_ollama.py#L1-L96)
- [app/backend/Dockerfile:1-49](file://app/backend/Dockerfile#L1-L49)

**Section sources**
- [app/backend/Dockerfile:1-49](file://app/backend/Dockerfile#L1-L49)
- [app/backend/scripts/docker-entrypoint.sh:1-20](file://app/backend/scripts/docker-entrypoint.sh#L1-L20)
- [app/backend/scripts/wait_for_ollama.py:1-96](file://app/backend/scripts/wait_for_ollama.py#L1-L96)
- [app/backend/main.py:354-460](file://app/backend/main.py#L354-L460)
- [app/backend/main.py:238-282](file://app/backend/main.py#L238-L282)

### Frontend Service
- Responsibilities
  - Build React app into static assets
  - Serve assets via Nginx in production
- Containerization
  - Multi-stage build: Node builder produces dist assets, Nginx serves them
  - Default Nginx config copied into image; overridden by bind mount in production

**Section sources**
- [app/frontend/Dockerfile:1-26](file://app/frontend/Dockerfile#L1-L26)
- [nginx/Dockerfile:1-13](file://nginx/Dockerfile#L1-L13)

### Nginx Reverse Proxy
- Development
  - Proxies frontend dev server and backend dev server on localhost
- Production
  - SSL termination with Let's Encrypt
  - Rate limiting for API endpoints
  - Streaming-specific configuration for SSE to avoid buffering
  - Health check passthrough to backend

```mermaid
flowchart TD
Start(["Incoming HTTP"]) --> CheckPort{"Port 80 or 443?"}
CheckPort --> |80| Redirect["Redirect to HTTPS"]
CheckPort --> |443| SSL["Serve SSL certs"]
SSL --> RouteFE["Route / to Frontend"]
SSL --> RouteAPI["Route /api/ to Backend"]
SSL --> Stream["Route /api/analyze/stream (SSE)"]
SSL --> Health["Route /health to Backend"]
```

**Diagram sources**
- [app/nginx/nginx.prod.conf:1-110](file://app/nginx/nginx.prod.conf#L1-L110)

**Section sources**
- [app/nginx/nginx.conf:1-37](file://app/nginx/nginx.conf#L1-L37)
- [app/nginx/nginx.prod.conf:1-110](file://app/nginx/nginx.prod.conf#L1-L110)

### Orchestration and Services
- Local development
  - Compose defines services with explicit healthchecks and interdependencies
  - Ports exposed for local access
- Production
  - Resource limits and deploy constraints for CPU/memory
  - Watchtower auto-updates containers with zero-downtime rolling restarts
  - Certbot renewal loop with persistent volumes
  - Enhanced health checks for all services

```mermaid
graph LR
Postgres["PostgreSQL"] -- "healthy?" --> Backend["Backend (4 workers)"]
Ollama["Ollama"] -- "healthy?" --> Backend
Backend --> Nginx["Nginx (Graceful Shutdown)"]
Frontend["Frontend"] --> Nginx
Watchtower["Watchtower (Rolling Restart)"] --> Containers["All Containers"]
Certbot["Certbot"] --> Nginx
```

**Diagram sources**
- [docker-compose.yml:1-102](file://docker-compose.yml#L1-L102)
- [docker-compose.prod.yml:1-236](file://docker-compose.prod.yml#L1-L236)

**Section sources**
- [docker-compose.yml:1-102](file://docker-compose.yml#L1-L102)
- [docker-compose.prod.yml:1-236](file://docker-compose.prod.yml#L1-L236)

## Dependency Analysis
- Internal dependencies
  - Backend depends on PostgreSQL and Ollama; healthchecks enforce startup order
  - Frontend depends on backend for API; Nginx depends on both
- External dependencies
  - Docker images for Python, Node, Nginx, PostgreSQL, Ollama, Certbot, Watchtower
  - GitHub Actions for CI/CD and Docker Hub for image storage
- Runtime dependencies
  - Ollama models must be pulled and warmed in production
  - Database migrations are applied on backend startup
  - Background tasks require proper shutdown handling

```mermaid
graph TD
Backend["Backend (4 workers)"] --> DB["PostgreSQL"]
Backend --> Ollama["Ollama"]
Frontend["Frontend"] --> Backend
Nginx["Nginx"] --> Frontend
Nginx --> Backend
Watchtower["Watchtower (Rolling Restart)"] --> Backend
Watchtower --> Frontend
Watchtower --> Nginx
Certbot["Certbot"] --> Nginx
```

**Diagram sources**
- [docker-compose.prod.yml:1-236](file://docker-compose.prod.yml#L1-L236)

**Section sources**
- [docker-compose.yml:71-75](file://docker-compose.yml#L71-L75)
- [docker-compose.prod.yml:100-104](file://docker-compose.prod.yml#L100-L104)
- [app/backend/scripts/wait_for_ollama.py:34-91](file://app/backend/scripts/wait_for_ollama.py#L34-L91)

## Performance Considerations
- Backend concurrency
  - Production sets 4 Uvicorn workers to handle I/O-bound tasks efficiently
  - Graceful shutdown timeout of 30 seconds allows background tasks to complete
- Ollama tuning
  - Parallelism and memory settings optimized for model throughput and stability
  - Warmup job ensures first requests are not delayed by cold starts
- Database tuning
  - Production Postgres parameters tuned for memory and connections
- Streaming
  - Nginx disables buffering for SSE endpoints to prevent timeouts and improve responsiveness
- Health check optimization
  - Shallow health check (<10ms) for container health monitoring
  - Deep health check provides comprehensive dependency validation

**Section sources**
- [docker-compose.prod.yml:82-84](file://docker-compose.prod.yml#L82-L84)
- [docker-compose.prod.yml:46-51](file://docker-compose.prod.yml#L46-L51)
- [docker-compose.prod.yml:151-184](file://docker-compose.prod.yml#L151-L184)
- [app/nginx/nginx.prod.conf:73-102](file://app/nginx/nginx.prod.conf#L73-L102)
- [app/backend/main.py:354-460](file://app/backend/main.py#L354-L460)

## Troubleshooting Guide
- Ollama not responding
  - Inspect container logs and ensure the required model is pulled
- Database locked errors
  - Restart backend container to resolve SQLite contention
- SSL certificate issues
  - Renew certificates manually and restart Nginx
- Deploy failures
  - Verify Docker Hub credentials, SSH keys, and firewall access
- Rolling restart issues
  - Check Watchtower logs for restart conflicts
  - Verify graceful shutdown timeout settings
- Health check failures
  - Use `/health` for shallow checks, `/api/health/deep` for comprehensive validation

**Section sources**
- [README.md:339-355](file://README.md#L339-L355)
- [README.md:357-362](file://README.md#L357-L362)

## Conclusion
This guide outlines a robust, repeatable deployment process for Resume AI by ThetaLogics. It leverages Docker Compose for development, GitHub Actions for CI/CD, and production-grade orchestration with Watchtower and Certbot. The system emphasizes enhanced health checks, zero-downtime rolling restarts, streaming readiness, and operational simplicity for maintenance and scaling.

## Appendices

### CI/CD Pipeline with GitHub Actions
- CI workflow
  - Runs backend and frontend tests on PRs and pushes
  - Publishes coverage artifacts
- CD workflow
  - Builds and pushes backend, frontend, and Nginx images to Docker Hub
  - Provides manual trigger and VPS deployment steps

```mermaid
sequenceDiagram
participant Dev as "Developer"
participant GH as "GitHub"
participant CI as "CI Workflow"
participant CD as "CD Workflow"
participant Hub as "Docker Hub"
participant VPS as "VPS"
Dev->>GH : "Push code"
GH->>CI : "Run tests"
CI-->>GH : "Test results"
GH->>CD : "Build & push images"
CD->>Hub : "Publish images"
Dev->>GH : "Manual deploy trigger"
GH->>VPS : "SSH and update stack"
```

**Diagram sources**
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

**Section sources**
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

### Environment Variables and Secrets
- Backend environment variables
  - Database URL, JWT secret, Ollama base URL and model selection, environment mode, startup gating
  - Worker count and graceful shutdown timeout for production
- Production secrets
  - Store sensitive values in repository secrets and pass them via Compose
- Example variables
  - Database credentials, JWT secret, Ollama model names, timeouts, and environment mode

**Section sources**
- [docker-compose.yml:60-70](file://docker-compose.yml#L60-L70)
- [docker-compose.prod.yml:85-99](file://docker-compose.prod.yml#L85-L99)
- [README.md:147-178](file://README.md#L147-L178)

### Monitoring and Logging
- Enhanced health checks
  - Shallow `/health` endpoint for container health monitoring (<10ms response)
  - Comprehensive `/api/health/deep` endpoint for full dependency validation
  - Nginx health check routes to backend
  - Compose healthchecks for PostgreSQL and Ollama
- Observability
  - Use container logs and health endpoints for basic monitoring
  - Extend with external tools for metrics and alerting

**Section sources**
- [app/backend/main.py:354-460](file://app/backend/main.py#L354-L460)
- [docker-compose.yml:18-22](file://docker-compose.yml#L18-L22)
- [docker-compose.prod.yml:111-116](file://docker-compose.prod.yml#L111-L116)
- [docker-compose.prod.yml:146-151](file://docker-compose.prod.yml#L146-L151)

### Rollback Procedures
- Automatic updates
  - Watchtower auto-updates containers with zero-downtime rolling restarts
  - Disable or pin images to control rollouts
- Manual rollback
  - Pull previous image tags and redeploy using Compose
  - Use graceful shutdown timeouts to minimize disruption

**Section sources**
- [docker-compose.prod.yml:205-211](file://docker-compose.prod.yml#L205-L211)

### Scaling Considerations
- Horizontal scaling
  - Increase Uvicorn workers in production for CPU-bound I/O concurrency
  - Graceful shutdown timeout should accommodate increased worker count
- Vertical scaling
  - Adjust CPU/memory limits per service in production Compose
- Streaming scaling
  - Ensure Nginx streaming configuration remains unchanged for SSE
- Health check scaling
  - Shallow health checks scale horizontally with worker count
  - Deep health checks remain centralized for dependency validation

**Section sources**
- [docker-compose.prod.yml:82-84](file://docker-compose.prod.yml#L82-L84)
- [docker-compose.prod.yml:58-64](file://docker-compose.prod.yml#L58-L64)
- [app/nginx/nginx.prod.conf:73-102](file://app/nginx/nginx.prod.conf#L73-L102)

### Security Hardening
- Secrets management
  - Use repository secrets for Docker Hub credentials and VPS access
- Network exposure
  - Limit published ports; rely on internal networking within Compose
- SSL/TLS
  - Use Certbot for automatic certificate management and renewal
- Access control
  - Restrict SSH access to VPS and rotate keys regularly
- Health check security
  - `/health` endpoint provides minimal information for container monitoring
  - `/api/health/deep` requires authentication and provides comprehensive validation

**Section sources**
- [.github/workflows/cd.yml:60-64](file://.github/workflows/cd.yml#L60-L64)
- [README.md:147-178](file://README.md#L147-L178)
- [docker-compose.prod.yml:213-220](file://docker-compose.prod.yml#L213-L220)

### Backup and Disaster Recovery
- Data persistence
  - Persist PostgreSQL and Ollama data volumes
- Image retention
  - Maintain recent image tags for quick rollback
- DR plan
  - Document restore steps for volumes and environment variables; automate where possible
- Rolling restart backup
  - Watchtower provides automatic rollback capability
  - Graceful shutdown ensures clean state preservation

**Section sources**
- [docker-compose.yml:99-101](file://docker-compose.yml#L99-L101)
- [docker-compose.prod.yml:26-27](file://docker-compose.prod.yml#L26-L27)
- [docker-compose.prod.yml:222-236](file://docker-compose.prod.yml#L222-L236)

### Zero-Downtime Deployment Strategy
- Rolling restart configuration
  - Watchtower configured with `--rolling-restart` flag for seamless updates
  - Graceful shutdown timeout of 30 seconds allows background tasks to complete
  - Stop grace period of 60 seconds for backend service
  - 30-second stop grace period for Nginx service
- Health check strategy
  - Shallow `/health` endpoint for container monitoring (<10ms)
  - Deep `/api/health/deep` endpoint for comprehensive dependency validation
  - Service health checks integrated with Docker Compose
- Background task management
  - Proper cleanup of background tasks during shutdown
  - Sentinel shutdown handling for Ollama integration
  - Database connection cleanup for transaction safety

**Section sources**
- [docker-compose.prod.yml:205-211](file://docker-compose.prod.yml#L205-L211)
- [docker-compose.prod.yml:82-84](file://docker-compose.prod.yml#L82-L84)
- [docker-compose.prod.yml:138-139](file://docker-compose.prod.yml#L138-L139)
- [app/backend/main.py:238-282](file://app/backend/main.py#L238-L282)