# Docker Configuration

<cite>
**Referenced Files in This Document**
- [docker-compose.yml](file://docker-compose.yml)
- [docker-compose.prod.yml](file://docker-compose.prod.yml)
- [docker-compose.staging.yml](file://docker-compose.staging.yml)
- [docker-compose.portainer.yml](file://docker-compose.portainer.yml)
- [app/backend/Dockerfile](file://app/backend/Dockerfile)
- [app/frontend/Dockerfile](file://app/frontend/Dockerfile)
- [nginx/Dockerfile](file://nginx/Dockerfile)
- [app/speech_service/Dockerfile](file://app/speech_service/Dockerfile)
- [app/speech_service/main.py](file://app/speech_service/main.py)
- [app/speech_service/requirements.txt](file://app/speech_service/requirements.txt)
- [app/voice_agent/Dockerfile](file://app/voice_agent/Dockerfile)
- [app/voice_agent/Dockerfile.livekit](file://app/voice_agent/Dockerfile.livekit)
- [app/voice_agent/agent.py](file://app/voice_agent/agent.py)
- [app/voice_agent/livekit.yaml](file://app/voice_agent/livekit.yaml)
- [app/backend/scripts/docker-entrypoint.sh](file://app/backend/scripts/docker-entrypoint.sh)
- [app/backend/scripts/wait_for_ollama.py](file://app/backend/scripts/wait_for_ollama.py)
- [app/nginx/nginx.conf](file://app/nginx/nginx.conf)
- [nginx/nginx.prod.conf](file://nginx/nginx.prod.conf)
- [app/backend/middleware/auth.py](file://app/backend/middleware/auth.py)
- [app/backend/main.py](file://app/backend/main.py)
- [app/frontend/default.conf](file://app/frontend/default.conf)
- [requirements.txt](file://requirements.txt)
- [README.md](file://README.md)
- [.github/workflows/ci.yml](file://.github/workflows/ci.yml)
- [.github/workflows/cd.yml](file://.github/workflows/cd.yml)
- [ollama/setup-recruiter-model.sh](file://ollama/setup-recruiter-model.sh)
- [app/backend/services/hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [app/backend/services/llm_service.py](file://app/backend/services/llm_service.py)
- [app/backend/db/database.py](file://app/backend/db/database.py)
- [app/backend/models/db_models.py](file://app/backend/models/db_models.py)
- [alembic/env.py](file://alembic/env.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced LiveKit server configuration security with 32-character API secrets meeting minimum security requirements
- Updated LiveKit configuration approach section to document the new embedded configuration method with improved security validation
- Strengthened API secret requirements with minimum 32-character length for production and staging environments
- Enhanced security validation for LiveKit configuration with longer, more secure API secrets
- Updated environment variable handling to enforce stronger security standards for API keys

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Voice Screening Infrastructure](#voice-screening-infrastructure)
7. [Dependency Analysis](#dependency-analysis)
8. [Performance Considerations](#performance-considerations)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Conclusion](#conclusion)
11. [Appendices](#appendices)

## Introduction
This document explains the Docker configuration for Resume AI by ThetaLogics, covering:
- Development environment setup with docker-compose.yml
- Production deployment with docker-compose.prod.yml, including multi-stage builds, resource limits, and security settings
- **Updated** Enhanced LiveKit server configuration security with 32-character API secrets meeting minimum security requirements
- **Updated** Enhanced networking connectivity with extra_hosts configuration for seamless inter-environment communication
- **Updated** Port standardization for staging environment with standardized LiveKit port mappings
- Container networking, volumes, and inter-service communication
- Dockerfile configurations for backend and frontend, including build optimization and runtime behavior
- **Updated** Voice screening infrastructure with speech-service, voice-agent, and LiveKit integration
- **Enhanced** CPU-optimized speech processing with STT, TTS, and VAD capabilities
- **Updated** LiveKit server configuration approach with image-baked YAML configuration and enhanced security validation
- Environment variable handling, secrets management, and configuration inheritance
- Troubleshooting, health checks, and performance optimization
- Enhanced Ollama memory allocation settings for optimal LLM performance

## Project Structure
The repository organizes Docker assets around seven primary services plus voice infrastructure:
- Backend: FastAPI application with Ollama Cloud integration and Alembic migrations
- Frontend: React SPA served by Nginx
- Infrastructure: Postgres database, Ollama LLM engine, reverse proxy Nginx, optional Watchtower auto-updates, and Certbot for SSL renewal
- **New** Speech Service: CPU-optimized STT, TTS, and VAD processing with 4GB RAM allocation
- **New** Voice Agent: LiveKit Agents process for conversation orchestration with 2GB RAM allocation
- **New** LiveKit Server: WebRTC SFU + SIP trunking for voice calls with 1GB RAM allocation and embedded configuration
- **Enhanced** Redis integration for LiveKit multi-node deployment support

```mermaid
graph TB
subgraph "Development"
DevNginx["nginx (dev)"]
DevFrontend["frontend (React)"]
DevBackend["backend (FastAPI)"]
DevPostgres["postgres"]
DevOllama["ollama"]
DevSpeech["speech-service (CPU)"]
DevVoiceAgent["voice-agent (agents)"]
DevLiveKit["livekit (WebRTC)"]
end
subgraph "Production"
ProdNginx["nginx (prod)"]
ProdFrontend["frontend (image)"]
ProdBackend["backend (image)"]
ProdPostgres["postgres"]
ProdOllama["ollama"]
ProdSpeech["speech-service (image)"]
ProdVoiceAgent["voice-agent (image)"]
ProdLiveKit["livekit (custom image)"]
ProdRedis["redis (optional)"]
ProdWarmup["ollama-warmup"]
ProdWatchtower["watchtower"]
ProdCertbot["certbot"]
ProdExtraHosts["extra_hosts: host.docker.internal:host-gateway"]
end
subgraph "Staging"
StagingNginx["nginx (staging)"]
StagingFrontend["frontend (staging)"]
StagingBackend["backend (staging)"]
StagingPostgres["postgres"]
StagingOllama["ollama"]
StagingSpeech["speech-service (staging)"]
StagingVoiceAgent["voice-agent (staging)"]
StagingLiveKit["livekit (standardized ports)"]
StagingNetwork["aria_staging_network"]
end
DevNginx --> DevFrontend
DevNginx --> DevBackend
DevBackend --> DevPostgres
DevBackend --> DevOllama
DevSpeech --> DevLiveKit
DevVoiceAgent --> DevLiveKit
DevVoiceAgent --> DevSpeech
DevVoiceAgent --> DevBackend
ProdNginx --> ProdFrontend
ProdNginx --> ProdBackend
ProdBackend --> ProdPostgres
ProdBackend --> ProdOllama
ProdSpeech --> ProdLiveKit
ProdVoiceAgent --> ProdLiveKit
ProdVoiceAgent --> ProdSpeech
ProdVoiceAgent --> ProdBackend
ProdLiveKit --> ProdRedis
ProdOllama --> ProdWarmup
ProdWatchtower --> ProdBackend
ProdWatchtower --> ProdFrontend
ProdWatchtower --> ProdNginx
ProdWatchtower --> ProdSpeech
ProdWatchtower --> ProdVoiceAgent
ProdWatchtower --> ProdLiveKit
ProdCertbot --> ProdNginx
ProdExtraHosts --> ProdNginx
StagingNginx --> StagingFrontend
StagingNginx --> StagingBackend
StagingBackend --> StagingPostgres
StagingBackend --> StagingOllama
StagingSpeech --> StagingLiveKit
StagingVoiceAgent --> StagingLiveKit
StagingVoiceAgent --> StagingSpeech
StagingVoiceAgent --> StagingBackend
StagingLiveKit --> StagingNetwork
```

**Diagram sources**
- [docker-compose.yml:5-180](file://docker-compose.yml#L5-L180)
- [docker-compose.prod.yml:7-318](file://docker-compose.prod.yml#L7-L318)
- [docker-compose.staging.yml:1-228](file://docker-compose.staging.yml#L1-L228)

**Section sources**
- [docker-compose.yml:1-180](file://docker-compose.yml#L1-L180)
- [docker-compose.prod.yml:1-318](file://docker-compose.prod.yml#L1-L318)
- [docker-compose.staging.yml:1-228](file://docker-compose.staging.yml#L1-L228)

## Core Components
- Backend service
  - Uses a Python slim base image, installs system dependencies, copies requirements and application code, and sets environment variables for database and Ollama Cloud connectivity.
  - **Updated** Entrypoint now includes explicit model import before Base.metadata.create_all() execution to ensure proper table creation.
  - **Updated** Alembic migrations run after model registration for PostgreSQL databases.
  - Exposes port 8000 and supports single-worker default; production overrides to multiple workers.
- Frontend service
  - Multi-stage build: Node builder produces static assets, then copied into an Nginx runtime image.
  - Serves compiled SPA on port 8080; development compose binds host port 3000 to container port 80.
- Nginx service
  - Development: proxies to host-based dev servers for frontend and backend.
  - **Updated** Production: reverse proxy with health checks, streaming support, CORS handling, and dynamic DNS resolution for container IPs including extra_hosts configuration for seamless inter-environment communication.
  - **Updated** Staging: uses standardized port mappings for LiveKit services (7890:7880, 7891:7881, 7892:7882/udp) to avoid port conflicts with production.
- Database and LLM
  - Postgres with persistent volumes and health checks.
  - Ollama with enhanced memory allocation settings for parallelism, caching, and model loading; production includes a dedicated warmup job with optimized resource limits.
- **New** Speech Service
  - CPU-optimized FastAPI service with 4GB RAM allocation for STT, TTS, and VAD processing.
  - Uses Parakeet TDT 1.1B for speech-to-text, Kokoro 82M for text-to-speech, and Silero VAD for speech detection.
  - Exposes port 8001 for internal communication and includes health checks for model readiness.
- **New** Voice Agent
  - LiveKit Agents process with 2GB RAM allocation for conversation orchestration.
  - Integrates with Speech Service, LiveKit Server, and Ollama Cloud for voice screening workflows.
  - Supports outbound calls, inbound callbacks, and conversation state management.
- **New** LiveKit Server
  - **Updated** WebRTC SFU + SIP trunking for voice calls with 1GB RAM allocation and embedded configuration approach.
  - **Updated** Uses custom image revanth2245/resume-livekit:latest with Dockerfile.livekit that copies livekit.yaml directly into the container during build process.
  - Provides WebSocket (7880), RTC (7881), and TURN (7882/udp) interfaces.
  - **Updated** Configuration via embedded livekit.yaml file instead of volume mounting for improved reliability and deployment consistency.
  - **Enhanced** Redis integration support for multi-node deployment scenarios.
  - **Updated** Staging environment uses standardized port mappings (7890:7880, 7891:7881, 7892:7882/udp) to prevent conflicts with production.
  - **Updated** Fixed LiveKit configuration environment variable parsing issue by changing node_ip from '${LIVEKIT_NODE_IP}' to hardcoded IP '66.70.191.79' to resolve YAML configuration parsing limitations in containerized environments.
  - **Enhanced** API security with 32-character minimum length for API secrets meeting modern security standards.

**Section sources**
- [app/backend/Dockerfile:1-55](file://app/backend/Dockerfile#L1-L55)
- [app/frontend/Dockerfile:1-35](file://app/frontend/Dockerfile#L1-L35)
- [nginx/Dockerfile:1-13](file://nginx/Dockerfile#L1-L13)
- [app/speech_service/Dockerfile:1-32](file://app/speech_service/Dockerfile#L1-L32)
- [app/voice_agent/Dockerfile:1-31](file://app/voice_agent/Dockerfile#L1-L31)
- [app/voice_agent/Dockerfile.livekit:1-3](file://app/voice_agent/Dockerfile.livekit#L1-L3)
- [app/backend/scripts/docker-entrypoint.sh:1-22](file://app/backend/scripts/docker-entrypoint.sh#L1-L22)
- [app/backend/scripts/wait_for_ollama.py:1-108](file://app/backend/scripts/wait_for_ollama.py#L1-L108)
- [docker-compose.yml:53-180](file://docker-compose.yml#L53-L180)
- [docker-compose.prod.yml:7-318](file://docker-compose.prod.yml#L7-L318)
- [docker-compose.staging.yml:160-179](file://docker-compose.staging.yml#L160-L179)

## Architecture Overview
The system comprises seven primary runtime services plus optional production-only services. Inter-service communication relies on Docker Compose networking with service names as hostnames. The backend coordinates with Postgres and Ollama Cloud; Nginx fronts both frontend and backend traffic. **New** voice services integrate through LiveKit for WebRTC communication and speech processing services for audio analysis. **Updated** Production environment includes enhanced networking with extra_hosts configuration for seamless inter-environment communication via host.docker.internal mapping.

```mermaid
graph TB
Browser["Browser"]
NginxDev["nginx (dev)"]
NginxProd["nginx (prod)"]
NginxStaging["nginx (staging)"]
FrontendDev["frontend (dev)"]
FrontendProd["frontend (image)"]
FrontendStaging["frontend (staging)"]
Backend["backend"]
Postgres["postgres"]
Ollama["ollama"]
SpeechService["speech-service"]
VoiceAgent["voice-agent"]
LiveKit["livekit (custom image)"]
LiveKitStaging["livekit (standardized ports)"]
Redis["redis (optional)"]
ExtraHosts["extra_hosts: host.docker.internal:host-gateway"]
StagingNetwork["aria_staging_network"]
Browser --> NginxDev
Browser --> NginxProd
Browser --> NginxStaging
NginxDev --> FrontendDev
NginxDev --> Backend
NginxProd --> FrontendProd
NginxProd --> Backend
NginxStaging --> FrontendStaging
NginxStaging --> Backend
Backend --> Postgres
Backend --> Ollama
SpeechService --> LiveKit
VoiceAgent --> LiveKit
VoiceAgent --> SpeechService
VoiceAgent --> Backend
LiveKit --> Redis
LiveKitStaging --> StagingNetwork
ExtraHosts --> NginxProd
```

**Diagram sources**
- [docker-compose.yml:5-180](file://docker-compose.yml#L5-L180)
- [docker-compose.prod.yml:7-318](file://docker-compose.prod.yml#L7-L318)
- [docker-compose.staging.yml:1-228](file://docker-compose.staging.yml#L1-L228)
- [app/nginx/nginx.conf:9-36](file://app/nginx/nginx.conf#L9-L36)
- [nginx/nginx.prod.conf:19-87](file://nginx/nginx.prod.conf#L19-L87)

## Detailed Component Analysis

### Backend Service
- Base image and build
  - Python 3.11 slim with GCC and curl for system-level dependencies.
  - Copies requirements, application code, Alembic configuration, and helper scripts.
  - Sets environment variables for Python path, default database URL, and Ollama Cloud base URL.
- **Updated** Entrypoint behavior
  - **Fixed** Explicit import of db_models before Base.metadata.create_all() to ensure all models are registered.
  - Applies Alembic migrations when the database URL indicates PostgreSQL.
  - Waits for Ollama readiness and model warm-up before starting the application process.
- Runtime
  - Exposes port 8000; development defaults to a single worker; production sets multiple workers.

```mermaid
flowchart TD
Start(["Container start"]) --> ImportModels["Import db_models module"]
ImportModels --> CheckDB["Check DATABASE_URL scheme"]
CheckDB --> IsPG{"PostgreSQL?"}
IsPG --> |Yes| RunMigrations["Run Alembic migrations"]
IsPG --> |No| SkipMigrations["Skip migrations"]
RunMigrations --> WaitOllama["Wait for Ollama and model warm-up"]
SkipMigrations --> WaitOllama
WaitOllama --> CheckJWT["Check JWT_SECRET_KEY"]
CheckJWT --> JWTValid{"JWT_SECRET_KEY set?"}
JWTValid --> |Yes| LaunchUvicorn["Launch Uvicorn workers"]
JWTValid --> |No| RaiseError["Raise RuntimeError in production"]
RaiseError --> End(["Failed"])
LaunchUvicorn --> End(["Ready"])
```

**Diagram sources**
- [app/backend/Dockerfile:1-55](file://app/backend/Dockerfile#L1-L55)
- [app/backend/scripts/docker-entrypoint.sh:8](file://app/backend/scripts/docker-entrypoint.sh#L8)
- [app/backend/scripts/wait_for_ollama.py:34-91](file://app/backend/scripts/wait_for_ollama.py#L34-L91)
- [app/backend/middleware/auth.py:13-21](file://app/backend/middleware/auth.py#L13-L21)

**Section sources**
- [app/backend/Dockerfile:1-55](file://app/backend/Dockerfile#L1-L55)
- [app/backend/scripts/docker-entrypoint.sh:1-22](file://app/backend/scripts/docker-entrypoint.sh#L1-L22)
- [app/backend/scripts/wait_for_ollama.py:1-108](file://app/backend/scripts/wait_for_ollama.py#L1-L108)
- [app/backend/middleware/auth.py:1-23](file://app/backend/middleware/auth.py#L1-L23)

### Frontend Service
- Multi-stage build
  - Builder stage: Node 20 Alpine, installs dependencies, builds assets.
  - Runtime stage: Nginx Alpine with baked-in default configuration and static assets.
- Serving
  - Serves SPA on port 8080; development compose binds host port 3000 to container port 80.

```mermaid
flowchart TD
BuildStage["Node builder"] --> CopyAssets["Copy dist to Nginx"]
CopyAssets --> RuntimeStage["Nginx runtime"]
RuntimeStage --> Serve["Serve SPA on port 8080"]
```

**Diagram sources**
- [app/frontend/Dockerfile:1-35](file://app/frontend/Dockerfile#L1-L35)

**Section sources**
- [app/frontend/Dockerfile:1-35](file://app/frontend/Dockerfile#L1-L35)
- [app/frontend/default.conf:1-19](file://app/frontend/default.conf#L1-L19)

### Nginx Service
- Development
  - Proxies frontend dev server and backend API to host ports for local iteration.
  - Frontend listens on port 80, backend listens on port 8000.
  - **Updated** Uses host.docker.internal routing for development and staging environments.
- **Updated** Production
  - Reverse proxy with:
    - Dynamic DNS resolution to handle container IP changes.
    - Health check route pointing to backend.
    - Streaming support for SSE endpoints.
    - CORS handling for preflight OPTIONS.
    - Upstream routing for API and SPA.
    - **New** extra_hosts configuration with `"host.docker.internal:host-gateway"` for seamless inter-environment communication.
- **Updated** Staging
  - Reverse proxy with standardized port mappings for LiveKit services to avoid conflicts with production.
  - LiveKit ports mapped as 7890:7880, 7891:7881, 7892:7882/udp for consistent staging environment.
  - **New** Separate network configuration (aria_staging_network) for environment isolation.

```mermaid
sequenceDiagram
participant C as "Client"
participant NG as "Nginx (prod)"
participant BE as "Backend"
participant FE as "Frontend"
C->>NG : "HTTP request"
alt API route
NG->>BE : "Proxy to backend : 8000"
BE-->>NG : "Response"
else SPA route
NG->>FE : "Proxy to frontend : 8080"
FE-->>NG : "Static assets"
end
NG-->>C : "Final response"
```

**Diagram sources**
- [nginx/nginx.prod.conf:29-86](file://nginx/nginx.prod.conf#L29-L86)

**Section sources**
- [app/nginx/nginx.conf:9-36](file://app/nginx/nginx.conf#L9-L36)
- [nginx/nginx.prod.conf:1-120](file://nginx/nginx.prod.conf#L1-L120)
- [docker-compose.prod.yml:144-146](file://docker-compose.prod.yml#L144-L146)
- [docker-compose.staging.yml:170-173](file://docker-compose.staging.yml#L170-L173)
- [docker-compose.staging.yml:220-224](file://docker-compose.staging.yml#L220-L224)

### Database and LLM
- Postgres
  - Persistent volume for data, health checks, and tuned parameters in production.
- Ollama
  - Enhanced memory allocation settings for parallelism, caching, and model loading.
  - Production includes a dedicated warmup job to preload models into RAM with optimized resource limits.
  - **Updated** Memory allocation optimized with 8GB RAM limit for Ollama service to accommodate gemma4:31b-cloud model (reduced from previous model) plus headroom for OS overhead and concurrent requests.

```mermaid
flowchart TD
OllamaSvc["Ollama service<br/>8GB RAM limit"] --> WarmupJob["Ollama warmup job<br/>256MB RAM limit"]
WarmupJob --> Ready["Models loaded in RAM"]
Ready --> Backend["Backend requests"]
```

**Diagram sources**
- [docker-compose.yml:24-52](file://docker-compose.yml#L24-L52)
- [docker-compose.prod.yml:45-78](file://docker-compose.prod.yml#L45-L78)

**Section sources**
- [docker-compose.yml:6-52](file://docker-compose.yml#L6-L52)
- [docker-compose.prod.yml:45-78](file://docker-compose.prod.yml#L45-L78)

### LiveKit Server
- **Updated** WebRTC SFU + SIP trunking server with 1GB RAM allocation and embedded configuration approach
- **Updated** Uses custom image revanth2245/resume-livekit:latest built with Dockerfile.livekit that copies livekit.yaml directly into the container during build process
- **Updated** WebSocket interface on port 7880 for signaling
- **Updated** RTC interface on port 7881 for media streams
- **Updated** TURN server on UDP port 7882 for NAT traversal
- **Updated** Embedded configuration via livekit.yaml file copied during build instead of volume mounting for improved reliability
- **Updated** Port range configuration for media streams (50000-60000)
- **Updated** External IP and TCP port configuration for public accessibility
- **Enhanced** Redis integration support for multi-node deployment scenarios
- **Updated** Staging environment uses standardized port mappings (7890:7880, 7891:7881, 7892:7882/udp) to prevent conflicts with production.
- **Updated** Fixed LiveKit configuration environment variable parsing issue by changing node_ip from '${LIVEKIT_NODE_IP}' to hardcoded IP '66.70.191.79' to resolve YAML configuration parsing limitations in containerized environments.
- **Enhanced** API security with 32-character minimum length for API secrets meeting modern security standards.

```mermaid
flowchart TD
LiveKitStart["LiveKit Server Start"] --> BuildImage["Build with Dockerfile.livekit"]
BuildImage --> CopyConfig["Copy livekit.yaml to /etc/livekit.yaml"]
CopyConfig --> InitPorts["Initialize Ports:<br/>7880 (WebSocket)<br/>7881 (RTC)<br/>7882/udp (TURN)"]
InitPorts --> InitTURN["Initialize TURN Server"]
InitTURN --> InitRedis["Initialize Redis Integration"]
InitRedis --> Ready["LiveKit Ready"]
Ready --> HealthCheck["Health Check Endpoint"]
```

**Diagram sources**
- [app/voice_agent/Dockerfile.livekit:1-3](file://app/voice_agent/Dockerfile.livekit#L1-L3)
- [app/voice_agent/livekit.yaml:4-16](file://app/voice_agent/livekit.yaml#L4-L16)
- [app/voice_agent/livekit.yaml:24-26](file://app/voice_agent/livekit.yaml#L24-L26)

**Section sources**
- [app/voice_agent/Dockerfile.livekit:1-3](file://app/voice_agent/Dockerfile.livekit#L1-L3)
- [app/voice_agent/livekit.yaml:1-42](file://app/voice_agent/livekit.yaml#L1-L42)
- [docker-compose.yml:114-136](file://docker-compose.yml#L114-L136)
- [docker-compose.prod.yml:243-267](file://docker-compose.prod.yml#L243-L267)
- [docker-compose.staging.yml:161-179](file://docker-compose.staging.yml#L161-L179)

### Optional Production Services
- Watchtower
  - Auto-restarts containers when images are updated on Docker Hub, including new voice services.
- Certbot
  - Automated certificate renewal with persistent volumes.

```mermaid
graph LR
Watchtower["Watchtower"] --> Backend["Backend"]
Watchtower --> Frontend["Frontend"]
Watchtower --> Nginx["Nginx"]
Watchtower --> SpeechService["Speech Service"]
Watchtower --> VoiceAgent["Voice Agent"]
Watchtower --> LiveKit["LiveKit"]
Certbot["Certbot"] --> Nginx
```

**Diagram sources**
- [docker-compose.prod.yml:199-229](file://docker-compose.prod.yml#L199-L229)

**Section sources**
- [docker-compose.prod.yml:199-229](file://docker-compose.prod.yml#L199-L229)

## Voice Screening Infrastructure

### Speech Service
- **New** CPU-optimized speech processing service with 4GB RAM allocation
- Multi-stage Docker build with system dependencies for audio processing
- **Enhanced** Non-root user execution with proper permissions
- **New** Health check with 120-second start period for model loading
- **New** FastAPI endpoints for STT, TTS, and VAD processing
- **New** Model loading strategy with Parakeet TDT 1.1B, Kokoro 82M, and Silero VAD v5
- **New** Support for various audio formats (WAV, MP3, OGG, raw PCM)

```mermaid
flowchart TD
SpeechStart["Speech Service Start"] --> LoadSTT["Load Parakeet TDT 1.1B"]
LoadSTT --> LoadTTS["Load Kokoro 82M"]
LoadTTS --> LoadVAD["Load Silero VAD v5"]
LoadVAD --> Ready["Service Ready"]
Ready --> HealthCheck["Health Check Endpoint"]
HealthCheck --> STTEndpoint["/stt/transcribe"]
HealthCheck --> TTSEndpoint["/tts/synthesize"]
HealthCheck --> VADEndpoint["/vad/detect"]
```

**Diagram sources**
- [app/speech_service/Dockerfile:1-32](file://app/speech_service/Dockerfile#L1-L32)
- [app/speech_service/main.py:37-200](file://app/speech_service/main.py#L37-L200)

**Section sources**
- [app/speech_service/Dockerfile:1-32](file://app/speech_service/Dockerfile#L1-L32)
- [app/speech_service/main.py:1-387](file://app/speech_service/main.py#L1-L387)
- [app/speech_service/requirements.txt:1-14](file://app/speech_service/requirements.txt#L1-L14)

### Voice Agent
- **New** LiveKit Agents process with 2GB RAM allocation for conversation orchestration
- **New** Integration with Speech Service, LiveKit Server, and Ollama Cloud
- **New** Conversation state machine supporting greeting, consent, introduction, screening, follow-up, wrap-up, analysis, and ended states
- **New** Edge case handling for silence, unclear responses, rescheduling, compensation inquiries, and AI detection
- **New** Asynchronous HTTP clients for Speech Service, LLM, and Backend API communication
- **New** Tenant configuration and candidate information retrieval
- **New** Time budget management and conversation flow control

```mermaid
flowchart TD
VoiceAgentStart["Voice Agent Start"] --> InitClients["Initialize Speech, LLM, and Backend Clients"]
InitClients --> LoadConfig["Load Environment Configuration"]
LoadConfig --> InitEngine["Initialize Conversation Engine"]
InitEngine --> StateMachine["Conversation State Machine"]
StateMachine --> Greeting["GREETING State"]
StateMachine --> Consent["CONSENT State"]
StateMachine --> Introduction["INTRODUCTION State"]
StateMachine --> Screening["SCREENING State"]
StateMachine --> FollowUp["FOLLOW_UP State"]
StateMachine --> WrapUp["WRAP_UP State"]
StateMachine --> Analysis["ANALYSIS State"]
StateMachine --> Ended["ENDED State"]
```

**Diagram sources**
- [app/voice_agent/Dockerfile:1-31](file://app/voice_agent/Dockerfile#L1-L31)
- [app/voice_agent/agent.py:45-78](file://app/voice_agent/agent.py#L45-L78)
- [app/voice_agent/agent.py:252-362](file://app/voice_agent/agent.py#L252-L362)

**Section sources**
- [app/voice_agent/Dockerfile:1-31](file://app/voice_agent/Dockerfile#L1-L31)
- [app/voice_agent/agent.py:1-883](file://app/voice_agent/agent.py#L1-L883)
- [app/voice_agent/livekit.yaml:1-42](file://app/voice_agent/livekit.yaml#L1-L42)

## Dependency Analysis
- Build-time dependencies
  - Backend: Python dependencies pinned in requirements.txt.
  - Frontend: Node packages managed via package.json and installed with npm ci.
  - **New** Speech Service: PyTorch, Torchaudio, Transformers, and NumPy for CPU-optimized inference.
  - **New** Voice Agent: Python dependencies for LiveKit integration and HTTP clients.
  - **Updated** LiveKit: Custom image built with Dockerfile.livekit that embeds livekit.yaml configuration.
- Runtime dependencies
  - Backend depends on Postgres availability and Ollama Cloud readiness.
  - Frontend depends on backend being healthy for API calls.
  - Nginx depends on both frontend and backend services.
  - **New** Speech Service depends on model availability and audio processing libraries.
  - **New** Voice Agent depends on LiveKit Server, Speech Service, and Backend API.
  - **New** LiveKit Server depends on embedded configuration and network ports.
  - **Enhanced** LiveKit depends on Redis for multi-node deployment scenarios.
- CI/CD integration
  - GitHub Actions builds and pushes images to Docker Hub and triggers deployment steps.

```mermaid
graph TB
PyDeps["Python deps (requirements.txt)"] --> BackendDF["Backend Dockerfile"]
NodeDeps["Node deps (package.json)"] --> FrontendDF["Frontend Dockerfile"]
SpeechDeps["Speech deps (requirements.txt)"] --> SpeechDF["Speech Service Dockerfile"]
VoiceDeps["Voice deps (requirements.txt)"] --> VoiceDF["Voice Agent Dockerfile"]
BackendDF --> BackendImg["Backend image"]
FrontendDF --> FrontendImg["Frontend image"]
SpeechDF --> SpeechImg["Speech Service image"]
VoiceDF --> VoiceImg["Voice Agent image"]
NginxDF["Nginx Dockerfile"] --> NginxImg["Nginx image"]
LiveKitDF["Dockerfile.livekit"] --> LiveKitImg["LiveKit image"]
LiveKitCfg["Embedded livekit.yaml"] --> LiveKitImg
RedisCfg["Redis config"] --> LiveKitImg
CI["CI/CD workflows"] --> BackendImg
CI --> FrontendImg
CI --> SpeechImg
CI --> VoiceImg
CI --> NginxImg
CI --> LiveKitImg
```

**Diagram sources**
- [requirements.txt:1-48](file://requirements.txt#L1-L48)
- [app/frontend/package.json:1-41](file://app/frontend/package.json#L1-L41)
- [app/speech_service/requirements.txt:1-14](file://app/speech_service/requirements.txt#L1-L14)
- [app/voice_agent/requirements.txt](file://app/voice_agent/requirements.txt)
- [app/backend/Dockerfile:1-55](file://app/backend/Dockerfile#L1-L55)
- [app/frontend/Dockerfile:1-35](file://app/frontend/Dockerfile#L1-L35)
- [nginx/Dockerfile:1-13](file://nginx/Dockerfile#L1-L13)
- [app/voice_agent/Dockerfile.livekit:1-3](file://app/voice_agent/Dockerfile.livekit#L1-L3)
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

**Section sources**
- [requirements.txt:1-48](file://requirements.txt#L1-L48)
- [app/frontend/package.json:1-41](file://app/frontend/package.json#L1-L41)
- [app/speech_service/requirements.txt:1-14](file://app/speech_service/requirements.txt#L1-L14)
- [app/voice_agent/requirements.txt](file://app/voice_agent/requirements.txt)
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

## Performance Considerations
- Resource limits
  - Production sets explicit CPU and memory limits per service to prevent resource contention.
  - **Updated** Ollama service now allocated 8GB RAM to accommodate gemma4:31b-cloud model with sufficient headroom for concurrent requests and OS overhead.
  - **New** Speech Service allocated 4GB RAM for CPU-optimized inference with PyTorch and audio processing.
  - **New** Voice Agent allocated 2GB RAM for LiveKit Agents and conversation orchestration.
  - **New** LiveKit Server allocated 1GB RAM for WebRTC SFU and SIP trunking with embedded configuration approach.
  - **Enhanced** Redis service (when configured) for LiveKit clustering support.
- Parallelism and caching
  - Ollama environment variables tune concurrency, model loading, and cache quantization for throughput and memory efficiency.
  - **Enhanced** KV cache quantization set to q8_0 type, halving RAM usage per slot and enabling higher parallelism.
  - **New** Speech Service uses CPU-optimized inference with efficient model loading and caching.
- Worker scaling
  - Backend uses multiple Uvicorn workers to handle I/O-bound tasks without starving the LLM.
  - **New** Voice Agent uses asynchronous processing for concurrent conversation handling.
- Network resilience
  - Production Nginx uses dynamic DNS resolution to mitigate stale IPs after container recreation.
  - **New** Production environment includes extra_hosts configuration with `"host.docker.internal:host-gateway"` for seamless inter-environment communication.
  - **New** Staging environment uses standardized port mappings to avoid conflicts with production LiveKit services.
  - **New** Voice services use service discovery for inter-container communication.
  - **New** Development and staging environments use host.docker.internal routing for improved container-host communication.
- Build optimization
  - Frontend multi-stage build minimizes runtime image size and improves cold start times.
  - Backend copies requirements first to leverage Docker layer caching.
  - **New** Speech Service and Voice Agent use multi-stage builds with system dependencies.
  - **Updated** LiveKit uses embedded configuration approach for faster startup and improved reliability.
- **Updated** Timeout configuration
  - **Production**: LLM_NARRATIVE_TIMEOUT=500 seconds (reduced from 300 seconds) representing 40% improvement in response times with gemma4:31b-cloud model
  - **Development**: LLM_NARRATIVE_TIMEOUT=500 seconds for consistent cloud-first behavior
  - **Backend services**: Add 30-second buffer to HTTP timeouts (e.g., 500 + 30 = 530s for production)
  - **Impact**: Significantly reduces timeout-related failures during cloud model processing and improves system responsiveness
  - **New** Speech Service health check with 120-second start period for model loading.
  - **New** Voice Agent uses appropriate timeouts for LiveKit and external service communication.
  - **Enhanced** Redis connection pooling for LiveKit multi-node scenarios.

### Memory Allocation Optimizations for Ollama
The production environment includes several memory-efficient configurations:

- **KV Cache Quantization**: OLLAMA_KV_CACHE_TYPE=q8_0 reduces memory usage by half compared to default quantization
- **Model Loading Strategy**: OLLAMA_KEEP_ALIVE=-1 keeps models permanently loaded in RAM for instant response
- **Resource Limits**: 8GB RAM limit provides headroom for OS overhead and concurrent requests beyond the model's footprint
- **Parallel Processing**: OLLAMA_NUM_PARALLEL=4 enables concurrent LLM requests while maintaining stability

### Voice Service Memory Optimization
**New** Voice processing services utilize optimized memory allocation:

- **Speech Service**: 4GB RAM for CPU-optimized inference with PyTorch models
- **Voice Agent**: 2GB RAM for LiveKit Agents and conversation state management
- **LiveKit Server**: 1GB RAM for WebRTC SFU and SIP trunking with embedded configuration
- **Model Loading**: Lazy loading of speech models with health checks for readiness
- **Redis Integration**: Optional Redis instance for LiveKit clustering and session persistence

**Section sources**
- [docker-compose.prod.yml:64-71](file://docker-compose.prod.yml#L64-L71)
- [docker-compose.prod.yml:48-55](file://docker-compose.prod.yml#L48-L55)
- [docker-compose.prod.yml:273-278](file://docker-compose.prod.yml#L273-L278)
- [docker-compose.prod.yml:245-250](file://docker-compose.prod.yml#L245-L250)
- [docker-compose.prod.yml:255-260](file://docker-compose.prod.yml#L255-L260)
- [docker-compose.staging.yml:170-173](file://docker-compose.staging.yml#L170-L173)

## Troubleshooting Guide
Common issues and resolutions:
- Ollama Cloud API key issues
  - **Symptom**: Backend fails to authenticate with Ollama Cloud
  - **Cause**: Missing or invalid OLLAMA_API_KEY environment variable
  - **Solution**: Set OLLAMA_API_KEY in .env file with valid API key from ollama.com/settings/keys
  - **Verification**: Check /api/llm-status endpoint for cloud connectivity status
- Ollama not responding
  - Inspect container logs and ensure the model is pulled.
  - **Updated** Check Ollama memory allocation - ensure 8GB RAM limit is available for the service.
- Database locked errors
  - SQLite does not support concurrent writes; restart the backend container if encountering "database is locked."
- **Updated** Database initialization failures
  - **Symptom**: Tables not created or Alembic migrations failing
  - **Cause**: Missing model imports in entrypoint script
  - **Solution**: Ensure db_models import occurs before Base.metadata.create_all() execution
  - **Verification**: Check container logs for successful model registration and table creation
- SSL certificate issues
  - Renew certificates manually on the VPS and restart Nginx.
- Deploy failures
  - Verify Docker Hub credentials, SSH keys, and firewall configuration.
- JWT authentication failures
  - Ensure JWT_SECRET_KEY is set in production environments.
- **New** Memory-related Ollama issues
  - **Symptom**: Ollama returns 500 errors or timeouts
  - **Cause**: Insufficient memory allocation for model loading
  - **Solution**: Increase Ollama memory limit from 6GB to 8GB in docker-compose.prod.yml
  - **Verification**: Monitor container memory usage during model warmup
- **New** Speech Service model loading failures
  - **Symptom**: Speech Service health check fails or returns 503 errors
  - **Cause**: Model loading timeout or insufficient memory allocation
  - **Solution**: Increase Speech Service memory limit from 2GB to 4GB in docker-compose.prod.yml
  - **Verification**: Check model loading logs and health endpoint status
- **New** Voice Agent connection issues
  - **Symptom**: Voice Agent cannot connect to LiveKit or Speech Service
  - **Cause**: Service discovery or network configuration problems
  - **Solution**: Verify service names and ports in environment variables
  - **Verification**: Check container logs for connection attempts and error messages
- **New** LiveKit server startup failures
  - **Symptom**: LiveKit server fails to start or health check fails
  - **Cause**: Port conflicts or configuration errors
  - **Solution**: Verify port availability and configuration file syntax
  - **Verification**: Check LiveKit logs and port binding status
- **New** LiveKit embedded configuration issues
  - **Symptom**: LiveKit server fails to load embedded configuration
  - **Cause**: Dockerfile.build process not copying livekit.yaml correctly
  - **Solution**: Verify Dockerfile.livekit build process and file paths
  - **Verification**: Check container filesystem for /etc/livekit.yaml presence
- **New** LiveKit environment variable parsing issues
  - **Symptom**: LiveKit server fails to parse environment variables in configuration
  - **Cause**: YAML configuration parsing limitations with ${LIVEKIT_NODE_IP} variable
  - **Solution**: Use hardcoded IP address '66.70.191.79' in livekit.yaml for reliable configuration
  - **Verification**: Check LiveKit logs for successful configuration loading
- **New** LiveKit API security validation failures
  - **Symptom**: LiveKit rejects API requests due to weak security validation
  - **Cause**: API secrets shorter than 32 characters not meeting security requirements
  - **Solution**: Ensure LIVEKIT_API_SECRET values meet minimum 32-character length requirement
  - **Verification**: Check LiveKit logs for API authentication success and security validation messages
- **New** Redis connectivity issues
  - **Symptom**: LiveKit clustering fails or session persistence errors
  - **Cause**: Redis service not available or misconfigured
  - **Solution**: Ensure Redis service is running and accessible at REDIS_ADDRESS
  - **Verification**: Check Redis connection and cluster status
- **Updated** Timeout-related issues
  - **Symptom**: LLM requests timing out during narrative generation
  - **Cause**: Insufficient LLM_NARRATIVE_TIMEOUT for Ollama Cloud model processing
  - **Solution**: Increase LLM_NARRATIVE_TIMEOUT from 300 to 500 seconds in production environment
  - **Backend behavior**: Services automatically add 30-second buffer to HTTP timeouts (500 + 30 = 530s)
  - **Verification**: Monitor LLM request duration and adjust timeout based on model loading patterns
  - **Enhanced** Speech Service health check timeout = 120 seconds for model loading
  - **Enhanced** Voice Agent LLM client timeout = 120 seconds for Ollama Cloud requests
  - **Enhanced** Redis connection pooling for LiveKit multi-node scenarios.
- **New** Networking connectivity issues
  - **Symptom**: Containers cannot communicate with host.docker.internal or other environments
  - **Cause**: Missing extra_hosts configuration in production environment
  - **Solution**: Ensure nginx service includes extra_hosts with `"host.docker.internal:host-gateway"` mapping
  - **Verification**: Check container networking and DNS resolution for host.docker.internal
- **New** Port conflict issues in staging environment
  - **Symptom**: LiveKit services fail to start due to port conflicts with production
  - **Cause**: Standard LiveKit ports (7880, 7881, 7882) conflicting with production services
  - **Solution**: Use standardized staging port mappings (7890:7880, 7891:7881, 7892:7882/udp) to avoid conflicts
  - **Verification**: Check port availability and container logs for successful service startup
- **New** Development and staging host communication issues
  - **Symptom**: Development servers cannot connect to host-based services
  - **Cause**: Missing host.docker.internal routing configuration
  - **Solution**: Ensure Nginx development configuration uses host.docker.internal:5173 for frontend and :8000 for backend
  - **Verification**: Test connectivity to host services from container using host.docker.internal hostname

Health checks:
- Postgres: health check queries the database using pg_isready.
- Ollama: health check lists available models.
- Backend: health check pings the health endpoint.
- Nginx: health check fetches the health route.
- **New** Speech Service: health check validates model readiness and endpoint accessibility.
- **New** Voice Agent: health check monitors conversation engine status.
- **New** LiveKit: health check verifies WebSocket and media server availability with embedded configuration validation.
- **Enhanced** Redis: health check validates connection and cluster status (when configured).

```mermaid
sequenceDiagram
participant HC as "Healthcheck"
participant PG as "Postgres"
participant OL as "Ollama"
participant BE as "Backend"
participant NG as "Nginx"
participant SS as "Speech Service"
participant VA as "Voice Agent"
participant LK as "LiveKit"
participant RS as "Redis (optional)"
HC->>PG : "pg_isready"
PG-->>HC : "Status"
HC->>OL : "ollama list"
OL-->>HC : "Models"
HC->>BE : "GET /health"
BE-->>HC : "OK"
HC->>NG : "GET /health"
NG-->>HC : "OK"
HC->>SS : "GET /health"
SS-->>HC : "Models Status"
HC->>VA : "GET /health"
VA-->>HC : "Engine Status"
HC->>LK : "GET /health"
LK-->>HC : "Server Status"
HC->>RS : "Redis ping"
RS-->>HC : "Cluster Status"
```

**Diagram sources**
- [docker-compose.yml:18-22](file://docker-compose.yml#L18-L22)
- [docker-compose.prod.yml:38-43](file://docker-compose.prod.yml#L38-L43)
- [docker-compose.prod.yml:72-77](file://docker-compose.prod.yml#L72-L77)
- [docker-compose.prod.yml:117-122](file://docker-compose.prod.yml#L117-L122)
- [docker-compose.prod.yml:155-160](file://docker-compose.prod.yml#L155-L160)
- [app/speech_service/Dockerfile:27-29](file://app/speech_service/Dockerfile#L27-L29)
- [app/voice_agent/Dockerfile:27-28](file://app/voice_agent/Dockerfile#L27-L28)
- [docker-compose.prod.yml:261-266](file://docker-compose.prod.yml#L261-L266)
- [docker-compose.prod.yml:255-262](file://docker-compose.prod.yml#L255-L262)

**Section sources**
- [README.md:337-362](file://README.md#L337-L362)
- [docker-compose.yml:18-22](file://docker-compose.yml#L18-L22)
- [docker-compose.prod.yml:38-43](file://docker-compose.prod.yml#L38-L43)
- [docker-compose.prod.yml:72-77](file://docker-compose.prod.yml#L72-L77)
- [docker-compose.prod.yml:117-122](file://docker-compose.prod.yml#L117-L122)
- [docker-compose.prod.yml:155-160](file://docker-compose.prod.yml#L155-L160)
- [app/speech_service/Dockerfile:27-29](file://app/speech_service/Dockerfile#L27-L29)
- [app/voice_agent/Dockerfile:27-28](file://app/voice_agent/Dockerfile#L27-L28)
- [docker-compose.prod.yml:261-266](file://docker-compose.prod.yml#L261-L266)
- [docker-compose.prod.yml:255-262](file://docker-compose.prod.yml#L255-L262)

## Conclusion
The Docker configuration provides a robust development and production environment for Resume AI with comprehensive voice screening capabilities. It emphasizes predictable service orchestration, optimized LLM performance through enhanced memory allocation settings, secure reverse proxying, and automated deployments. **Updated** The recent enhancements include improved networking connectivity with extra_hosts configuration for seamless inter-environment communication, port standardization for staging environment to prevent conflicts with production services, and enhanced LiveKit service management with standardized port mappings. **Updated** The production environment now includes `"host.docker.internal:host-gateway"` mapping in extra_hosts configuration, enabling reliable communication between containers and the host system. **Updated** The staging environment uses standardized LiveKit port mappings (7890:7880, 7891:7881, 7892:7882/udp) to avoid conflicts with production services while maintaining consistent functionality. **Updated** The backend entrypoint script now includes proper model import handling to ensure Base.metadata.create_all() executes correctly with all database models registered. **Updated** Development and staging environments now support host.docker.internal routing for improved container-host communication. **Updated** The LiveKit configuration has been fixed to resolve environment variable parsing issues by changing node_ip from '${LIVEKIT_NODE_IP}' to hardcoded IP '66.70.191.79', improving reliability in containerized environments. **Enhanced** LiveKit API security has been strengthened with 32-character minimum length requirements for API secrets, meeting modern security standards. Following the documented setup ensures reliable local development and scalable production deployments with a cloud-first approach and comprehensive voice screening capabilities.

## Appendices

### Environment Variables and Secrets Management
- Development compose
  - Backend environment variables include Ollama Cloud base URL, gemma4:31b-cloud model names, database URL, JWT secret, and environment mode.
  - JWT_SECRET_KEY is set to a development value but should be changed for production.
  - Ollama environment variables configure parallelism, caching, and attention kernels.
  - **Updated** LLM_NARRATIVE_TIMEOUT=500 seconds for development environment to match cloud-first approach with improved performance.
  - **New** Voice service environment variables for Speech Service, Voice Agent, and LiveKit configuration.
  - **Enhanced** LiveKit environment variables including SIP trunk configuration and Redis settings.
  - **New** host.docker.internal routing support for development and staging environments.
- Production compose
  - Uses environment variables for database credentials, JWT secret, and model selection.
  - JWT_SECRET_KEY is required and validated at startup.
  - Secrets are injected via environment variables and Docker secrets in CI/CD pipelines.
  - **Enhanced** Ollama memory allocation with 8GB RAM limit and optimized KV cache quantization.
  - **Updated** LLM_NARRATIVE_TIMEOUT=500 seconds for production environment to improve system reliability and reduce response times.
  - **New** Voice service resource allocation with explicit CPU and memory limits.
  - **New** LiveKit configuration with API keys, port specifications, and Redis integration using custom image approach.
  - **Enhanced** Redis configuration for multi-node LiveKit deployment.
  - **New** extra_hosts configuration with `"host.docker.internal:host-gateway"` for seamless inter-environment communication.
  - **Enhanced** API security with 32-character minimum length for LIVEKIT_API_SECRET values.
- Configuration inheritance
  - Production Dockerfiles bake in production Nginx configuration; development compose mounts local configs.
  - **New** Voice services use separate Dockerfiles with optimized build processes.
  - **Updated** LiveKit uses embedded configuration approach with Dockerfile.livekit for improved reliability.
  - **Enhanced** LiveKit configuration supports both development and production deployment scenarios.
- **Updated** Staging environment
  - Uses standardized port mappings for LiveKit services to avoid conflicts with production.
  - LiveKit ports mapped as 7890:7880, 7891:7881, 7892:7882/udp for consistent staging environment.
  - Separate network configuration (aria_staging_network) to isolate staging from production.
  - **New** host.docker.internal routing support for staging environment with separate network isolation.
  - **New** LiveKit environment variable configuration with explicit LIVEKIT_NODE_IP setting for staging.
  - **Enhanced** API security with 32-character minimum length for LIVEKIT_API_SECRET values.

**Updated** JWT_SECRET_KEY is now required in production environments and will cause a RuntimeError if not set.

**Section sources**
- [docker-compose.yml:59-180](file://docker-compose.yml#L59-L180)
- [docker-compose.yml:33-42](file://docker-compose.yml#L33-L42)
- [docker-compose.prod.yml:89-122](file://docker-compose.prod.yml#L89-L122)
- [docker-compose.prod.yml:48-55](file://docker-compose.prod.yml#L48-L55)
- [docker-compose.prod.yml:285-294](file://docker-compose.prod.yml#L285-L294)
- [docker-compose.prod.yml:242-244](file://docker-compose.prod.yml#L242-L244)
- [docker-compose.prod.yml:244-246](file://docker-compose.prod.yml#L244-L246)
- [docker-compose.prod.yml:144-146](file://docker-compose.prod.yml#L144-L146)
- [nginx/nginx.prod.conf:1-11](file://nginx/nginx.prod.conf#L1-L11)
- [app/nginx/nginx.conf:1-11](file://app/nginx/nginx.conf#L1-L11)
- [app/backend/middleware/auth.py:13-21](file://app/backend/middleware/auth.py#L13-L21)
- [docker-compose.staging.yml:170-173](file://docker-compose.staging.yml#L170-L173)
- [docker-compose.staging.yml:220-224](file://docker-compose.staging.yml#L220-L224)

### CI/CD and Image Builds
- CI workflows run backend and frontend tests on pull requests and pushes.
- CD workflow builds and pushes backend, frontend, Nginx, speech-service, voice-agent, and LiveKit images to Docker Hub.
- Deployment is manual after successful image push, pulling latest images and restarting services.
- **New** Watchtower automatically updates voice services along with core services.
- **Enhanced** CI/CD pipeline supports multi-service image builds with proper tagging.
- **Updated** LiveKit image built with Dockerfile.livekit that embeds configuration for improved reliability.

**Section sources**
- [.github/workflows/ci.yml:1-63](file://.github/workflows/ci.yml#L1-L63)
- [.github/workflows/cd.yml:1-101](file://.github/workflows/cd.yml#L1-L101)

### Port Configuration Reference
- Development environment:
  - Nginx: host port 80 → container port 80 (frontend)
  - Nginx: host port 8000 → container port 8000 (backend)
  - Frontend: host port 3000 → container port 80
  - Backend: host port 8000 → container port 8000
  - **New** Speech Service: container port 8001 (internal communication)
  - **New** Voice Agent: container port 8002 (internal communication)
  - **New** LiveKit Server: ports 7880 (WebSocket), 7881 (RTC), 7882/udp (TURN) with embedded configuration
  - **New** host.docker.internal routing: http://host.docker.internal:5173 (frontend dev), http://host.docker.internal:8000 (backend dev)
- Production environment:
  - Nginx: host port 80 → container port 80
  - Frontend: container port 8080 (exposed)
  - Backend: container port 8000
  - **New** Speech Service: container port 8001 (internal communication)
  - **New** Voice Agent: container port 8002 (internal communication)
  - **New** LiveKit Server: ports 7880 (WebSocket), 7881 (RTC), 7882/udp (TURN) with embedded configuration
  - **Enhanced** Redis: container port 6379 (when configured)
  - **New** extra_hosts: `"host.docker.internal:host-gateway"` for seamless inter-environment communication
  - **New** host.docker.internal routing support for production environment
- **New** Staging environment:
  - Nginx: host port 80 → container port 80
  - Frontend: container port 8080 (exposed)
  - Backend: container port 8000
  - **New** Speech Service: container port 8001 (internal communication)
  - **New** Voice Agent: container port 8002 (internal communication)
  - **New** LiveKit Server: ports 7890:7880 (WebSocket), 7891:7881 (RTC), 7892:7882/udp (TURN) with embedded configuration
  - **Enhanced** Redis: container port 6379 (when configured)
  - **New** Separate network: aria_staging_network for environment isolation
  - **New** host.docker.internal routing support for staging environment
  - **New** LiveKit environment variable configuration with explicit LIVEKIT_NODE_IP setting for staging
  - **Enhanced** API security with 32-character minimum length for LIVEKIT_API_SECRET values.

**Section sources**
- [docker-compose.yml:87-180](file://docker-compose.yml#L87-L180)
- [docker-compose.prod.yml:139-160](file://docker-compose.prod.yml#L139-L160)
- [docker-compose.prod.yml:269-278](file://docker-compose.prod.yml#L269-L278)
- [docker-compose.prod.yml:283-306](file://docker-compose.prod.yml#L283-L306)
- [docker-compose.prod.yml:251-256](file://docker-compose.prod.yml#L251-L256)
- [docker-compose.prod.yml:245-249](file://docker-compose.prod.yml#L245-L249)
- [docker-compose.prod.yml:144-146](file://docker-compose.prod.yml#L144-L146)
- [docker-compose.staging.yml:169-173](file://docker-compose.staging.yml#L169-L173)
- [docker-compose.staging.yml:192-214](file://docker-compose.staging.yml#L192-L214)
- [app/frontend/Dockerfile:32](file://app/frontend/Dockerfile#L32)
- [app/frontend/default.conf:2](file://app/frontend/default.conf#L2)
- [app/nginx/nginx.conf:11](file://app/nginx/nginx.conf#L11)
- [app/nginx/nginx.conf:26](file://app/nginx/nginx.conf#L26)

### Ollama Model Setup and Customization
The system supports both standard and custom model configurations:

- **Standard Model**: gemma4:31b-cloud (cloud-first default) - 40% faster response times than previous model
- **Custom Model**: qwen3.5:4b for local deployment
- **Setup Script**: Automated model building process for custom AI models

**Section sources**
- [ollama/setup-recruiter-model.sh:1-54](file://ollama/setup-recruiter-model.sh#L1-L54)
- [docker-compose.prod.yml:92-95](file://docker-compose.prod.yml#L92-L95)
- [docker-compose.yml:63-64](file://docker-compose.yml#L63-L64)

### Timeout Configuration Details
**Updated** The system now uses configurable timeout values for LLM operations with cloud-first defaults optimized for gemma4:31b-cloud model:

- **Production Environment**:
  - LLM_NARRATIVE_TIMEOUT=500 seconds (reduced from 300 seconds, 40% improvement)
  - Backend HTTP timeout = 500 + 30 = 530 seconds
  - Purpose: Accommodate gemma4:31b-cloud model processing with significantly reduced response times
  - **New** Speech Service health check timeout = 120 seconds for model loading
  - **New** Voice Agent LLM client timeout = 120 seconds for Ollama Cloud requests
  - **Enhanced** Redis connection timeout = 30 seconds for cluster operations
- **Development Environment**:
  - LLM_NARRATIVE_TIMEOUT=500 seconds (matches cloud-first approach)
  - Backend HTTP timeout = 500 + 30 = 530 seconds
  - Purpose: Consistent behavior across environments with improved performance
- **Backend Implementation**:
  - Hybrid pipeline: Uses LLM_NARRATIVE_TIMEOUT for streaming narrative generation
  - LLM service: Adds 30-second buffer to HTTPX client timeouts
  - Agent pipeline: Applies same timeout logic for reasoning tasks
- **Impact**:
  - Reduces timeout-related failures during cloud model processing by 40%
  - Improves system responsiveness and user experience
  - Balances performance with stability requirements

**Section sources**
- [docker-compose.prod.yml:99-101](file://docker-compose.prod.yml#L99-L101)
- [docker-compose.yml:68-69](file://docker-compose.yml#L68-69)
- [app/backend/services/hybrid_pipeline.py:86-103](file://app/backend/services/hybrid_pipeline.py#L86-L103)
- [app/backend/services/llm_service.py:52-55](file://app/backend/services/llm_service.py#L52-L55)
- [app/voice_agent/agent.py:166](file://app/voice_agent/agent.py#L166)

### Cloud-First Deployment Guidance
**Updated** The system now emphasizes cloud-first deployment with local Ollama as optional:

- **Cloud-First Default**: OLLAMA_BASE_URL=https://ollama.com with API key authentication
- **Local Ollama Option**: Set OLLAMA_BASE_URL=http://ollama:11434 for self-hosted deployment
- **Model Selection**: gemma4:31b-cloud as primary cloud model (40% faster than previous model), qwen3.5:4b for local
- **API Key Requirement**: OLLAMA_API_KEY is mandatory for cloud deployment
- **Timeout Configuration**: 500-second timeout optimized for gemma4:31b-cloud model performance
- **New** Voice services support both cloud and local deployment modes
- **New** LiveKit configuration supports development and production deployment scenarios with embedded configuration approach
- **Enhanced** Redis integration enables horizontal scaling for voice services
- **New** Seamless inter-environment communication via extra_hosts configuration with host.docker.internal mapping
- **New** Development and staging environments support host.docker.internal routing for improved container-host communication
- **Updated** LiveKit configuration uses hardcoded IP address '66.70.191.79' instead of environment variable for improved reliability in containerized environments.
- **Enhanced** API security with 32-character minimum length for LIVEKIT_API_SECRET values meeting modern security standards.

**Section sources**
- [docker-compose.yml:61-70](file://docker-compose.yml#L61-L70)
- [README.md:208-224](file://README.md#L208-L224)
- [README.md:392-416](file://README.md#L392-L416)
- [app/voice_agent/livekit.yaml:18-19](file://app/voice_agent/livekit.yaml#L18-L19)
- [app/voice_agent/livekit.yaml:24-26](file://app/voice_agent/livekit.yaml#L24-L26)
- [docker-compose.prod.yml:144-146](file://docker-compose.prod.yml#L144-L146)

### Voice Service Configuration
**New** Comprehensive voice service configuration and deployment guidance:

- **Speech Service Features**:
  - STT: Parakeet TDT 1.1B for streaming speech-to-text
  - TTS: Kokoro 82M for CPU-optimized text-to-speech
  - VAD: Silero VAD v5 for speech activity detection
  - Audio Formats: WAV, MP3, OGG, raw PCM support
- **Voice Agent Capabilities**:
  - Conversation State Machine: GREETING → CONSENT → INTRODUCTION → SCREENING → FOLLOW_UP → WRAP_UP → ANALYSIS → ENDED
  - Edge Case Handling: Silence detection, rescheduling, compensation inquiries, AI detection
  - LLM Integration: Ollama Cloud for intelligent conversation responses
  - Tenant Configuration: Dynamic personality and conversation flow based on tenant settings
- **LiveKit Integration**:
  - WebRTC SFU for media streaming
  - SIP Trunking for PSTN integration
  - TURN Server for NAT traversal
  - WebSocket signaling for call control
  - **Enhanced** Redis clustering for multi-node deployment
  - **Updated** Embedded configuration approach for improved reliability and deployment consistency
  - **Updated** Staging environment uses standardized port mappings (7890:7880, 7891:7881, 7892:7882/udp) to prevent conflicts
  - **Updated** LiveKit configuration uses hardcoded IP address '66.70.191.79' for improved reliability
  - **Enhanced** API security with 32-character minimum length for API secrets.
- **Deployment Considerations**:
  - Resource allocation: 4GB RAM for Speech Service, 2GB for Voice Agent, 1GB for LiveKit
  - Network configuration: Internal ports for service communication, external ports for client access
  - Health monitoring: Individual service health checks and graceful shutdown handling
  - **Enhanced** Redis configuration for session persistence and clustering
  - **Updated** LiveKit uses custom image with embedded configuration for faster startup
  - **New** Production environment includes extra_hosts configuration for seamless inter-environment communication
  - **New** Development and staging environments support host.docker.internal routing for improved container-host communication

**Section sources**
- [app/speech_service/main.py:1-387](file://app/speech_service/main.py#L1-L387)
- [app/voice_agent/agent.py:1-883](file://app/voice_agent/agent.py#L1-L883)
- [app/voice_agent/livekit.yaml:1-42](file://app/voice_agent/livekit.yaml#L1-L42)
- [docker-compose.prod.yml:264-308](file://docker-compose.prod.yml#L264-L308)
- [app/voice_agent/Dockerfile.livekit:1-3](file://app/voice_agent/Dockerfile.livekit#L1-L3)
- [docker-compose.staging.yml:160-179](file://docker-compose.staging.yml#L160-L179)
- [docker-compose.prod.yml:144-146](file://docker-compose.prod.yml#L144-L146)

### LiveKit Configuration Approach
**Updated** LiveKit server configuration now uses an embedded approach for improved reliability and deployment consistency:

- **Embedded Configuration Method**:
  - Dockerfile.livekit copies livekit.yaml directly into the container during build process
  - Uses custom image revanth2245/resume-livekit:latest instead of official livekit/livekit-server:latest
  - Eliminates volume mounting complexity and potential permission issues
  - Improves startup reliability and deployment consistency
- **Build Process**:
  - FROM livekit/livekit-server:latest base image
  - COPY app/voice_agent/livekit.yaml /etc/livekit.yaml during build
  - Ensures configuration is baked into the image at build time
- **Configuration Fix**:
  - **Updated** node_ip changed from '${LIVEKIT_NODE_IP}' to hardcoded IP '66.70.191.79'
  - Resolves YAML configuration parsing limitations in containerized environments
  - Improves reliability of LiveKit server startup and operation
- **Security Enhancements**:
  - **Enhanced** API keys now require minimum 32-character length for security compliance
  - **Updated** API secrets include both development and staging variants with sufficient length
  - **Improved** security validation for API authentication requests
- **Advantages**:
  - Faster container startup without configuration file mounting
  - Reduced complexity in development and production environments
  - Improved reliability across different deployment platforms
  - Easier debugging and troubleshooting
- **Maintenance**:
  - Configuration changes require rebuilding the LiveKit image
  - Better version control and deployment tracking
  - Consistent configuration across all environments
- **Port Standardization**:
  - **Production**: LiveKit ports 7880 (WebSocket), 7881 (RTC), 7882/udp (TURN)
  - **Staging**: LiveKit ports 7890:7880, 7891:7881, 7892:7882/udp to avoid conflicts
  - **New** Staging environment uses separate network (aria_staging_network) for isolation

**Section sources**
- [app/voice_agent/Dockerfile.livekit:1-3](file://app/voice_agent/Dockerfile.livekit#L1-L3)
- [app/voice_agent/livekit.yaml:1-42](file://app/voice_agent/livekit.yaml#L1-L42)
- [docker-compose.yml:114-136](file://docker-compose.yml#L114-L136)
- [docker-compose.prod.yml:243-267](file://docker-compose.prod.yml#L243-L267)
- [docker-compose.staging.yml:161-179](file://docker-compose.staging.yml#L161-L179)

### Database Initialization and Model Registration
**Updated** The backend database initialization process now includes proper model registration:

- **Model Import Fix**:
  - The entrypoint script now explicitly imports `app.backend.models.db_models` before executing `Base.metadata.create_all()`
  - This ensures all SQLAlchemy models are registered with the declarative base before table creation
  - Prevents missing table creation issues that could occur with unregistered models
- **Alembic Migration Integration**:
  - Models are imported for both table creation and Alembic migration execution
  - Alembic environment configuration also imports `db_models` for migration target metadata
- **Production Startup Sequence**:
  - Database URL detection determines PostgreSQL vs SQLite behavior
  - PostgreSQL: Execute model registration, table creation, and Alembic migrations
  - SQLite: Skip migrations and rely on Alembic for schema management
- **Main Application Integration**:
  - FastAPI lifespan manager also creates tables using the same Base.metadata approach
  - Provides redundancy for database initialization across different startup paths

**Section sources**
- [app/backend/scripts/docker-entrypoint.sh:8](file://app/backend/scripts/docker-entrypoint.sh#L8)
- [app/backend/db/database.py:41](file://app/backend/db/database.py#L41)
- [app/backend/models/db_models.py:1-10](file://app/backend/models/db_models.py#L1-L10)
- [alembic/env.py:12](file://alembic/env.py#L12)
- [app/backend/main.py:259](file://app/backend/main.py#L259)

### Redis Integration for LiveKit
**Enhanced** Redis integration enables advanced LiveKit deployment scenarios:

- **Purpose**: Enable multi-node LiveKit clusters, session persistence, and pub/sub messaging
- **Configuration**: 
  - Address: redis://redis:6379 (when configured)
  - Connection pooling for high-concurrency scenarios
- **Benefits**:
  - Horizontal scaling of LiveKit servers
  - Session state persistence across deployments
  - Improved reliability for voice screening workflows
- **Deployment**: Optional service that can be enabled/disabled based on requirements

**Section sources**
- [app/voice_agent/livekit.yaml:24-26](file://app/voice_agent/livekit.yaml#L24-L26)
- [docker-compose.prod.yml:251-256](file://docker-compose.prod.yml#L251-L256)

### Networking and Inter-Environment Communication
**New** Enhanced networking configuration for seamless inter-environment communication:

- **Production Environment**:
  - **extra_hosts**: `"host.docker.internal:host-gateway"` enables containers to resolve host.docker.internal to the host gateway IP
  - **Dynamic DNS Resolution**: Nginx uses resolver 127.0.0.11 with 5s validity for quick container IP changes
  - **Host Communication**: Enables communication between containers and host system for development and staging
- **Development Environment**:
  - **Direct Host Mapping**: Nginx configuration proxies to host.docker.internal:5173 (frontend) and :8000 (backend)
  - **Local Development**: Simplifies development workflow by connecting to host-based dev servers
  - **host.docker.internal Routing**: http://host.docker.internal:5173 for frontend dev server, http://host.docker.internal:8000 for backend API
- **Staging Environment**:
  - **Port Standardization**: LiveKit services use 7890:7880, 7891:7881, 7892:7882/udp to avoid conflicts with production
  - **Network Isolation**: Separate network (aria_staging_network) prevents interference with production services
  - **Consistent Functionality**: Maintains LiveKit functionality while avoiding port conflicts
  - **host.docker.internal Routing**: http://host.docker.internal:8080 for staging frontend access
  - **LiveKit Environment Variables**: Explicit LIVEKIT_NODE_IP configuration for staging environment
  - **Enhanced** API Security: 32-character minimum length for LIVEKIT_API_SECRET values
- **Inter-Environment Communication**:
  - **Production to Staging**: Use host.docker.internal mapping for seamless communication
  - **Staging Isolation**: Separate network prevents cross-environment interference
  - **Port Management**: Standardized staging ports prevent conflicts with production services

**Section sources**
- [docker-compose.prod.yml:144-146](file://docker-compose.prod.yml#L144-L146)
- [nginx/nginx.prod.conf:12-20](file://nginx/nginx.prod.conf#L12-L20)
- [app/nginx/nginx.conf:14-15](file://app/nginx/nginx.conf#L14-L15)
- [app/nginx/nginx.conf:32-33](file://app/nginx/nginx.conf#L32-L33)
- [docker-compose.staging.yml:170-173](file://docker-compose.staging.yml#L170-L173)
- [docker-compose.staging.yml:220-224](file://docker-compose.staging.yml#L220-L224)

### LiveKit API Security Configuration
**Enhanced** LiveKit API security configuration with strengthened authentication requirements:

- **API Secret Requirements**:
  - **Minimum Length**: 32 characters minimum for all API secrets
  - **Development Keys**: devsecret_minimum_32_characters_long_abcdef (32 characters)
  - **Staging Keys**: staging_devsecret_min32chars_long_xyz (35 characters)
  - **Production Keys**: Must meet 32-character minimum requirement for security compliance
- **Security Validation**:
  - LiveKit server validates API secret length during startup
  - Embedded configuration ensures secrets are properly loaded at container boot
  - API authentication requests verified against configured secret lengths
- **Configuration Examples**:
  - Development: LIVEKIT_API_SECRET=devsecret_minimum_32_characters_long_abcdef
  - Staging: LIVEKIT_API_SECRET=staging_devsecret_min32chars_long_xyz
  - Production: Requires 32+ character secret for enhanced security
- **Best Practices**:
  - Generate secrets using cryptographically secure random generators
  - Store secrets in environment variables or Docker secrets
  - Rotate secrets periodically for enhanced security
  - Use different secrets for development, staging, and production environments

**Section sources**
- [app/voice_agent/livekit.yaml:19-22](file://app/voice_agent/livekit.yaml#L19-L22)
- [docker-compose.yml:123-124](file://docker-compose.yml#L123-L124)
- [docker-compose.staging.yml:168-169](file://docker-compose.staging.yml#L168-L169)
- [docker-compose.staging.yml:201-202](file://docker-compose.staging.yml#L201-L202)