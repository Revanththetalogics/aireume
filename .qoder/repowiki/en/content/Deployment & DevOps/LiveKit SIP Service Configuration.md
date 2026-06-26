# LiveKit SIP Service Configuration

<cite>
**Referenced Files in This Document**
- [livekit.yaml](file://app/voice_agent/livekit.yaml)
- [Dockerfile.livekit](file://app/voice_agent/Dockerfile.livekit)
- [agent.py](file://app/voice_agent/agent.py)
- [docker-compose.yml](file://docker-compose.yml)
- [docker-compose.staging.yml](file://docker-compose.staging.yml)
- [docker-compose.prod.yml](file://docker-compose.prod.yml)
- [voice.py](file://app/backend/routes/voice.py)
- [voice_call_scheduler.py](file://app/backend/services/voice_call_scheduler.py)
- [voice_screening_service.py](file://app/backend/services/voice_screening_service.py)
- [requirements.txt](file://app/voice_agent/requirements.txt)
</cite>

## Update Summary
**Changes Made**
- Updated Docker Compose configuration documentation to reflect the corrected VOICE_AGENT_URL environment variable from container name to service name for improved DNS resolution and service discovery reliability
- Enhanced service discovery documentation with proper container-to-service naming conventions
- Updated troubleshooting guidance for service URL configuration issues

## Table of Contents
1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [LiveKit Server Configuration](#livekit-server-configuration)
4. [SIP Trunk Management](#sip-trunk-management)
5. [Voice Agent Integration](#voice-agent-integration)
6. [Docker Deployment](#docker-deployment)
7. [Environment Variables](#environment-variables)
8. [Configuration Best Practices](#configuration-best-practices)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Conclusion](#conclusion)

## Introduction

The LiveKit SIP Service Configuration provides a comprehensive framework for implementing automated voice screening capabilities using LiveKit's WebRTC infrastructure and SIP trunking technology. This system enables organizations to conduct automated phone interviews with candidates through outbound SIP calls, leveraging AI-powered conversation agents and real-time speech processing.

The configuration encompasses three primary components: the LiveKit server for WebRTC communication and SIP trunking, the voice agent service for conversation orchestration, and the backend scheduling system for managing call workflows. This documentation provides detailed insights into the complete setup, configuration options, and operational procedures.

## System Architecture

The LiveKit SIP Service operates within a microservices architecture that integrates multiple specialized components working together to deliver automated voice screening capabilities.

```mermaid
graph TB
subgraph "External Systems"
Twilio[Twilio PSTN Network]
Candidates[Candidates]
end
subgraph "Backend Services"
Backend[Backend API]
Scheduler[Voice Call Scheduler]
Database[(PostgreSQL Database)]
end
subgraph "Voice Infrastructure"
LiveKit[LiveKit Server]
VoiceAgent[Voice Agent Service]
SpeechService[Speech Service]
Ollama[Ollama LLM]
end
subgraph "Internal Components"
SIPTrunk[SIP Trunk Manager]
RoomManager[Room Manager]
ConversationEngine[Conversation Engine]
end
Candidates --> Twilio
Twilio --> LiveKit
Backend --> Scheduler
Scheduler --> VoiceAgent
VoiceAgent --> LiveKit
VoiceAgent --> SpeechService
VoiceAgent --> Ollama
LiveKit --> SIPTrunk
LiveKit --> RoomManager
VoiceAgent --> ConversationEngine
Backend --> Database
VoiceAgent --> Database
LiveKit --> Database
```

**Diagram sources**
- [docker-compose.yml:114-175](file://docker-compose.yml#L114-L175)
- [agent.py:535-688](file://app/voice_agent/agent.py#L535-L688)

The architecture follows a clear separation of concerns with distinct services handling different aspects of the voice screening workflow. The LiveKit server manages the WebRTC infrastructure and SIP connections, while the voice agent service orchestrates conversations and integrates with external services.

## LiveKit Server Configuration

The LiveKit server serves as the central communication hub for the voice screening system, providing WebRTC signaling, media relay, and SIP trunking capabilities.

### Core Configuration Parameters

The LiveKit server configuration file defines essential networking and security parameters:

```mermaid
flowchart TD
ConfigFile[livekit.yaml] --> PortConfig[Port Configuration]
ConfigFile --> RTCConfig[RTC Settings]
ConfigFile --> TURNConfig[TURN Server]
ConfigFile --> AuthConfig[Authentication]
ConfigFile --> RedisConfig[Redis Connection]
PortConfig --> WebPort[Web Socket: 7880]
PortConfig --> TCPConfig[TCP Port: 7881]
PortConfig --> UDPConfig[UDP Port: 7882]
RTCConfig --> PortRange[Port Range: 10000-10100]
RTCConfig --> ExternalIP[External IP: 66.70.191.79]
RTCConfig --> NodeIP[Node IP: 66.70.191.79]
RTCConfig --> UseExternal[Use External IP: false]
TURNConfig --> TURNEnabled[TURN Enabled: true]
TURNConfig --> Domain[Domain: ""]
TURNConfig --> TLSPort[TLS Port: 0]
TURNConfig --> UDPPort[UDP Port: 7882]
TURNConfig --> ExternalTLS[External TLS: false]
AuthConfig --> DevKey[Dev Key: devsecret_minimum_32_characters_long_abcdef]
AuthConfig --> StagingKey[Staging Key: staging_devsecret_min32chars_long_xyz]
RedisConfig --> RedisAddr[Address: livekit-redis:6379]
```

**Diagram sources**
- [livekit.yaml:4-31](file://app/voice_agent/livekit.yaml#L4-L31)

### Network Configuration Details

**Updated** The LiveKit server now uses an optimized RTP port range for improved operational efficiency and Portainer interface stability.

The server utilizes a streamlined port allocation strategy to support various communication protocols:

| Component | Port | Protocol | Purpose |
|-----------|------|----------|---------|
| WebSocket | 7880 | TCP | Primary WebRTC signaling |
| TCP Fallback | 7881 | TCP | Alternative signaling channel |
| TURN/UDP | 7882 | UDP | Media relay for NAT traversal |
| RTC Range | 10000-10100 | UDP/TCP | Optimized media transport (reduced from 50000-50200) |

**Section sources**
- [livekit.yaml:4-31](file://app/voice_agent/livekit.yaml#L4-L31)

### Authentication and Security

The configuration implements a dual-key authentication system supporting both development and staging environments:

- **Development Keys**: Used for local testing and development
- **Staging Keys**: Designed for pre-production environments
- **Production Keys**: To be configured in deployment environments

**Section sources**
- [livekit.yaml:19-21](file://app/voice_agent/livekit.yaml#L19-L21)

## SIP Trunk Management

The SIP trunk management system provides programmatic control over SIP trunk creation and configuration, enabling dynamic integration with external telephony providers.

### Enhanced Trunk Resolution Process

**Updated** Improved SIP trunk resolution with termination address matching for enhanced reliability

```mermaid
sequenceDiagram
participant VoiceAgent as Voice Agent
participant LiveKitAPI as LiveKit API
participant SIPProtocol as SIP Protocol
participant TrunkStore as Trunk Storage
VoiceAgent->>LiveKitAPI : resolve_sip_trunk_id()
LiveKitAPI->>SIPProtocol : list_outbound_trunk()
SIPProtocol-->>LiveKitAPI : ListSIPOutboundTrunkResponse
LiveKitAPI->>TrunkStore : Check existing trunks
alt Trunk Found by Termination Address
TrunkStore-->>VoiceAgent : Return trunk_id
else Trunk Found by Name/ID
VoiceAgent->>LiveKitAPI : _create_sip_trunk()
LiveKitAPI->>SIPProtocol : create_outbound_trunk()
SIPProtocol-->>LiveKitAPI : SIPOutboundTrunkInfo
LiveKitAPI->>TrunkStore : Store new trunk
TrunkStore-->>VoiceAgent : Return new trunk_id
end
```

**Diagram sources**
- [agent.py:544-592](file://app/voice_agent/agent.py#L544-L592)

### SIP Termination Address Configuration

**New** Enhanced SIP termination address management for improved telephony reliability

The system now supports configurable SIP termination addresses with priority matching:

| Matching Priority | Configuration | Purpose |
|-------------------|---------------|---------|
| 1 | `SIP_TERMINATION_ADDRESS` | Primary termination address (e.g., `aria-staging.pstn.twilio.com`) |
| 2 | `SIP_TRUNK_ID` | Fallback trunk identifier |
| 3 | `SIP_OUTBOUND_NUMBER` | Trunk number matching |

**Section sources**
- [agent.py:41-42](file://app/voice_agent/agent.py#L41-L42)
- [agent.py:574-577](file://app/voice_agent/agent.py#L574-L577)
- [agent.py:605-607](file://app/voice_agent/agent.py#L605-L607)

### Trunk Configuration Parameters

The SIP trunk configuration supports flexible provider integration with Twilio as the primary PSTN provider:

| Parameter | Value | Description |
|-----------|-------|-------------|
| Provider Address | `sip.pstn.twilio.com` | Twilio SIP endpoint |
| Trunk Name | `twilio-aria` | Logical identifier |
| Outbound Number | `+18722789563` | Twilio phone number |
| Authentication | `aria-livekit` / `Itslogical1.` | SIP credentials |
| Termination Address | `aria-staging.pstn.twilio.com` | SIP termination endpoint |

**Section sources**
- [agent.py:594-619](file://app/voice_agent/agent.py#L594-L619)
- [docker-compose.staging.yml:252-253](file://docker-compose.staging.yml#L252-L253)

### Programmatic Trunk Creation

The system automatically detects existing trunks and creates new ones when necessary, ensuring reliable operation without manual intervention:

```mermaid
flowchart TD
Start[Start Trunk Resolution] --> CheckCache[Check Resolved Trunk ID]
CheckCache --> CacheHit{Cache Hit?}
CacheHit --> |Yes| ReturnCached[Return Cached Trunk ID]
CacheHit --> |No| ListTrunks[List Existing Trunks]
ListTrunks --> ParseResponse[Parse Trunk Response]
ParseResponse --> FindMatch{Find Matching Trunk?}
FindMatch --> |By Termination Address| CacheTrunk[Cache and Return Trunk ID]
FindMatch --> |By Name/ID| CreateTrunk[Create New Trunk]
FindMatch --> |No Match| CreateTrunk
CreateTrunk --> StoreTrunk[Store in Local Cache]
StoreTrunk --> ReturnNew[Return New Trunk ID]
ReturnCached --> End[End]
CacheTrunk --> End
ReturnNew --> End
```

**Diagram sources**
- [agent.py:544-592](file://app/voice_agent/agent.py#L544-L592)

**Section sources**
- [agent.py:544-619](file://app/voice_agent/agent.py#L544-L619)

## Voice Agent Integration

The voice agent service acts as the central coordinator for the voice screening workflow, managing call initiation, conversation orchestration, and integration with external services.

### Service Architecture

```mermaid
classDiagram
class LiveKitSIPDispatcher {
-lk_url : string
-api_key : string
-api_secret : string
-_resolved_trunk_id : Optional[string]
+resolve_sip_trunk_id(api) string
+_create_sip_trunk(api) Optional[string]
+dispatch_call(session_id, phone_number, candidate_name) dict
+_create_agent_token(room_name) string
}
class VoiceAgentWorker {
-_active_sessions : dict
+handle_room(room_name, agent_token, session_ctx) void
+process_audio_stream() void
+manage_conversation() void
}
class ConversationEngine {
-ctx : ScreeningContext
-speech : SpeechClient
-llm : LLMClient
-backend : BackendClient
-history : list
+get_bot_response(user_text) string
+advance_state() void
+handle_edge_case(user_text) Optional[string]
+check_time_budget() bool
}
class ScreeningContext {
+session_id : int
+tenant_id : int
+candidate_id : int
+phone_number : string
+bot_name : string
+state : CallState
+transcript : list
+call_duration_max : int
}
LiveKitSIPDispatcher --> VoiceAgentWorker : "coordinates"
VoiceAgentWorker --> ConversationEngine : "uses"
ConversationEngine --> ScreeningContext : "manages"
```

**Diagram sources**
- [agent.py:535-830](file://app/voice_agent/agent.py#L535-L830)

### Call Dispatch Process

The voice agent orchestrates the complete call lifecycle from initiation to completion:

```mermaid
sequenceDiagram
participant Backend as Backend Service
participant VoiceAgent as Voice Agent
participant LiveKit as LiveKit Server
participant Candidate as Candidate
participant SpeechSvc as Speech Service
participant LLM as LLM Service
Backend->>VoiceAgent : POST /dispatch
VoiceAgent->>LiveKit : resolve_sip_trunk_id()
LiveKit-->>VoiceAgent : Trunk ID
VoiceAgent->>LiveKit : create_room()
LiveKit-->>VoiceAgent : Room Created
VoiceAgent->>LiveKit : create_sip_participant()
LiveKit-->>VoiceAgent : SIP Participant Created
VoiceAgent->>LiveKit : _create_agent_token()
LiveKit-->>VoiceAgent : Agent Token
VoiceAgent->>SpeechSvc : Initialize Speech Client
VoiceAgent->>LLM : Initialize LLM Client
VoiceAgent->>VoiceAgent : handle_room()
VoiceAgent->>Candidate : Connect to Room
Candidate-->>VoiceAgent : Audio Stream
VoiceAgent->>SpeechSvc : transcribe(audio)
SpeechSvc-->>VoiceAgent : text
VoiceAgent->>LLM : get_bot_response(text)
LLM-->>VoiceAgent : response
VoiceAgent->>Candidate : Play Response
```

**Diagram sources**
- [agent.py:636-688](file://app/voice_agent/agent.py#L636-L688)
- [voice_call_scheduler.py:189-220](file://app/backend/services/voice_call_scheduler.py#L189-L220)

**Section sources**
- [agent.py:431-531](file://app/voice_agent/agent.py#L431-L531)
- [agent.py:636-688](file://app/voice_agent/agent.py#L636-L688)

### Conversation Management

The conversation engine implements a sophisticated state machine managing the complete screening process:

| State | Description | Actions |
|-------|-------------|---------|
| GREETING | Initial contact with candidate | Identity confirmation |
| CONSENT | Obtain recording consent | Legal compliance |
| INTRODUCTION | Role explanation | Position details |
| SCREENING | Core interview questions | Skill assessment |
| FOLLOW_UP | Additional probing | Weak answers |
| WRAP_UP | Closing remarks | Next steps |
| ANALYSIS | Post-call processing | Assessment generation |
| ENDED | Call termination | Cleanup |

**Section sources**
- [agent.py:51-84](file://app/voice_agent/agent.py#L51-L84)
- [agent.py:355-374](file://app/voice_agent/agent.py#L355-L374)

## Docker Deployment

The Docker configuration provides a comprehensive containerized deployment for the LiveKit SIP Service ecosystem.

### Container Orchestration

```mermaid
graph TB
subgraph "Docker Compose Services"
LiveKitContainer[LiveKit Server Container]
VoiceAgentContainer[Voice Agent Container]
SpeechServiceContainer[Speech Service Container]
BackendContainer[Backend API Container]
FrontendContainer[Frontend Container]
NginxContainer[Nginx Proxy Container]
PostgresContainer[PostgreSQL Database]
OllamaContainer[Ollama LLM Container]
end
subgraph "Network Configuration"
InternalNetwork[Internal Network]
ExternalNetwork[External Network]
end
LiveKitContainer --> InternalNetwork
VoiceAgentContainer --> InternalNetwork
SpeechServiceContainer --> InternalNetwork
BackendContainer --> InternalNetwork
FrontendContainer --> InternalNetwork
NginxContainer --> ExternalNetwork
PostgresContainer --> InternalNetwork
OllamaContainer --> InternalNetwork
LiveKitContainer --> VoiceAgentContainer
VoiceAgentContainer --> SpeechServiceContainer
VoiceAgentContainer --> BackendContainer
BackendContainer --> PostgresContainer
BackendContainer --> OllamaContainer
FrontendContainer --> BackendContainer
NginxContainer --> FrontendContainer
NginxContainer --> BackendContainer
```

**Diagram sources**
- [docker-compose.yml:114-175](file://docker-compose.yml#L114-L175)

### Service Dependencies

The deployment enforces strict dependency ordering to ensure reliable service startup:

| Service | Startup Order | Dependencies |
|---------|---------------|--------------|
| PostgreSQL | 1st | None |
| Ollama | 2nd | PostgreSQL |
| Backend | 3rd | PostgreSQL, Ollama |
| Nginx | 4th | Frontend, Backend |
| LiveKit | 5th | Backend |
| Speech Service | 6th | LiveKit |
| Voice Agent | 7th | LiveKit, Speech Service, Backend |

**Section sources**
- [docker-compose.yml:76-82](file://docker-compose.yml#L76-L82)
- [docker-compose.yml:168-175](file://docker-compose.yml#L168-L175)

### Health Monitoring

Each service implements comprehensive health checks for reliable operation:

```mermaid
flowchart TD
HealthCheck[Health Check] --> PostgresHealth[PostgreSQL Health]
HealthCheck --> OllamaHealth[Ollama Health]
HealthCheck --> LiveKitHealth[LiveKit Health]
HealthCheck --> BackendHealth[Backend Health]
PostgresHealth --> PostgresReady{PostgreSQL Ready?}
OllamaHealth --> OllamaReady{Ollama Ready?}
LiveKitHealth --> LiveKitReady{LiveKit Ready?}
BackendHealth --> BackendReady{Backend Ready?}
PostgresReady --> |Yes| ProceedStartup[Proceed with Startup]
PostgresReady --> |No| WaitRetry[Wait and Retry]
OllamaReady --> |Yes| ProceedStartup
OllamaReady --> |No| WaitRetry
LiveKitReady --> |Yes| ProceedStartup
LiveKitReady --> |No| WaitRetry
BackendReady --> |Yes| ProceedStartup
BackendReady --> |No| WaitRetry
```

**Diagram sources**
- [docker-compose.yml:18-22](file://docker-compose.yml#L18-L22)
- [docker-compose.yml:27-31](file://docker-compose.yml#L27-L31)
- [docker-compose.yml:130-135](file://docker-compose.yml#L130-L135)

**Section sources**
- [docker-compose.yml:18-22](file://docker-compose.yml#L18-L22)
- [docker-compose.yml:27-31](file://docker-compose.yml#L27-L31)
- [docker-compose.yml:130-135](file://docker-compose.yml#L130-L135)

### Port Configuration Details

**Updated** The deployment now uses optimized port ranges for improved operational efficiency and Portainer interface stability.

The LiveKit SIP service uses a reduced port range to minimize conflicts and improve management:

| Service | Port Mapping | Protocol | Purpose |
|---------|--------------|----------|---------|
| LiveKit Server | 7880:7880 | TCP | WebSocket signaling |
| LiveKit Server | 7881:7881 | TCP | ICE/TCP fallback |
| LiveKit Server | 7882:7882/udp | UDP | TURN server |
| LiveKit Server | 10000-10100:10000-10100/udp | UDP | Optimized RTP media |
| LiveKit SIP | 5060:5060 | TCP/UDP | SIP signaling |
| LiveKit SIP | 5060:5060/udp | UDP | SIP signaling |
| LiveKit SIP | 10000-10100:10000-10100/udp | UDP | SIP RTP media |

**Section sources**
- [docker-compose.staging.yml:183-225](file://docker-compose.staging.yml#L183-L225)

## Environment Variables

The system relies on comprehensive environment variable configuration for flexible deployment across different environments.

### LiveKit Configuration Variables

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `LIVEKIT_API_KEY` | `devkey` | LiveKit server API key |
| `LIVEKIT_API_SECRET` | `devsecret` | LiveKit server API secret |
| `LIVEKIT_URL` | `ws://livekit:7880` | LiveKit WebSocket URL |

### Voice Agent Configuration Variables

**Updated** Enhanced SIP configuration with termination address support and corrected service discovery URLs

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `SPEECH_SERVICE_URL` | `http://speech-service:8001` | Speech service endpoint |
| `OLLAMA_BASE_URL` | `https://ollama.com` | Ollama LLM service URL |
| `OLLAMA_API_KEY` | `` | Ollama API key |
| `OLLAMA_MODEL` | `gemma4:31b-cloud` | LLM model to use |
| `ARIA_BACKEND_URL` | `http://backend:8000` | Backend API endpoint |
| `SIP_TRUNK_ID` | `twilio-aria` | SIP trunk identifier |
| `SIP_OUTBOUND_NUMBER` | `+18722789563` | Twilio phone number |
| `SIP_TERMINATION_ADDRESS` | `aria-staging.pstn.twilio.com` | SIP termination endpoint address |
| `AGENT_PORT` | `8002` | Voice agent service port |

### Backend Integration Variables

**Updated** Corrected VOICE_AGENT_URL from container name to service name for improved DNS resolution and service discovery reliability

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `DATABASE_URL` | `postgresql://aria:aria_secret@postgres:5432/aria_db` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | `change-this-in-production-use-a-long-random-string` | JWT signing key |
| `ENVIRONMENT` | `development` | Application environment |
| `VOICE_AGENT_URL` | `http://voice-agent:8002` | Voice agent service URL (service name-based) |

**Section sources**
- [docker-compose.yml:60-82](file://docker-compose.yml#L60-L82)
- [docker-compose.yml:154-165](file://docker-compose.yml#L154-L165)
- [docker-compose.staging.yml:252-253](file://docker-compose.staging.yml#L252-L253)

## Configuration Best Practices

### Security Configuration

1. **API Key Management**: Replace default development keys with secure production credentials
2. **Network Security**: Configure firewall rules to restrict access to LiveKit ports
3. **TLS Configuration**: Enable HTTPS for all external communications
4. **Authentication**: Implement proper user authentication and authorization

### Performance Optimization

1. **Resource Allocation**: Ensure adequate CPU and memory resources for concurrent calls
2. **Network Bandwidth**: Configure appropriate bandwidth limits for audio streaming
3. **Caching Strategy**: Implement efficient caching for frequently accessed data
4. **Connection Pooling**: Optimize database and external service connections

### Monitoring and Logging

1. **Health Checks**: Implement comprehensive monitoring for all service components
2. **Logging Levels**: Configure appropriate log levels for different environments
3. **Metrics Collection**: Monitor key performance indicators and error rates
4. **Alerting**: Set up alerts for critical system failures

### Scalability Considerations

1. **Load Balancing**: Distribute traffic across multiple LiveKit instances
2. **Database Scaling**: Implement read replicas and connection pooling
3. **Auto-scaling**: Configure automatic scaling based on call volume
4. **CDN Integration**: Use content delivery networks for static assets

### SIP Configuration Best Practices

**New** Enhanced SIP configuration guidelines for improved reliability

1. **Termination Address Verification**: Ensure SIP termination addresses match provider configurations
2. **Fallback Configuration**: Maintain multiple trunk identification methods (address, name, ID)
3. **Number Normalization**: Implement phone number validation and normalization before call initiation
4. **Import Error Handling**: Verify LiveKit protocol module imports for Python SDK compatibility
5. **Port Range Optimization**: Use the optimized 101-port range (10000-10100) for improved operational efficiency
6. **Service Discovery**: Use service names (voice-agent) instead of container names for reliable DNS resolution

### Service Discovery Best Practices

**Updated** Service discovery best practices for improved reliability

1. **Service Name Usage**: Always use service names (voice-agent) rather than container names (staging-voice-agent) for inter-service communication
2. **DNS Resolution**: Docker Compose automatically resolves service names to internal network addresses
3. **Container Naming**: Container names can differ from service names but service names must remain consistent for network communication
4. **Network Isolation**: Services communicate through Docker networks using service names, not container names

## Troubleshooting Guide

### Common Issues and Solutions

#### LiveKit Connection Problems

**Symptoms**: Voice agent cannot connect to LiveKit server
**Causes**: 
- Incorrect LiveKit URL configuration
- Network connectivity issues
- Authentication failures

**Solutions**:
1. Verify LiveKit server is running and healthy
2. Check network connectivity between services
3. Validate API key and secret credentials
4. Review LiveKit server logs for errors

#### SIP Trunk Configuration Issues

**Symptoms**: Outbound calls fail or hang
**Causes**:
- Incorrect SIP trunk credentials
- Network routing problems
- Provider connectivity issues
- **Updated** Mismatched SIP termination address or port range configuration

**Solutions**:
1. Verify Twilio account credentials
2. Check SIP trunk provisioning status
3. Test network connectivity to Twilio endpoints
4. **New** Validate SIP termination address matches provider configuration
5. **New** Verify RTP port range (10000-10100) is properly mapped in Docker configuration
6. Review SIP trunk logs for authentication errors

#### Python SDK Import Errors

**New** Python SDK import error handling for LiveKit protocol modules

**Symptoms**: Import failures for `livekit.protocol.sip` modules
**Causes**:
- Missing or incompatible LiveKit Python SDK versions
- Module import path issues
- Dependency conflicts

**Solutions**:
1. Verify LiveKit SDK versions in requirements.txt meet minimum requirements
2. Check Python SDK compatibility with current LiveKit server version
3. Ensure proper import statements for protocol modules
4. Validate SDK installation and import paths

#### Phone Number Normalization Issues

**New** Phone number validation and normalization for telephony reliability

**Symptoms**: Call failures due to invalid phone numbers
**Causes**:
- Non-E.164 formatted phone numbers
- Invalid country codes
- Special characters in phone numbers

**Solutions**:
1. Validate phone numbers follow E.164 format (+1234567890)
2. Remove special characters and spaces
3. Ensure proper country code inclusion
4. Implement phone number validation before call initiation

#### Port Configuration Issues

**New** Troubleshooting guidance for the optimized port range

**Symptoms**: RTP media transmission failures or Portainer interface instability
**Causes**:
- Port range conflicts with other services
- Docker port mapping issues
- Firewall restrictions

**Solutions**:
1. Verify the optimized port range (10000-10100) is not conflicting with other applications
2. Check Docker port mappings in compose files match the expected range
3. Ensure firewall allows UDP traffic on the 10000-10100 range
4. Validate Portainer interface has proper access to the new port range
5. Review container logs for port binding errors

#### Call Scheduling Failures

**Symptoms**: Scheduled calls not initiating
**Causes**:
- Backend service downtime
- Database connectivity issues
- APScheduler misconfiguration

**Solutions**:
1. Check backend service health status
2. Verify database connectivity
3. Review APScheduler job configuration
4. Examine call scheduling logs

#### Service Discovery Issues

**Updated** Service discovery troubleshooting for corrected VOICE_AGENT_URL configuration

**Symptoms**: Backend cannot reach voice agent service
**Causes**:
- Incorrect VOICE_AGENT_URL configuration
- DNS resolution failures between services
- Container name vs service name confusion

**Solutions**:
1. Verify VOICE_AGENT_URL uses service name (voice-agent) not container name (staging-voice-agent)
2. Check Docker network connectivity between backend and voice-agent services
3. Validate service name resolution in Docker Compose network
4. Review service discovery logs for DNS resolution errors
5. Ensure service name consistency across all environment files

### Diagnostic Commands

```bash
# Check LiveKit server status
docker compose ps livekit

# View LiveKit logs
docker compose logs livekit

# Verify database connectivity
docker compose exec postgres psql -U aria -c "SELECT 1;"

# Test speech service availability
curl http://localhost:8001/health

# Check voice agent status
docker compose ps voice-agent

# Verify SIP termination address configuration
echo $SIP_TERMINATION_ADDRESS

# Check port range configuration
docker compose config | grep -A 10 -B 5 "10000-10100"

# Verify service discovery resolution
docker compose exec backend nslookup voice-agent

# Check VOICE_AGENT_URL configuration
echo $VOICE_AGENT_URL
```

**Section sources**
- [docker-compose.yml:130-135](file://docker-compose.yml#L130-L135)
- [agent.py:149-152](file://app/voice_agent/agent.py#L149-L152)

## Conclusion

The LiveKit SIP Service Configuration provides a robust foundation for implementing automated voice screening capabilities. The system's modular architecture, comprehensive configuration options, and production-ready deployment patterns enable organizations to deliver scalable, reliable voice communication solutions.

**Updated** Recent enhancements include the optimized RTP port range from 201 ports (50000-50200) to 101 ports (10000-10100), which significantly improves operational efficiency and Portainer interface stability. These optimizations, combined with enhanced SIP termination address configuration, improved trunk resolution logic, Python SDK import error handling, and phone number normalization considerations, provide substantial improvements to telephony reliability and proper SIP termination addressing.

**Updated** The most significant improvement relates to the corrected VOICE_AGENT_URL environment variable configuration. The system now properly uses the service name 'voice-agent' instead of the container name 'staging-voice-agent' for improved DNS resolution and service discovery reliability. This change ensures consistent service communication regardless of container naming conventions and provides better isolation between development and production environments.

Key strengths of the configuration include:

- **Enhanced SIP Integration**: Programmatic trunk management with termination address matching supports multiple telephony providers
- **Improved Reliability**: Multiple fallback mechanisms for SIP trunk identification and Python SDK compatibility
- **Optimized Port Management**: Reduced port range (10000-10100) minimizes conflicts and improves operational efficiency
- **AI-Powered Conversations**: Seamless integration with LLM services for intelligent dialogue
- **Production-Ready Deployment**: Comprehensive Docker orchestration with health monitoring
- **Scalable Architecture**: Designed to handle varying call volumes and concurrent sessions
- **Reliable Service Discovery**: Proper service naming conventions ensure consistent inter-service communication

The configuration serves as a solid foundation for organizations seeking to implement automated voice screening while maintaining flexibility for customization and extension based on specific requirements.