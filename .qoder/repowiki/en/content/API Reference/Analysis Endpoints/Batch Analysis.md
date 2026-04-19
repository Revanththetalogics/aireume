# Batch Analysis

<cite>
**Referenced Files in This Document**
- [analyze.py](file://app/backend/routes/analyze.py)
- [schemas.py](file://app/backend/models/schemas.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [subscription.py](file://app/backend/routes/subscription.py)
- [BatchPage.jsx](file://app/frontend/src/pages/BatchPage.jsx)
- [api.js](file://app/frontend/src/lib/api.js)
- [001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)
</cite>

## Update Summary
**Changes Made**
- Updated to reflect current state where POST /api/analyze/batch endpoint remains fully functional
- Documented both synchronous batch processing and chunked upload capabilities
- Clarified that batch functionality is not experimental but production-ready
- Updated frontend integration to show both analyzeBatch and analyzeBatchChunked usage

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
This document describes the POST /api/analyze/batch endpoint for concurrent processing of multiple resumes. It covers:
- Array-based resume uploads with both synchronous and chunked processing modes
- Batch size limits based on subscription plans (default 50, configurable)
- Automatic ranking by fit_score
- Request/response schemas for batch processing
- Error handling for individual file failures and partial success scenarios
- Usage counting for batch operations
- JD caching optimization shared across all workers
- Performance considerations for large batches
- Examples of batch processing workflows, result ranking algorithms, and integration patterns

**Updated** The batch analysis functionality is production-ready and fully implemented, not experimental as initially described in the update reason.

## Project Structure
The batch analysis feature spans backend FastAPI routes, models, schemas, subscription enforcement, and frontend integration.

```mermaid
graph TB
subgraph "Backend"
A["analyze.py<br/>Routes"]
B["schemas.py<br/>Pydantic Schemas"]
C["db_models.py<br/>Database Models"]
D["subscription.py<br/>Usage & Limits"]
end
subgraph "Frontend"
E["BatchPage.jsx<br/>UI"]
F["api.js<br/>HTTP Client"]
end
G["Alembic Migration<br/>001_enrich_candidates_add_caches.py"]
E --> F
F --> A
A --> B
A --> C
A --> D
G --> C
```

**Diagram sources**
- [analyze.py](file://app/backend/routes/analyze.py)
- [schemas.py](file://app/backend/models/schemas.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [subscription.py](file://app/backend/routes/subscription.py)
- [BatchPage.jsx](file://app/frontend/src/pages/BatchPage.jsx)
- [api.js](file://app/frontend/src/lib/api.js)
- [001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)

**Section sources**
- [analyze.py](file://app/backend/routes/analyze.py)
- [schemas.py](file://app/backend/models/schemas.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [subscription.py](file://app/backend/routes/subscription.py)
- [BatchPage.jsx](file://app/frontend/src/pages/BatchPage.jsx)
- [api.js](file://app/frontend/src/lib/api.js)
- [001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)

## Core Components
- Route: POST /api/analyze/batch (synchronous) and POST /api/analyze/batch-chunked (chunked upload)
- Request: multipart/form-data with array of resumes, optional job_description or job_file, optional scoring_weights
- Response: BatchAnalysisResponse with results ordered by fit_score descending
- Batch size limit: derived from tenant's plan limits (default 50)
- Usage counting: increments by number of valid resumes processed
- JD caching: shared DB cache across all workers for the provided job description
- Concurrency control: semaphore-based limiting of concurrent batch operations

**Section sources**
- [analyze.py](file://app/backend/routes/analyze.py)
- [schemas.py](file://app/backend/models/schemas.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [subscription.py](file://app/backend/routes/subscription.py)

## Architecture Overview
The batch endpoint orchestrates concurrent resume parsing and analysis, enforces usage limits, and persists results. Both synchronous and chunked processing modes are supported.

```mermaid
sequenceDiagram
participant FE as "Frontend"
participant API as "FastAPI Route"
participant SUB as "Subscription Router"
participant DB as "Database"
participant PARSE as "Parser Service"
participant PIPE as "Hybrid Pipeline"
FE->>API : POST /api/analyze/batch (multipart)
API->>SUB : Check usage (quantity = valid_count)
SUB-->>API : allowed=true/false
API->>API : Validate files and job description
API->>DB : Cache JD (shared across workers)
API->>PARSE : Parse resume N (async with semaphore)
PARSE-->>API : Parsed data
API->>PIPE : Run hybrid pipeline (async)
PIPE-->>API : Analysis result
API->>DB : Store ScreeningResult
API-->>FE : BatchAnalysisResponse (sorted by fit_score)
```

**Diagram sources**
- [analyze.py](file://app/backend/routes/analyze.py)
- [subscription.py](file://app/backend/routes/subscription.py)
- [db_models.py](file://app/backend/models/db_models.py)

## Detailed Component Analysis

### Endpoint Definition and Behavior
- Path: POST /api/analyze/batch (synchronous) and POST /api/analyze/batch-chunked (chunked)
- Request form fields:
  - resumes: array of UploadFile (PDF, DOCX, DOC) - synchronous mode
  - upload_ids: array of assembly IDs - chunked mode
  - filenames: array of original filenames - chunked mode
  - job_description: string (optional if job_file provided)
  - job_file: UploadFile (optional if job_description provided)
  - scoring_weights: stringified JSON object (optional)
- Response: BatchAnalysisResponse with:
  - results: array of BatchAnalysisResult sorted by fit_score descending
  - total: integer count of processed results
  - failed: array of failed items with error details
  - successful: count of successful analyses
  - failed_count: count of failed analyses

Processing steps for synchronous batch:
1. Validate presence of resumes and allowed extensions
2. Determine max batch size from plan limits (default 50)
3. Check usage allowance for quantity equal to valid resume count
4. Resolve job description from text or file
5. Validate JD length
6. Pre-parse and cache JD once for all resumes
7. Read and validate each resume file
8. Concurrently process resumes via asyncio.gather with semaphore control
9. For each result:
   - Extract file hash
   - Deduplicate/create candidate
   - Persist ScreeningResult
10. Sort results by fit_score descending
11. Return BatchAnalysisResponse

**Section sources**
- [analyze.py](file://app/backend/routes/analyze.py)
- [schemas.py](file://app/backend/models/schemas.py)

### Request and Response Schemas
- Request form fields:
  - resumes: list[UploadFile] (synchronous)
  - upload_ids: list[str] (chunked)
  - filenames: list[str] (chunked)
  - job_description: str (optional)
  - job_file: UploadFile (optional)
  - scoring_weights: str (optional)
- Response:
  - results: List[BatchAnalysisResult]
  - total: int
  - failed: List[BatchFailedItem]
  - successful: int
  - failed_count: int

BatchAnalysisResult:
- rank: int
- filename: str
- result: AnalysisResponse

BatchFailedItem:
- filename: str
- error: str

AnalysisResponse includes fit_score, final_recommendation, risk_level, and other fields produced by the hybrid pipeline.

**Section sources**
- [analyze.py](file://app/backend/routes/analyze.py)
- [schemas.py](file://app/backend/models/schemas.py)

### Batch Size Limits and Usage Counting
- Max batch size:
  - Default 50
  - Overridden by tenant.plan.limits.batch_size if present
  - Enforced before processing resumes
- Usage counting:
  - _check_and_increment_usage increments by valid_count
  - Uses tenant.plan.limits.analyses_per_month for monthly cap
  - Records UsageLog entries for each successful analysis
- Frontend integration:
  - BatchPage enforces maxFiles based on subscription limits
  - Displays remaining analyses and usage status
  - Supports both analyzeBatch and analyzeBatchChunked

**Section sources**
- [analyze.py](file://app/backend/routes/analyze.py)
- [subscription.py](file://app/backend/routes/subscription.py)
- [BatchPage.jsx](file://app/frontend/src/pages/BatchPage.jsx)

### JD Caching Optimization
- Shared across all workers via DB:
  - Key: MD5 of first 2000 characters of job description
  - Stored in JdCache table
  - Retrieved or computed once per batch
- Benefits:
  - Avoids repeated parsing of identical or similar JDs
  - Reduces CPU and latency for large batches

**Section sources**
- [analyze.py](file://app/backend/routes/analyze.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [001_enrich_candidates_add_caches.py](file://alembic/versions/001_enrich_candidates_add_caches.py)

### Ranking Algorithm
- Sorting: results are ordered by fit_score descending
- fit_score is computed by the hybrid pipeline scoring module
- The endpoint returns results as-is from the pipeline, then sorts client-side by fit_score

**Section sources**
- [analyze.py](file://app/backend/routes/analyze.py)

### Error Handling and Partial Success
- Validation errors:
  - No resumes provided
  - Invalid file types or oversized files
  - Missing or too-short job description
  - Exceeds batch size limit
  - Usage limit exceeded
- Runtime exceptions during processing:
  - Individual resume failures are tracked separately
  - Other resumes continue processing
  - Failed items are returned with error details
  - Successful results are still processed and ranked
- Usage rollback note:
  - Current behavior increments usage before validation; tests document this limitation

**Section sources**
- [analyze.py](file://app/backend/routes/analyze.py)
- [subscription.py](file://app/backend/routes/subscription.py)
- [BatchPage.jsx](file://app/frontend/src/pages/BatchPage.jsx)

### Frontend Integration Patterns
- BatchPage:
  - Drag-and-drop multiple resumes with maxFiles bound to subscription limits
  - Displays usage banner and remaining counts
  - Supports both synchronous and chunked upload modes
  - Calls analyzeBatch or analyzeBatchChunked and renders ranked results
- API client:
  - analyzeBatch constructs FormData with resumes array and optional job fields
  - analyzeBatchChunked handles chunked uploads for large files
  - Sets Content-Type to multipart/form-data
  - Timeout configured for batch operations (300s for synchronous, 600s for chunked)

**Section sources**
- [BatchPage.jsx](file://app/frontend/src/pages/BatchPage.jsx)
- [api.js](file://app/frontend/src/lib/api.js)

## Dependency Analysis
```mermaid
classDiagram
class BatchAnalysisResponse {
+BatchAnalysisResult[] results
+BatchFailedItem[] failed
+int total
+int successful
+int failed_count
}
class BatchAnalysisResult {
+int rank
+string filename
+AnalysisResponse result
}
class BatchFailedItem {
+string filename
+string error
}
class AnalysisResponse {
+int? fit_score
+string final_recommendation
+string risk_level
+dict jd_analysis
+dict candidate_profile
+dict skill_analysis
+dict edu_timeline_analysis
+dict explainability
+string recommendation_rationale
+string[] adjacent_skills
+string[] pipeline_errors
+string analysis_quality
+bool narrative_pending
+int? result_id
+int? candidate_id
+string? candidate_name
}
BatchAnalysisResponse --> BatchAnalysisResult
BatchAnalysisResponse --> BatchFailedItem
BatchAnalysisResult --> AnalysisResponse
```

**Diagram sources**
- [schemas.py](file://app/backend/models/schemas.py)

**Section sources**
- [schemas.py](file://app/backend/models/schemas.py)

## Performance Considerations
- Concurrency:
  - Uses asyncio.gather to process resumes concurrently
  - Semaphore-based control limits concurrent batch operations to 5
  - Parsing occurs in thread pool to avoid blocking the event loop
- Memory and throughput:
  - Pre-validate file sizes and types before reading
  - Limit batch size by plan limits to prevent overload
  - Chunked upload bypasses CDN upload limits for large files
- Database contention:
  - JD cache reduces repeated parsing
  - Batch writes commit once at the end
- Frontend UX:
  - Large timeouts configured for batch requests
  - Progressive rendering of results after processing completes
  - Upload progress tracking for chunked operations

## Troubleshooting Guide
Common issues and resolutions:
- Batch denied due to plan limits:
  - Verify tenant.plan.limits.batch_size and analyses_per_month
  - Use GET /api/subscription/check/batch_analysis to preflight
- Usage limit exceeded:
  - Check remaining analyses and upgrade plan if needed
  - Review UsageLog entries for recent activity
- Invalid file types or oversized files:
  - Ensure PDF, DOCX, or DOC; under 10MB per file
- Missing job description:
  - Provide either job_description or job_file
  - Ensure job description meets minimum word count
- Partial failures:
  - Some resumes may fail while others succeed; check failed array for error details
  - Successful results are still processed and ranked
- JD parsing inconsistencies:
  - Confirm that identical JDs produce the same cache key
- Chunked upload issues:
  - Verify assembly directory permissions
  - Check upload IDs and filename mappings
  - Monitor overall progress for large batches

**Section sources**
- [analyze.py](file://app/backend/routes/analyze.py)
- [subscription.py](file://app/backend/routes/subscription.py)
- [BatchPage.jsx](file://app/frontend/src/pages/BatchPage.jsx)

## Conclusion
The POST /api/analyze/batch endpoint enables efficient, scalable bulk resume screening with plan-aware limits, shared JD caching, and automatic ranking. By leveraging concurrency and robust error handling, it supports high-volume workflows while maintaining usage compliance and performance. Both synchronous and chunked upload modes provide flexibility for different use cases and file sizes.

## Appendices

### API Reference: POST /api/analyze/batch
- Method: POST
- Path: /api/analyze/batch
- Content-Type: multipart/form-data
- Form Fields:
  - resumes: array of files (PDF, DOCX, DOC)
  - job_description: string (optional if job_file provided)
  - job_file: file (optional if job_description provided)
  - scoring_weights: stringified JSON object (optional)
- Response:
  - BatchAnalysisResponse with results sorted by fit_score descending

### API Reference: POST /api/analyze/batch-chunked
- Method: POST
- Path: /api/analyze/batch-chunked
- Content-Type: multipart/form-data
- Form Fields:
  - upload_ids: array of assembly IDs
  - filenames: array of original filenames
  - job_description: string (optional if job_file provided)
  - job_file: file (optional if job_description provided)
  - scoring_weights: stringified JSON object (optional)
- Response:
  - BatchAnalysisResponse with results sorted by fit_score descending

**Section sources**
- [analyze.py](file://app/backend/routes/analyze.py)
- [schemas.py](file://app/backend/models/schemas.py)

### Example Workflows
- Bulk screening:
  - Upload 10–50 resumes against a single job description
  - Receive ranked shortlist with fit_score and recommendations
- Template reuse:
  - Save job descriptions as templates and reuse across batches
- Export:
  - Export CSV or Excel of selected candidates for downstream actions
- Large file processing:
  - Use chunked upload mode for files larger than CDN limits
- Mixed file sizes:
  - Combine small and large files in single batch operation

**Section sources**
- [BatchPage.jsx](file://app/frontend/src/pages/BatchPage.jsx)
- [api.js](file://app/frontend/src/lib/api.js)