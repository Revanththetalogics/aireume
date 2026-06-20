#!/bin/sh
set -e

# Apply DB migrations when using PostgreSQL (production). Idempotent: safe on every start.
case "${DATABASE_URL:-}" in
  postgresql*|postgres://*)
    echo "[entrypoint] Creating base tables (if not exist)..."
    cd /app && python -c "from app.backend.db.database import Base, engine; import app.backend.models.db_models; Base.metadata.create_all(bind=engine)"
    echo "[entrypoint] Running Alembic migrations..."
    cd /app && alembic -c alembic.ini upgrade heads
    echo "[entrypoint] Migrations complete."
    ;;
  *)
    echo "[entrypoint] Skipping Alembic (not a PostgreSQL DATABASE_URL)."
    ;;
esac

if [ -f /app/wait_for_ollama.py ]; then
  python /app/wait_for_ollama.py
fi
exec "$@"
