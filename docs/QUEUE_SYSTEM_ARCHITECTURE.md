# Scalable Queue-Based Analysis System - Architecture Documentation

## Overview

This document describes the scalable, queue-based architecture for resume analysis processing. The system replaces the synchronous, direct-to-database approach with a robust job queue that provides:

- **Reliability**: Automatic retries with exponential backoff
- **Scalability**: Horizontal scaling with multiple workers
- **Observability**: Comprehensive metrics and monitoring
- **Data Integrity**: No incomplete records in production tables
- **Performance**: Priority-based scheduling and deduplication

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT REQUEST                           │
│                    (Upload Resume + JD)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                         │
│  POST /queue/submit                                              │
│  - Validate input                                                │
│  - Compute hashes (deduplication)                                │
│  - Create artifact + job                                         │
│  - Return job_id immediately                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE - QUEUE TABLES                       │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ analysis_jobs    │  │ analysis_artifacts│                    │
│  ├──────────────────┤  ├──────────────────┤                    │
│  │ • id (UUID)      │  │ • id (UUID)      │                    │
│  │ • status         │  │ • resume_text    │                    │
│  │ • priority       │  │ • jd_text        │                    │
│  │ • retry_count    │  │ • hashes         │                    │
│  │ • worker_id      │  │ • parsed_cache   │                    │
│  │ • artifact_id ───┼──┤                  │                    │
│  │ • result_id      │  └──────────────────┘                    │
│  └──────────────────┘                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    QUEUE WORKER (Background)                     │
│                                                                   │
│  1. Poll for next job (priority + FIFO)                         │
│     SELECT ... WHERE status='queued'                             │
│     ORDER BY priority ASC, queued_at ASC                         │
│     FOR UPDATE SKIP LOCKED                                       │
│                                                                   │
│  2. Claim job (atomic)                                           │
│     UPDATE status='processing', worker_id=self                   │
│                                                                   │
│  3. Process job                                                  │
│     ├─ Load artifact (resume + JD)                              │
│     ├─ Run analysis pipeline                                     │
│     ├─ Validate result (required fields)                         │
│     └─ Save to analysis_results                                  │
│                                                                   │
│  4. Update job status                                            │
│     ├─ Success: status='completed', result_id=...               │
│     └─ Failure: status='retrying' or 'failed'                   │
│                                                                   │
│  5. Record metrics                                               │
│     INSERT INTO job_metrics (timings, tokens, etc.)             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 DATABASE - RESULTS TABLE                         │
│                                                                   │
│  ┌──────────────────────────────────────────┐                   │
│  │ analysis_results (IMMUTABLE)             │                   │
│  ├──────────────────────────────────────────┤                   │
│  │ • id (UUID)                              │                   │
│  │ • job_id (UNIQUE)                        │                   │
│  │ • fit_score (NOT NULL) ✓                 │                   │
│  │ • final_recommendation (NOT NULL) ✓      │                   │
│  │ • analysis_data (JSONB, validated) ✓     │                   │
│  │ • parsed_resume (JSONB) ✓                │                   │
│  │ • parsed_jd (JSONB) ✓                    │                   │
│  │ • narrative_status, narrative_data       │                   │
│  │ • processing_time_ms, model_used         │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                   │
│  ✓ All records are COMPLETE and VALIDATED                       │
│  ✓ No "pending" or incomplete data                              │
│  ✓ Database constraints enforce integrity                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### 1. `analysis_jobs` - Main Queue Table

**Purpose**: Track all analysis jobs from submission to completion.

**Key Features**:
- UUID primary key for distributed systems
- Deduplication via `input_hash` (resume + JD + tenant)
- Priority-based scheduling (1=highest, 10=lowest)
- Automatic retry with exponential backoff
- Worker assignment and heartbeat monitoring
- Progress tracking (0-100%)

**Status Flow**:
```
queued → processing → completed
   ↓         ↓
retrying → failed
   ↑
cancelled
```

**Critical Fields**:
```sql
id                UUID PRIMARY KEY
tenant_id         INT (tenant isolation)
status            VARCHAR(20) -- queued, processing, completed, failed, retrying, cancelled
priority          INT (1-10)
retry_count       INT
max_retries       INT (default: 3)
worker_id         VARCHAR(100) -- which worker is processing
worker_heartbeat  TIMESTAMP -- last heartbeat (detect stale jobs)
artifact_id       UUID → analysis_artifacts
result_id         UUID → analysis_results (when completed)
```

**Indexes**:
- `(status, priority, queued_at)` - Queue processing
- `(worker_id, worker_heartbeat)` - Stale job detection
- `(tenant_id, status, created_at)` - Tenant filtering
- `input_hash` - Deduplication

---

### 2. `analysis_results` - Immutable Completed Analyses

**Purpose**: Store ONLY complete, validated analysis results.

**Key Features**:
- **Immutable**: Once written, never updated
- **Validated**: Database triggers ensure data completeness
- **NOT NULL constraints**: fit_score, final_recommendation required
- **One-to-one**: Each job has exactly one result

**Data Validation**:
```sql
-- Trigger ensures these fields exist in analysis_data JSON:
✓ strengths
✓ weaknesses
✓ matched_skills
✓ score_breakdown
✓ fit_score (matches column value)
```

**Critical Fields**:
```sql
id                    UUID PRIMARY KEY
job_id                UUID UNIQUE → analysis_jobs
fit_score             INT NOT NULL (0-100)
final_recommendation  VARCHAR(50) NOT NULL
analysis_data         JSONB NOT NULL (complete analysis)
parsed_resume         JSONB NOT NULL
parsed_jd             JSONB NOT NULL
narrative_status      VARCHAR(20) -- pending, processing, ready, failed
ai_enhanced           BOOLEAN
processing_time_ms    INT
confidence_score      FLOAT (0.0-1.0)
```

**Constraints**:
```sql
CHECK (fit_score >= 0 AND fit_score <= 100)
CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1))
```

---

### 3. `analysis_artifacts` - Input Data Storage

**Purpose**: Store resume and JD files with deduplication.

**Key Features**:
- **Deduplication**: Same resume+JD reused across jobs
- **Access tracking**: Count how many times artifact is used
- **Expiration**: Auto-cleanup after 30 days
- **Caching**: Store parsed data to avoid re-parsing

**Critical Fields**:
```sql
id                  UUID PRIMARY KEY
resume_hash         VARCHAR(64) -- SHA-256 of resume content
jd_hash             VARCHAR(64) -- SHA-256 of JD content
resume_text         TEXT NOT NULL
jd_text             TEXT NOT NULL
parsed_resume_cache JSONB -- Cache parsed structure
parsed_jd_cache     JSONB
access_count        INT -- How many jobs used this
expires_at          TIMESTAMP -- For cleanup
```

**Storage Options**:
- **Default**: Store text directly in database
- **S3/Object Storage**: Store `resume_storage_path`, `resume_storage_bucket`

---

### 4. `job_metrics` - Performance Tracking

**Purpose**: Collect detailed metrics for monitoring and optimization.

**Metrics Collected**:
```sql
queue_wait_time_ms    INT -- Time in queue
parsing_time_ms       INT -- Resume + JD parsing
llm_time_ms           INT -- LLM inference
narrative_time_ms     INT -- AI enhancement
total_time_ms         INT -- End-to-end

llm_tokens_input      INT
llm_tokens_output     INT
llm_calls_count       INT
memory_peak_mb        INT

stage_timings         JSONB -- {"parse": 150, "analyze": 3000, ...}
```

**Analytics Queries**:
```sql
-- Average processing time by day
SELECT DATE(created_at), AVG(total_time_ms)
FROM job_metrics
GROUP BY DATE(created_at);

-- P95 latency
SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_time_ms)
FROM job_metrics
WHERE created_at > NOW() - INTERVAL '7 days';
```

---

## Queue Manager - Worker System

### Worker Architecture

**Single Worker**:
```python
QueueManager
├─ worker_id: "worker-abc123"
├─ max_concurrent_jobs: 3
├─ poll_interval: 2 seconds
├─ heartbeat_interval: 30 seconds
└─ worker_loop()
   ├─ get_next_job() -- SELECT FOR UPDATE SKIP LOCKED
   ├─ process_job()
   │  ├─ Load artifact
   │  ├─ Run analysis
   │  ├─ Validate result
   │  └─ Save to analysis_results
   ├─ update_heartbeat()
   └─ recover_stale_jobs() -- Every 5 minutes
```

**Multiple Workers** (Horizontal Scaling):
```
Worker-1 (server-1)  ─┐
Worker-2 (server-1)  ─┤
Worker-3 (server-2)  ─┼─→ PostgreSQL Queue
Worker-4 (server-2)  ─┤   (SELECT FOR UPDATE SKIP LOCKED)
Worker-5 (server-3)  ─┘
```

### Concurrency Safety

**PostgreSQL Row-Level Locking**:
```sql
SELECT * FROM analysis_jobs
WHERE status IN ('queued', 'retrying')
  AND (next_retry_at IS NULL OR next_retry_at <= NOW())
ORDER BY priority ASC, queued_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;  -- ← Critical for multi-worker safety
```

**How it works**:
1. Worker-1 locks row #123
2. Worker-2 tries to lock row #123 → **SKIPPED** (already locked)
3. Worker-2 gets row #124 instead
4. No duplicate processing!

### Retry Logic

**Exponential Backoff**:
```python
retry_delays = [60, 300, 900]  # 1min, 5min, 15min

# Attempt 1 fails → retry after 1 minute
# Attempt 2 fails → retry after 5 minutes
# Attempt 3 fails → retry after 15 minutes
# Attempt 4 fails → status='failed' (permanent)
```

**Retry Scenarios**:
- ✅ Ollama service temporarily down
- ✅ LLM timeout
- ✅ Network error
- ✅ Invalid JSON (with retry)
- ❌ Invalid resume format (fail immediately)

### Stale Job Recovery

**Problem**: Worker crashes mid-processing, job stuck in "processing" state.

**Solution**: Heartbeat monitoring
```python
# Worker updates heartbeat every 30 seconds
UPDATE analysis_jobs
SET worker_heartbeat = NOW()
WHERE id = current_job_id;

# Recovery process (every 5 minutes)
SELECT * FROM analysis_jobs
WHERE status = 'processing'
  AND worker_heartbeat < NOW() - INTERVAL '10 minutes';

# Requeue stale jobs
UPDATE analysis_jobs
SET status = 'retrying',
    retry_count = retry_count + 1,
    next_retry_at = NOW() + INTERVAL '1 minute',
    worker_id = NULL
WHERE id IN (stale_job_ids);
```

---

## API Endpoints

### Job Submission

**POST `/queue/submit`**
```json
{
  "resume_text": "...",
  "resume_filename": "john_doe.pdf",
  "job_description": "...",
  "candidate_id": 123,
  "priority": 5
}

Response:
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Analysis job submitted successfully"
}
```

### Job Status Polling

**GET `/queue/status/{job_id}`**
```json
{
  "job_id": "550e8400-...",
  "status": "processing",
  "progress_percent": 45,
  "processing_stage": "analyzing",
  "queue_position": null,
  "estimated_wait_seconds": null,
  "created_at": "2026-04-12T18:00:00Z",
  "started_at": "2026-04-12T18:00:30Z"
}
```

**Status Values**:
- `queued` - Waiting in queue
- `processing` - Currently being analyzed
- `completed` - Analysis finished, result available
- `failed` - Permanently failed (max retries exceeded)
- `retrying` - Failed but will retry
- `cancelled` - Manually cancelled

### Get Result

**GET `/queue/result/{job_id}`**
```json
{
  "job_id": "550e8400-...",
  "result_id": "660f9511-...",
  "fit_score": 85,
  "final_recommendation": "Strong Match",
  "risk_level": "Low",
  "processing_time_ms": 3245,
  "analysis": {
    "strengths": [...],
    "weaknesses": [...],
    "matched_skills": [...],
    ...
  },
  "parsed_resume": {...},
  "narrative_status": "ready",
  "ai_enhanced": true
}
```

### Queue Monitoring

**GET `/queue/stats`**
```json
{
  "tenant_id": 1,
  "status_counts": {
    "queued": 5,
    "processing": 2,
    "completed": 1234,
    "failed": 12,
    "retrying": 1
  },
  "queue_depth": 6,
  "avg_processing_time_ms": 3500,
  "success_rate_percent": 99.03,
  "jobs_last_24h": 87
}
```

**GET `/queue/metrics/performance?days=7`**
```json
{
  "period_days": 7,
  "daily_metrics": [
    {
      "date": "2026-04-12",
      "total_jobs": 45,
      "completed": 44,
      "failed": 1,
      "success_rate": 97.78,
      "avg_processing_time_ms": 3200
    },
    ...
  ]
}
```

---

## Deployment Guide

### Phase 1: Database Migration

```bash
# 1. Backup existing database
pg_dump -U aria -d aria_db > backup_before_queue_migration.sql

# 2. Run migration
cd app/backend
alembic upgrade head  # Runs migration 008

# 3. Verify tables created
psql -U aria -d aria_db -c "\dt analysis_*"
```

### Phase 2: Start Queue Worker

**Option A: Integrated with FastAPI**
```python
# In main.py
from services.queue_manager import start_queue_worker, stop_queue_worker

@app.on_event("startup")
async def startup():
    await start_queue_worker()

@app.on_event("shutdown")
async def shutdown():
    await stop_queue_worker()
```

**Option B: Standalone Worker Process**
```bash
# Run as separate process
python -m services.queue_worker

# Or with systemd
sudo systemctl start aria-queue-worker
```

### Phase 3: Update Frontend

```javascript
// Old: Synchronous analysis
const result = await analyzeResume(resume, jd);
showReport(result);

// New: Async with polling
const { job_id } = await submitAnalysisJob(resume, jd);

// Poll for completion
const pollStatus = setInterval(async () => {
  const status = await getJobStatus(job_id);
  
  updateProgress(status.progress_percent);
  
  if (status.status === 'completed') {
    clearInterval(pollStatus);
    const result = await getJobResult(job_id);
    showReport(result);
  } else if (status.status === 'failed') {
    clearInterval(pollStatus);
    showError(status.error_message);
  }
}, 2000);  // Poll every 2 seconds
```

### Phase 4: Migrate Existing Data

```sql
-- Migrate old screening_results to new system
INSERT INTO analysis_artifacts (
  tenant_id, resume_hash, jd_hash, resume_text, jd_text, ...
)
SELECT DISTINCT
  tenant_id,
  MD5(parsed_data::text),
  MD5(analysis_result::json->>'job_description'),
  ...
FROM screening_results
WHERE status = 'completed';

INSERT INTO analysis_results (
  tenant_id, fit_score, final_recommendation, analysis_data, ...
)
SELECT
  tenant_id,
  (analysis_result::json->>'fit_score')::int,
  analysis_result::json->>'final_recommendation',
  analysis_result::jsonb,
  ...
FROM screening_results
WHERE status = 'completed'
  AND (analysis_result::json->>'fit_score') IS NOT NULL;
```

---

## Monitoring & Observability

### Key Metrics to Track

**Queue Health**:
- Queue depth (jobs waiting)
- Average wait time
- Worker utilization
- Stale job count

**Performance**:
- P50, P95, P99 processing time
- Success rate
- Retry rate
- LLM token usage

**Alerts**:
```yaml
- name: Queue Depth High
  condition: queue_depth > 100
  action: Scale up workers

- name: High Failure Rate
  condition: failure_rate > 5%
  action: Alert ops team

- name: Stale Jobs Detected
  condition: stale_jobs > 0
  action: Investigate worker health
```

### Grafana Dashboard

```sql
-- Queue depth over time
SELECT
  time_bucket('5 minutes', created_at) AS time,
  COUNT(*) FILTER (WHERE status IN ('queued', 'retrying')) AS queue_depth
FROM analysis_jobs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY time
ORDER BY time;

-- Processing time percentiles
SELECT
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_time_ms) AS p50,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_time_ms) AS p95,
  PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_time_ms) AS p99
FROM job_metrics
WHERE created_at > NOW() - INTERVAL '1 hour';
```

---

## Scaling Strategies

### Vertical Scaling (Single Worker)

Increase `max_concurrent_jobs`:
```python
# .env
QUEUE_MAX_CONCURRENT=5  # Process 5 jobs simultaneously
```

**Limits**:
- CPU cores (LLM inference)
- Memory (model loading)
- Database connections

### Horizontal Scaling (Multiple Workers)

Deploy multiple worker instances:
```yaml
# docker-compose.yml
services:
  queue-worker-1:
    image: resume-backend:latest
    command: python -m services.queue_worker
    environment:
      QUEUE_MAX_CONCURRENT: 3
  
  queue-worker-2:
    image: resume-backend:latest
    command: python -m services.queue_worker
    environment:
      QUEUE_MAX_CONCURRENT: 3
```

**Benefits**:
- Linear scaling
- Fault tolerance
- Zero-downtime deployments

### Priority-Based Routing

```python
# Premium users get priority 1-2
if user.subscription_tier == 'premium':
    priority = 1
elif user.subscription_tier == 'pro':
    priority = 3
else:
    priority = 5  # Free tier

await queue_manager.enqueue_job(..., priority=priority)
```

---

## Cost Optimization

### Deduplication Savings

```sql
-- Check deduplication effectiveness
SELECT
  COUNT(DISTINCT input_hash) AS unique_analyses,
  COUNT(*) AS total_jobs,
  (1 - COUNT(DISTINCT input_hash)::float / COUNT(*)) * 100 AS dedup_rate_percent
FROM analysis_jobs;

-- Example: 1000 jobs, 800 unique → 20% deduplication
-- Savings: 200 LLM calls avoided
```

### Artifact Reuse

```sql
-- Track artifact reuse
SELECT
  access_count,
  COUNT(*) AS artifacts
FROM analysis_artifacts
GROUP BY access_count
ORDER BY access_count DESC;

-- Cleanup old artifacts
DELETE FROM analysis_artifacts
WHERE expires_at < NOW()
  AND access_count = 1;  -- Only used once
```

---

## Troubleshooting

### Jobs Stuck in "processing"

**Symptom**: Jobs never complete, status stays "processing".

**Diagnosis**:
```sql
SELECT id, worker_id, started_at, worker_heartbeat
FROM analysis_jobs
WHERE status = 'processing'
  AND worker_heartbeat < NOW() - INTERVAL '10 minutes';
```

**Fix**: Stale job recovery will automatically requeue them.

### High Failure Rate

**Symptom**: Many jobs failing with same error.

**Diagnosis**:
```sql
SELECT error_type, error_message, COUNT(*)
FROM analysis_jobs
WHERE status = 'failed'
  AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY error_type, error_message
ORDER BY COUNT(*) DESC;
```

**Common Causes**:
- Ollama service down
- LLM model not loaded
- Invalid JD format
- Database connection pool exhausted

### Queue Depth Growing

**Symptom**: Queue depth increasing, jobs not being processed fast enough.

**Diagnosis**:
```sql
SELECT
  COUNT(*) AS queued_jobs,
  MIN(queued_at) AS oldest_job,
  EXTRACT(EPOCH FROM (NOW() - MIN(queued_at))) AS wait_seconds
FROM analysis_jobs
WHERE status = 'queued';
```

**Solutions**:
1. Scale up workers (horizontal)
2. Increase `max_concurrent_jobs` (vertical)
3. Optimize LLM inference time
4. Add more database connections

---

## Migration Checklist

- [ ] Backup production database
- [ ] Run migration 008 in staging
- [ ] Test queue worker in staging
- [ ] Update frontend to use queue API
- [ ] Deploy queue worker to production
- [ ] Monitor queue depth and processing time
- [ ] Migrate existing screening_results data
- [ ] Deprecate old analyze endpoint
- [ ] Update documentation
- [ ] Train team on new monitoring dashboards

---

## Summary

This queue-based architecture provides:

✅ **Reliability**: Automatic retries, stale job recovery
✅ **Scalability**: Horizontal scaling with multiple workers
✅ **Data Integrity**: No incomplete records in production
✅ **Observability**: Comprehensive metrics and monitoring
✅ **Performance**: Priority scheduling, deduplication
✅ **Cost Efficiency**: Artifact reuse, smart caching

**Key Improvement**: Zero incomplete "pending" records in the database. All data in `analysis_results` is complete and validated.
