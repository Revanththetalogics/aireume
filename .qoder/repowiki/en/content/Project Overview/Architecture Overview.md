# Architecture Overview

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [docker-compose.yml](file://docker-compose.yml)
- [docker-compose.prod.yml](file://docker-compose.prod.yml)
- [app/backend/main.py](file://app/backend/main.py)
- [app/backend/db/database.py](file://app/backend/db/database.py)
- [app/backend/models/db_models.py](file://app/backend/models/db_models.py)
- [app/backend/routes/analyze.py](file://app/backend/routes/analyze.py)
- [app/backend/services/analysis_service.py](file://app/backend/services/analysis_service.py)
- [app/backend/middleware/auth.py](file://app/backend/middleware/auth.py)
- [app/backend/Dockerfile](file://app/backend/Dockerfile)
- [app/frontend/src/lib/api.js](file://app/frontend/src/lib/api.js)
- [app/frontend/vite.config.js](file://app/frontend/vite.config.js)
- [app/frontend/Dockerfile](file://app/frontend/Dockerfile)
- [app/nginx/nginx.conf](file://app/nginx/nginx.conf)
</cite>

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
This document presents the architecture of Resume AI by ThetaLogics, a local-first AI-powered SaaS for recruiters. The system emphasizes privacy and offline capability by keeping sensitive data on disk and leveraging a local LLM via Ollama. It comprises:
- Browser frontend (React) served by Nginx
- FastAPI backend handling authentication, orchestration, and persistence
- Ollama AI service for LLM-driven analysis
- SQLite/PostgreSQL database for tenant-aware storage
- Docker-based microservices orchestrated via Docker Compose

The architecture supports both development and production topologies, with a reverse proxy configuration and health-checked services. It documents data flows from user uploads through parsing, scoring, and AI narrative generation to result delivery.

## Project Structure
The repository is organized into three primary layers:
- app/backend: FastAPI application, routes, services, models, and database configuration
- app/frontend: React SPA with Vite dev server and Nginx static hosting
- app/nginx: Local development Nginx configuration; production uses dedicated nginx image/container

```mermaid
graph TB
subgraph "Browser"
FE["React SPA<br/>Vite dev server / Nginx static"]
end
subgraph "Reverse Proxy"
NGINX["Nginx<br/>Port 80/8000"]
end
subgraph "Backend"
FASTAPI["FastAPI App<br/>Routes + Services"]
DB["SQLite/PostgreSQL"]
end
subgraph "AI"
OLLAMA["Ollama (llama3/gemma4)"]
end
FE --> NGINX
NGINX --> FASTAPI
FASTAPI --> DB
FASTAPI --> OLLAMA
```

**Diagram sources**
- [app/frontend/vite.config.js:9-14](file://app/frontend/vite.config.js#L9-L14)
- [app/nginx/nginx.conf:9-35](file://app/nginx/nginx.conf#L9-L35)
- [app/backend/main.py:174-215](file://app/backend/main.py#L174-L215)
- [app/backend/db/database.py:1-33](file://app/backend/db/database.py#L1-L33)

**Section sources**
- [README.md:273-333](file://README.md#L273-L333)
- [docker-compose.yml:1-101](file://docker-compose.yml#L1-L101)
- [docker-compose.prod.yml:1-227](file://docker-compose.prod.yml#L1-L227)

## Core Components
- Browser Frontend (React)
  - Provides upload forms, streaming analysis UI, and authenticated API interactions
  - Uses Axios for REST and native fetch for SSE streaming
- Nginx Reverse Proxy
  - Local dev: proxies frontend and backend to host services
  - Production: serves static assets and routes API traffic to backend
- FastAPI Backend
  - Authentication middleware, route handlers, and orchestration services
  - Health checks, startup diagnostics, and dependency verification
- Ollama AI Service
  - Local LLM inference for narrative analysis and structured outputs
- Database
  - SQLite for local/dev; PostgreSQL for production with tuned parameters

**Section sources**
- [app/frontend/src/lib/api.js:47-147](file://app/frontend/src/lib/api.js#L47-L147)
- [app/frontend/vite.config.js:9-14](file://app/frontend/vite.config.js#L9-L14)
- [app/nginx/nginx.conf:9-35](file://app/nginx/nginx.conf#L9-L35)
- [app/backend/main.py:68-149](file://app/backend/main.py#L68-L149)
- [app/backend/db/database.py:1-33](file://app/backend/db/database.py#L1-L33)

## Architecture Overview
The system follows a microservices architecture with Docker containers for each component. The frontend is served statically (in production) or via Vite dev server (in local dev). Nginx acts as a reverse proxy and SSL terminator in production. The backend exposes REST endpoints and SSE streams, orchestrating parsing, gap detection, and LLM-driven narrative generation. The database persists tenant-aware entities and usage logs. Ollama runs as a separate service for local LLM inference.

```mermaid
graph TB
Browser["Browser"] --> NginxDev["Nginx Dev<br/>localhost:80/8000"]
NginxDev --> FE["Frontend<br/>Vite/Nginx"]
FE --> API["FastAPI Backend<br/>/api/*"]
API --> DB["Database<br/>SQLite/PostgreSQL"]
API --> Ollama["Ollama LLM<br/>llama3/gemma4"]
%% Production specifics
subgraph "Production"
ProdNginx["Nginx Prod<br/>Port 80/443"]
FEProd["Static Assets"]
BEProd["FastAPI Workers"]
OllamaProd["Ollama"]
DBProd["PostgreSQL"]
end
Browser --> ProdNginx
ProdNginx --> FEProd
ProdNginx --> BEProd
BEProd --> DBProd
BEProd --> OllamaProd
```

**Diagram sources**
- [docker-compose.yml:86-96](file://docker-compose.yml#L86-L96)
- [docker-compose.prod.yml:126-145](file://docker-compose.prod.yml#L126-L145)
- [app/backend/Dockerfile:36-38](file://app/backend/Dockerfile#L36-L38)
- [app/frontend/Dockerfile:15-25](file://app/frontend/Dockerfile#L15-L25)

## Detailed Component Analysis

### Data Flow: Upload to Analysis to Result Delivery
End-to-end flow for a single resume analysis:
1. Frontend uploads resume and optional job description/file
2. Backend validates inputs, parses resume in a thread pool, computes gaps, and caches JD
3. Hybrid pipeline executes Python-based scoring and LLM narrative
4. Results are persisted to the database and returned to the frontend
5. Optional SSE streaming emits stages for real-time UX

```mermaid
sequenceDiagram
participant U as "User"
participant F as "Frontend"
participant N as "Nginx"
participant B as "FastAPI Backend"
participant P as "Parser Service"
participant G as "Gap Detector"
participant H as "Hybrid Pipeline"
participant L as "Ollama LLM"
participant D as "Database"
U->>F : "Upload resume + job"
F->>N : "POST /api/analyze"
N->>B : "Proxy to backend"
B->>P : "parse_resume()"
P-->>B : "parsed_data"
B->>G : "analyze_gaps()"
G-->>B : "gap_analysis"
B->>H : "run_hybrid_pipeline()"
H->>L : "LLM call"
L-->>H : "narrative JSON"
H-->>B : "combined result"
B->>D : "persist ScreeningResult"
D-->>B : "ack"
B-->>F : "JSON result"
F-->>U : "Display fit score + insights"
```

**Diagram sources**
- [app/frontend/src/lib/api.js:47-63](file://app/frontend/src/lib/api.js#L47-L63)
- [app/backend/routes/analyze.py:268-318](file://app/backend/routes/analyze.py#L268-L318)
- [app/backend/services/analysis_service.py:10-53](file://app/backend/services/analysis_service.py#L10-L53)
- [app/backend/main.py:228-259](file://app/backend/main.py#L228-L259)

**Section sources**
- [app/frontend/src/lib/api.js:47-147](file://app/frontend/src/lib/api.js#L47-L147)
- [app/backend/routes/analyze.py:354-501](file://app/backend/routes/analyze.py#L354-L501)
- [app/backend/services/analysis_service.py:1-121](file://app/backend/services/analysis_service.py#L1-L121)

### Microservices and Containerization
- Backend
  - Entrypoint waits for Ollama readiness and optional model warmup
  - Exposes health checks and diagnostic endpoints
- Frontend
  - Nginx static hosting in production; Vite dev server proxy in local dev
- Nginx
  - Local dev: routes to host services
  - Production: serves static assets and proxies API to backend
- Ollama
  - Configured with parallelism and memory tuning for CPU inference
- Database
  - SQLite for local; PostgreSQL for production with tuned parameters

```mermaid
graph TB
subgraph "Local Dev"
DC["docker-compose.yml"]
DC --> FE["frontend:3000->80"]
DC --> NG["nginx:80->80"]
DC --> BE["backend:8000->8000"]
DC --> OL["ollama:11434->11434"]
FE --> NG
NG --> BE
BE --> OL
end
subgraph "Production"
DCP["docker-compose.prod.yml"]
DCP --> FEProd["frontend:latest"]
DCP --> NGProd["nginx:latest"]
DCP --> BEProd["backend:latest (4 workers)"]
DCP --> OLProd["ollama:latest"]
DCP --> PG["postgres:16-alpine"]
NGProd --> FEProd
NGProd --> BEProd
BEProd --> PG
BEProd --> OLProd
end
```

**Diagram sources**
- [docker-compose.yml:52-96](file://docker-compose.yml#L52-L96)
- [docker-compose.prod.yml:75-145](file://docker-compose.prod.yml#L75-L145)
- [app/backend/Dockerfile:36-38](file://app/backend/Dockerfile#L36-L38)
- [app/frontend/Dockerfile:15-25](file://app/frontend/Dockerfile#L15-L25)

**Section sources**
- [docker-compose.yml:1-101](file://docker-compose.yml#L1-L101)
- [docker-compose.prod.yml:1-227](file://docker-compose.prod.yml#L1-L227)
- [app/backend/Dockerfile:1-39](file://app/backend/Dockerfile#L1-L39)
- [app/frontend/Dockerfile:1-26](file://app/frontend/Dockerfile#L1-L26)

### Authentication and Authorization
- JWT bearer tokens are validated on each request
- Admin-only endpoints are protected via a decorator
- Token refresh flow is handled in the frontend interceptor

```mermaid
flowchart TD
Start(["Request"]) --> CheckAuth["Check Authorization header"]
CheckAuth --> ValidToken{"Valid JWT?"}
ValidToken --> |No| Unauthorized["401 Unauthorized"]
ValidToken --> |Yes| LoadUser["Load user from DB"]
LoadUser --> UserFound{"User exists and active?"}
UserFound --> |No| Unauthorized
UserFound --> |Yes| Next["Proceed to handler"]
```

**Diagram sources**
- [app/backend/middleware/auth.py:19-40](file://app/backend/middleware/auth.py#L19-L40)

**Section sources**
- [app/backend/middleware/auth.py:1-47](file://app/backend/middleware/auth.py#L1-L47)
- [app/frontend/src/lib/api.js:18-43](file://app/frontend/src/lib/api.js#L18-L43)

### Database Schema and Multi-Tenancy
The backend defines tenant-aware entities for subscriptions, users, candidates, screening results, transcripts, training examples, and a shared JD cache. This enables multi-tenant isolation and usage tracking.

```mermaid
erDiagram
SUBSCRIPTION_PLAN {
int id PK
string name UK
string display_name
text description
text limits
int price_monthly
int price_yearly
string currency
text features
boolean is_active
int sort_order
timestamp created_at
timestamp updated_at
}
TENANT {
int id PK
string name
string slug UK
int plan_id FK
string subscription_status
timestamp current_period_start
timestamp current_period_end
int analyses_count_this_month
bigint storage_used_bytes
timestamp usage_reset_at
string stripe_customer_id
string stripe_subscription_id
timestamp subscription_updated_at
timestamp created_at
}
USER {
int id PK
int tenant_id FK
string email UK
string hashed_password
string role
boolean is_active
timestamp created_at
}
CANDIDATE {
int id PK
int tenant_id FK
string name
string email
string phone
timestamp created_at
string resume_file_hash
text raw_resume_text
text parsed_skills
text parsed_education
text parsed_work_exp
text gap_analysis_json
string current_role
string current_company
float total_years_exp
string profile_quality
timestamp profile_updated_at
}
SCREENING_RESULT {
int id PK
int tenant_id FK
int candidate_id FK
int role_template_id FK
text resume_text
text jd_text
text parsed_data
text analysis_result
string status
timestamp timestamp
}
ROLE_TEMPLATE {
int id PK
int tenant_id FK
string name
text jd_text
text scoring_weights
string tags
timestamp created_at
}
TEAM_MEMBER {
int id PK
int tenant_id FK
int user_id FK
string role
}
COMMENT {
int id PK
int result_id FK
int user_id FK
text text
timestamp created_at
}
TRAINING_EXAMPLE {
int id PK
int tenant_id FK
int screening_result_id FK
string outcome
text feedback
timestamp created_at
}
TRANSCRIPT_ANALYSIS {
int id PK
int tenant_id FK
int candidate_id FK
int role_template_id FK
text transcript_text
string source_platform
text analysis_result
timestamp created_at
}
USAGE_LOG {
int id PK
int tenant_id FK
int user_id FK
string action
int quantity
text details
timestamp created_at
}
SKILL {
int id PK
string name UK
text aliases
string domain
string status
string source
int frequency
timestamp created_at
}
JD_CACHE {
string hash PK
text result_json
timestamp created_at
}
SUBSCRIPTION_PLAN ||--o{ TENANT : "has"
TENANT ||--o{ USER : "contains"
TENANT ||--o{ CANDIDATE : "contains"
TENANT ||--o{ SCREENING_RESULT : "contains"
TENANT ||--o{ ROLE_TEMPLATE : "contains"
TENANT ||--o{ TEAM_MEMBER : "contains"
TENANT ||--o{ USAGE_LOG : "generates"
USER ||--o{ COMMENT : "writes"
SCREENING_RESULT ||--o{ COMMENT : "has"
CANDIDATE ||--o{ SCREENING_RESULT : "produces"
ROLE_TEMPLATE ||--o{ SCREENING_RESULT : "used_in"
CANDIDATE ||--o{ TRANSCRIPT_ANALYSIS : "has"
ROLE_TEMPLATE ||--o{ TRANSCRIPT_ANALYSIS : "used_in"
SKILL ||--|| JD_CACHE : "cached_by"
```

**Diagram sources**
- [app/backend/models/db_models.py:11-250](file://app/backend/models/db_models.py#L11-L250)

**Section sources**
- [app/backend/models/db_models.py:1-250](file://app/backend/models/db_models.py#L1-L250)
- [app/backend/db/database.py:1-33](file://app/backend/db/database.py#L1-L33)

### Reverse Proxy and Service Communication
- Local development
  - Nginx forwards / to Vite dev server (host.docker.internal:5173)
  - Nginx forwards /api to backend (host.docker.internal:8000)
- Production
  - Nginx serves static assets and proxies API to backend
  - Backend runs multiple workers behind Nginx
  - Ollama warmup ensures first request latency is minimized

```mermaid
flowchart LR
A["Browser"] --> B["Nginx (Dev)<br/>localhost:80/8000"]
B --> C["Frontend (Vite)"]
B --> D["Backend (FastAPI)"]
E["Nginx (Prod)<br/>Port 80/443"] --> F["Static Assets"]
E --> G["Backend Workers"]
G --> H["PostgreSQL"]
G --> I["Ollama"]
```

**Diagram sources**
- [app/nginx/nginx.conf:9-35](file://app/nginx/nginx.conf#L9-L35)
- [docker-compose.prod.yml:126-145](file://docker-compose.prod.yml#L126-L145)

**Section sources**
- [app/nginx/nginx.conf:1-37](file://app/nginx/nginx.conf#L1-L37)
- [docker-compose.yml:86-96](file://docker-compose.yml#L86-L96)
- [docker-compose.prod.yml:126-145](file://docker-compose.prod.yml#L126-L145)

## Dependency Analysis
- Backend depends on:
  - SQLAlchemy for ORM and sessions
  - httpx for asynchronous Ollama API calls
  - Routes and services for orchestration
- Frontend depends on:
  - Axios for REST
  - Native fetch for SSE
  - Vite proxy for local development
- Infrastructure:
  - Docker Compose for local dev
  - Production Compose for orchestrated deployment

```mermaid
graph LR
FE["Frontend"] --> API["FastAPI Backend"]
API --> DB["Database"]
API --> OLL["Ollama"]
NG["Nginx"] --> FE
NG --> API
```

**Diagram sources**
- [app/backend/main.py:8-21](file://app/backend/main.py#L8-L21)
- [app/frontend/src/lib/api.js:1-16](file://app/frontend/src/lib/api.js#L1-L16)
- [docker-compose.yml:52-96](file://docker-compose.yml#L52-L96)

**Section sources**
- [app/backend/main.py:1-327](file://app/backend/main.py#L1-L327)
- [app/frontend/src/lib/api.js:1-395](file://app/frontend/src/lib/api.js#L1-L395)
- [docker-compose.yml:1-101](file://docker-compose.yml#L1-L101)

## Performance Considerations
- Concurrency and Parallelism
  - Backend uses multiple workers in production to handle concurrent requests without starving Ollama
  - Ollama configured with parallel slots and flash attention for improved throughput
- I/O-bound Design
  - Parsing and LLM calls are offloaded to threads and async clients to avoid blocking the event loop
- Caching and Deduplication
  - JD parsing is cached per hash across workers
  - Candidate deduplication prevents redundant processing
- Storage
  - SQLite for local simplicity; PostgreSQL for production with tuned memory and connection parameters
- Streaming
  - SSE endpoints provide progressive UI updates during analysis

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common operational issues and remedies:
- Ollama not reachable or model not loaded
  - Verify health endpoints and model lists
  - Warmup container ensures models are loaded in production
- Database locked errors
  - SQLite does not support concurrent writes; restart backend container if locked
- SSL certificate renewal
  - Renew certificates and restart Nginx in production
- Deployment failures
  - Check GitHub Actions logs for Docker Hub token, SSH keys, and firewall issues

**Section sources**
- [app/backend/main.py:228-326](file://app/backend/main.py#L228-L326)
- [docker-compose.prod.yml:151-184](file://docker-compose.prod.yml#L151-L184)
- [README.md:337-375](file://README.md#L337-L375)

## Conclusion
Resume AI employs a pragmatic microservices architecture with Docker, a reverse proxy, and a local LLM to deliver a privacy-focused, offline-capable solution. The backend’s hybrid pipeline combines deterministic scoring with LLM narrative generation, while the frontend provides responsive UX with streaming updates. Production-grade configurations emphasize reliability, scalability, and observability.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Deployment Topology
- Development
  - docker-compose.yml defines services for frontend, backend, Nginx, Ollama, and Postgres
  - Local Nginx proxies to host services for seamless dev experience
- Production
  - docker-compose.prod.yml orchestrates multi-worker backend, static frontend, Nginx, Postgres, Ollama, and Watchtower for auto-updates
  - Ollama warmup ensures cold-start mitigation

**Section sources**
- [docker-compose.yml:1-101](file://docker-compose.yml#L1-L101)
- [docker-compose.prod.yml:1-227](file://docker-compose.prod.yml#L1-L227)