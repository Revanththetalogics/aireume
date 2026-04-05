#!/bin/sh
set -e
if [ -f /app/wait_for_ollama.py ]; then
  python /app/wait_for_ollama.py
fi
exec "$@"
