# Analysis Endpoints

<cite>
**Referenced Files in This Document**
- [analyze.py](file://app/backend/routes/analyze.py)
- [schemas.py](file://app/backend/models/schemas.py)
- [auth.py](file://app/backend/middleware/auth.py)
- [subscription.py](file://app/backend/routes/subscription.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [parser_service.py](file://app/backend/services/parser_service.py)
- [gap_detector.py](file://app/backend/services/gap_detector.py)
- [hybrid_pipeline.py](file://app/backend/services/hybrid_pipeline.py)
- [nginx.prod.conf](file://app/nginx/nginx.prod.conf)
- [api.js](file://app/frontend/src/lib/api.js)
- [007_narrative_status.py](file://alembic/versions/007_narrative_status.py)
- [test_api.py](file://app/backend/tests/test_api.py)
</cite>

## Update Summary
**Changes Made**
- Removed documentation for LLM-based contact enrichment system that was eliminated from the analysis pipeline
- Updated AnalysisResponse schema to remove contact_info field from core and extended fields
- Removed references to enrich_parsed_resume_async function and related contact extraction enhancements
- Updated response schemas to reflect simplified contact information handling
- Clarified that contact information is now handled through parser service fallback methods only

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

## Introduction
This document provides comprehensive API documentation for the resume analysis endpoints. It covers:
- POST /api/analyze: Single resume processing with multipart form data, including resume file upload, job description text or file, optional scoring weights JSON, and action parameters.
- POST /api/analyze/stream: Real-time streaming analysis using Server-Sent Events (SSE) with progressive result stages (parsing, scoring, complete).
- POST /api/analyze/batch: Concurrent batch processing of multiple resumes with automatic ranking.
- **GET /api/analysis/{id}/narrative: Enhanced endpoint with three-state status tracking (pending, ready, failed) and fallback mechanisms.**

It also documents request/response schemas, file size limits and supported formats, error handling for invalid files and insufficient job description content, usage limits, subscription enforcement, rate limiting, and examples of streaming event payloads and batch result structures.

## Project Structure
The analysis endpoints are implemented in the backend FastAPI application under app/backend/routes/analyze.py. Supporting services include:
- Parser service for resume and job description text extraction with enhanced contact information fallback
- Gap detector for employment timeline analysis
- Hybrid pipeline orchestrating Python-first scoring and LLM narrative with status tracking
- Subscription and usage enforcement
- Authentication middleware

```mermaid
graph TB
Client["Client"]
Auth["Auth Middleware<br/>JWT Bearer"]
Routes["Routes<br/>/api/analyze, /api/analyze/stream, /api/analyze/batch, /api/analysis/{id}/narrative"]
Parser["Parser Service<br/>parse_resume, extract_jd_text<br/>enhanced contact fallbacks"]
Gap["Gap Detector<br/>analyze_gaps"]
Hybrid["Hybrid Pipeline<br/>run_hybrid_pipeline, astream_hybrid_pipeline, _background_llm_narrative"]
DB["Database<br/>SQLAlchemy ORM<br/>narrative_status tracking"]
Sub["Subscription & Usage<br/>record_usage, limits"]
Nginx["Nginx Proxy<br/>Rate Limits, Buffering"]
Client --> Auth --> Routes
Routes --> Parser
Routes --> Gap
Routes --> Hybrid
Routes --> DB
Routes --> Sub
Routes --> Nginx
```

**Diagram sources**
- [analyze.py:354-800](file://app/backend/routes/analyze.py#L354-L800)
- [parser_service.py:1-552](file://app/backend/services/parser_service.py#L1-L552)
- [gap_detector.py:1-219](file://app/backend/services/gap_detector.py#L1-L219)
- [hybrid_pipeline.py:1-800](file://app/backend/services/hybrid_pipeline.py#L1-L800)
- [subscription.py:427-477](file://app/backend/routes/subscription.py#L427-L477)
- [auth.py:1-47](file://app/backend/middleware/auth.py#L1-L47)
- [nginx.prod.conf:50-95](file://app/nginx/nginx.prod.conf#L50-L95)

**Section sources**
- [analyze.py:1-813](file://app/backend/routes/analyze.py#L1-L813)
- [parser_service.py:1-552](file://app/backend/services/parser_service.py#L1-L552)
- [gap_detector.py:1-219](file://app/backend/services/gap_detector.py#L1-L219)
- [hybrid_pipeline.py:1-800](file://app/backend/services/hybrid_pipeline.py#L1-L800)
- [subscription.py:1-477](file://app/backend/routes/subscription.py#L1-L477)
- [auth.py:1-47](file://app/backend/middleware/auth.py#L1-L47)
- [nginx.prod.conf:50-95](file://app/nginx/nginx.prod.conf#L50-L95)

## Core Components
- Authentication: JWT bearer token required for all analysis endpoints.
- Usage enforcement: Monthly analysis limits per tenant plan, enforced before processing.
- File validation: Allowed resume formats (.pdf, .docx, .doc) with size limits; job description file size limit.
- Deduplication: Three-layer deduplication by email, file hash, and name+phone; action parameter controls behavior.
- Streaming: SSE endpoint emits progressive stages with heartbeat pings.
- Batch: Concurrent processing with automatic ranking by fit score.
- **Status Tracking: Enhanced narrative endpoint with three-state status system (pending, ready, failed) and fallback mechanisms.**
- **Contact Information: Simplified handling through parser service fallback methods (NER, email-based, relaxed header scan, filename-based) without LLM-based enrichment.**

**Section sources**
- [auth.py:19-40](file://app/backend/middleware/auth.py#L19-L40)
- [analyze.py:323-352](file://app/backend/routes/analyze.py#L323-L352)
- [analyze.py:369-384](file://app/backend/routes/analyze.py#L369-L384)
- [analyze.py:147-215](file://app/backend/routes/analyze.py#L147-L215)
- [analyze.py:506-646](file://app/backend/routes/analyze.py#L506-L646)
- [analyze.py:649-758](file://app/backend/routes/analyze.py#L649-L758)

## Architecture Overview
The analysis pipeline integrates file parsing, gap analysis, and hybrid scoring with optional LLM narrative. The hybrid pipeline supports both synchronous and streaming modes with enhanced status tracking for narrative generation. Contact information is now handled through enhanced fallback methods in the parser service.

```mermaid
sequenceDiagram
participant C as "Client"
participant R as "Routes<br/>analyze.py"
participant P as "Parser Service<br/>enhanced contact fallbacks"
participant G as "Gap Detector"
participant H as "Hybrid Pipeline"
participant S as "Subscription"
participant D as "Database"
C->>R : POST /api/analyze (multipart/form-data)
R->>S : Check usage limits
S-->>R : Allowed/Forbidden
R->>P : parse_resume(resume bytes, filename)<br/>enhanced contact fallbacks
P-->>R : Parsed resume data (improved contact info)
R->>G : analyze_gaps(work_experience)
G-->>R : Gap analysis
R->>H : run_hybrid_pipeline(...)
H-->>R : Python results + fallback narrative
R->>D : Store ScreeningResult + Candidate
D-->>R : Stored IDs
R-->>C : AnalysisResponse JSON (without LLM contact enrichment)
C->>R : GET /api/analysis/{id}/narrative
R->>D : Check narrative_status
D-->>R : Status : pending/ready/failed
R-->>C : Status response with fallback/LLM narrative
```

**Diagram sources**
- [analyze.py:354-501](file://app/backend/routes/analyze.py#L354-L501)
- [parser_service.py:547-552](file://app/backend/services/parser_service.py#L547-L552)
- [gap_detector.py:217-219](file://app/backend/services/gap_detector.py#L217-L219)
- [hybrid_pipeline.py:1-800](file://app/backend/services/hybrid_pipeline.py#L1-L800)
- [subscription.py:427-477](file://app/backend/routes/subscription.py#L427-L477)

## Detailed Component Analysis

### Endpoint: POST /api/analyze
Single resume analysis returning a JSON response.

- Method: POST
- Path: /api/analyze
- Authentication: Required (JWT Bearer)
- Content-Type: multipart/form-data
- Form fields:
  - resume: file (required)
  - job_description: string (optional)
  - job_file: file (optional)
  - scoring_weights: string (JSON) (optional)
  - action: string (optional) — one of use_existing, update_profile, create_new
- Response: AnalysisResponse

Request validation and limits:
- Allowed resume extensions: .pdf, .docx, .doc
- Resume file size limit: 10 MB
- Job description file size limit: 5 MB
- Job description text or file required; minimum word count enforced
- Usage limit checked before processing; raises 429 if exceeded

Processing steps:
- Parse resume in thread pool with enhanced contact fallbacks
- Analyze gaps
- Parse or cache job description analysis
- Run hybrid pipeline
- Deduplicate candidates (3-layer) and optionally update stored profile
- Persist result and candidate profile
- Return result with identifiers

Response schema (AnalysisResponse):
- Core fields: fit_score, job_role, strengths, weaknesses, employment_gaps, education_analysis, risk_signals, final_recommendation, score_breakdown, matched_skills, missing_skills, risk_level, interview_questions, required_skills_count, work_experience
- Extended fields: jd_analysis, candidate_profile, skill_analysis, edu_timeline_analysis, explainability, recommendation_rationale, adjacent_skills, pipeline_errors, analysis_quality, narrative_pending, duplicate_candidate
- Auxiliary identifiers: result_id, candidate_id, candidate_name

**Updated** Removed contact_info field from AnalysisResponse as LLM-based contact enrichment system has been eliminated. Contact information is now handled through parser service fallback methods only.

Error handling:
- 400 for unsupported file types, oversized files, insufficient JD content
- 401/403 for authentication/authorization failures
- 429 for usage limit exceeded
- 5xx for internal errors during parsing or pipeline execution

**Section sources**
- [analyze.py:354-501](file://app/backend/routes/analyze.py#L354-L501)
- [schemas.py:89-125](file://app/backend/models/schemas.py#L89-L125)
- [auth.py:19-40](file://app/backend/middleware/auth.py#L19-L40)
- [subscription.py:427-477](file://app/backend/routes/subscription.py#L427-L477)

### Endpoint: POST /api/analyze/stream
Real-time streaming analysis using Server-Sent Events (SSE).

- Method: POST
- Path: /api/analyze/stream
- Authentication: Required (JWT Bearer)
- Content-Type: multipart/form-data
- Form fields: same as single endpoint
- Response: text/event-stream

Streaming stages:
- Stage "parsing": Python-only scores and partial analysis (within 2s)
- Stage "scoring": LLM narrative and explainability (after ~40s)
- Stage "complete": full merged result
- Heartbeat pings maintain connection through proxies

Proxy configuration:
- Nginx disables buffering for SSE to prevent Cloudflare 524 errors
- Separate rate limits for streaming endpoint

Frontend consumption example:
- ReadableStream reader decodes chunks and parses "data: " lines
- On each event, invoke onStageComplete callback
- On completion, finalResult contains the full result

**Section sources**
- [analyze.py:506-646](file://app/backend/routes/analyze.py#L506-L646)
- [hybrid_pipeline.py:1410-1498](file://app/backend/services/hybrid_pipeline.py#L1410-L1498)
- [nginx.prod.conf:66-95](file://app/nginx/nginx.prod.conf#L66-L95)
- [api.js:96-141](file://app/frontend/src/lib/api.js#L96-L141)

### Endpoint: POST /api/analyze/batch
Concurrent batch processing of multiple resumes with automatic ranking.

- Method: POST
- Path: /api/analyze/batch
- Authentication: Required (JWT Bearer)
- Content-Type: multipart/form-data
- Form fields:
  - resumes: list of files (required)
  - job_description: string (optional)
  - job_file: file (optional)
  - scoring_weights: string (JSON) (optional)
- Response: BatchAnalysisResponse

Processing:
- Validates allowed extensions and size limits
- Checks usage limits for the batch size
- Pre-parses and caches job description analysis
- Processes resumes concurrently using asyncio.gather
- Persists each result and candidate
- Sorts results by fit_score descending

Response schema (BatchAnalysisResponse):
- results: list of BatchAnalysisResult
- total: integer count

BatchAnalysisResult:
- rank: integer
- filename: string
- result: AnalysisResponse

**Section sources**
- [analyze.py:649-758](file://app/backend/routes/analyze.py#L649-L758)
- [schemas.py:127-136](file://app/backend/models/schemas.py#L127-L136)
- [subscription.py:670-681](file://app/backend/routes/subscription.py#L670-L681)

### Endpoint: GET /api/analysis/{id}/narrative
**Enhanced** endpoint with three-state status tracking system for LLM narrative polling.

- Method: GET
- Path: /api/analysis/{analysis_id}
- Authentication: Required (JWT Bearer)
- Response: JSON with status tracking

**Status States:**
- **pending**: LLM narrative is still being generated
  - Response: `{"status": "pending"}`
  - Used when `narrative_status` is "pending" or `narrative_json` is NULL
- **ready**: LLM narrative is available
  - Response: `{"status": "ready", "narrative": {...}}`
  - Contains the complete narrative JSON with all fields
- **failed**: LLM narrative generation failed
  - Response: `{"status": "failed", "error": "...", "narrative": {...}}`
  - Includes error message and fallback narrative

**Fallback Mechanisms:**
- When LLM fails or times out, deterministic fallback narrative is generated
- Fallback contains basic fit summary, strengths, concerns, and interview questions
- Error messages are stored in `narrative_error` field for debugging

**Database Integration:**
- Uses `narrative_status` field in ScreeningResult model
- Supports three states: "pending", "processing", "ready", "failed"
- Stores error details in `narrative_error` field
- Maintains tenant isolation through filtering by `tenant_id`

**Frontend Polling Strategy:**
- Client polls endpoint when `narrative_pending` is True in initial analysis
- Adaptive polling intervals: 2s for first 30s, then 5s for longer waits
- Maximum 36 attempts (~2.25 minutes total)
- Graceful degradation when LLM is unavailable

**Section sources**
- [analyze.py:1117-1168](file://app/backend/routes/analyze.py#L1117-L1168)
- [db_models.py:129-151](file://app/backend/models/db_models.py#L129-L151)
- [hybrid_pipeline.py:1896-2038](file://app/backend/services/hybrid_pipeline.py#L1896-L2038)
- [007_narrative_status.py:1-65](file://alembic/versions/007_narrative_status.py#L1-L65)
- [test_api.py:277-381](file://app/backend/tests/test_api.py#L277-L381)

### Deduplication and Candidate Profile Storage
Three-layer deduplication:
- Email match within tenant
- File hash match
- Name + phone match

Action parameter behavior:
- use_existing: reuse stored profile if available
- update_profile: update stored profile on match
- create_new: bypass deduplication
- None/unrecognized: deduplicate and optionally return duplicate_candidate info

Stored candidate profile includes:
- Skills, education, work experience
- Gap analysis JSON
- Current role/company and total years experience
- Quality and timestamps

**Section sources**
- [analyze.py:147-215](file://app/backend/routes/analyze.py#L147-L215)
- [schemas.py:8-20](file://app/backend/models/schemas.py#L8-L20)
- [db_models.py:97-126](file://app/backend/models/db_models.py#L97-L126)

### Job Description Parsing and Caching
- extract_jd_text supports multiple formats (PDF, DOCX, DOC, TXT, RTF, HTML, ODT, Markdown)
- parse_jd_rules extracts role title, domain, seniority, required skills, required years, nice-to-have skills, and responsibilities
- JdCache stores parsed JD results keyed by MD5 hash for reuse across workers

**Section sources**
- [parser_service.py:20-128](file://app/backend/services/parser_service.py#L20-L128)
- [hybrid_pipeline.py:467-560](file://app/backend/services/hybrid_pipeline.py#L467-L560)
- [db_models.py:229-236](file://app/backend/models/db_models.py#L229-L236)

### Enhanced Contact Information Handling
**Updated** Contact information is now handled through enhanced fallback methods in the parser service:

- **Parser Service Fallback Methods:**
  - spaCy NER extraction for diverse name formats
  - Email-based name extraction as fallback
  - Relaxed header scanning for name detection
  - Filename-based extraction when other methods fail
  - Automatic merging of LLM contact extraction results with regex results

- **Contact Information Sources:**
  - Name: Extracted from resume text using multiple fallback tiers
  - Email: Extracted using regex patterns
  - Phone: Extracted using regex patterns
  - LinkedIn: Extracted using regex patterns

- **Contact Information Storage:**
  - Stored in Candidate table for future analysis
  - Available for deduplication and profile updates
  - Used for candidate name resolution in results

**Section sources**
- [parser_service.py:1080-1155](file://app/backend/services/parser_service.py#L1080-L1155)
- [analyze.py:166-172](file://app/backend/routes/analyze.py#L166-L172)
- [analyze.py:191-196](file://app/backend/routes/analyze.py#L191-L196)

### Usage Limits, Subscription Enforcement, and Rate Limiting
Usage enforcement:
- Monthly analysis limit per tenant plan
- Usage increments on successful analysis
- Limits retrieved from SubscriptionPlan.limits JSON

Subscription endpoints:
- GET /api/subscription — current plan, usage stats, available plans
- GET /api/subscription/check/{action} — check limits before action
- GET /api/subscription/usage-history — recent usage logs

Rate limiting:
- Nginx zones enforce request rates:
  - Non-streaming: limit_req zone=api burst=20 nodelay
  - Streaming: limit_req zone=api burst=5 nodelay
- Streaming endpoint disables proxy buffering and gzip to ensure immediate event delivery

**Section sources**
- [subscription.py:172-253](file://app/backend/routes/subscription.py#L172-L253)
- [subscription.py:256-343](file://app/backend/routes/subscription.py#L256-L343)
- [subscription.py:427-477](file://app/backend/routes/subscription.py#L427-L477)
- [nginx.prod.conf:50-95](file://app/nginx/nginx.prod.conf#L50-L95)

## Dependency Analysis
The analysis endpoints depend on several services and models.

```mermaid
graph LR
A["analyze.py"]
P["parser_service.py<br/>enhanced contact fallbacks"]
G["gap_detector.py"]
H["hybrid_pipeline.py"]
S["schemas.py"]
M["db_models.py"]
U["subscription.py"]
T["auth.py"]
N["nginx.prod.conf"]
A --> P
A --> G
A --> H
A --> S
A --> M
A --> U
A --> T
A --> N
```

**Diagram sources**
- [analyze.py:1-813](file://app/backend/routes/analyze.py#L1-L813)
- [parser_service.py:1-552](file://app/backend/services/parser_service.py#L1-L552)
- [gap_detector.py:1-219](file://app/backend/services/gap_detector.py#L1-L219)
- [hybrid_pipeline.py:1-800](file://app/backend/services/hybrid_pipeline.py#L1-L800)
- [schemas.py:1-379](file://app/backend/models/schemas.py#L1-L379)
- [db_models.py:1-250](file://app/backend/models/db_models.py#L1-L250)
- [subscription.py:1-477](file://app/backend/routes/subscription.py#L1-L477)
- [auth.py:1-47](file://app/backend/middleware/auth.py#L1-L47)
- [nginx.prod.conf:50-95](file://app/nginx/nginx.prod.conf#L50-L95)

**Section sources**
- [analyze.py:1-813](file://app/backend/routes/analyze.py#L1-L813)
- [schemas.py:1-379](file://app/backend/models/schemas.py#L1-L379)
- [db_models.py:1-250](file://app/backend/models/db_models.py#L1-L250)
- [subscription.py:1-477](file://app/backend/routes/subscription.py#L1-L477)
- [auth.py:1-47](file://app/backend/middleware/auth.py#L1-L47)
- [nginx.prod.conf:50-95](file://app/nginx/nginx.prod.conf#L50-L95)

## Performance Considerations
- Asynchronous parsing: Resume parsing runs in a thread pool to avoid blocking the event loop.
- Streaming: SSE endpoint yields heartbeat pings to keep connections alive through proxies.
- Concurrency: Batch endpoint uses asyncio.gather for concurrent processing.
- Caching: JD parsing is cached per tenant to avoid repeated LLM calls.
- Rate limiting: Nginx zones protect the API from overload.
- **Status tracking: Database-level status tracking reduces polling overhead and improves user experience.**
- **Enhanced contact fallbacks: Improved contact information extraction reduces dependency on LLM-based contact enrichment.**

## Troubleshooting Guide
Common errors and resolutions:
- Unsupported resume format: Ensure .pdf, .docx, or .doc. See ALLOWED_EXTENSIONS.
- Resume too large: Maximum 10 MB. See size checks.
- Job description missing or too short: Provide text or file; minimum word count enforced.
- Usage limit exceeded: Upgrade plan or wait until next reset. Check /api/subscription.
- Authentication failures: Verify JWT Bearer token.
- Streaming timeouts: Ensure SSE endpoint is proxied without buffering and with adequate timeouts.
- **Narrative polling issues: Check that analysis_id belongs to the authenticated user's tenant. Verify narrative_status field values.**
- **Contact information issues: Verify that enhanced fallback methods are working correctly. Check parser service contact extraction logs.**

**Section sources**
- [analyze.py:369-384](file://app/backend/routes/analyze.py#L369-L384)
- [analyze.py:255-266](file://app/backend/routes/analyze.py#L255-L266)
- [subscription.py:256-343](file://app/backend/routes/subscription.py#L256-L343)
- [nginx.prod.conf:66-95](file://app/nginx/nginx.prod.conf#L66-L95)

## Conclusion
The analysis endpoints provide robust, scalable resume screening with optional real-time streaming and batch processing. They enforce usage limits through a subscription system, support multiple file formats, and deliver comprehensive results with explainability and risk signals. The enhanced GET /api/analysis/{id}/narrative endpoint with three-state status tracking significantly improves user experience by providing clear feedback on narrative generation progress and fallback mechanisms. 

**Updated** The elimination of the LLM-based contact enrichment system simplifies the pipeline while maintaining contact information accuracy through enhanced fallback methods in the parser service. This change reduces complexity, improves performance, and maintains the quality of contact information extraction through multiple fallback tiers (NER, email-based, relaxed header scan, filename-based). Proper configuration of authentication, rate limiting, and proxy buffering ensures reliable operation in production environments.