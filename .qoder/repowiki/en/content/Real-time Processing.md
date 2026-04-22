# Real-time Processing

<cite>
**Referenced Files in This Document**
- [analyze.py](file://app/backend/routes/analyze.py)
- [admin.py](file://app/backend/routes/admin.py)
- [webhook_service.py](file://app/backend/services/webhook_service.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [013_webhooks_and_notifications.py](file://alembic/versions/013_webhooks_and_notifications.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [llm_service.py](file://app/backend/services/llm_service.py)
- [agent_pipeline.py](file://app/backend/services/agent_pipeline.py)
- [api.js](file://app/frontend/src/lib/api.js)
- [Dashboard.jsx](file://app/frontend/src/pages/Dashboard.jsx)
- [ReportPage.jsx](file://app/frontend/src/pages/ReportPage.jsx)
- [ResultCard.jsx](file://app/frontend/src/components/ResultCard.jsx)
- [Timeline.jsx](file://app/frontend/src/components/Timeline.jsx)
- [nginx.prod.conf](file://nginx/nginx.prod.conf)
- [main.py](file://app/backend/main.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced real-time processing with comprehensive webhook system for event-driven integrations
- Added webhook configuration management with admin endpoints for tenant-level webhook setup
- Implemented event delivery tracking with retry mechanisms and comprehensive logging
- Integrated webhook dispatch into analysis completion flow with non-blocking error handling
- Added webhook delivery history tracking and monitoring capabilities

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Enhanced SSE Streaming Data Handling](#enhanced-sse-streaming-data-handling)
7. [Type-Safe String Conversion Utilities](#type-safe-string-conversion-utilities)
8. [Enhanced LLM Error Handling](#enhanced-llm-error-handling)
9. [Webhook System Integration](#webhook-system-integration)
10. [Webhook Configuration Management](#webhook-configuration-management)
11. [Event Delivery Tracking and Retry Logic](#event-delivery-tracking-and-retry-logic)
12. [Concurrency Control and Rate Limiting](#concurrency-control-and-rate-limiting)
13. [Batch Analysis Streaming](#batch-analysis-streaming)
14. [Dependency Analysis](#dependency-analysis)
15. [Performance Considerations](#performance-considerations)
16. [Troubleshooting Guide](#troubleshooting-guide)
17. [Conclusion](#conclusion)

## Introduction
This document explains the real-time processing implementation for Resume AI by ThetaLogics using Server-Sent Events (SSE). It covers the streaming API design, event lifecycle, client-side consumption, progress indicators, error handling, and operational considerations for reliable long-running analysis. The system now features enhanced SSE streaming data handling with robust string coercion mechanisms for server-side events, safeStr utility function implementations across frontend components to handle type-safe string conversion for dynamic data streams, and a comprehensive webhook system for event-driven integrations with automatic retry mechanisms and delivery tracking.

## Project Structure
The real-time pipeline spans backend FastAPI routes, streaming generators, webhook services, and frontend consumers:
- Backend: FastAPI route emits Server-Sent Events for live updates with enhanced error handling
- Streaming generator: Produces structured events for parsing, scoring, and completion with retry logic
- Webhook service: Handles event-driven integrations with HMAC signing, retry mechanisms, and delivery tracking
- Frontend: Reads SSE stream, updates UI progressively, and navigates to the final report
- Type-safe utilities: safeStr function provides robust string coercion for dynamic data streams
- Batch processing: Concurrent batch analysis with individual result streaming

```mermaid
graph TB
subgraph "Backend"
R["FastAPI Route<br/>/api/analyze/stream"]
GS["Batch Streaming Route<br/>/api/analyze/batch-stream"]
G["Streaming Generator<br/>astream_hybrid_pipeline()"]
S["Services<br/>hybrid_pipeline.py / agent_pipeline.py"]
LS["LLM Service<br/>with exponential backoff"]
SEM["Semaphore<br/>Concurrency Control"]
WS["Webhook Service<br/>dispatch_event_background()"]
W["Webhook Model<br/>Webhook / WebhookDelivery"]
END["JSON Serialization<br/>with _json_default"]
END2["Batch Streaming<br/>JSON Serialization"]
end
subgraph "Frontend"
U["UploadForm.jsx"]
D["Dashboard.jsx"]
RP["ReportPage.jsx"]
API["api.js<br/>analyzeResumeStream()"]
BATCH["Batch Streaming<br/>analyzeBatchStream()"]
SAFE["safeStr Utility<br/>Type-safe String Conversion"]
RC["ResultCard.jsx<br/>safeStr Usage"]
TL["Timeline.jsx<br/>safeStr Usage"]
end
N["Nginx<br/>proxy_buffering off"]
U --> D
D --> API
API --> R
GS --> BATCH
R --> G
G --> S
S --> LS
LS --> SEM
S --> WS
WS --> W
G --> END
END --> API
API --> SAFE
SAFE --> RC
SAFE --> TL
API --> RP
R -. "proxy_buffering off" .-> N
```

**Diagram sources**
- [analyze.py:506-646](file://app/backend/routes/analyze.py#L506-L646)
- [analyze.py:1291-1509](file://app/backend/routes/analyze.py#L1291-L1509)
- [webhook_service.py:46-138](file://app/backend/services/webhook_service.py#L46-L138)
- [db_models.py:331-364](file://app/backend/models/db_models.py#L331-L364)
- [hybrid_pipeline.py:1369-1568](file://app/backend/services/hybrid_pipeline.py#L1369-L1568)
- [llm_service.py:41-65](file://app/backend/services/llm_service.py#L41-L65)
- [api.js:210-318](file://app/frontend/src/lib/api.js#L210-L318)
- [api.js:413-515](file://app/frontend/src/lib/api.js#L413-L515)
- [ResultCard.jsx:13-19](file://app/frontend/src/components/ResultCard.jsx#L13-L19)
- [Timeline.jsx:3-9](file://app/frontend/src/components/Timeline.jsx#L3-L9)
- [Dashboard.jsx:243-275](file://app/frontend/src/pages/Dashboard.jsx#L243-L275)
- [ReportPage.jsx:82-120](file://app/frontend/src/pages/ReportPage.jsx#L82-L120)
- [nginx.prod.conf:66-95](file://nginx/nginx.prod.conf#L66-L95)

**Section sources**
- [analyze.py:506-646](file://app/backend/routes/analyze.py#L506-L646)
- [analyze.py:1291-1509](file://app/backend/routes/analyze.py#L1291-L1509)
- [webhook_service.py:46-138](file://app/backend/services/webhook_service.py#L46-L138)
- [db_models.py:331-364](file://app/backend/models/db_models.py#L331-L364)
- [hybrid_pipeline.py:1369-1568](file://app/backend/services/hybrid_pipeline.py#L1369-L1568)
- [llm_service.py:41-65](file://app/backend/services/llm_service.py#L41-L65)
- [api.js:210-318](file://app/frontend/src/lib/api.js#L210-L318)
- [api.js:413-515](file://app/frontend/src/lib/api.js#L413-L515)
- [ResultCard.jsx:13-19](file://app/frontend/src/components/ResultCard.jsx#L13-L19)
- [Timeline.jsx:3-9](file://app/frontend/src/components/Timeline.jsx#L3-L9)
- [Dashboard.jsx:243-275](file://app/frontend/src/pages/Dashboard.jsx#L243-L275)
- [ReportPage.jsx:82-120](file://app/frontend/src/pages/ReportPage.jsx#L82-L120)
- [nginx.prod.conf:66-95](file://nginx/nginx.prod.conf#L66-L95)

## Core Components
- **Streaming route**: Implements SSE with structured events for parsing, scoring, and completion with enhanced error handling
- **Streaming generator**: Emits events with stage markers and payloads; includes heartbeat pings to keep connections alive
- **Enhanced LLM service**: Features exponential backoff retry logic for rate limiting (429 errors) and improved error handling
- **Webhook service**: Provides event-driven integrations with HMAC signing, retry mechanisms, and comprehensive delivery tracking
- **Webhook configuration**: Admin endpoints for tenant-level webhook management with event filtering and status monitoring
- **Type-safe string conversion**: safeStr utility function provides robust string coercion for dynamic data streams
- **Concurrency control**: Semaphore-based system to prevent thundering herd effects and manage LLM resource limits
- **Frontend consumer**: Parses SSE stream, updates UI progressively, and handles completion with retry mechanisms
- **Infrastructure**: Nginx configured to disable buffering for SSE endpoints

Key event structure emitted by the backend:
- Stage "parsing": Early Python-only scores
- Stage "scoring": LLM narrative and interview kit with retry logic
- Stage "complete": Final merged result with analysis_id for polling
- Heartbeat comments ": ping" to maintain connection
- Batch events: "result", "failed", and "done" for concurrent processing
- Webhook events: "analysis.completed" dispatched after analysis completion
- JSON serialization with _json_default for type-safe encoding

**Section sources**
- [analyze.py:506-646](file://app/backend/routes/analyze.py#L506-L646)
- [analyze.py:1291-1509](file://app/backend/routes/analyze.py#L1291-L1509)
- [webhook_service.py:46-138](file://app/backend/services/webhook_service.py#L46-L138)
- [hybrid_pipeline.py:1369-1568](file://app/backend/services/hybrid_pipeline.py#L1369-L1568)
- [llm_service.py:41-65](file://app/backend/services/llm_service.py#L41-L65)
- [api.js:210-318](file://app/frontend/src/lib/api.js#L210-L318)
- [ResultCard.jsx:13-19](file://app/frontend/src/components/ResultCard.jsx#L13-L19)
- [Timeline.jsx:3-9](file://app/frontend/src/components/Timeline.jsx#L3-L9)

## Architecture Overview
The streaming architecture ensures the client receives incremental updates while the backend performs long-running analysis. The generator yields structured events that the route wraps into SSE messages. The frontend consumes these events to render progress and final results. Enhanced error handling provides resilience against rate limiting and service interruptions, while type-safe string conversion ensures robust rendering of dynamic data streams. The webhook system provides event-driven integrations that complement the real-time streaming by delivering analysis completion notifications to external systems with reliable delivery guarantees.

```mermaid
sequenceDiagram
participant Client as "Browser"
participant API as "Frontend API<br/>api.js"
participant Route as "FastAPI Route<br/>/api/analyze/stream"
participant Gen as "Streaming Generator<br/>astream_hybrid_pipeline()"
participant LLM as "LLM Service<br/>Exponential Backoff"
participant Sem as "Semaphore<br/>Rate Limiting"
participant WS as "Webhook Service<br/>dispatch_event_background()"
participant DB as "Database<br/>Webhook Models"
participant Safe as "safeStr Utility<br/>Type Conversion"
Client->>API : "analyzeResumeStream(file, jd, weights)"
API->>Route : "POST /api/analyze/stream"
Route->>Gen : "Start streaming generator"
Gen->>Sem : "Acquire semaphore"
Sem-->>Gen : "Allow LLM call"
Gen->>LLM : "Call with retry logic"
LLM-->>Gen : "Success or 429 error"
alt Rate Limited (429)
Gen->>Gen : "Exponential backoff retry"
end
Gen->>Sem : "Release semaphore"
Gen-->>Route : "Event {stage : 'parsing'|'scoring'|'complete', result : ...}"
Route-->>API : "SSE data : {stage : 'parsing'|'scoring'|'complete', result : ...}"
Route->>WS : "dispatch_event_background() after completion"
WS->>DB : "Store webhook configuration"
WS->>DB : "Track delivery attempts"
API->>Safe : "safeStr(value) for rendering"
Safe-->>API : "Type-safe string"
API->>Client : "Update UI with parsing scores"
```

**Diagram sources**
- [analyze.py:506-646](file://app/backend/routes/analyze.py#L506-L646)
- [analyze.py:795-801](file://app/backend/routes/analyze.py#L795-L801)
- [analyze.py:1069-1075](file://app/backend/routes/analyze.py#L1069-L1075)
- [webhook_service.py:114-138](file://app/backend/services/webhook_service.py#L114-L138)
- [db_models.py:331-364](file://app/backend/models/db_models.py#L331-L364)
- [hybrid_pipeline.py:1369-1568](file://app/backend/services/hybrid_pipeline.py#L1369-L1568)
- [llm_service.py:41-65](file://app/backend/services/llm_service.py#L41-L65)
- [api.js:210-318](file://app/frontend/src/lib/api.js#L210-L318)
- [Dashboard.jsx:243-275](file://app/frontend/src/pages/Dashboard.jsx#L243-L275)
- [ReportPage.jsx:82-120](file://app/frontend/src/pages/ReportPage.jsx#L82-L120)
- [ResultCard.jsx:13-19](file://app/frontend/src/components/ResultCard.jsx#L13-L19)

## Detailed Component Analysis

### Backend Streaming Route
- Validates inputs and parses resume and job description
- Starts a streaming generator that yields structured events
- Emits heartbeat comments to keep the connection alive
- Persists results to the database upon completion
- Sets appropriate SSE headers and disables buffering
- Handles client disconnection with early result saving
- Uses _json_default for type-safe JSON serialization
- **Updated**: Integrates webhook dispatch after analysis completion with non-blocking error handling

```mermaid
flowchart TD
Start(["POST /api/analyze/stream"]) --> Validate["Validate inputs<br/>files, sizes, JD length"]
Validate --> Parse["Parse resume + JD in thread pool"]
Parse --> Stream["Start event_stream() generator"]
Stream --> YieldParsing["Yield {stage: 'parsing'}"]
YieldParsing --> YieldScoring["Yield {stage: 'scoring'}"]
YieldScoring --> YieldComplete["Yield {stage: 'complete'}"]
YieldComplete --> Persist["Persist to DB"]
Persist --> Webhook["dispatch_event_background()<br/>analysis.completed"]
Webhook --> Done(["Return [DONE]"])
```

**Diagram sources**
- [analyze.py:506-646](file://app/backend/routes/analyze.py#L506-L646)
- [analyze.py:795-801](file://app/backend/routes/analyze.py#L795-L801)

**Section sources**
- [analyze.py:506-646](file://app/backend/routes/analyze.py#L506-L646)
- [analyze.py:795-801](file://app/backend/routes/analyze.py#L795-L801)

### Streaming Generator (Python + LLM with Enhanced Error Handling)
- Runs Python phase to compute early scores
- Emits parsing stage with Python-only results
- Executes LLM phase with heartbeat pings and exponential backoff retry logic
- Handles 429 rate limit errors with progressive delays
- Emits scoring stage with LLM narrative
- Merges results and emits complete stage

```mermaid
flowchart TD
A["Start generator"] --> B["Run Python phase"]
B --> C["Yield {stage: 'parsing', result: python}"]
C --> D["Start LLM task with semaphore"]
D --> E{"LLM Response"}
E --> |Success| F["Receive LLM result"]
E --> |429 Error| G["Exponential backoff retry<br/>delay = base * 2^attempt + random"]
G --> D
E --> |Other Error| H["Raise error with details"]
F --> I["Yield {stage: 'scoring', result: llm}"]
I --> J["Merge Python + LLM results"]
J --> K["Yield {stage: 'complete', result: final}"]
```

**Diagram sources**
- [hybrid_pipeline.py:1369-1568](file://app/backend/services/hybrid_pipeline.py#L1369-L1568)

**Section sources**
- [hybrid_pipeline.py:1369-1568](file://app/backend/services/hybrid_pipeline.py#L1369-L1568)

### Frontend Consumer and Progress UI
- Initiates streaming analysis and reads SSE events
- Updates progress UI based on received stage markers
- Navigates to the report page when complete
- Handles connection errors and displays user-friendly messages
- Supports batch streaming with individual file progress tracking
- Applies safeStr utility for type-safe string conversion

```mermaid
sequenceDiagram
participant User as "User"
participant UI as "Dashboard.jsx"
participant API as "api.js"
participant SSE as "SSE Stream"
User->>UI : "Click Analyze"
UI->>API : "analyzeResumeStream(file, jd, weights, onStageComplete)"
API->>SSE : "fetch('/api/analyze/stream')"
loop "Read stream"
SSE-->>API : "data : {stage : 'parsing'|'scoring'|'complete', result : ...}"
API->>API : "safeStr(value) for type safety"
API->>UI : "onStageComplete(event)"
UI->>UI : "Update progress UI"
end
API-->>UI : "Final result"
UI->>UI : "Navigate to ReportPage"
```

**Diagram sources**
- [Dashboard.jsx:243-275](file://app/frontend/src/pages/Dashboard.jsx#L243-L275)
- [api.js:210-318](file://app/frontend/src/lib/api.js#L210-L318)

**Section sources**
- [Dashboard.jsx:243-275](file://app/frontend/src/pages/Dashboard.jsx#L243-L275)
- [api.js:210-318](file://app/frontend/src/lib/api.js#L210-L318)

### Infrastructure: Nginx SSE Configuration
- Disables proxy buffering for the streaming endpoint to forward events immediately
- Sets headers to prevent intermediate caching or compression of the stream
- Configures extended timeouts for long-running LLM operations

```mermaid
flowchart TD
Client["Client"] --> Nginx["Nginx"]
Nginx --> Upstream["FastAPI Backend"]
Upstream --> SSE["/api/analyze/stream SSE"]
SSE --> Client
Nginx-- "proxy_buffering off" --> SSE
Nginx-- "X-Accel-Buffering no" --> SSE
Nginx-- "chunked_transfer_encoding on" --> SSE
Nginx-- "gzip off" --> SSE
```

**Diagram sources**
- [nginx.prod.conf:66-95](file://nginx/nginx.prod.conf#L66-L95)

**Section sources**
- [nginx.prod.conf:66-95](file://nginx/nginx.prod.conf#L66-L95)

## Enhanced SSE Streaming Data Handling
The system now implements robust string coercion mechanisms for server-side events to ensure type-safe data transmission:

### Type-Safe JSON Serialization
- Backend uses _json_default function for custom JSON serialization
- Handles complex data types including datetime objects, UUIDs, and numpy arrays
- Ensures consistent serialization across different event types
- Prevents JSON parsing errors in the frontend

### Frontend Type Safety Enhancements
- safeStr utility function provides robust string coercion
- Handles null/undefined values by converting to empty strings
- Converts primitive types (number, boolean) to strings safely
- Uses JSON.stringify as fallback with error handling
- Applied consistently across all result rendering components

### Event Stream Robustness
- Enhanced error handling for malformed SSE events
- Graceful degradation when type conversion fails
- Logging of conversion errors for debugging
- Prevention of UI crashes from unexpected data types

**Section sources**
- [analyze.py:506-646](file://app/backend/routes/analyze.py#L506-L646)
- [api.js:210-318](file://app/frontend/src/lib/api.js#L210-L318)
- [ResultCard.jsx:13-19](file://app/frontend/src/components/ResultCard.jsx#L13-L19)
- [Timeline.jsx:3-9](file://app/frontend/src/components/Timeline.jsx#L3-L9)

## Type-Safe String Conversion Utilities
The safeStr utility function provides comprehensive type-safe string conversion for dynamic data streams:

### Implementation Details
- Null/undefined values: Returns empty string ('')
- String values: Returned unchanged
- Number/boolean values: Converted using String() constructor
- Object/array values: Attempt JSON.stringify(), fallback to String()
- Error handling: Try-catch prevents crashes, falls back to String()

### Frontend Component Integration
- ResultCard.jsx: Used extensively for rendering analysis results
- Timeline.jsx: Applied for job title and company name rendering
- Interview questions: Safe conversion for dynamic question content
- Risk flags and recommendations: Type-safe display of dynamic content
- Skill lists and education analysis: Robust rendering of mixed data types

### Benefits
- Prevents UI crashes from unexpected data types
- Ensures consistent string representation across components
- Handles edge cases in dynamic data streams gracefully
- Improves user experience by avoiding broken displays

**Section sources**
- [ResultCard.jsx:13-19](file://app/frontend/src/components/ResultCard.jsx#L13-L19)
- [Timeline.jsx:3-9](file://app/frontend/src/components/Timeline.jsx#L3-L9)
- [api.js:210-318](file://app/frontend/src/lib/api.js#L210-L318)

## Enhanced LLM Error Handling
The system now implements comprehensive error handling for LLM operations with exponential backoff retry logic:

### Rate Limiting (429 Errors)
- Detects HTTP 429 rate limit responses from LLM service
- Implements exponential backoff with jitter: `delay = base_delay * (2^attempt) + random.uniform(0, 1.0)`
- Maximum 3 retry attempts for rate-limited requests
- Logs detailed retry information with attempt numbers and delays

### Authentication and Network Errors
- Handles HTTP 401 authentication failures with specific error messages
- Manages HTTP 5xx server errors with retry logic
- Catches connection errors and timeout exceptions
- Wraps langchain ResponseError instances that contain 429 status codes

### Fallback Mechanisms
- Provides deterministic fallback narratives when LLM is unavailable
- Retries with higher temperature settings for edge cases
- Validates JSON extraction and handles malformed responses

**Section sources**
- [hybrid_pipeline.py:1369-1568](file://app/backend/services/hybrid_pipeline.py#L1369-L1568)

## Webhook System Integration
The system now provides comprehensive webhook integration for event-driven notifications:

### Webhook Dispatch Architecture
- **Non-blocking design**: Webhook dispatch uses `dispatch_event_background()` to prevent blocking the main analysis flow
- **Automatic error handling**: Webhook failures are caught and logged without affecting analysis completion
- **Tenant-scoped events**: Each webhook is associated with a specific tenant for proper isolation
- **Event filtering**: Webhooks can subscribe to specific events or use wildcard (*) for all events

### Analysis Completion Integration
- **Single analysis**: After `/api/analyze` completion, webhook is dispatched with `analysis.completed` event
- **Streaming analysis**: After `/api/analyze/stream` completion, webhook is dispatched with `analysis.completed` event
- **Payload structure**: Includes `result_id` for external systems to fetch analysis details
- **Retry mechanism**: Background dispatch handles retry logic without user intervention

### Security and Reliability
- **HMAC-SHA256 signing**: All webhook payloads are signed with configurable secrets
- **Signature verification**: External systems can verify payload authenticity using the provided signature
- **Delivery tracking**: Comprehensive logging of all delivery attempts with status and response details
- **Auto-disable**: Webhooks are automatically disabled after excessive consecutive failures

**Section sources**
- [analyze.py:795-801](file://app/backend/routes/analyze.py#L795-L801)
- [analyze.py:1069-1075](file://app/backend/routes/analyze.py#L1069-L1075)
- [webhook_service.py:46-138](file://app/backend/services/webhook_service.py#L46-L138)

## Webhook Configuration Management
The system provides comprehensive webhook administration through dedicated endpoints:

### Database Schema
- **Webhook table**: Stores tenant webhook configurations with URL, secret, and event subscriptions
- **WebhookDelivery table**: Tracks all delivery attempts with timestamps, status, and response details
- **Index optimization**: Proper indexing for tenant queries and delivery history retrieval

### Admin Endpoints
- **Create webhook**: POST `/api/admin/tenants/{tenant_id}/webhooks` - Configure new webhook with URL, secret, and event filters
- **List webhooks**: GET `/api/admin/tenants/{tenant_id}/webhooks` - View all tenant webhooks with status and metrics
- **Delete webhook**: DELETE `/api/admin/tenants/{tenant_id}/webhooks/{webhook_id}` - Remove webhook configuration
- **List deliveries**: GET `/api/admin/tenants/{tenant_id}/webhooks/{webhook_id}/deliveries` - View delivery history with pagination

### Event Subscription Management
- **Wildcard support**: Use `"*"` to subscribe to all events
- **Selective filtering**: Specify exact event names like `"analysis.completed"`
- **JSON serialization**: Events stored as JSON arrays for flexible subscription management
- **Status monitoring**: Track failure counts, last triggered/failed timestamps for operational visibility

### Security Features
- **Secret management**: Automatic secret generation when not provided
- **Audit logging**: All webhook operations are logged for security and compliance
- **Platform admin only**: Only platform administrators can manage webhook configurations
- **Tenant isolation**: Webhook configurations are properly scoped to tenant boundaries

**Section sources**
- [db_models.py:331-364](file://app/backend/models/db_models.py#L331-L364)
- [013_webhooks_and_notifications.py:36-88](file://alembic/versions/013_webhooks_and_notifications.py#L36-L88)
- [admin.py:820-926](file://app/backend/routes/admin.py#L820-L926)

## Event Delivery Tracking and Retry Logic
The webhook system implements sophisticated delivery tracking with comprehensive retry mechanisms:

### Retry Strategy
- **Three-tier retry**: Attempts after 1s, 5s, and 30s delays for exponential backoff
- **Attempt tracking**: Each delivery attempt is recorded with attempt number and timestamp
- **Success/failure differentiation**: Clear distinction between successful deliveries and failures
- **Auto-disable threshold**: Webhooks disabled after 10 consecutive failures to prevent spam

### Delivery History
- **Comprehensive logging**: All delivery attempts captured with payload, response status, and body
- **Status tracking**: Real-time monitoring of webhook activity through failure counts and timestamps
- **Pagination support**: Delivery history retrieval with configurable limits for performance
- **Audit trail**: Complete history for troubleshooting and compliance purposes

### Payload Security
- **HMAC-SHA256 signatures**: All payloads signed with tenant-specific secrets
- **Header inclusion**: Signature included in `X-Webhook-Signature` header for easy verification
- **Timestamp embedding**: Each payload includes UTC timestamp for freshness verification
- **Content-type specification**: Application/json with proper content-type headers

### Monitoring and Metrics
- **Failure count tracking**: Automatic increment on delivery failures with reset on success
- **Last triggered/failed timestamps**: Real-time status indicators for webhook health
- **Success rate calculation**: Historical data enables performance monitoring and alerting
- **Auto-healing capability**: System automatically recovers from transient failures

**Section sources**
- [webhook_service.py:13-15](file://app/backend/services/webhook_service.py#L13-L15)
- [webhook_service.py:18-44](file://app/backend/services/webhook_service.py#L18-L44)
- [webhook_service.py:79-111](file://app/backend/services/webhook_service.py#L79-L111)
- [test_webhooks.py:117-177](file://app/backend/tests/test_webhooks.py#L117-L177)

## Concurrency Control and Rate Limiting
The system implements sophisticated concurrency control to prevent thundering herd effects:

### Semaphore-Based Architecture
- Global semaphore controls concurrent LLM requests
- Auto-detection of Ollama Cloud vs local instance
- Cloud instances: default concurrency of 4 (conservative to avoid 429 rate limits)
- Local instances: default concurrency of 1 (single-threaded support)
- Environment variable override: `OLLAMA_MAX_CONCURRENT`

### Throttling Strategies
- Prevents overwhelming external LLM APIs during peak usage
- Reduces risk of rate limiting and service degradation
- Balances throughput with resource constraints
- Protects against thundering herd effects in distributed environments

### Health Monitoring
- Ollama health sentinel monitors model availability
- Automatic warmup for local Ollama instances
- Cloud instances skip health checks (no warmup required)
- Proactive detection of service issues

**Section sources**
- [llm_service.py:41-65](file://app/backend/services/llm_service.py#L41-L65)

## Batch Analysis Streaming
The system now supports concurrent batch analysis with progressive streaming:

### Concurrent Processing
- Processes multiple resumes simultaneously using asyncio
- Streams individual results as soon as they complete
- Maintains progress tracking for each file independently
- Handles pre-flight validation failures separately

### Event Stream Format
- "result" events: `{event: "result", index, total, filename, result, screening_result_id}`
- "failed" events: `{event: "failed", index, total, filename?, error}`
- "done" events: `{event: "done", total, successful, failed_count}`

### Usage Limits and Validation
- Enforces tenant plan limits for batch operations
- Validates batch size against subscription plan restrictions
- Atomic usage increment prevents race conditions
- Supports chunked upload processing for large files

**Section sources**
- [analyze.py:1291-1509](file://app/backend/routes/analyze.py#L1291-L1509)

## Dependency Analysis
- Route depends on streaming generator and database persistence
- Generator depends on analysis services for Python and LLM phases
- Enhanced LLM service includes exponential backoff and semaphore management
- **Updated**: Webhook service provides event-driven integrations with database-backed configuration
- **Updated**: Admin routes manage webhook configurations with tenant isolation
- Frontend depends on route for SSE and on UI components for rendering
- Infrastructure depends on route for SSE-specific configuration
- safeStr utility provides type-safe string conversion across frontend components

```mermaid
graph LR
Route["routes/analyze.py"] --> Gen["services/hybrid_pipeline.py"]
Gen --> Services["services/agent_pipeline.py"]
Gen --> LLM["services/llm_service.py<br/>Enhanced with backoff"]
Route --> WS["services/webhook_service.py<br/>Enhanced with webhook dispatch"]
WS --> DB["models/db_models.py<br/>Webhook + WebhookDelivery"]
API["frontend/src/lib/api.js"] --> Route
UI["frontend/src/pages/Dashboard.jsx"] --> API
UI --> Report["frontend/src/pages/ReportPage.jsx"]
Safe["frontend/src/components/ResultCard.jsx<br/>safeStr()"] --> UI
Safe2["frontend/src/components/Timeline.jsx<br/>safeStr()"] --> UI
Nginx["nginx/nginx.prod.conf"] --> Route
Batch["Batch Streaming"] --> Route
Admin["routes/admin.py<br/>Webhook Admin"] --> DB
```

**Diagram sources**
- [analyze.py:506-646](file://app/backend/routes/analyze.py#L506-L646)
- [analyze.py:1291-1509](file://app/backend/routes/analyze.py#L1291-L1509)
- [webhook_service.py:46-138](file://app/backend/services/webhook_service.py#L46-L138)
- [db_models.py:331-364](file://app/backend/models/db_models.py#L331-L364)
- [admin.py:820-926](file://app/backend/routes/admin.py#L820-L926)
- [hybrid_pipeline.py:1369-1568](file://app/backend/services/hybrid_pipeline.py#L1369-L1568)
- [llm_service.py:41-65](file://app/backend/services/llm_service.py#L41-L65)
- [agent_pipeline.py:520-540](file://app/backend/services/agent_pipeline.py#L520-L540)
- [api.js:210-318](file://app/frontend/src/lib/api.js#L210-L318)
- [Dashboard.jsx:243-275](file://app/frontend/src/pages/Dashboard.jsx#L243-L275)
- [ReportPage.jsx:82-120](file://app/frontend/src/pages/ReportPage.jsx#L82-L120)
- [ResultCard.jsx:13-19](file://app/frontend/src/components/ResultCard.jsx#L13-L19)
- [Timeline.jsx:3-9](file://app/frontend/src/components/Timeline.jsx#L3-L9)
- [nginx.prod.conf:66-95](file://nginx/nginx.prod.conf#L66-L95)

**Section sources**
- [analyze.py:506-646](file://app/backend/routes/analyze.py#L506-L646)
- [analyze.py:1291-1509](file://app/backend/routes/analyze.py#L1291-L1509)
- [webhook_service.py:46-138](file://app/backend/services/webhook_service.py#L46-L138)
- [db_models.py:331-364](file://app/backend/models/db_models.py#L331-L364)
- [admin.py:820-926](file://app/backend/routes/admin.py#L820-L926)
- [hybrid_pipeline.py:1369-1568](file://app/backend/services/hybrid_pipeline.py#L1369-L1568)
- [llm_service.py:41-65](file://app/backend/services/llm_service.py#L41-L65)
- [agent_pipeline.py:520-540](file://app/backend/services/agent_pipeline.py#L520-L540)
- [api.js:210-318](file://app/frontend/src/lib/api.js#L210-L318)
- [Dashboard.jsx:243-275](file://app/frontend/src/pages/Dashboard.jsx#L243-L275)
- [ReportPage.jsx:82-120](file://app/frontend/src/pages/ReportPage.jsx#L82-L120)
- [ResultCard.jsx:13-19](file://app/frontend/src/components/ResultCard.jsx#L13-L19)
- [Timeline.jsx:3-9](file://app/frontend/src/components/Timeline.jsx#L3-L9)
- [nginx.prod.conf:66-95](file://nginx/nginx.prod.conf#L66-L95)

## Performance Considerations
- **Enhanced Concurrency Control**: LLM calls are limited by a semaphore to avoid overwhelming the inference backend
- **Exponential Backoff**: Rate limiting (429 errors) handled with progressive delays to prevent service saturation
- **Heartbeat Pings**: Prevent upstream proxies from closing idle connections during long waits
- **Buffering**: Disabled for SSE to ensure immediate event delivery
- **Timeouts**: LLM tasks enforce timeouts to bound latency and resource usage
- **Resource Management**: Thread pool used for parsing to avoid blocking the event loop
- **Batch Processing**: Concurrent processing with individual result streaming for improved throughput
- **Early Result Saving**: Client disconnections trigger early database persistence of Python results
- **Type Conversion Optimization**: safeStr utility reduces rendering overhead through efficient type checking
- **Memory Management**: Frontend components minimize unnecessary re-renders through type-safe data handling
- **Webhook Performance**: Background dispatch prevents webhook failures from impacting analysis performance
- **Database Optimization**: Proper indexing on webhook tables ensures efficient configuration and delivery queries

Recommendations:
- Monitor LLM semaphore usage and adjust concurrency based on hardware capacity
- Tune proxy timeouts and keep-alive settings to match expected analysis durations
- Consider rate limiting for SSE endpoints to protect backend resources
- Implement circuit breaker patterns for external LLM services
- Monitor exponential backoff effectiveness and adjust base delays
- Optimize safeStr usage patterns to minimize repeated conversions
- Monitor webhook delivery success rates and adjust retry thresholds as needed
- Consider webhook payload size limits to prevent excessive network usage

**Section sources**
- [hybrid_pipeline.py:24-32](file://app/backend/services/hybrid_pipeline.py#L24-L32)
- [hybrid_pipeline.py:1446-1492](file://app/backend/services/hybrid_pipeline.py#L1446-L1492)
- [llm_service.py:41-65](file://app/backend/services/llm_service.py#L41-L65)
- [nginx.prod.conf:81-94](file://nginx/nginx.prod.conf#L81-L94)
- [ResultCard.jsx:13-19](file://app/frontend/src/components/ResultCard.jsx#L13-L19)
- [webhook_service.py:13-15](file://app/backend/services/webhook_service.py#L13-L15)

## Troubleshooting Guide
Common issues and resolutions:
- **Stream ends without completion**:
  - Ensure the generator yields a final "complete" event and "[DONE]" marker
  - Verify the frontend reads until "[DONE]" and throws if missing
- **Connection drops or timeouts**:
  - Confirm Nginx disables buffering and sets proper headers for SSE
  - Use heartbeat pings to keep the connection alive
- **LLM rate limiting (429 errors)**:
  - System now automatically applies exponential backoff retry logic
  - Check OLLAMA_MAX_CONCURRENT environment variable for concurrency limits
  - Monitor retry attempts and adjust base delay if needed
- **LLM offline or slow**:
  - The backend falls back gracefully with deterministic narratives
  - Frontend shows a notice and quality indicator
  - Use the diagnostic endpoint to check model readiness
- **Batch processing failures**:
  - Individual file failures are streamed separately
  - Check tenant plan limits for batch size restrictions
  - Monitor concurrent processing limits
- **Frontend errors**:
  - The frontend surfaces HTTP errors and malformed events
  - Display user-friendly messages with retry options
- **Type conversion issues**:
  - safeStr utility prevents crashes from unexpected data types
  - Check browser console for conversion warnings
  - Verify data integrity in backend serialization
- **Webhook delivery failures**:
  - Check webhook configuration in admin interface
  - Verify webhook URL is reachable and responds with 2xx status
  - Review delivery history for specific error patterns
  - Ensure HMAC signature verification on receiving end
- **Webhook auto-disabled**:
  - Webhooks are automatically disabled after 10 consecutive failures
  - Check delivery logs to identify root cause
  - Recreate webhook with updated configuration after fixing issues

Operational checks:
- Health endpoint validates database and Ollama connectivity
- LLM status endpoint reports model availability and readiness
- Monitor semaphore utilization and rate limiting effectiveness
- Track exponential backoff retry patterns and success rates
- Verify safeStr conversion logs for debugging type issues
- Monitor webhook delivery success rates and failure patterns
- Check webhook configuration validity and event subscription filters

**Section sources**
- [analyze.py:584-587](file://app/backend/routes/analyze.py#L584-L587)
- [api.js:102-109](file://app/frontend/src/lib/api.js#L102-L109)
- [api.js:132-140](file://app/frontend/src/lib/api.js#L132-L140)
- [nginx.prod.conf:81-94](file://nginx/nginx.prod.conf#L81-L94)
- [main.py:228-259](file://app/backend/main.py#L228-L259)
- [main.py:262-326](file://app/backend/main.py#L262-L326)
- [ResultCard.jsx:13-19](file://app/frontend/src/components/ResultCard.jsx#L13-L19)
- [webhook_service.py:106-111](file://app/backend/services/webhook_service.py#L106-L111)

## Conclusion
The real-time processing pipeline delivers responsive, incremental feedback during long-running analysis by combining FastAPI SSE with a structured streaming generator. The enhanced implementation now features comprehensive error handling with exponential backoff retry logic for rate limiting, reduced concurrency limits to prevent thundering herd effects, and improved streaming architecture for batch analysis operations. The introduction of safeStr utility functions provides robust type-safe string conversion for dynamic data streams, preventing UI crashes and ensuring consistent rendering across all frontend components. The frontend consumes these events to provide clear progress indicators and a smooth user experience. 

**Updated**: The system now includes a comprehensive webhook system that provides event-driven integrations for external systems. Webhook configuration management through admin endpoints enables tenant-level webhook setup with event filtering, HMAC signing for security, and comprehensive delivery tracking with retry mechanisms. The webhook service operates in the background, ensuring that webhook failures never impact the core analysis completion process while providing reliable event delivery for integration scenarios.

Proper infrastructure configuration and enhanced error handling ensure reliability under production conditions with improved resilience against external service limitations, data type inconsistencies, and webhook delivery failures. The combination of real-time streaming updates and webhook notifications creates a robust foundation for both user-facing analysis and automated system integrations.