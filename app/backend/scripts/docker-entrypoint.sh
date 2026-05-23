#!/bin/sh
set -e

# Apply DB migrations when using PostgreSQL (production). Idempotent: safe on every start.
case "${DATABASE_URL:-}" in
  postgresql*|postgres://*)
    echo "[entrypoint] Running Alembic migrations..."
    cd /app && alembic -c alembic.ini upgrade head
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
