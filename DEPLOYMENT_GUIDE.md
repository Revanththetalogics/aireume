# Intelligent Scoring Weights System - Deployment Guide

## Quick Start

This guide walks you through deploying the intelligent scoring weights system to production.

## Pre-Deployment Checklist

### Backend Verification
- All backend files created and reviewed
- Database migration file exists
- Weight mapper service created
- Weight suggester service created
- Pipeline updates applied
- API routes updated

### Frontend Verification
- All frontend components created
- WeightSuggestionPanel.jsx exists
- UniversalWeightsPanel.jsx exists
- VersionHistory.jsx exists
- ReanalyzeModal.jsx exists
- ComparisonView.jsx exists
- UploadForm.jsx updated

## Step 1: Database Migration

### Backup Current Database

```bash
pg_dump -U your_user -d resume_ai > backup.sql
```

### Run Migration

```bash
cd /path/to/project
alembic upgrade head
```

### Verify Migration

```bash
psql -U your_user -d resume_ai
\d screening_results
\q
```

## Step 2: Backend Deployment

### Docker Deployment

```bash
docker-compose -f docker-compose.prod.yml build backend
docker-compose -f docker-compose.prod.yml up -d backend
docker-compose -f docker-compose.prod.yml logs -f backend
```

## Step 3: Frontend Deployment

### Build Frontend

```bash
cd app/frontend
npm install
npm run build
```

### Deploy Static Files

```bash
cp -r dist/* /var/www/html/
```

## Step 4: Testing

### Test Weight Suggestion Endpoint

```bash
curl -X POST http://localhost:8000/api/analyze/suggest-weights \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "job_description=Senior Backend Engineer with 8+ years experience..."
```

### Test Analysis with New Weights

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "resume=@test_resume.pdf" \
  -F "job_description=..." \
  -F "scoring_weights={\"core_competencies\":0.30,...}"
```

## Step 5: Monitoring

### Check Logs

```bash
tail -f /var/log/backend.log
```

### Monitor Database

```sql
SELECT COUNT(*) FROM screening_results WHERE version_number > 1;
SELECT role_category, COUNT(*) FROM screening_results GROUP BY role_category;
```

## Rollback Plan

If issues occur:

```bash
alembic downgrade -1
docker-compose -f docker-compose.prod.yml restart backend
```

## AI Recruiter Feature

### Prerequisites
- No new services required — uses existing voice-agent, speech-service, and LiveKit infrastructure
- Requires migration 045 (auto-applied on backend startup via Alembic)

### Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `RECRUITER_INTERVIEW_ENABLED` | `true` | Feature flag to enable/disable AI Recruiter |

### Enabling/Disabling
Set `RECRUITER_INTERVIEW_ENABLED=false` in your environment to disable the feature entirely (all recruiter endpoints will return 404).

### Auto-Trigger Setup
Configure via the UI at `/recruiter-interviews` → Configuration tab, or via API:
```
PUT /api/recruiter/config
{
  "enabled": true,
  "trigger_pipeline_stage": "in_review",
  "min_fit_score_threshold": 40,
  "max_fit_score_threshold": 85
}
```

### Troubleshooting
- If interviews stay in "pending_strategy": Check Ollama connectivity (LLM generates strategy)
- If interviews never complete: Check voice-agent logs and backend `/api/internal/recruiter/complete` endpoint
- If scorecard not generated: Check backend logs for "aria.recruiter" logger entries

## Support

For issues, check:
- Backend logs
- Database migration status
- LLM service availability
- Frontend console errors
