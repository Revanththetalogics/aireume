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
- [app/backend/services/queue_manager.py](file://app/backend/services/queue_manager.py)
- [app/backend/routes/queue_api.py](file://app/backend/routes/queue_api.py)
- [deploy_queue_migration.sh](file://deploy_queue_migration.sh)
- [deploy_queue_migration.ps1](file://deploy_queue_migration.ps1)
- [requirements.txt](file://requirements.txt)
- [README.md](file://README.md)
</cite>

## Update Summary
**Changes Made**
- Enhanced deployment with comprehensive queue system architecture and management
- Improved Nginx configuration with advanced SSL support, rate limiting, and streaming optimizations
- Updated CI/CD pipelines with automated Docker builds for all three services
- Added migration system support with dedicated deployment scripts
- Implemented DNS resolution fixes for container networking reliability
- Expanded monitoring and health checking capabilities for queue workers

## Table of Contents
1. [Introduction](#introduction)
2. [Cloud-First Architecture](#cloud-first-architecture)
3. [Project Structure](#project-structure)
4. [Core Components](#core-components)
5. [Architecture Overview](#architecture-overview)
6. [Detailed Component Analysis](#detailed-component-analysis)
7. [Queue System Implementation](#queue-system-implementation)
8. [Nginx SSL and Streaming Configuration](#nginx-ssl-and-streaming-configuration)
9. [CI/CD Pipeline Enhancements](#cicd-pipeline-enhancements)
10. [Migration System Support](#migration-system-support)
11. [DNS Resolution and Networking](#dns-resolution-and-networking)
12. [Dependency Analysis](#dependency-analysis)
13. [Performance Considerations](#performance-considerations)
14. [Troubleshooting Guide](#troubleshooting-guide)
15. [Conclusion](#conclusion)
16. [Appendices](#appendices)

## Introduction
This document provides comprehensive deployment and DevOps guidance for Resume AI by ThetaLogics with enhanced cloud-first approach. The platform now features a robust queue system for scalable job processing, advanced Nginx configuration with SSL support, automated CI/CD pipelines, and comprehensive migration management. It covers Docker configuration for development and production, multi-container orchestration, queue-based job processing, SSL termination, environment variables and secrets management, monitoring and logging, health checks, maintenance, troubleshooting, rollback procedures, scaling, security hardening, backups, and disaster recovery.

**Updated** Enhanced with queue system architecture, improved Nginx SSL configuration, automated CI/CD builds, and migration system support.

## Cloud-First Architecture
The Resume AI platform is designed with a cloud-first approach featuring a comprehensive queue system for scalable job processing. The architecture emphasizes:

- **Cloud-Native Design**: Container-first deployment with minimal local infrastructure requirements
- **Queue-Based Processing**: Asynchronous job processing with priority scheduling and retry mechanisms
- **Ollama Cloud Integration**: Default configuration uses Ollama Cloud for scalable LLM inference
- **Advanced Nginx Configuration**: SSL termination, rate limiting, and streaming optimizations
- **Automated CI/CD**: Three-service pipeline with Docker Hub integration
- **Migration Management**: Automated database schema updates with rollback support
- **DNS Resolution**: Embedded DNS configuration for reliable container networking

```mermaid
graph TB
subgraph "Enhanced Cloud Architecture"
Client["Browser Clients"] --> Nginx["Nginx (SSL + Rate Limiting)"]
Nginx --> FE["Frontend (React Static)"]
Nginx --> BE["Backend (FastAPI)"]
BE --> Queue["Queue System (Priority + Retry)"]
Queue --> DB["PostgreSQL (Managed)"]
BE --> OllamaCloud["Ollama Cloud (Default)"]
BE --> OllamaLocal["Ollama Local (Optional)"]
end
subgraph "Cloud Infrastructure"
Watchtower["Watchtower (Auto Updates)"]
Certbot["Certbot (SSL Management)"]
QueueWorker["Queue Worker (Background)"]
end
Nginx --> Certbot
BE --> Watchtower
QueueWorker --> DB
```

**Diagram sources**
- [docker-compose.yml:60-67](file://docker-compose.yml#L60-L67)
- [docker-compose.prod.yml:86-89](file://docker-compose.prod.yml#L86-L89)
- [app/backend/main.py:463-554](file://app/backend/main.py#L463-L554)
- [app/backend/services/queue_manager.py:189-215](file://app/backend/services/queue_manager.py#L189-L215)

**Section sources**
- [README.md:208-224](file://README.md#L208-L224)
- [docker-compose.yml:60-67](file://docker-compose.yml#L60-L67)
- [docker-compose.prod.yml:86-89](file://docker-compose.prod.yml#L86-L89)

## Project Structure
The repository organizes the stack into five primary services plus supporting configurations, optimized for cloud deployment with queue system integration:

- **Backend service (FastAPI)** with enhanced cloud-native health checks, queue worker integration, and Ollama Cloud authentication
- **Frontend service (React)** built into Nginx static assets for optimal CDN delivery
- **Nginx reverse proxy** with cloud-optimized SSL termination, rate limiting, and streaming configuration
- **Queue system** with priority-based job scheduling, automatic retry, and worker monitoring
- **Orchestration via Docker Compose** for both development and production cloud environments
- **CI/CD workflows** for automated testing and cloud image publishing across all services

```mermaid
graph TB
subgraph "Enhanced Cloud-Optimized Services"
DCDev["docker-compose.yml"]
DCDev --> PostgresDev["PostgreSQL (Managed)"]
DCDev --> OllamaCloudDev["Ollama Cloud (Default)"]
DCDev --> BackendDev["Backend (FastAPI + Queue)"]
DCDev --> FrontendDev["Frontend (Nginx static)"]
DCDev --> NginxDev["Nginx (Cloud Config)"]
DCDev --> QueueWorkerDev["Queue Worker (Background)"]
end
subgraph "Production Cloud"
DCP["docker-compose.prod.yml"]
DCP --> PostgresProd["PostgreSQL (Managed)"]
DCP --> OllamaCloudProd["Ollama Cloud (Default)"]
DCP --> BackendProd["Backend (FastAPI + Queue)"]
DCP --> FrontendProd["Frontend (Nginx static)"]
DCP --> NginxProd["Nginx (Cloud Config)"]
DCP --> Watchtower["Watchtower (Cloud Updates)"]
DCP --> Certbot["Certbot (Cloud SSL)"]
DCP --> QueueWorkerProd["Queue Worker (Background)"]
end
```

**Diagram sources**
- [docker-compose.yml:1-113](file://docker-compose.yml#L1-L113)
- [docker-compose.prod.yml:1-241](file://docker-compose.prod.yml#L1-L241)
- [app/nginx/nginx.conf:1-45](file://app/nginx/nginx.conf#L1-L45)
- [app/nginx/nginx.prod.conf:1-110](file://app/nginx/nginx.prod.conf#L1-L110)

**Section sources**
- [README.md:231-251](file://README.md#L231-L251)
- [docker-compose.yml:1-113](file://docker-compose.yml#L1-L113)
- [docker-compose.prod.yml:1-241](file://docker-compose.prod.yml#L1-L241)

## Core Components
- **Backend service**
  - FastAPI application with enhanced cloud-native health checks and Ollama Cloud authentication
  - Integrated queue worker for asynchronous job processing with priority scheduling
  - Automatic Ollama Cloud model loading and warmup for optimal performance
  - Comprehensive `/api/health/deep` endpoint for full dependency validation
  - Optimized with 4 workers and graceful shutdown handling for cloud environments
- **Frontend service**
  - React app built into static assets served by Nginx for CDN optimization
  - Multi-stage Dockerfile for efficient cloud production images
- **Nginx reverse proxy**
  - Cloud-optimized configuration with SSL termination, rate limiting, and streaming for SSE
  - Advanced security headers and performance optimizations
  - Health check passthrough to backend with cloud-native routing
- **Queue system**
  - Priority-based job scheduling with automatic retry and exponential backoff
  - Worker health monitoring and stale job recovery mechanisms
  - Comprehensive job tracking with metrics collection and progress reporting
- **Orchestration**
  - Local compose for development with cloud-first defaults
  - Production compose optimized for cloud infrastructure with resource limits and healthchecks

**Updated** Enhanced backend service with integrated queue worker and improved cloud-native Ollama Cloud integration.

**Section sources**
- [app/backend/main.py:354-460](file://app/backend/main.py#L354-L460)
- [app/backend/scripts/docker-entrypoint.sh:1-20](file://app/backend/scripts/docker-entrypoint.sh#L1-L20)
- [app/backend/scripts/wait_for_ollama.py:1-108](file://app/backend/scripts/wait_for_ollama.py#L1-L108)
- [app/frontend/Dockerfile:1-35](file://app/frontend/Dockerfile#L1-L35)
- [nginx/Dockerfile:1-13](file://nginx/Dockerfile#L1-L13)
- [app/nginx/nginx.conf:1-45](file://app/nginx/nginx.conf#L1-L45)
- [app/nginx/nginx.prod.conf:1-110](file://app/nginx/nginx.prod.conf#L1-L110)
- [app/backend/services/queue_manager.py:189-215](file://app/backend/services/queue_manager.py#L189-L215)

## Architecture Overview
The system uses a cloud-optimized reverse proxy (Nginx) with advanced SSL configuration to route traffic to the React frontend and FastAPI backend. The backend now includes integrated queue processing for scalable job management. PostgreSQL is managed as a cloud service, and Ollama Cloud provides scalable LLM inference. In production, Watchtower monitors images and auto-updates containers with zero-downtime rolling restarts, while Certbot manages SSL certificates for cloud domains. The queue worker operates as a background service for asynchronous job processing.

```mermaid
graph TB
Client["Browser"] --> Nginx["Nginx (Cloud SSL + Rate Limiting)"]
Nginx --> FE["Frontend (React Static)"]
Nginx --> BE["Backend (FastAPI + Queue)"]
BE --> Queue["Queue System"]
Queue --> DB["PostgreSQL (Cloud Managed)"]
BE --> OllamaCloud["Ollama Cloud (Default)"]
BE --> OllamaLocal["Ollama Local (Optional)"]
BE --> QueueWorker["Queue Worker"]
subgraph "Cloud Orchestration"
Watchtower["Watchtower (Cloud Updates)"]
Certbot["Certbot (Cloud SSL)"]
end
Watchtower -.-> Containers["Cloud Containers"]
Certbot -.-> Nginx
QueueWorker -.-> DB
```

**Diagram sources**
- [app/nginx/nginx.prod.conf:1-110](file://app/nginx/nginx.prod.conf#L1-L110)
- [docker-compose.prod.yml:1-241](file://docker-compose.prod.yml#L1-L241)

## Detailed Component Analysis

### Backend Service
- **Responsibilities**
  - Application lifecycle: database initialization, dependency checks, startup banner
  - Enhanced cloud-native health checks: shallow `/health` for container health and comprehensive `/api/health/deep` for full dependency validation
  - Streaming and non-streaming API routes with graceful shutdown support
  - Ollama Cloud authentication and model management
  - Integrated queue worker for asynchronous job processing
- **Startup flow**
  - Entrypoint runs migrations for PostgreSQL and waits for Ollama readiness before launching Uvicorn
  - Shallow health endpoint validates process is alive (fast <10ms)
  - Deep health endpoint reports database connectivity, Ollama sentinel state, and disk space
  - Cloud-native Ollama Cloud integration with automatic authentication
  - Background tasks for cleanup with proper shutdown handling
  - Queue worker initialization with priority-based job processing
- **Containerization**
  - Python slim image with system dependencies
  - Copies application code, Alembic migrations, and entrypoint scripts
  - Exposes port 8000; CMD overridden in production to use 4 workers with graceful shutdown

```mermaid
sequenceDiagram
participant Entrypoint as "Entrypoint Script"
participant Alembic as "Alembic"
participant Wait as "Wait for Ollama"
participant OllamaAuth as "Ollama Cloud Auth"
participant Uvicorn as "Uvicorn (4 workers)"
Entrypoint->>Alembic : "Upgrade database to head"
Alembic-->>Entrypoint : "Complete"
Entrypoint->>Wait : "Poll /api/tags and warm model"
Wait->>OllamaAuth : "Authenticate with API key"
OllamaAuth-->>Wait : "Validated"
Wait-->>Entrypoint : "Ready"
Entrypoint->>Uvicorn : "Start server with graceful shutdown"
Uvicorn->>QueueWorker : "Initialize queue worker"
```

**Diagram sources**
- [app/backend/scripts/docker-entrypoint.sh:1-20](file://app/backend/scripts/docker-entrypoint.sh#L1-L20)
- [app/backend/scripts/wait_for_ollama.py:1-108](file://app/backend/scripts/wait_for_ollama.py#L1-L108)
- [app/backend/Dockerfile:1-49](file://app/backend/Dockerfile#L1-L49)

**Section sources**
- [app/backend/Dockerfile:1-49](file://app/backend/Dockerfile#L1-L49)
- [app/backend/scripts/docker-entrypoint.sh:1-20](file://app/backend/scripts/docker-entrypoint.sh#L1-L20)
- [app/backend/scripts/wait_for_ollama.py:1-108](file://app/backend/scripts/wait_for_ollama.py#L1-L108)
- [app/backend/main.py:354-460](file://app/backend/main.py#L354-L460)
- [app/backend/main.py:238-282](file://app/backend/main.py#L238-L282)

### Frontend Service
- **Responsibilities**
  - Build React app into static assets for optimal CDN delivery
  - Serve assets via Nginx in production with cloud optimization
- **Containerization**
  - Multi-stage build: Node builder produces dist assets, Nginx serves them
  - Default Nginx config copied into image; overridden by bind mount in production

**Section sources**
- [app/frontend/Dockerfile:1-35](file://app/frontend/Dockerfile#L1-L35)
- [nginx/Dockerfile:1-13](file://nginx/Dockerfile#L1-L13)

### Nginx Reverse Proxy
- **Development**
  - Proxies frontend dev server and backend dev server on localhost
- **Production**
  - Cloud-optimized SSL termination with Let's Encrypt and advanced security headers
  - Rate limiting for API endpoints with configurable zones and burst protection
  - Streaming-specific configuration for SSE to avoid buffering with proxy_buffering off
  - Health check passthrough to backend with cloud routing
  - Embedded DNS resolution for reliable container networking

```mermaid
flowchart TD
Start(["Incoming HTTP"]) --> CheckPort{"Port 80 or 443?"}
CheckPort --> |80| Redirect["Redirect to HTTPS"]
CheckPort --> |443| SSL["Serve SSL certs (Cloud)"]
SSL --> RateLimit["Rate Limiting Zone"]
SSL --> SecurityHeaders["Security Headers"]
SSL --> RouteFE["Route / to Frontend"]
SSL --> RouteAPI["Route /api/ to Backend"]
SSL --> Stream["Route /api/analyze/stream (SSE)"]
SSL --> Health["Route /health to Backend"]
SSL --> Resolver["Embedded DNS Resolution"]
```

**Diagram sources**
- [app/nginx/nginx.prod.conf:1-110](file://app/nginx/nginx.prod.conf#L1-L110)

**Section sources**
- [app/nginx/nginx.conf:1-45](file://app/nginx/nginx.conf#L1-L45)
- [app/nginx/nginx.prod.conf:1-110](file://app/nginx/nginx.prod.conf#L1-L110)

### Orchestration and Services
- **Local development**
  - Compose defines services with explicit healthchecks and interdependencies
  - Cloud-first defaults with Ollama Cloud as default configuration
  - Ports exposed for local access
- **Production**
  - Cloud-optimized resource limits and deploy constraints for CPU/memory
  - Watchtower auto-updates containers with zero-downtime rolling restarts
  - Certbot renewal loop with persistent volumes for cloud SSL
  - Enhanced health checks for all services with cloud-native monitoring
  - Queue worker service for background job processing

```mermaid
graph LR
Postgres["PostgreSQL (Cloud)"] -- "healthy?" --> Backend["Backend (4 workers + Queue)"]
OllamaCloud["Ollama Cloud (Default)"] -- "healthy?" --> Backend
Backend --> Nginx["Nginx (Cloud Optimized)"]
Frontend["Frontend"] --> Nginx
Nginx --> Certbot["Certbot (SSL)"]
Backend --> Watchtower["Watchtower (Updates)"]
Backend --> QueueWorker["Queue Worker"]
QueueWorker --> Postgres
```

**Diagram sources**
- [docker-compose.yml:1-113](file://docker-compose.yml#L1-L113)
- [docker-compose.prod.yml:1-241](file://docker-compose.prod.yml#L1-L241)

**Section sources**
- [docker-compose.yml:1-113](file://docker-compose.yml#L1-L113)
- [docker-compose.prod.yml:1-241](file://docker-compose.prod.yml#L1-L241)

## Queue System Implementation
The platform now features a comprehensive queue system for scalable job processing with the following capabilities:

- **Priority-Based Scheduling**: Jobs are processed based on priority levels (1-10) with configurable poll intervals
- **Automatic Retry**: Exponential backoff retry mechanism with configurable delay patterns
- **Worker Health Monitoring**: Heartbeat tracking and stale job recovery for fault tolerance
- **Deduplication**: Input hashing prevents duplicate job processing
- **Metrics Collection**: Comprehensive performance tracking and error reporting
- **Background Processing**: Queue worker operates independently for non-blocking job execution

```mermaid
sequenceDiagram
participant Client as "Client"
participant API as "Queue API"
participant Queue as "Queue Manager"
participant Worker as "Queue Worker"
participant DB as "PostgreSQL"
Client->>API : "POST /queue/submit"
API->>Queue : "enqueue_job()"
Queue->>DB : "Insert AnalysisJob"
DB-->>Queue : "Job Created"
Queue-->>API : "job_id"
API-->>Client : "Queued Response"
loop Worker Loop
Worker->>Queue : "get_next_job()"
Queue->>DB : "SELECT FOR UPDATE SKIP LOCKED"
DB-->>Queue : "Next Job"
Queue-->>Worker : "Job Details"
Worker->>Worker : "process_job()"
Worker->>DB : "Update Job Status"
DB-->>Worker : "Status Updated"
Worker-->>Queue : "Processing Complete"
end
```

**Diagram sources**
- [app/backend/services/queue_manager.py:221-304](file://app/backend/services/queue_manager.py#L221-L304)
- [app/backend/services/queue_manager.py:526-562](file://app/backend/services/queue_manager.py#L526-L562)

**Section sources**
- [app/backend/services/queue_manager.py:189-215](file://app/backend/services/queue_manager.py#L189-L215)
- [app/backend/routes/queue_api.py:38-76](file://app/backend/routes/queue_api.py#L38-L76)
- [app/backend/services/queue_manager.py:349-496](file://app/backend/services/queue_manager.py#L349-L496)

## Nginx SSL and Streaming Configuration
The Nginx configuration has been significantly enhanced with advanced SSL support and streaming optimizations:

- **SSL Termination**: Cloud-native SSL configuration with Let's Encrypt integration
- **Rate Limiting**: Configurable rate limiting zones with burst protection for API endpoints
- **Security Headers**: Comprehensive security headers including HSTS, XSS protection, and CSP
- **Streaming Optimization**: Critical SSE streaming configuration with proxy_buffering off
- **DNS Resolution**: Embedded DNS configuration to handle container IP changes
- **Health Checks**: Dedicated health check endpoint routing to backend

```mermaid
flowchart TD
SSLConfig["SSL Configuration"] --> Certificates["Let's Encrypt Certificates"]
SSLConfig --> SecurityHeaders["Security Headers"]
SSLConfig --> RateLimiting["Rate Limiting Zones"]
Streaming["Streaming Configuration"] --> BufferingOff["proxy_buffering off"]
Streaming --> ChunkedTransfer["chunked_transfer_encoding on"]
Streaming --> GzipOff["gzip off"]
Streaming --> XAccelBuffering["X-Accel-Buffering no"]
DNS["DNS Resolution"] --> Resolver127["resolver 127.0.0.11"]
DNS --> ValidCache["valid=30s"]
DNS --> IPv6Off["ipv6=off"]
```

**Diagram sources**
- [app/nginx/nginx.prod.conf:27-102](file://app/nginx/nginx.prod.conf#L27-L102)

**Section sources**
- [app/nginx/nginx.prod.conf:1-110](file://app/nginx/nginx.prod.conf#L1-L110)
- [nginx/nginx.prod.conf:12-21](file://nginx/nginx.prod.conf#L12-L21)

## CI/CD Pipeline Enhancements
The CI/CD pipeline has been updated to support automated Docker builds for all three services:

- **CI Workflow**
  - Runs backend and frontend tests on PRs and pushes
  - Publishes coverage artifacts with cloud-native testing
- **CD Workflow**
  - Builds and pushes backend, frontend, and Nginx images to Docker Hub
  - Provides manual trigger and cloud deployment steps
  - Supports concurrent builds with caching optimization

```mermaid
sequenceDiagram
participant Dev as "Developer"
participant GH as "GitHub"
participant CI as "CI Workflow"
participant CD as "CD Workflow"
participant Hub as "Docker Hub (Cloud)"
participant Cloud as "Cloud Provider"
Dev->>GH : "Push code"
GH->>CI : "Run tests"
CI-->>GH : "Test results"
GH->>CD : "Build & push images"
CD->>Hub : "Publish cloud images"
CD->>Hub : "Build backend : latest"
CD->>Hub : "Build frontend : latest"
CD->>Hub : "Build nginx : latest"
Dev->>GH : "Manual deploy trigger"
GH->>Cloud : "Deploy to cloud infrastructure"
```

**Diagram sources**
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

**Section sources**
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

## Migration System Support
The platform now includes comprehensive migration system support with dedicated deployment scripts:

- **Database Migrations**: Alembic-based schema updates for queue system tables
- **Deployment Scripts**: Platform-specific scripts for Windows and Unix systems
- **Backup and Rollback**: Automated backup creation and rollback capabilities
- **Verification**: Post-migration table verification and structure validation

```mermaid
flowchart TD
Migration["Queue Migration"] --> Backup["Database Backup"]
Backup --> Status["Current Migration Status"]
Status --> Upgrade["alembic upgrade head"]
Upgrade --> Verify["Verify Tables Created"]
Verify --> Structure["Check Table Structure"]
Structure --> Complete["Migration Complete"]
Complete --> NextSteps["Next Steps Notification"]
```

**Diagram sources**
- [deploy_queue_migration.sh:18-34](file://deploy_queue_migration.sh#L18-L34)

**Section sources**
- [deploy_queue_migration.sh:1-67](file://deploy_queue_migration.sh#L1-L67)
- [deploy_queue_migration.ps1:1-66](file://deploy_queue_migration.ps1#L1-L66)

## DNS Resolution and Networking
The platform implements advanced DNS resolution mechanisms for reliable container networking:

- **Embedded DNS**: Docker embedded DNS service configuration for dynamic hostname resolution
- **Resolver Configuration**: Custom resolver settings with 30-second cache and 5-second timeout
- **IPv6 Handling**: Explicit IPv6 disabling for Docker bridge network compatibility
- **Health Check Routing**: Dynamic upstream routing for health check endpoints
- **Container IP Changes**: Automatic DNS refresh to handle container recreation scenarios

**Section sources**
- [nginx/nginx.prod.conf:12-21](file://nginx/nginx.prod.conf#L12-L21)
- [app/nginx/nginx.prod.conf:36-41](file://app/nginx/nginx.prod.conf#L36-L41)

## Dependency Analysis
- **Internal dependencies**
  - Backend depends on PostgreSQL and Ollama Cloud; healthchecks enforce startup order
  - Frontend depends on backend for API; Nginx depends on both
  - Queue worker depends on database for job processing
  - Cloud-native dependencies optimized for managed services
- **External dependencies**
  - Docker images for Python, Node, Nginx, PostgreSQL (managed), Ollama Cloud, Certbot, Watchtower
  - GitHub Actions for CI/CD and Docker Hub for cloud image storage
- **Runtime dependencies**
  - Ollama Cloud models managed automatically; authentication handled via API keys
  - Database migrations applied on backend startup to managed PostgreSQL
  - Background tasks require proper shutdown handling for cloud environments
  - Queue worker requires database connectivity for job processing

```mermaid
graph TD
Backend["Backend (4 workers + Queue)"] --> DB["PostgreSQL (Cloud)"]
Backend --> OllamaCloud["Ollama Cloud (Default)"]
Frontend["Frontend"] --> Backend
Nginx["Nginx (Cloud)"] --> Frontend
Nginx --> Backend
Watchtower["Watchtower (Cloud Updates)"] --> Backend
Watchtower --> Frontend
Watchtower --> Nginx
Certbot["Certbot (Cloud SSL)"] --> Nginx
QueueWorker["Queue Worker"] --> DB
```

**Diagram sources**
- [docker-compose.prod.yml:1-241](file://docker-compose.prod.yml#L1-L241)

**Section sources**
- [docker-compose.yml:76-82](file://docker-compose.yml#L76-L82)
- [docker-compose.prod.yml:103-109](file://docker-compose.prod.yml#L103-L109)
- [app/backend/scripts/wait_for_ollama.py:34-91](file://app/backend/scripts/wait_for_ollama.py#L34-L91)

## Performance Considerations
- **Backend concurrency**
  - Production sets 4 Uvicorn workers to handle I/O-bound tasks efficiently in cloud environments
  - Graceful shutdown timeout of 30 seconds allows background tasks to complete
- **Queue system optimization**
  - Configurable max concurrent jobs (default: 3) with adjustable poll intervals
  - Exponential backoff retry delays (1min, 5min, 15min) for fault tolerance
  - Heartbeat monitoring with stale job recovery (default: 10min timeout)
- **Ollama Cloud optimization**
  - Cloud-native model loading and warmup for optimal performance
  - Automatic authentication reduces cold start latency
  - Scalable infrastructure handles varying load patterns
- **Database tuning**
  - Production Postgres parameters tuned for cloud-managed services
  - Connection pooling optimized for cloud environments
- **Streaming**
  - Nginx disables buffering for SSE endpoints to prevent timeouts and improve responsiveness
  - Cloud CDN optimization for static asset delivery
- **Health check optimization**
  - Shallow health check (<10ms) for container health monitoring
  - Deep health check provides comprehensive dependency validation

**Section sources**
- [docker-compose.prod.yml:82-84](file://docker-compose.prod.yml#L82-L84)
- [docker-compose.prod.yml:46-51](file://docker-compose.prod.yml#L46-L51)
- [docker-compose.prod.yml:151-184](file://docker-compose.prod.yml#L151-L184)
- [app/nginx/nginx.prod.conf:73-102](file://app/nginx/nginx.prod.conf#L73-L102)
- [app/backend/main.py:354-460](file://app/backend/main.py#L354-L460)
- [app/backend/services/queue_manager.py:201-204](file://app/backend/services/queue_manager.py#L201-L204)

## Troubleshooting Guide
- **Ollama Cloud authentication issues**
  - Verify OLLAMA_API_KEY environment variable is set correctly
  - Check cloud service availability and rate limits
- **Database connectivity problems**
  - Verify PostgreSQL connection string for cloud-managed service
  - Check network connectivity and firewall rules
- **SSL certificate issues**
  - Renew certificates manually and restart Nginx
  - Verify DNS configuration for cloud domains
- **Queue system issues**
  - Check queue worker logs for job processing errors
  - Verify database connectivity for job persistence
  - Monitor queue depth and processing times
- **DNS resolution problems**
  - Verify embedded DNS configuration in Nginx
  - Check resolver settings and timeout values
  - Ensure container networking is functioning properly
- **Deploy failures**
  - Verify Docker Hub credentials, SSH keys, and firewall access
  - Check cloud provider quotas and limits
- **Rolling restart issues**
  - Check Watchtower logs for restart conflicts
  - Verify graceful shutdown timeout settings
- **Health check failures**
  - Use `/health` for shallow checks, `/api/health/deep` for comprehensive validation
  - Monitor cloud-native health indicators

**Section sources**
- [README.md:339-355](file://README.md#L339-L355)
- [README.md:357-362](file://README.md#L357-L362)

## Conclusion
This guide outlines a robust, cloud-first deployment process for Resume AI by ThetaLogics with enhanced queue system capabilities. It leverages Docker Compose for development with cloud-native defaults, GitHub Actions for CI/CD with automated Docker builds, and production-grade orchestration with Watchtower and Certbot. The system emphasizes enhanced health checks, zero-downtime rolling restarts, streaming readiness, comprehensive queue processing, SSL security, migration management, and operational simplicity for maintenance and scaling in cloud environments.

**Updated** Enhanced emphasis on cloud-native deployment patterns with Ollama Cloud as the default configuration, comprehensive queue system integration, and advanced SSL configuration.

## Appendices

### CI/CD Pipeline with GitHub Actions
- **CI workflow**
  - Runs backend and frontend tests on PRs and pushes
  - Publishes coverage artifacts with cloud-native testing
- **CD workflow**
  - Builds and pushes backend, frontend, and Nginx images to Docker Hub
  - Provides manual trigger and cloud deployment steps

```mermaid
sequenceDiagram
participant Dev as "Developer"
participant GH as "GitHub"
participant CI as "CI Workflow"
participant CD as "CD Workflow"
participant Hub as "Docker Hub (Cloud)"
participant Cloud as "Cloud Provider"
Dev->>GH : "Push code"
GH->>CI : "Run tests"
CI-->>GH : "Test results"
GH->>CD : "Build & push images"
CD->>Hub : "Publish cloud images"
Dev->>GH : "Manual deploy trigger"
GH->>Cloud : "Deploy to cloud infrastructure"
```

**Diagram sources**
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

**Section sources**
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

### Environment Variables and Secrets
- **Backend environment variables**
  - Database URL for cloud-managed PostgreSQL, JWT secret, Ollama Cloud API key and model selection
  - Cloud-native environment mode with startup gating
  - Worker count and graceful shutdown timeout for production
  - Queue system configuration (max concurrent, poll intervals, heartbeat)
- **Production secrets**
  - Store sensitive values in repository secrets and pass them via Compose
  - Cloud-native secret management for API keys and credentials
- **Example variables**
  - Database credentials, JWT secret, Ollama Cloud API key, timeouts, and environment mode

**Section sources**
- [docker-compose.yml:60-82](file://docker-compose.yml#L60-L82)
- [docker-compose.prod.yml:85-103](file://docker-compose.prod.yml#L85-L103)
- [README.md:147-178](file://README.md#L147-L178)

### Monitoring and Logging
- **Enhanced health checks**
  - Shallow `/health` endpoint for container health monitoring (<10ms response)
  - Comprehensive `/api/health/deep` endpoint for full dependency validation
  - Nginx health check routes to backend
  - Compose healthchecks for cloud-managed PostgreSQL and Ollama Cloud
- **Queue monitoring**
  - Worker statistics and job processing metrics
  - Queue depth and performance tracking
  - Error rates and retry patterns
- **Cloud-native observability**
  - Use container logs and health endpoints for basic monitoring
  - Extend with external tools for metrics and alerting in cloud environments
  - Prometheus metrics collection for cloud monitoring

**Section sources**
- [app/backend/main.py:354-460](file://app/backend/main.py#L354-L460)
- [docker-compose.yml:18-22](file://docker-compose.yml#L18-L22)
- [docker-compose.prod.yml:115-121](file://docker-compose.prod.yml#L115-L121)
- [docker-compose.prod.yml:149-156](file://docker-compose.prod.yml#L149-L156)
- [app/backend/services/queue_manager.py:573-583](file://app/backend/services/queue_manager.py#L573-L583)

### Rollback Procedures
- **Automatic updates**
  - Watchtower auto-updates containers with zero-downtime rolling restarts
  - Disable or pin images to control rollouts
- **Manual rollback**
  - Pull previous image tags and redeploy using Compose
  - Use graceful shutdown timeouts to minimize disruption
- **Cloud-native rollback**
  - Leverage cloud provider rollback capabilities
  - Use image versioning for controlled rollbacks
- **Migration rollback**
  - Use Alembic downgrade commands for database schema changes
  - Restore from backup files created during migration

**Section sources**
- [docker-compose.prod.yml:205-211](file://docker-compose.prod.yml#L205-L211)
- [deploy_queue_migration.sh:64-67](file://deploy_queue_migration.sh#L64-L67)

### Scaling Considerations
- **Horizontal scaling**
  - Increase Uvicorn workers in production for CPU-bound I/O concurrency
  - Graceful shutdown timeout should accommodate increased worker count
  - Scale queue workers based on job volume and processing requirements
- **Vertical scaling**
  - Adjust CPU/memory limits per service in production Compose
  - Cloud-native autoscaling for managed services
- **Streaming scaling**
  - Ensure Nginx streaming configuration remains unchanged for SSE
  - Cloud CDN optimization for static assets
- **Health check scaling**
  - Shallow health checks scale horizontally with worker count
  - Deep health checks remain centralized for dependency validation
- **Queue scaling**
  - Increase max concurrent jobs based on available resources
  - Adjust poll intervals for optimal job processing throughput

**Section sources**
- [docker-compose.prod.yml:82-84](file://docker-compose.prod.yml#L82-L84)
- [docker-compose.prod.yml:58-64](file://docker-compose.prod.yml#L58-L64)
- [app/nginx/nginx.prod.conf:73-102](file://app/nginx/nginx.prod.conf#L73-L102)
- [app/backend/services/queue_manager.py:201-204](file://app/backend/services/queue_manager.py#L201-L204)

### Security Hardening
- **Secrets management**
  - Use repository secrets for Docker Hub credentials and cloud access
  - Implement cloud-native secret management for API keys
- **Network exposure**
  - Limit published ports; rely on internal networking within Compose
  - Use cloud-native security groups and network policies
- **SSL/TLS**
  - Use Certbot for automatic certificate management and renewal
  - Cloud-native SSL termination and certificate management
- **Access control**
  - Restrict SSH access to cloud infrastructure and rotate keys regularly
  - Implement cloud-native IAM policies and access controls
- **Health check security**
  - `/health` endpoint provides minimal information for container monitoring
  - `/api/health/deep` requires authentication and provides comprehensive validation
- **Queue security**
  - Job deduplication prevents unauthorized duplicate processing
  - Worker isolation protects against cross-job interference

**Section sources**
- [.github/workflows/cd.yml:60-64](file://.github/workflows/cd.yml#L60-L64)
- [README.md:147-178](file://README.md#L147-L178)
- [docker-compose.prod.yml:213-220](file://docker-compose.prod.yml#L213-L220)

### Backup and Disaster Recovery
- **Data persistence**
  - Persist PostgreSQL and Ollama data through cloud-managed services
  - Implement cloud-native backup strategies for managed databases
- **Image retention**
  - Maintain recent image tags for quick rollback
  - Cloud-native container registry management
- **DR plan**
  - Document restore steps for cloud-managed services and environment variables
  - Automate where possible with cloud-native DR tools
  - Include queue system state and job persistence in recovery procedures
- **Rolling restart backup**
  - Watchtower provides automatic rollback capability
  - Graceful shutdown ensures clean state preservation
- **Migration backup**
  - Automated backup creation before database schema changes
  - Verified restoration procedures for rollback scenarios

**Section sources**
- [docker-compose.yml:99-101](file://docker-compose.yml#L99-L101)
- [docker-compose.prod.yml:26-27](file://docker-compose.prod.yml#L26-L27)
- [docker-compose.prod.yml:222-241](file://docker-compose.prod.yml#L222-L241)
- [deploy_queue_migration.sh:18-23](file://deploy_queue_migration.sh#L18-L23)

### Zero-Downtime Deployment Strategy
- **Rolling restart configuration**
  - Watchtower configured with `--rolling-restart` flag for seamless updates
  - Graceful shutdown timeout of 30 seconds allows background tasks to complete
  - Stop grace period of 60 seconds for backend service
  - 30-second stop grace period for Nginx service
- **Health check strategy**
  - Shallow `/health` endpoint for container monitoring (<10ms)
  - Deep `/api/health/deep` endpoint for comprehensive dependency validation
  - Service health checks integrated with Docker Compose
- **Background task management**
  - Proper cleanup of background tasks during shutdown
  - Sentinel shutdown handling for Ollama Cloud integration
  - Database connection cleanup for transaction safety
- **Queue worker management**
  - Graceful shutdown of queue workers during container updates
  - Job state preservation across deployments
  - Worker restart verification after updates

**Section sources**
- [docker-compose.prod.yml:205-211](file://docker-compose.prod.yml#L205-L211)
- [docker-compose.prod.yml:82-84](file://docker-compose.prod.yml#L82-L84)
- [docker-compose.prod.yml:138-139](file://docker-compose.prod.yml#L138-L139)
- [app/backend/main.py:238-282](file://app/backend/main.py#L238-L282)

### Ollama Cloud Integration Guide
- **Authentication Setup**
  - Obtain API key from [ollama.com/settings/keys](https://ollama.com/settings/keys)
  - Configure OLLAMA_API_KEY environment variable
  - Default OLLAMA_BASE_URL points to cloud service
- **Model Selection**
  - Default cloud model: qwen3-coder:480b-cloud
  - Fast model fallback: qwen3-coder:480b-cloud
  - Automatic model loading and warmup
- **Pricing Considerations**
  - Pay-per-token pricing model for cloud inference
  - No local hardware requirements or GPU setup
  - Scalable pricing tiers based on usage
- **Migration from Local Ollama**
  - Set OLLAMA_BASE_URL=https://ollama.com
  - Configure OLLAMA_API_KEY environment variable
  - Remove local Ollama service dependencies

**Section sources**
- [README.md:208-224](file://README.md#L208-L224)
- [docker-compose.yml:60-67](file://docker-compose.yml#L60-L67)
- [docker-compose.prod.yml:86-99](file://docker-compose.prod.yml#L86-L99)
- [app/backend/scripts/wait_for_ollama.py:40-51](file://app/backend/scripts/wait_for_ollama.py#L40-L51)

### Queue System Administration
- **Queue Management**
  - Monitor queue depth and processing rates
  - Track job completion times and error rates
  - Manage job priorities and retry policies
- **Worker Monitoring**
  - Track worker statistics and job processing metrics
  - Monitor worker health and heartbeat patterns
  - Handle worker failures and recovery scenarios
- **Performance Tuning**
  - Adjust max concurrent jobs based on resource availability
  - Optimize poll intervals for job processing throughput
  - Configure retry delays for optimal fault tolerance

**Section sources**
- [app/backend/routes/queue_api.py:214-273](file://app/backend/routes/queue_api.py#L214-L273)
- [app/backend/services/queue_manager.py:573-583](file://app/backend/services/queue_manager.py#L573-L583)
- [app/backend/services/queue_manager.py:201-204](file://app/backend/services/queue_manager.py#L201-L204)