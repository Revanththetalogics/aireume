# ARIA operations runbook

## Production process layout

- **API**: `uvicorn app.backend.main:app --workers 6` with `RUN_BACKGROUND_WORKERS=0`
- **Worker**: `python -m app.backend.worker` with `RUN_BACKGROUND_WORKERS=1`
- **Redis**: required (`REDIS_URL`) for rate limits, feature flags, scoring cache. LiveKit uses Redis DB 1 on the same instance (`LIVEKIT_REDIS_ADDRESS=redis:6379`).
- **Object storage**: `S3_ENDPOINT` + `S3_BUCKET` required. Production does **not** fall back to database BYTEA.
- **ClamAV**: `clamav/clamav` service in `docker-compose.prod.yml`. `CLAMAV_REQUIRED=1` and `CLAMAV_HOST=clamav`. Uploads fail closed until ClamAV is accepting connections (first start can take several minutes while virus definitions download).
- **LiveKit**: no `devkey` defaults; set `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET`. Redis hostname is `redis`, not `livekit-redis`.

## Health

- Public liveness: `GET /health` (includes a cheap DB ping)
- Dependency check: `GET /api/health`
- Deep diagnostics (`/api/health/deep`, `/api/llm-status`, `/metrics`) require `X-Metrics-Token` or `X-Internal-Service-Secret` in production

## If Redis is down

- Rate limiting returns **503** (fail closed). Do not scale API workers as a workaround.
- Restore Redis, then confirm `redis-cli -a $REDIS_PASSWORD ping`.
- Feature flags and scoring cache will miss until Redis is back; they are not a substitute for rate limits.

## If ClamAV is down or still warming

- File ingress fails closed while `CLAMAV_REQUIRED=1`.
- Check `docker logs resume-screener-clamav`. Fresh nodes often need 2–5 minutes for `freshclam`.
- Do **not** set `CLAMAV_REQUIRED=0` in production to “unblock uploads” unless you have accepted that malware scanning is off and documented it for the customer.

## If S3 / MinIO is down

- Analyze/upload returns **503**. Files are not written into Postgres.
- Restore the bucket, then retry the upload. No BYTEA recovery path in production.

## If LiveKit / voice will not start

- Confirm `LIVEKIT_REDIS_ADDRESS=redis:6379` and `LIVEKIT_REDIS_PASSWORD` matches `REDIS_PASSWORD`.
- Confirm Redis is healthy. LiveKit uses logical DB **1** so it does not collide with app keys on DB 0.

## Restore (Postgres)

1. Stop API and worker: `docker stop resume-screener-backend resume-screener-worker`
2. Restore the `postgres_data` volume (or `pg_restore` into `POSTGRES_DB`)
3. Start Postgres, wait for healthy, then start worker and API
4. Hit `GET /api/health`

## Background jobs (worker)

- Queue processing and stale-job recovery
- Dunning retries, trial expiry, scheduled reports
- GDPR expired-data cleanup every 6 hours

## Incident checks

1. Worker logs: `docker logs resume-screener-worker`
2. Redis: `redis-cli -a $REDIS_PASSWORD ping`
3. ClamAV: `docker logs resume-screener-clamav`
4. DLQ depth: admin queue / dead-letter tables
5. Sentry (API: `SENTRY_DSN`; frontend: `VITE_SENTRY_DSN`)
